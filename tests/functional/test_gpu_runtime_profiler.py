"""
文件用途：验证 GPU runtime profiler 在无 GPU 与 stop-file 场景下的行为。
File purpose: Validate GPU runtime profiler behavior under no-GPU and stop-file scenarios.
Module type: Functional test module
"""

from __future__ import annotations

import csv
import json
import subprocess
import threading
import time
from pathlib import Path

import pytest

from paper_workflow.notebook_utils import runtime_profile_workflow
import scripts.profile_runtime.profile_gpu_runtime as gpu_profile_module
from scripts.profile_runtime.summarize_gpu_profile import summarize_gpu_runtime_profile
from scripts.profile_runtime.summarize_run_timing import summarize_run_timing


pytestmark = pytest.mark.quick


def test_gpu_runtime_profiler_writes_unavailable_trace_without_nvidia_smi(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the profiler emits a valid unavailable trace without nvidia-smi.

    Args:
        tmp_path: Temporary run root.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    output_csv = run_root / "runtime_profile" / "gpu_runtime_trace.csv"
    stop_file = run_root / "runtime_profile" / "gpu_profile_stop.flag"
    output_json = run_root / "runtime_profile" / "gpu_runtime_summary.json"
    output_md = run_root / "runtime_profile" / "gpu_runtime_report.md"

    monkeypatch.setattr(gpu_profile_module.shutil, "which", lambda command_name: None)

    payload = gpu_profile_module.profile_gpu_runtime(
        run_root=run_root,
        interval_seconds=0.01,
        output_csv=output_csv,
        stop_file=stop_file,
    )
    summary = summarize_gpu_runtime_profile(
        run_root=run_root,
        trace_csv=output_csv,
        output_json=output_json,
        output_md=output_md,
    )

    rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))
    assert payload["status"] is True
    assert payload["trace_available"] is True
    assert payload["nvidia_smi_available"] is False
    assert len(rows) == 1
    assert rows[0]["gpu_name"] == "unavailable"
    assert summary["trace_available"] is True
    assert summary["usable_sample_count"] == 0
    assert summary["unavailable_sample_count"] == 1
    assert summary["profiling_status"] == "unavailable"
    assert summary["profiling_failure_reason"] == "gpu_runtime_samples_unavailable"
    assert summary["gpu_name"] == "unavailable"
    assert output_json.exists()
    assert output_md.exists()
    assert (run_root / "runtime_profile").exists()


def test_gpu_runtime_profiler_stop_file_terminates_sampling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the stop-file mechanism terminates the sampling loop.

    Args:
        tmp_path: Temporary run root.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    output_csv = run_root / "runtime_profile" / "gpu_runtime_trace.csv"
    stop_file = run_root / "runtime_profile" / "gpu_profile_stop.flag"
    event_tag_file = run_root / "runtime_profile" / "current_runtime_event_tag.txt"
    event_tag_file.parent.mkdir(parents=True, exist_ok=True)
    event_tag_file.write_text("runner\n", encoding="utf-8")

    def fake_which(command_name: str) -> str | None:
        if command_name == "nvidia-smi":
            return "/usr/bin/nvidia-smi"
        return None

    def fake_check_output(command: list[str], **_: object) -> str:
        assert command[0] == "/usr/bin/nvidia-smi"
        return "0, Fake GPU, 35, 4096, 8192, 120, 60\n"

    monkeypatch.setattr(gpu_profile_module.shutil, "which", fake_which)
    monkeypatch.setattr(gpu_profile_module.subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(gpu_profile_module, "_probe_cpu_and_ram", lambda: (12.5, 3.0, 16.0))

    thread = threading.Thread(
        target=gpu_profile_module.profile_gpu_runtime,
        kwargs={
            "run_root": run_root,
            "interval_seconds": 0.01,
            "output_csv": output_csv,
            "stop_file": stop_file,
            "current_event_tag_file": event_tag_file,
        },
        daemon=True,
    )
    thread.start()
    time.sleep(0.05)
    stop_file.write_text("stop\n", encoding="utf-8")
    thread.join(timeout=1.0)

    rows = list(csv.DictReader(output_csv.open("r", encoding="utf-8", newline="")))
    assert thread.is_alive() is False
    assert len(rows) >= 1
    assert all(row["event_tag"] == "runner" for row in rows)


def test_runtime_profile_workflow_records_start_warning_when_profiler_launch_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate notebook helper persists a warning when profiler startup fails.

    Args:
        tmp_path: Temporary run root.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"

    def _raise_on_popen(*_: object, **__: object) -> subprocess.Popen[str]:
        raise OSError("simulated startup failure")

    monkeypatch.setattr(runtime_profile_workflow.subprocess, "Popen", _raise_on_popen)

    process = runtime_profile_workflow.start_gpu_runtime_profile(run_root=run_root, interval_seconds=3)
    session_path = run_root / "runtime_profile" / "gpu_runtime_profiler_session.json"
    payload = json.loads(session_path.read_text(encoding="utf-8"))

    assert process is None
    assert payload["status"] is False
    assert payload["process_started"] is False
    assert payload["warning_count"] == 1
    assert payload["warnings"][0]["warning_type"] == "gpu_runtime_profiler_start_failed"
    assert "simulated startup failure" in payload["error_message"]


def test_runtime_profile_workflow_records_warnings_for_forced_profiler_shutdown(
    tmp_path: Path,
) -> None:
    """Validate notebook helper records warnings when stop must terminate and kill the profiler.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    session_path = run_root / "runtime_profile" / "gpu_runtime_profiler_session.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(
        json.dumps(
            {
                "status": True,
                "process_started": True,
                "warnings": [],
                "warning_count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeProcess:
        def __init__(self) -> None:
            self.args = ["python", "-m", "scripts.profile_runtime.profile_gpu_runtime"]
            self.pid = 4321
            self._wait_calls = 0

        def wait(self, timeout: float) -> int | None:
            self._wait_calls += 1
            if self._wait_calls < 3:
                raise subprocess.TimeoutExpired(cmd="fake_gpu_profiler", timeout=timeout)
            return 0

        def terminate(self) -> None:
            return None

        def kill(self) -> None:
            return None

    runtime_profile_workflow.stop_gpu_runtime_profile(FakeProcess(), run_root=run_root)
    payload = json.loads(session_path.read_text(encoding="utf-8"))

    assert (run_root / "runtime_profile" / "gpu_profile_stop.flag").exists()
    assert payload["forced_termination"] is True
    assert payload["forced_kill"] is True
    assert payload["warning_count"] == 2
    assert payload["warnings"][0]["warning_type"] == "gpu_runtime_profiler_force_terminate"
    assert payload["warnings"][1]["warning_type"] == "gpu_runtime_profiler_force_kill"


def test_runtime_profile_workflow_writes_skipped_gpu_audit_record_without_trace(
    tmp_path: Path,
) -> None:
    """Validate a skipped GPU audit record is still persisted without trace output.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"

    payload = runtime_profile_workflow.write_gpu_runtime_audit_record(
        run_root=run_root,
        profiling_mode="notebook_setup_only",
        profiling_expected=False,
    )
    audit_path = run_root / "runtime_profile" / "gpu_runtime_audit_record.json"

    assert audit_path.exists()
    assert payload["record_status"] == "skipped"
    assert payload["profiling_status"] == "not_sampled"
    assert payload["skip_reason"] == "gpu_runtime_profile_not_requested"
    assert payload["trace_exists"] is False
    assert payload["summary_exists"] is False
    assert payload["gpu_runtime_summary"] is None


def test_runtime_profile_workflow_writes_available_gpu_audit_record_from_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate GPU audit record materializes summary payload when trace exists.

    Args:
        tmp_path: Temporary run root.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    stop_file = run_root / "runtime_profile" / "gpu_profile_stop.flag"
    trace_path = run_root / "runtime_profile" / "gpu_runtime_trace.csv"

    monkeypatch.setattr(gpu_profile_module.shutil, "which", lambda command_name: None)
    gpu_profile_module.profile_gpu_runtime(
        run_root=run_root,
        interval_seconds=0.01,
        output_csv=trace_path,
        stop_file=stop_file,
    )

    payload = runtime_profile_workflow.write_gpu_runtime_audit_record(
        run_root=run_root,
        profiling_mode="stage2_mechanism_calibration",
        profiling_expected=True,
    )
    audit_path = run_root / "runtime_profile" / "gpu_runtime_audit_record.json"
    summary_path = run_root / "runtime_profile" / "gpu_runtime_summary.json"

    assert audit_path.exists()
    assert summary_path.exists()
    assert payload["record_status"] == "available"
    assert payload["profiling_status"] == "unavailable"
    assert payload["profiling_failure_reason"] == "gpu_runtime_samples_unavailable"
    assert payload["skip_reason"] is None
    assert payload["trace_exists"] is True
    assert payload["summary_exists"] is True
    assert isinstance(payload["gpu_runtime_summary"], dict)
    assert payload["gpu_runtime_summary"]["trace_available"] is True
    assert payload["gpu_runtime_summary"]["usable_sample_count"] == 0


def test_runtime_profile_workflow_lightweight_gpu_profile_writes_sampled_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """验证轻量 GPU profiling 补救路径可以直接写出可汇总的 trace。"""
    run_root = tmp_path / "run_root"

    def fake_which(command_name: str) -> str | None:
        if command_name == "nvidia-smi":
            return "/usr/bin/nvidia-smi"
        return None

    def fake_check_output(command: list[str], **_: object) -> str:
        assert command[0] == "/usr/bin/nvidia-smi"
        return "0, Fake GPU, 72, 4096, 8192, 120, 60\n"

    monkeypatch.setattr(gpu_profile_module.shutil, "which", fake_which)
    monkeypatch.setattr(gpu_profile_module.subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(
        runtime_profile_workflow,
        "_run_lightweight_cuda_workload",
        lambda duration_seconds: {
            "status": True,
            "workload_executed": True,
            "iteration_count": 1,
        },
    )

    payload = runtime_profile_workflow.run_lightweight_gpu_runtime_profile(
        run_root=run_root,
        interval_seconds=0.01,
        duration_seconds=0.05,
        event_tag="unit_lightweight_gpu_profile",
    )

    trace_path = run_root / "runtime_profile" / "gpu_runtime_trace.csv"
    summary_path = run_root / "runtime_profile" / "gpu_runtime_summary.json"
    smoke_summary_path = (
        run_root / "runtime_profile" / "gpu_runtime_lightweight_profile_summary.json"
    )
    assert trace_path.exists()
    assert summary_path.exists()
    assert smoke_summary_path.exists()
    assert payload["status"] is True
    assert payload["gpu_runtime_summary"]["profiling_status"] == "sampled"
    assert payload["gpu_runtime_summary"]["usable_sample_count"] >= 1
    assert payload["workload_summary"]["workload_executed"] is True


def test_runtime_profile_workflow_loads_governed_profile_config() -> None:
    """Validate the notebook helper loads a governed runtime-profile config.

    Args:
        None.

    Returns:
        None.
    """
    payload = runtime_profile_workflow.load_runtime_profile_config(
        runtime_profile="l4_formal",
    )

    assert payload["runtime_profile"] == "l4_formal"
    assert payload["gpu_target"] == "L4"
    assert payload["batch_size_frames"] == 128
    assert payload["vae_batch_size_frames"] == 128
    assert payload["profile_runtime"] is True
    assert payload["config_path"].endswith("configs\\runtime_profiles\\l4_formal.json")
    assert len(payload["config_digest"]) == 64


def test_run_timing_summary_reports_runner_substage_totals(tmp_path: Path) -> None:
    """Validate runner substage timing events are summarized for performance audit.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"
    events_path = runtime_profile_dir / "run_timing_events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "run_id": "run_root",
            "event_name": "runner_cross_event_decode_video",
            "event_group": "runner_substage",
            "elapsed_seconds": 1.0,
            "status": "ok",
            "metadata": {"event_group": "runner_substage", "invocation_count": 1},
        },
        {
            "run_id": "run_root",
            "event_name": "runner_attack_materialization",
            "event_group": "runner_substage",
            "elapsed_seconds": 3.0,
            "status": "ok",
            "metadata": {"event_group": "runner_substage", "invocation_count": 2},
        },
        {
            "run_id": "run_root",
            "event_name": "runner_cross_event_reencode_latent",
            "event_group": "runner_substage",
            "elapsed_seconds": 6.0,
            "status": "ok",
            "metadata": {"event_group": "runner_substage", "invocation_count": 3},
        },
        {
            "run_id": "run_root",
            "event_name": "runner_reencode_latent",
            "event_group": "runner_substage",
            "elapsed_seconds": 5.0,
            "status": "ok",
            "metadata": {"event_group": "runner_substage", "invocation_count": 4},
        },
        {
            "run_id": "run_root",
            "event_name": "runner_quality_metrics",
            "event_group": "runner_substage",
            "elapsed_seconds": 7.0,
            "status": "ok",
            "metadata": {"event_group": "runner_substage", "invocation_count": 4},
        },
    ]
    events_path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )

    summary = summarize_run_timing(
        run_root=run_root,
        events_jsonl=events_path,
        output_json=runtime_profile_dir / "run_timing_summary.json",
        output_md=runtime_profile_dir / "run_timing_report.md",
    )

    assert summary["decode_video_seconds"] == 1.0
    assert summary["video_attack_seconds"] == 3.0
    assert summary["vae_reencode_seconds"] == 11.0
    assert summary["quality_metrics_seconds"] == 7.0
    assert summary["events_by_group"]["runner_substage"] == 22.0
    assert summary["event_counts_by_group"]["runner_substage"] == 5
    assert summary["runner_preparation_seconds"] == 0.0
    assert summary["threshold_calibration_seconds"] == 0.0
    assert summary["record_persistence_seconds"] == 0.0
    assert summary["top_timing_events"][0]["event_name"] == "runner_quality_metrics"
    assert summary["top_timing_events"][0]["elapsed_seconds"] == 7.0
    assert summary["runner_substage_counts"]["runner_reencode_latent"] == 4
    assert summary["runner_substage_counts"]["runner_cross_event_reencode_latent"] == 3


def test_runtime_profile_workflow_persists_profile_plan(tmp_path: Path) -> None:
    """Validate runtime-profile config loading persists a profile plan under run_root.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    payload = runtime_profile_workflow.load_runtime_profile_config(
        runtime_profile="a100_80g_formal",
        run_root=run_root,
    )
    plan_path = run_root / "runtime_profile" / "runtime_profile_plan.json"
    persisted_payload = json.loads(plan_path.read_text(encoding="utf-8"))

    assert plan_path.exists()
    assert persisted_payload["runtime_profile"] == "a100_80g_formal"
    assert persisted_payload["batch_size_frames"] == 256
    assert persisted_payload["config_digest"] == payload["config_digest"]


def test_runtime_profile_workflow_rejects_semantic_override_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate runtime-profile configs reject semantic override keys.

    Args:
        tmp_path: Temporary config root.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        None.
    """
    config_root = tmp_path / "configs" / "runtime_profiles"
    config_root.mkdir(parents=True, exist_ok=True)
    invalid_config_path = config_root / "l4_invalid.json"
    invalid_config_path.write_text(
        json.dumps(
            {
                "runtime_profile": "l4_invalid",
                "gpu_target": "L4",
                "device": "cuda",
                "vae_dtype": "float16",
                "vae_batch_size_frames": 8,
                "target_fpr_override": 0.001,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        runtime_profile_workflow,
        "_runtime_profile_config_root",
        lambda: config_root,
    )

    with pytest.raises(ValueError, match="forbidden semantic keys"):
        runtime_profile_workflow.load_runtime_profile_config(
            runtime_profile="l4_invalid",
        )

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

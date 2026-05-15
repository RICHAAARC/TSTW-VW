"""
文件用途：验证阶段 2 notebook workflow helper 的 manifest handoff 与 session model 语义。
File purpose: Validate dataset-manifest handoff and session-model semantics for the stage-two notebook workflow helpers.
Module type: General module
"""

from __future__ import annotations

import os
import json
import shutil
from io import StringIO
from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

import paper_workflow.notebook_utils.real_video_vae_latent_probe_workflow as workflow_module

from paper_workflow.notebook_utils.real_video_vae_latent_probe_workflow import (
    merge_probe_method_shard_outputs,
    prepare_probe_runtime_workspace,
    run_probe_stage2_mechanism_calibration,
    run_probe_method_shards,
    run_probe_runner,
    write_probe_runtime_config,
)
from scripts.prepare_models.prepare_session_autoencoder_kl import (
    prepare_session_autoencoder_kl,
)


@pytest.mark.unit
def test_write_probe_runtime_config_persists_dataset_manifest_path(tmp_path: Path) -> None:
    """Validate notebook runtime config records the processed dataset manifest path.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    local_dataset_root = tmp_path / "runtime" / "datasets" / "probe"
    processed_dataset_root = tmp_path / "drive" / "processed" / "probe"
    local_model_root = tmp_path / "runtime" / "models" / "autoencoder_kl"
    dataset_manifest_path = local_dataset_root / "dataset_manifest.json"
    runtime_config_path = tmp_path / "runtime_config.json"

    local_dataset_root.mkdir(parents=True, exist_ok=True)
    processed_dataset_root.mkdir(parents=True, exist_ok=True)
    local_model_root.mkdir(parents=True, exist_ok=True)
    dataset_manifest_path.write_text("{}\n", encoding="utf-8")

    handoff = write_probe_runtime_config(
        runtime_config_path=runtime_config_path,
        execution_environment="colab",
        processed_dataset_key="real_video_probe",
        local_dataset_root=local_dataset_root,
        processed_dataset_root=processed_dataset_root,
        vae_model_local_path=local_model_root,
        dataset_manifest_path=dataset_manifest_path,
        require_formal_pass_criteria=True,
    )

    payload = json.loads(runtime_config_path.read_text(encoding="utf-8"))
    assert handoff["runtime_config"]["dataset_manifest_path"] == str(dataset_manifest_path)
    assert payload["dataset_manifest_path"] == str(dataset_manifest_path)
    assert payload["local_dataset_root"] == str(local_dataset_root)


@pytest.mark.unit
def test_write_probe_runtime_config_preserves_batch_size_frames_extra_config(tmp_path: Path) -> None:
    """Validate runtime config keeps batch_size_frames as a notebook-visible tuning knob.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    local_dataset_root = tmp_path / "runtime" / "datasets" / "probe"
    processed_dataset_root = tmp_path / "drive" / "processed" / "probe"
    local_model_root = tmp_path / "runtime" / "models" / "autoencoder_kl"
    dataset_manifest_path = local_dataset_root / "dataset_manifest.json"
    runtime_config_path = tmp_path / "runtime_config.json"

    local_dataset_root.mkdir(parents=True, exist_ok=True)
    processed_dataset_root.mkdir(parents=True, exist_ok=True)
    local_model_root.mkdir(parents=True, exist_ok=True)
    dataset_manifest_path.write_text("{}\n", encoding="utf-8")

    write_probe_runtime_config(
        runtime_config_path=runtime_config_path,
        execution_environment="colab",
        processed_dataset_key="real_video_probe",
        local_dataset_root=local_dataset_root,
        processed_dataset_root=processed_dataset_root,
        vae_model_local_path=local_model_root,
        dataset_manifest_path=dataset_manifest_path,
        require_formal_pass_criteria=True,
        extra_config={"batch_size_frames": 16},
    )

    payload = json.loads(runtime_config_path.read_text(encoding="utf-8"))
    assert payload["batch_size_frames"] == 16


@pytest.mark.unit
def test_prepare_probe_runtime_workspace_falls_back_to_processed_dataset_when_copy_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate copy failures fall back to the verified processed dataset root.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    processed_dataset_root = tmp_path / "drive" / "processed" / "probe"
    local_dataset_root = tmp_path / "runtime" / "datasets" / "probe"
    family_root = tmp_path / "drive" / "results" / "family"
    run_root = tmp_path / "runtime" / "runs" / "probe"
    source_root = processed_dataset_root / "source"
    source_root.mkdir(parents=True, exist_ok=True)
    source_video_path = source_root / "sample.mp4"
    source_video_path.write_bytes(b"video-bytes")
    (processed_dataset_root / "dataset_manifest.json").write_text(
        json.dumps(
            {
                "dataset_name": "probe",
                "dataset_version": "test",
                "samples": [
                    {
                        "video_source_id": "sample_001",
                        "split": "dev",
                        "relpath": "source/sample.mp4",
                    },
                    {
                        "video_source_id": "sample_002",
                        "split": "calibration",
                        "relpath": "source/sample.mp4",
                    },
                    {
                        "video_source_id": "sample_003",
                        "split": "test",
                        "relpath": "source/sample.mp4",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def _failing_copytree(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise shutil.Error([("src", "dst", "transport endpoint is not connected")])

    monkeypatch.setattr(workflow_module.shutil, "copytree", _failing_copytree)

    handoff = prepare_probe_runtime_workspace(
        processed_dataset_root=processed_dataset_root,
        local_dataset_root=local_dataset_root,
        family_root=family_root,
        run_root=run_root,
        copy_processed_dataset=True,
    )

    assert handoff["local_dataset_root"] == str(processed_dataset_root)
    assert handoff["requested_local_dataset_root"] == str(local_dataset_root)
    assert handoff["local_dataset_manifest_path"] == str(
        processed_dataset_root / "dataset_manifest.json"
    )
    assert handoff["dataset_source_mode"] == "processed_dataset_in_place_fallback"
    assert "transport endpoint is not connected" in str(handoff["dataset_copy_error"])
    assert handoff["local_dataset_ready"] is True


@pytest.mark.unit
def test_prepare_probe_runtime_workspace_preserves_build_aligned_drive_root(
    tmp_path: Path,
) -> None:
    """Validate run workspace preparation keeps the build-aligned Drive root unchanged.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    drive_root = tmp_path / "content" / "drive" / "MyDrive"
    processed_dataset_root = drive_root / "TSTW" / "datasets" / "processed" / "probe"
    family_root = drive_root / "TSTW" / "results" / "families" / "family_001"
    local_dataset_root = tmp_path / "runtime" / "datasets" / "probe"
    run_root = tmp_path / "runtime" / "runs" / "probe"

    source_root = processed_dataset_root / "source"
    source_root.mkdir(parents=True, exist_ok=True)
    (source_root / "sample.mp4").write_bytes(b"video-bytes")
    (processed_dataset_root / "dataset_manifest.json").write_text(
        json.dumps(
            {
                "dataset_name": "probe",
                "dataset_version": "test",
                "samples": [
                    {
                        "video_source_id": "sample_001",
                        "split": "dev",
                        "relpath": "source/sample.mp4",
                    },
                    {
                        "video_source_id": "sample_002",
                        "split": "calibration",
                        "relpath": "source/sample.mp4",
                    },
                    {
                        "video_source_id": "sample_003",
                        "split": "test",
                        "relpath": "source/sample.mp4",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    handoff = prepare_probe_runtime_workspace(
        processed_dataset_root=processed_dataset_root,
        local_dataset_root=local_dataset_root,
        family_root=family_root,
        run_root=run_root,
        copy_processed_dataset=False,
    )

    assert handoff["processed_dataset_root"] == str(processed_dataset_root)
    assert handoff["local_dataset_root"] == str(processed_dataset_root)
    assert handoff["local_dataset_manifest_path"] == str(
        processed_dataset_root / "dataset_manifest.json"
    )
    assert handoff["family_root"] == str(family_root)
    assert handoff["dataset_source_mode"] == "processed_dataset_in_place"


@pytest.mark.unit
def test_prepare_session_autoencoder_kl_copies_local_model_into_session_root(
    tmp_path: Path,
) -> None:
    """Validate local model directories are copied into the session-local runtime root.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    source_model_root = tmp_path / "drive_models" / "vae"
    session_model_root = tmp_path / "runtime" / "session_models" / "autoencoder_kl"
    session_manifest_path = tmp_path / "session_model_manifest.json"

    source_model_root.mkdir(parents=True, exist_ok=True)
    (source_model_root / "config.json").write_text(
        json.dumps({"scaling_factor": 0.18215}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (source_model_root / "weights.bin").write_bytes(b"stage2-vae")

    manifest_payload = prepare_session_autoencoder_kl(
        model_id=str(source_model_root),
        local_model_root=session_model_root,
        session_manifest_path=session_manifest_path,
    )

    model_entry = manifest_payload["models"][0]
    assert model_entry["source_kind"] == "local_path_copied_to_session"
    assert Path(model_entry["local_path"]) == session_model_root.resolve()
    assert (session_model_root / "config.json").exists()
    assert (session_model_root / "weights.bin").exists()
    assert json.loads(session_manifest_path.read_text(encoding="utf-8"))["models"][0][
        "local_path"
    ] == str(session_model_root.resolve())


@pytest.mark.unit
def test_run_probe_runner_forwards_dataset_manifest_to_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the notebook workflow forwards the processed dataset manifest to the runner CLI.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    captured_call: dict[str, object] = {}

    class _FakeProcess:
        def __init__(self, command: list[str], **kwargs: object) -> None:
            captured_call["command"] = list(command)
            captured_call["kwargs"] = kwargs
            self.stdout = StringIO("runner ok\n")

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(workflow_module.subprocess, "Popen", _FakeProcess)
    dataset_manifest_path = tmp_path / "dataset_manifest.json"
    dataset_manifest_path.write_text("{}\n", encoding="utf-8")

    run_probe_runner(
        run_root=tmp_path / "run_root",
        run_mode="formal",
        runtime_profile="formal",
        runtime_config_path=tmp_path / "runtime_config.json",
        dataset_manifest=dataset_manifest_path,
        batch_size_frames=16,
        python_executable="python",
    )

    command = captured_call["command"]
    kwargs = captured_call["kwargs"]
    repository_root = Path(workflow_module.__file__).resolve().parents[2]
    assert "--dataset-manifest" in command
    assert str(dataset_manifest_path) in command
    assert "--batch-size-frames" in command
    assert "16" in command
    assert kwargs["cwd"] == repository_root
    assert kwargs["stdout"] == workflow_module.subprocess.PIPE
    assert kwargs["stderr"] == workflow_module.subprocess.STDOUT
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert kwargs["env"]["PYTHONPATH"].split(os.pathsep)[0] == str(repository_root)


@pytest.mark.unit
def test_run_probe_runner_surfaces_runner_output_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate notebook runner failures expose the child-process output.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """

    class _FailingProcess:
        def __init__(self, command: list[str], **kwargs: object) -> None:
            del command, kwargs
            self.stdout = StringIO("traceback line\nroot cause detail\n")

        def wait(self) -> int:
            return 1

    monkeypatch.setattr(workflow_module.subprocess, "Popen", _FailingProcess)

    with pytest.raises(RuntimeError, match="root cause detail") as exc_info:
        run_probe_runner(
            run_root=tmp_path / "run_root",
            run_mode="formal",
            runtime_profile="formal",
            runtime_config_path=tmp_path / "runtime_config.json",
            python_executable="python",
        )

    assert "run_probe_runner failed while executing the governed runner" in str(
        exc_info.value
    )


@pytest.mark.unit
def test_run_probe_method_shards_launches_governed_method_allowlists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate method shards split the formal variants into governed runner subprocesses.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    captured_commands: list[list[str]] = []
    merge_calls: dict[str, object] = {}

    class _FakeProcess:
        def __init__(self, command: list[str], **kwargs: object) -> None:
            del kwargs
            captured_commands.append(list(command))

        def communicate(self) -> tuple[str, None]:
            return ("runner ok\n", None)

        def wait(self) -> int:
            return 0

    monkeypatch.setattr(workflow_module.subprocess, "Popen", _FakeProcess)
    monkeypatch.setattr(
        workflow_module,
        "merge_probe_method_shard_outputs",
        lambda *, run_root, shard_run_roots, runtime_config_path=None, method_shard_plan=None: merge_calls.update(
            {
                "run_root": str(run_root),
                "shard_run_roots": [str(path) for path in shard_run_roots],
                "runtime_config_path": str(runtime_config_path) if runtime_config_path is not None else None,
                "method_shard_plan": method_shard_plan,
            }
        )
        or {"status": "merged"},
    )

    result = run_probe_method_shards(
        run_root=tmp_path / "run_root",
        run_mode="formal",
        runtime_profile="formal",
        runtime_config_path=tmp_path / "runtime_config.json",
        method_variants=[
            "frame_prc",
            "tubelet_only",
            "tubelet_sync",
            "tubelet_only_lt01",
            "tubelet_only_lt02",
        ],
        shard_count=2,
        python_executable="python",
    )

    assert len(captured_commands) == 2
    assert "--method-variants" in captured_commands[0]
    assert captured_commands[0][-3:] == ["frame_prc", "tubelet_only", "tubelet_sync"]
    assert captured_commands[1][-2:] == ["tubelet_only_lt01", "tubelet_only_lt02"]
    assert merge_calls["run_root"] == str(tmp_path / "run_root")
    assert merge_calls["shard_run_roots"] == [
        str(tmp_path / "run_root" / "method_shards" / "shard_01_main_variants"),
        str(tmp_path / "run_root" / "method_shards" / "shard_02_tubelet_sweep"),
    ]
    assert result["shard_count"] == 2


@pytest.mark.unit
def test_run_probe_stage2_mechanism_calibration_forwards_governed_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate notebook calibration helper delegates to the governed calibration runner.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    captured_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        workflow_module,
        "run_stage2_mechanism_calibration",
        lambda **kwargs: captured_kwargs.update(kwargs)
        or {
            "calibration_summary_path": tmp_path / "stage2_mechanism_calibration_summary.json",
            "generated_tubelet_sync_candidate_config_path": tmp_path
            / "tubelet_sync_real_video_vae_candidate.json",
            "selected_tubelet_sync_candidate": {
                "method_variant": "tubelet_sync_real_video_vae_candidate"
            },
        },
    )

    summary = run_probe_stage2_mechanism_calibration(
        run_root=tmp_path / "calibration_run",
        run_mode="formal",
        runtime_profile="formal",
        dataset_manifest_path=tmp_path / "dataset_manifest.json",
        runtime_config_path=tmp_path / "runtime_config.json",
        samples_per_role=2,
        batch_size_frames=8,
        output_method_config_path=tmp_path / "candidate_method.json",
    )

    assert captured_kwargs["run_root"] == tmp_path / "calibration_run"
    assert captured_kwargs["run_mode"] == "formal"
    assert captured_kwargs["runtime_profile"] == "formal"
    assert captured_kwargs["samples_per_role"] == 2
    assert captured_kwargs["batch_size_frames"] == 8
    assert captured_kwargs["output_method_config_path"] == tmp_path / "candidate_method.json"
    assert summary["calibration_summary_path"] == str(
        tmp_path / "stage2_mechanism_calibration_summary.json"
    )
    assert summary["generated_tubelet_sync_candidate_config_path"] == str(
        tmp_path / "tubelet_sync_real_video_vae_candidate.json"
    )


@pytest.mark.unit
def test_merge_probe_method_shard_outputs_combines_records_and_runtime_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate shard merging writes combined governed records and runtime metadata.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    run_root = tmp_path / "merged_run"
    shard_a_root = run_root / "method_shards" / "shard_01_main_variants"
    shard_b_root = run_root / "method_shards" / "shard_02_tubelet_sweep"
    runtime_config_path = tmp_path / "runtime_config.json"
    runtime_config_path.write_text(
        json.dumps({"run_mode": "formal", "runtime_profile": "formal"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    record_store: dict[str, dict[str, object]] = {
        str(shard_a_root): {
            "event_score_records": [
                {"method_variant": "frame_prc", "attack_name": "no_attack"},
                {"method_variant": "tubelet_only", "attack_name": "no_attack"},
            ],
            "threshold_records": [{"threshold_id": "frame_prc:threshold"}],
        },
        str(shard_b_root): {
            "event_score_records": [
                {"method_variant": "tubelet_only_lt01", "attack_name": "no_attack"},
            ],
            "threshold_records": [{"threshold_id": "tubelet_only_lt01:threshold"}],
        },
        str(run_root): {
            "event_score_records": [],
            "threshold_records": [],
        },
    }

    class _FakeRecordWriter:
        def __init__(self, output_root: str | Path) -> None:
            self._output_root = str(Path(output_root))

        def read_event_score_records(self) -> list[dict[str, object]]:
            return list(record_store[self._output_root]["event_score_records"])

        def read_threshold_records(self) -> list[dict[str, object]]:
            return list(record_store[self._output_root]["threshold_records"])

        def write_event_score_records(self, records: list[dict[str, object]]) -> None:
            record_store[self._output_root]["written_event_score_records"] = list(records)

        def write_threshold_records(self, records: list[dict[str, object]]) -> None:
            record_store[self._output_root]["written_threshold_records"] = list(records)

    class _FakeArtifactBuilder:
        def build_artifacts(
            self,
            event_score_records: list[dict[str, object]],
            threshold_records: list[dict[str, object]],
            output_root: str | Path,
        ) -> dict[str, Path]:
            del event_score_records, threshold_records
            output_paths = workflow_module.build_real_video_vae_latent_output_paths(output_root)
            for table_path in output_paths.table_paths():
                table_path.parent.mkdir(parents=True, exist_ok=True)
                table_path.write_text("header\n", encoding="utf-8")
            for figure_path in output_paths.figure_paths():
                figure_path.parent.mkdir(parents=True, exist_ok=True)
                figure_path.write_bytes(b"png")
            output_paths.report_path.parent.mkdir(parents=True, exist_ok=True)
            output_paths.report_path.write_text("- RealVideoVaeLatentDecision: INCONCLUSIVE\n", encoding="utf-8")
            return {
                "main_tpr_fpr_table_path": output_paths.main_tpr_fpr_table_path,
                "report_path": output_paths.report_path,
            }

    monkeypatch.setattr(workflow_module, "RecordWriter", _FakeRecordWriter)
    monkeypatch.setattr(workflow_module, "RealVideoVaeLatentArtifactBuilder", _FakeArtifactBuilder)

    for shard_root, method_variant in (
        (shard_a_root, "frame_prc"),
        (shard_b_root, "tubelet_only_lt01"),
    ):
        output_paths = workflow_module.build_real_video_vae_latent_output_paths(shard_root)
        output_paths.artifact_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.artifact_manifest_path.write_text(
            json.dumps(
                [{"artifact_kind": "decoded_video", "relpath": f"artifacts/videos/{method_variant}.mp4", "digest": f"{method_variant}-digest"}],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        output_paths.runtime_config_path.write_text(
            json.dumps({"method_variants": [method_variant]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output_paths.runtime_manifest_path.write_text(
            json.dumps({"run_id": shard_root.name, "runtime_profile": "formal"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output_paths.run_manifest_path.write_text(
            json.dumps(
                {
                    "run_id": shard_root.name,
                    "created_at": "2026-05-15T00:00:00Z",
                    "construction_phase": "real_video_vae_latent_probe",
                    "protocol_name": "fixed_low_fpr_calibrated_detection",
                    "method_config_digest": f"{method_variant}-method-digest",
                    "protocol_config_digest": "protocol-digest",
                    "attack_matrix_digest": "attack-digest",
                    "ablation_config_digest": "ablation-digest",
                    "records_digest": "records-digest",
                    "thresholds_digest": "thresholds-digest",
                    "tables_digest": "tables-digest",
                    "figures_digest": "figures-digest",
                    "placeholder_fields": [],
                    "random_fields": ["latent_generation_seed_random"],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    summary = merge_probe_method_shard_outputs(
        run_root=run_root,
        shard_run_roots=[shard_a_root, shard_b_root],
        runtime_config_path=runtime_config_path,
        method_shard_plan=[
            {"shard_name": "shard_01_main_variants", "method_variants": ["frame_prc", "tubelet_only"]},
            {"shard_name": "shard_02_tubelet_sweep", "method_variants": ["tubelet_only_lt01"]},
        ],
    )

    assert len(record_store[str(run_root)]["written_event_score_records"]) == 3
    assert len(record_store[str(run_root)]["written_threshold_records"]) == 2
    merged_runtime_config = json.loads(
        (run_root / "artifacts" / "runtime_config.json").read_text(encoding="utf-8")
    )
    assert merged_runtime_config["method_shard_mode"] == "parallel_method_variants"
    assert merged_runtime_config["shard_count"] == 2
    assert merged_runtime_config["method_variants"] == [
        "frame_prc",
        "tubelet_only",
        "tubelet_only_lt01",
    ]
    assert len(summary["method_shard_schedule"]) == 2
"""
文件用途：验证阶段 2 notebook workflow helper 的 manifest handoff 与 session model 语义。
File purpose: Validate dataset-manifest handoff and session-model semantics for the stage-two notebook workflow helpers.
Module type: General module
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import zipfile
from io import StringIO
from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

from experiments.synthetic_tubelet_sync_probe.synthetic_video_latent import (
    SyntheticVideoLatentPlaceholder,
)
from main.attacks.temporal import TemporalAttackPlaceholder
from main.methods.temporal_tubelet_watermark.method import build_method_from_config

import paper_workflow.notebook_utils.real_video_vae_latent_probe_workflow as workflow_module

from paper_workflow.notebook_utils.real_video_vae_latent_probe_workflow import (
    export_probe_stage2_calibration_family_snapshot,
    materialize_probe_family_results_to_drive,
    merge_probe_method_variant_split_outputs,
    package_probe_non_formal_audit_bundle,
    prepare_probe_runtime_workspace,
    reset_probe_runtime_run_root,
    run_probe_stage2_mechanism_calibration,
    run_probe_method_variant_splits,
    run_probe_runner,
    write_probe_tubelet_anchor_forensics,
    write_probe_stage2_local_clip_sync_candidate_surface_forensics,
    write_probe_stage2_local_clip_sync_diagnostics,
    write_probe_runtime_config,
)
from scripts.prepare_models.prepare_session_autoencoder_kl import (
    prepare_session_autoencoder_kl,
)


def _build_local_clip_surface_candidate_config(
    method_variant: str,
    *,
    lambda_sync: float,
    min_sync_positive_margin: float,
    min_sync_alignment_coverage_ratio: float,
) -> dict[str, object]:
    return {
        "method_family": "temporal_tubelet_watermark",
        "method_variant": method_variant,
        "base_method_variant": "tubelet_sync",
        "method_status": "stage2_mechanism_calibration_candidate",
        "enable_frame_prc": False,
        "enable_tubelet": True,
        "enable_sync": True,
        "enable_trajectory": False,
        "tubelet_length": 4,
        "score_calibration": {
            "embedding_projection_support_weight": 0.25,
        },
        "sync_search": {
            "offset_search_min": -8,
            "offset_search_max": 8,
            "enable_scale_search": False,
            "coverage_penalty_enabled": True,
            "min_sync_positive_margin": min_sync_positive_margin,
            "min_sync_alignment_coverage_ratio": min_sync_alignment_coverage_ratio,
            "min_sync_alignment_matched_count": 1,
        },
        "lambda_sync": lambda_sync,
        "fusion_rule": "sync_rescue_fusion",
    }


def _build_local_clip_surface_event_record(
    *,
    stage_run_root: Path,
    method_config: dict[str, object],
    sample_id: str,
    clip_length: int,
) -> dict[str, object]:
    backend = SyntheticVideoLatentPlaceholder(latent_shape=(32, 4, 16, 16))
    backend.set_output_root(stage_run_root)
    base_sample = backend.build_sample(sample_id, "calibration", "watermarked_positive")
    watermark_method = build_method_from_config(method_config)
    watermarked_sample = watermark_method.embed(base_sample, {})
    clipped_sample = TemporalAttackPlaceholder(
        "local_clip",
        {"clip_length": clip_length},
    ).apply(watermarked_sample)
    detection_result = watermark_method.detect(clipped_sample, threshold_record=None)

    mechanism_trace = dict(detection_result.mechanism_trace or {})
    mechanism_trace.update(
        {
            "video_source_relpath": f"processed_dataset/{sample_id}.mp4",
            "latent_shape": list(clipped_sample.latent_shape),
            "latent_artifact_relpath": clipped_sample.latent_artifact_relpath,
            "latent_artifact_digest": clipped_sample.latent_artifact_digest,
            "reencoded_latent_relpath": clipped_sample.latent_artifact_relpath,
            "reencoded_latent_digest": clipped_sample.latent_artifact_digest,
        }
    )
    return {
        "event_id": f"{method_config['method_variant']}:{sample_id}:local_clip_len_{clip_length:02d}",
        "sample_id": sample_id,
        "split": clipped_sample.split,
        "sample_role": "attacked_positive",
        "method_variant": method_config["method_variant"],
        "attack_name": "local_clip",
        "attack_params": clipped_sample.applied_attack_params,
        "latent_backend_name": clipped_sample.latent_backend_name,
        "latent_backend_status": clipped_sample.latent_backend_status,
        "latent_tensor_digest_random": clipped_sample.latent_tensor_digest_random,
        "latent_generation_seed_random": clipped_sample.latent_generation_seed_random,
        "mechanism_trace": mechanism_trace,
    }


def _build_tubelet_anchor_event_record(
    *,
    stage_run_root: Path,
    method_config: dict[str, object],
    sample_id: str,
    sample_role: str,
    threshold_record: dict[str, object],
) -> dict[str, object]:
    """构造单条 tubelet-only anchor 取证测试记录。

    Args:
        stage_run_root: 本轮校准 stage 的临时输出根目录。
        method_config: tubelet-only 方法配置。
        sample_id: 样本标识。
        sample_role: 样本角色。
        threshold_record: 检测时使用的阈值记录。

    Returns:
        可写入 event_scores.jsonl 的轻量记录。
    """
    backend = SyntheticVideoLatentPlaceholder(latent_shape=(16, 4, 16, 16))
    backend.set_output_root(stage_run_root)
    base_sample = backend.build_sample(sample_id, "calibration", sample_role)
    watermark_method = build_method_from_config(method_config)
    input_sample = (
        watermark_method.embed(base_sample, {})
        if sample_role == "watermarked_positive"
        else base_sample
    )
    detection_result = watermark_method.detect(input_sample, threshold_record)

    mechanism_trace = dict(detection_result.mechanism_trace or {})
    mechanism_trace.update(
        {
            "latent_shape": list(input_sample.latent_shape),
            "latent_artifact_relpath": input_sample.latent_artifact_relpath,
            "latent_artifact_digest": input_sample.latent_artifact_digest,
            "reencoded_latent_relpath": input_sample.latent_artifact_relpath,
            "reencoded_latent_digest": input_sample.latent_artifact_digest,
        }
    )
    return {
        "event_id": f"{method_config['method_variant']}:{sample_id}:no_attack",
        "sample_id": sample_id,
        "split": input_sample.split,
        "sample_role": sample_role,
        "method_variant": method_config["method_variant"],
        "attack_name": "no_attack",
        "attack_params": {},
        "threshold_id": threshold_record["threshold_id"],
        "decision": detection_result.decision,
        "evidence_scores": detection_result.evidence_scores,
        "latent_backend_name": input_sample.latent_backend_name,
        "latent_backend_status": input_sample.latent_backend_status,
        "latent_tensor_digest_random": input_sample.latent_tensor_digest_random,
        "latent_generation_seed_random": input_sample.latent_generation_seed_random,
        "mechanism_trace": mechanism_trace,
    }


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
def test_materialize_probe_family_results_to_drive_copies_after_local_package(
    tmp_path: Path,
) -> None:
    """验证阶段 2 notebook 只在本地结果包存在后才创建 Drive family 目录。"""
    local_family_root = tmp_path / "runtime" / "families" / "real_video_vae_latent_probe" / "family_a"
    drive_root = tmp_path / "drive" / "MyDrive"
    drive_family_root = drive_root / "TSTW" / "results" / "real_video_vae_latent_probe" / "family_a"
    local_package_path = local_family_root / "packages" / "run_a.tar.zst"
    local_summary_path = local_family_root / "family_summary.json"
    local_package_path.parent.mkdir(parents=True, exist_ok=True)
    local_package_path.write_bytes(b"package")
    local_summary_path.write_text('{"status": true}\n', encoding="utf-8")

    assert not drive_family_root.exists()

    summary = materialize_probe_family_results_to_drive(
        local_family_root=local_family_root,
        drive_family_root=drive_family_root,
        package_payload={
            "drive_archive_path": str(local_package_path),
            "package_path": str(local_package_path),
            "package_format": "tar.zst",
            "archive_format": "tar.zst",
            "compat_pack_root": str(local_family_root),
            "zip_pack": {
                "zip_path": str(local_family_root / "packages" / "run_a.zip"),
            },
        },
        drive_root=drive_root,
        family_id="family_a",
        workflow_key="workflow_a",
        step_key="step_a",
        run_mode="formal",
        formal_validation_summary={"status": True},
        mechanism_summary={"Stage2MechanismDecision": "PASS"},
    )

    assert drive_family_root.exists()
    assert (drive_family_root / "packages" / "run_a.tar.zst").exists()
    assert summary["drive_archive_path"] == str(drive_family_root / "packages" / "run_a.tar.zst")
    assert summary["package_payload"]["compat_pack_root"] == str(drive_family_root)
    result_registry_path = Path(summary["registry_paths"]["result_registry.jsonl"])
    assert result_registry_path.as_posix().endswith("TSTW/registry/result_registry.jsonl")
    registry_entry = json.loads(result_registry_path.read_text(encoding="utf-8").splitlines()[0])
    assert registry_entry["archive_path"] == str(
        drive_family_root / "packages" / "run_a.tar.zst"
    )
    assert registry_entry["archive_path"] != str(local_package_path)


@pytest.mark.unit
def test_reset_probe_runtime_run_root_removes_only_allowed_child(
    tmp_path: Path,
) -> None:
    """校验 notebook reset helper 只清理允许父目录下的指定 run root.

    Args:
        tmp_path: 临时输出根目录.

    Returns:
        None.
    """
    allowed_parent_root = tmp_path / "runtime" / "runs"
    run_root = allowed_parent_root / "real_video_calibration"
    stale_artifact_path = run_root / "artifacts" / "latents" / "stale.npy"
    sibling_artifact_path = allowed_parent_root / "sibling_run" / "keep.txt"
    stale_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    sibling_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    stale_artifact_path.write_bytes(b"stale")
    sibling_artifact_path.write_text("keep\n", encoding="utf-8")

    summary = reset_probe_runtime_run_root(
        run_root=run_root,
        allowed_parent_root=allowed_parent_root,
        reason="unit_test_reset",
    )

    assert summary["existed_before_reset"] is True
    assert Path(summary["reset_run_root"]) == run_root.resolve()
    assert run_root.exists()
    assert not stale_artifact_path.exists()
    assert sibling_artifact_path.exists()


@pytest.mark.unit
def test_reset_probe_runtime_run_root_rejects_paths_outside_allowed_parent(
    tmp_path: Path,
) -> None:
    """校验 reset helper 拒绝删除允许父目录之外的路径.

    Args:
        tmp_path: 临时输出根目录.

    Returns:
        None.
    """
    allowed_parent_root = tmp_path / "runtime" / "runs"
    outside_run_root = tmp_path / "other_runtime" / "runs" / "calibration"

    with pytest.raises(ValueError, match="allowed_parent_root"):
        reset_probe_runtime_run_root(
            run_root=outside_run_root,
            allowed_parent_root=allowed_parent_root,
            reason="unit_test_reject",
        )


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
        shard_count=4,
        shard_index=1,
        worker_count=3,
        python_executable="python",
    )

    command = captured_call["command"]
    kwargs = captured_call["kwargs"]
    repository_root = Path(workflow_module.__file__).resolve().parents[2]
    assert "--dataset-manifest" in command
    assert str(dataset_manifest_path) in command
    assert "--batch-size-frames" in command
    assert "16" in command
    assert "--shard-count" in command
    assert "4" in command
    assert "--shard-index" in command
    assert "1" in command
    assert "--worker-count" in command
    assert "3" in command
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
def test_run_probe_method_variant_splits_launches_governed_method_allowlists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate legacy method-variant splits launch governed runner subprocesses.

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
        "merge_probe_method_variant_split_outputs",
        lambda *, run_root, split_run_roots, runtime_config_path=None, method_variant_split_plan=None: merge_calls.update(
            {
                "run_root": str(run_root),
                "method_variant_split_run_roots": [str(path) for path in split_run_roots],
                "runtime_config_path": str(runtime_config_path) if runtime_config_path is not None else None,
                "method_variant_split_plan": method_variant_split_plan,
            }
        )
        or {"status": "merged"},
    )

    result = run_probe_method_variant_splits(
        run_root=tmp_path / "run_root",
        run_mode="formal",
        runtime_profile="formal",
        runtime_config_path=tmp_path / "runtime_config.json",
        method_variants=[
            "frame_prc",
            "tubelet_only",
            "tubelet_sync",
        ],
        method_variant_split_count=2,
        python_executable="python",
    )

    assert len(captured_commands) == 2
    assert "--method-variants" in captured_commands[0]
    assert captured_commands[0][-2:] == ["frame_prc", "tubelet_sync"]
    assert captured_commands[1][-1:] == ["tubelet_only"]
    assert merge_calls["run_root"] == str(tmp_path / "run_root")
    assert merge_calls["method_variant_split_run_roots"] == [
        str(tmp_path / "run_root" / "method_variant_splits" / "split_01"),
        str(tmp_path / "run_root" / "method_variant_splits" / "split_02"),
    ]
    assert result["method_variant_split_count"] == 2


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
def test_export_probe_stage2_calibration_family_snapshot_persists_summary_and_candidate(
    tmp_path: Path,
) -> None:
    """Validate calibration-only notebook runs persist a family snapshot.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    family_root = tmp_path / "families" / "family_a"
    calibration_run_root = tmp_path / "runs" / "stage2_calibration"
    artifacts_root = calibration_run_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)

    summary_path = artifacts_root / "stage2_mechanism_calibration_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "selection_completion_status": "incomplete_no_eligible_tubelet_sync_candidate",
                "selection_blocking_reason": "no_tubelet_sync_candidate_passes_selection_gate",
                "selected_tubelet_sync_candidate": None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    candidate_path = artifacts_root / "tubelet_sync_real_video_vae_candidate.json"
    candidate_path.write_text(
        json.dumps(
            {
                "method_variant": "tubelet_sync_real_video_vae_candidate",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    diagnostics_path = artifacts_root / "selected_candidate_local_clip_sync_diagnostics.csv"
    diagnostics_path.write_text(
        "event_id,method_variant\nexample,tubelet_sync_real_video_vae_candidate\n",
        encoding="utf-8",
    )
    anchor_forensics_csv_path = artifacts_root / "selected_tubelet_anchor_forensics.csv"
    anchor_forensics_csv_path.write_text(
        "event_id,method_variant\nanchor,tubelet_only_cal_tl02_sp04x04_w025\n",
        encoding="utf-8",
    )
    anchor_forensics_summary_path = (
        artifacts_root / "selected_tubelet_anchor_forensics_summary.json"
    )
    anchor_forensics_summary_path.write_text(
        json.dumps({"record_count": 1}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = export_probe_stage2_calibration_family_snapshot(
        family_root=family_root,
        calibration_run_root=calibration_run_root,
        diagnostics_csv_path=diagnostics_path,
        anchor_forensics_csv_path=anchor_forensics_csv_path,
        anchor_forensics_summary_path=anchor_forensics_summary_path,
    )

    stage2_family_root = family_root / "stage2_calibration"
    assert summary["stage2_family_root"] == str(stage2_family_root)
    assert summary["summary_copy_path"] == str(
        stage2_family_root / "stage2_mechanism_calibration_summary.json"
    )
    assert summary["candidate_copy_path"] == str(
        stage2_family_root / "tubelet_sync_real_video_vae_candidate.json"
    )
    assert summary["diagnostics_copy_path"] == str(
        stage2_family_root / "selected_candidate_local_clip_sync_diagnostics.csv"
    )
    assert summary["anchor_forensics_csv_copy_path"] == str(
        stage2_family_root / "selected_tubelet_anchor_forensics.csv"
    )
    assert summary["anchor_forensics_summary_copy_path"] == str(
        stage2_family_root / "selected_tubelet_anchor_forensics_summary.json"
    )
    assert summary["selection_completion_status"] == (
        "incomplete_no_eligible_tubelet_sync_candidate"
    )
    assert (stage2_family_root / "stage2_mechanism_calibration_summary.json").exists()
    assert (stage2_family_root / "tubelet_sync_real_video_vae_candidate.json").exists()
    assert (stage2_family_root / "selected_candidate_local_clip_sync_diagnostics.csv").exists()
    assert (stage2_family_root / "selected_tubelet_anchor_forensics.csv").exists()
    assert (
        stage2_family_root / "selected_tubelet_anchor_forensics_summary.json"
    ).exists()


@pytest.mark.unit
def test_export_probe_stage2_calibration_family_snapshot_skips_missing_candidate(
    tmp_path: Path,
) -> None:
    """Validate calibration-only export succeeds when no sync candidate config was generated.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    family_root = tmp_path / "families" / "family_a"
    calibration_run_root = tmp_path / "runs" / "stage2_calibration"
    artifacts_root = calibration_run_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)

    summary_path = artifacts_root / "stage2_mechanism_calibration_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "calibration_summary_path": str(summary_path),
                "selection_completion_status": "incomplete_no_eligible_tubelet_sync_candidate",
                "selection_blocking_reason": "no_tubelet_sync_candidate_passes_selection_gate",
                "generated_tubelet_sync_candidate_config_path": None,
                "selected_tubelet_sync_candidate": None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = export_probe_stage2_calibration_family_snapshot(
        family_root=family_root,
        calibration_run_root=calibration_run_root,
        calibration_summary={
            "calibration_summary_path": str(summary_path),
            "selection_completion_status": "incomplete_no_eligible_tubelet_sync_candidate",
            "selection_blocking_reason": "no_tubelet_sync_candidate_passes_selection_gate",
            "generated_tubelet_sync_candidate_config_path": None,
            "selected_tubelet_sync_candidate": None,
        },
    )

    stage2_family_root = family_root / "stage2_calibration"
    assert summary["stage2_family_root"] == str(stage2_family_root)
    assert summary["candidate_copy_path"] is None
    assert summary["selected_tubelet_sync_candidate_present"] is False
    assert (stage2_family_root / "stage2_mechanism_calibration_summary.json").exists()
    assert not (stage2_family_root / "tubelet_sync_real_video_vae_candidate.json").exists()


@pytest.mark.unit
def test_write_probe_tubelet_anchor_forensics_exports_selected_anchor_rows(
    tmp_path: Path,
) -> None:
    """验证 tubelet-only anchor 取证表可从校准记录中重建。

    Args:
        tmp_path: 临时输出根目录。

    Returns:
        None.
    """
    run_root = tmp_path / "calibration_run"
    artifacts_root = run_root / "artifacts"
    stage_run_root = run_root / "stages" / "anchor_tubelet_only_wide"
    records_root = stage_run_root / "records"
    thresholds_root = stage_run_root / "thresholds"
    method_config_root = tmp_path / "workspace" / "method_configs"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    records_root.mkdir(parents=True, exist_ok=True)
    thresholds_root.mkdir(parents=True, exist_ok=True)
    method_config_root.mkdir(parents=True, exist_ok=True)

    method_variant = "tubelet_only_cal_tl02_sp04x04_w025"
    method_config = {
        "method_family": "temporal_tubelet_watermark",
        "method_variant": method_variant,
        "base_method_variant": "tubelet_only",
        "method_status": "stage2_mechanism_calibration_candidate",
        "enable_frame_prc": False,
        "enable_tubelet": True,
        "enable_sync": False,
        "enable_trajectory": False,
        "tubelet_length": 2,
        "embedding_margin": 0.25,
        "tubelet_partition": {"spatial_patch_size": [4, 4]},
        "score_calibration": {
            "embedding_projection_support_weight": 0.25,
        },
        "sync_search": {
            "coverage_penalty_enabled": True,
        },
        "fusion_rule": "tubelet_score_only",
    }
    method_config_path = method_config_root / f"{method_variant}.json"
    method_config_path.write_text(
        json.dumps(method_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    stage_ablation_config_path = tmp_path / "workspace" / "anchor_ablation_config.json"
    stage_ablation_config_path.write_text(
        json.dumps(
            {
                "method_config_paths": {
                    method_variant: str(method_config_path),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    threshold_record = {
        "threshold_id": "threshold:tubelet_anchor",
        "method_variant": method_variant,
        "score_name": "S_final",
        "threshold_value": 0.0,
    }
    (thresholds_root / "thresholds.json").write_text(
        json.dumps([threshold_record], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    event_records = [
        _build_tubelet_anchor_event_record(
            stage_run_root=stage_run_root,
            method_config=method_config,
            sample_id="sample_anchor_positive_000001",
            sample_role="watermarked_positive",
            threshold_record=threshold_record,
        ),
        _build_tubelet_anchor_event_record(
            stage_run_root=stage_run_root,
            method_config=method_config,
            sample_id="sample_anchor_negative_000002",
            sample_role="clean_negative",
            threshold_record=threshold_record,
        ),
    ]
    (records_root / "event_scores.jsonl").write_text(
        "".join(
            json.dumps(record, ensure_ascii=False) + "\n" for record in event_records
        ),
        encoding="utf-8",
    )
    (artifacts_root / "stage2_mechanism_calibration_summary.json").write_text(
        json.dumps(
            {
                "selected_tubelet_only_candidate": {
                    "method_variant": method_variant,
                },
                "search_stage_summaries": [
                    {
                        "stage_name": "anchor_tubelet_only_wide",
                        "selection_scope": "tubelet_only",
                        "run_root": str(stage_run_root),
                        "ablation_config_path": str(stage_ablation_config_path),
                        "selected_tubelet_only_candidate": {
                            "method_variant": method_variant,
                        },
                        "top_tubelet_only_candidates": [
                            {
                                "method_variant": method_variant,
                            },
                        ],
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = write_probe_tubelet_anchor_forensics(run_root=run_root)

    assert summary["selected_stage_name"] == "anchor_tubelet_only_wide"
    assert summary["selected_method_variant"] == method_variant
    assert summary["record_count"] == 2
    assert summary["sample_roles"] == ["clean_negative", "watermarked_positive"]
    assert Path(summary["output_csv_path"]).exists()
    assert Path(summary["output_summary_path"]).exists()

    with Path(summary["output_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["sample_role"] for row in rows} == {
        "clean_negative",
        "watermarked_positive",
    }
    required_columns = {
        "payload_projection_mean",
        "tubelet_projection_coverage_ratio",
        "embedding_support_score",
        "threshold_margin",
        "recomputed_delta_vs_recorded_S_tubelet",
        "payload_coded_projection_digest",
    }
    assert required_columns.issubset(rows[0].keys())
    assert all(
        abs(float(row["recomputed_delta_vs_recorded_S_tubelet"])) <= 1e-6
        for row in rows
    )

    summary_payload = json.loads(
        Path(summary["output_summary_path"]).read_text(encoding="utf-8")
    )
    assert summary_payload["record_count"] == 2
    assert len(summary_payload["decision_rate_by_role_attack"]) == 2
    assert summary_payload["lowest_positive_margin_records"][0]["sample_role"] == (
        "watermarked_positive"
    )


@pytest.mark.unit
def test_write_probe_stage2_local_clip_sync_diagnostics_skips_without_selected_candidate(
    tmp_path: Path,
) -> None:
    """Validate diagnostics skip cleanly when calibration selected no sync candidate.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "stage2_calibration"
    artifacts_root = run_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)

    calibration_summary_path = artifacts_root / "stage2_mechanism_calibration_summary.json"
    calibration_summary_path.write_text(
        json.dumps(
            {
                "selected_tubelet_sync_candidate": None,
                "selection_completion_status": "incomplete_no_eligible_tubelet_sync_candidate",
                "selection_blocking_reason": "no_eligible_tubelet_sync_candidate",
                "selection_blocking_details": {
                    "tubelet_sync_row_count": 2160,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = write_probe_stage2_local_clip_sync_diagnostics(run_root=run_root)

    assert summary["skipped"] is True
    assert summary["skip_reason"] == "selected_tubelet_sync_candidate_missing"
    assert summary["selection_completion_status"] == "incomplete_no_eligible_tubelet_sync_candidate"
    assert summary["selection_blocking_reason"] == "no_eligible_tubelet_sync_candidate"
    assert summary["selection_blocking_details"] == {"tubelet_sync_row_count": 2160}
    assert summary["output_csv_path"] is None
    assert summary["record_count"] == 0
    assert summary["surface_export_status"] == "skipped"
    assert summary["surface_export_failure_reason"] == "selected_tubelet_sync_candidate_missing"


@pytest.mark.unit
def test_write_probe_stage2_local_clip_sync_diagnostics_persists_selected_candidate_rows(
    tmp_path: Path,
) -> None:
    """Validate local-clip diagnostics emit a CSV for the selected sync candidate.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "stage2_calibration"
    artifacts_root = run_root / "artifacts"
    stage_run_root = run_root / "stages" / "sync_refine_scan"
    records_root = stage_run_root / "records"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    records_root.mkdir(parents=True, exist_ok=True)

    selected_method_variant = "tubelet_sync_cal_ls025_sr08_pm000_cov062_mc1"
    calibration_summary_path = artifacts_root / "stage2_mechanism_calibration_summary.json"
    calibration_summary_path.write_text(
        json.dumps(
            {
                "selected_tubelet_sync_candidate": {
                    "method_variant": selected_method_variant,
                },
                "search_stage_summaries": [
                    {
                        "stage_name": "sync_refine_scan",
                        "selection_scope": "tubelet_sync",
                        "run_root": str(stage_run_root),
                        "selected_tubelet_sync_candidate": {
                            "method_variant": selected_method_variant,
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    event_scores_path = records_root / "event_scores.jsonl"
    event_scores_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_id": "selected:sample_a:local_clip_len_04",
                        "sample_id": "sample_a",
                        "split": "calibration",
                        "sample_role": "attacked_positive",
                        "method_variant": selected_method_variant,
                        "attack_name": "local_clip",
                        "attack_params": {"clip_length": 4},
                        "mechanism_trace": {
                            "sync_confident": False,
                            "S_sync_peak_margin": -0.02,
                            "sync_alignment_matched_count": 1,
                            "sync_alignment_coverage_ratio": 0.0625,
                            "sync_estimated_offset": -3,
                            "sync_ground_truth_offset": -4,
                            "sync_candidate_score_raw": 0.19,
                            "sync_candidate_score_penalized": 0.04,
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "event_id": "selected:sample_b:local_clip_len_08",
                        "sample_id": "sample_b",
                        "split": "calibration",
                        "sample_role": "attacked_negative",
                        "method_variant": selected_method_variant,
                        "attack_name": "local_clip",
                        "attack_params": {"clip_length": 8},
                        "mechanism_trace": {
                            "sync_confident": False,
                            "S_sync_peak_margin": 0.0,
                            "sync_alignment_matched_count": 1,
                            "sync_alignment_coverage_ratio": 0.125,
                            "sync_estimated_offset": -6,
                            "sync_ground_truth_offset": -6,
                            "sync_candidate_score_raw": 0.12,
                            "sync_candidate_score_penalized": 0.03,
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "event_id": "other:sample_c:local_clip_len_12",
                        "sample_id": "sample_c",
                        "split": "calibration",
                        "sample_role": "attacked_positive",
                        "method_variant": "tubelet_sync_cal_other_variant",
                        "attack_name": "local_clip",
                        "attack_params": {"clip_length": 12},
                        "mechanism_trace": {
                            "sync_confident": True,
                            "S_sync_peak_margin": 0.2,
                            "sync_alignment_matched_count": 4,
                            "sync_alignment_coverage_ratio": 0.5,
                            "sync_estimated_offset": -2,
                            "sync_ground_truth_offset": -2,
                            "sync_candidate_score_raw": 0.41,
                            "sync_candidate_score_penalized": 0.33,
                        },
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "event_id": "selected:sample_d:no_attack",
                        "sample_id": "sample_d",
                        "split": "calibration",
                        "sample_role": "watermarked_positive",
                        "method_variant": selected_method_variant,
                        "attack_name": "no_attack",
                        "attack_params": {},
                        "mechanism_trace": {},
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = write_probe_stage2_local_clip_sync_diagnostics(run_root=run_root)

    assert summary["selected_stage_name"] == "sync_refine_scan"
    assert summary["selected_method_variant"] == selected_method_variant
    assert summary["method_variant_filter_applied"] is True
    assert summary["record_count"] == 2
    assert summary["clip_lengths"] == [4, 8]
    assert summary["surface_export_status"] == "skipped"

    output_csv_path = Path(summary["output_csv_path"])
    assert output_csv_path == artifacts_root / "selected_candidate_local_clip_sync_diagnostics.csv"
    assert output_csv_path.exists()
    with output_csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["event_id"] for row in rows] == [
        "selected:sample_b:local_clip_len_08",
        "selected:sample_a:local_clip_len_04",
    ]
    assert rows[0]["sync_candidate_score_raw"] == "0.12"
    assert rows[0]["sync_candidate_score_penalized"] == "0.03"


@pytest.mark.unit
def test_write_probe_stage2_local_clip_sync_diagnostics_falls_back_to_stage_rows(
    tmp_path: Path,
) -> None:
    """Validate diagnostics still land when the selected summary variant is normalized.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "stage2_calibration"
    artifacts_root = run_root / "artifacts"
    stage_run_root = run_root / "stages" / "sync_refine_scan"
    records_root = stage_run_root / "records"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    records_root.mkdir(parents=True, exist_ok=True)

    calibration_summary_path = artifacts_root / "stage2_mechanism_calibration_summary.json"
    calibration_summary_path.write_text(
        json.dumps(
            {
                "selected_tubelet_sync_candidate": {
                    "method_variant": "tubelet_sync_real_video_vae_candidate",
                },
                "search_stage_summaries": [
                    {
                        "stage_name": "sync_refine_scan",
                        "selection_scope": "tubelet_sync",
                        "run_root": str(stage_run_root),
                        "selected_tubelet_sync_candidate": {
                            "method_variant": "tubelet_sync_real_video_vae_candidate",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    event_scores_path = records_root / "event_scores.jsonl"
    event_scores_path.write_text(
        json.dumps(
            {
                "event_id": "generated:sample_a:local_clip_len_04",
                "sample_id": "sample_a",
                "split": "calibration",
                "sample_role": "attacked_positive",
                "method_variant": "tubelet_sync_cal_generated_variant",
                "attack_name": "local_clip",
                "attack_params": {"clip_length": 4},
                "mechanism_trace": {
                    "sync_confident": False,
                    "S_sync_peak_margin": -0.01,
                    "sync_alignment_matched_count": 1,
                    "sync_alignment_coverage_ratio": 0.0625,
                    "sync_estimated_offset": -5,
                    "sync_ground_truth_offset": -4,
                    "sync_candidate_score_raw": 0.15,
                    "sync_candidate_score_penalized": 0.02,
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = write_probe_stage2_local_clip_sync_diagnostics(run_root=run_root)

    assert summary["method_variant_filter_applied"] is False
    assert summary["record_count"] == 1
    assert summary["surface_export_status"] == "skipped"
    with Path(summary["output_csv_path"]).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["method_variant"] == "tubelet_sync_cal_generated_variant"


@pytest.mark.unit
def test_write_probe_stage2_local_clip_sync_diagnostics_persists_candidate_surface_artifacts(
    tmp_path: Path,
) -> None:
    """Validate local-clip diagnostics also emit candidate-surface forensics.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "stage2_calibration"
    artifacts_root = run_root / "artifacts"
    stage_run_root = run_root / "stages" / "sync_refine_scan"
    records_root = stage_run_root / "records"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    records_root.mkdir(parents=True, exist_ok=True)

    selected_method_variant = "tubelet_sync_cal_surface_probe"
    candidate_config = {
        "method_family": "temporal_tubelet_watermark",
        "method_variant": selected_method_variant,
        "base_method_variant": "tubelet_sync",
        "method_status": "stage2_mechanism_calibration_candidate",
        "enable_frame_prc": False,
        "enable_tubelet": True,
        "enable_sync": True,
        "enable_trajectory": False,
        "tubelet_length": 4,
        "score_calibration": {
            "embedding_projection_support_weight": 0.45,
        },
        "sync_search": {
            "offset_search_min": -8,
            "offset_search_max": 8,
            "enable_scale_search": False,
            "coverage_penalty_enabled": True,
            "min_sync_positive_margin": 0.0,
            "min_sync_alignment_coverage_ratio": 0.0625,
            "min_sync_alignment_matched_count": 1,
        },
        "lambda_sync": 0.1,
        "fusion_rule": "sync_rescue_fusion",
    }
    candidate_config_path = artifacts_root / "tubelet_sync_real_video_vae_candidate.json"
    candidate_config_path.write_text(
        json.dumps(candidate_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    calibration_summary_path = artifacts_root / "stage2_mechanism_calibration_summary.json"
    calibration_summary_path.write_text(
        json.dumps(
            {
                "selected_tubelet_sync_candidate": {
                    "method_variant": selected_method_variant,
                },
                "generated_tubelet_sync_candidate_config_path": str(candidate_config_path),
                "search_stage_summaries": [
                    {
                        "stage_name": "sync_refine_scan",
                        "selection_scope": "tubelet_sync",
                        "run_root": str(stage_run_root),
                        "selected_tubelet_sync_candidate": {
                            "method_variant": selected_method_variant,
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    backend = SyntheticVideoLatentPlaceholder(latent_shape=(32, 4, 16, 16))
    backend.set_output_root(stage_run_root)
    base_sample = backend.build_sample(
        "sample_surface_probe_000001",
        "calibration",
        "watermarked_positive",
    )
    watermark_method = build_method_from_config(candidate_config)
    watermarked_sample = watermark_method.embed(base_sample, {})
    clipped_sample = TemporalAttackPlaceholder(
        "local_clip",
        {"clip_length": 4},
    ).apply(watermarked_sample)
    detection_result = watermark_method.detect(clipped_sample, threshold_record=None)

    mechanism_trace = dict(detection_result.mechanism_trace or {})
    mechanism_trace.update(
        {
            "video_source_relpath": "processed_dataset/sample_surface_probe_000001.mp4",
            "latent_shape": list(clipped_sample.latent_shape),
            "latent_artifact_relpath": clipped_sample.latent_artifact_relpath,
            "latent_artifact_digest": clipped_sample.latent_artifact_digest,
            "reencoded_latent_relpath": clipped_sample.latent_artifact_relpath,
            "reencoded_latent_digest": clipped_sample.latent_artifact_digest,
        }
    )
    event_scores_path = records_root / "event_scores.jsonl"
    event_scores_path.write_text(
        json.dumps(
            {
                "event_id": f"{selected_method_variant}:sample_surface_probe_000001:local_clip",
                "sample_id": "event_alias_attacked_positive_000001",
                "split": clipped_sample.split,
                "sample_role": "attacked_positive",
                "method_variant": selected_method_variant,
                "attack_name": "local_clip",
                "attack_params": clipped_sample.applied_attack_params,
                "latent_backend_name": clipped_sample.latent_backend_name,
                "latent_backend_status": clipped_sample.latent_backend_status,
                "latent_tensor_digest_random": clipped_sample.latent_tensor_digest_random,
                "latent_generation_seed_random": clipped_sample.latent_generation_seed_random,
                "mechanism_trace": mechanism_trace,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = write_probe_stage2_local_clip_sync_diagnostics(run_root=run_root)

    assert summary["surface_export_status"] == "ok"
    assert summary["surface_event_count"] == 1
    assert summary["surface_row_count"] > 1

    surface_csv_path = Path(summary["output_surface_csv_path"])
    surface_summary_path = Path(summary["output_surface_summary_path"])
    assert surface_csv_path.exists()
    assert surface_summary_path.exists()

    with surface_csv_path.open("r", encoding="utf-8", newline="") as handle:
        surface_rows = list(csv.DictReader(handle))
    assert any(row["is_current_selected_candidate"] == "True" for row in surface_rows)
    assert any(row["is_ground_truth_candidate"] == "True" for row in surface_rows)
    assert "rank_hybrid_no_prior" in surface_rows[0]
    assert "selected_hybrid_no_prior" in surface_rows[0]

    surface_summary_payload = json.loads(surface_summary_path.read_text(encoding="utf-8"))
    assert surface_summary_payload["surface_event_count"] == 1
    assert surface_summary_payload["ranking_rule_names"] == [
        "penalized_prior",
        "penalized_no_prior",
        "hybrid_prior",
        "hybrid_no_prior",
        "raw_prior",
        "raw_no_prior",
    ]
    assert surface_summary_payload["events"][0]["search_score_rule"] == "hybrid_no_prior"
    assert surface_summary_payload["events"][0]["selected_candidate"][
        "selected_hybrid_no_prior"
    ] is True
    assert surface_summary_payload["events"][0]["selected_candidate"][
        "is_current_selected_candidate"
    ] is True
    assert "sync_candidate_score_hybrid" in surface_summary_payload["events"][0][
        "ranking_summaries"
    ]["hybrid_no_prior"]["winner"]


@pytest.mark.unit
def test_write_probe_stage2_local_clip_sync_candidate_surface_forensics_exports_explicit_method_variant(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "stage2_calibration"
    artifacts_root = run_root / "artifacts"
    stage_run_root = run_root / "stages" / "sync_wide_scan"
    records_root = stage_run_root / "records"
    stage_workspace_root = tmp_path / "workspace" / "sync_wide_scan"
    method_config_root = stage_workspace_root / "method_configs"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    records_root.mkdir(parents=True, exist_ok=True)
    method_config_root.mkdir(parents=True, exist_ok=True)

    target_method_variant = (
        "tubelet_sync_cal_tl02_sp04x04_w025_sr04_ls000_mg120_cv250_mc01_frsync_rescue"
    )
    other_method_variant = (
        "tubelet_sync_cal_tl01_sp04x04_w045_sr12_ls000_mg000_cv500_mc01_frsync_rescue"
    )
    target_method_config = _build_local_clip_surface_candidate_config(
        target_method_variant,
        lambda_sync=0.1,
        min_sync_positive_margin=0.12,
        min_sync_alignment_coverage_ratio=0.25,
    )
    other_method_config = _build_local_clip_surface_candidate_config(
        other_method_variant,
        lambda_sync=0.0,
        min_sync_positive_margin=0.0,
        min_sync_alignment_coverage_ratio=0.5,
    )
    target_method_config_path = method_config_root / f"{target_method_variant}.json"
    other_method_config_path = method_config_root / f"{other_method_variant}.json"
    target_method_config_path.write_text(
        json.dumps(target_method_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    other_method_config_path.write_text(
        json.dumps(other_method_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    stage_ablation_config_path = stage_workspace_root / "sync_wide_scan_ablation.json"
    stage_ablation_config_path.write_text(
        json.dumps(
            {
                "method_config_paths": {
                    target_method_variant: str(target_method_config_path),
                    other_method_variant: str(other_method_config_path),
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    calibration_summary_path = artifacts_root / "stage2_mechanism_calibration_summary.json"
    calibration_summary_path.write_text(
        json.dumps(
            {
                "selected_tubelet_sync_candidate": None,
                "search_stage_summaries": [
                    {
                        "stage_name": "sync_wide_scan",
                        "selection_scope": "tubelet_sync",
                        "run_root": str(stage_run_root),
                        "ablation_config_path": str(stage_ablation_config_path),
                        "selected_tubelet_only_candidate": {
                            "method_variant": "tubelet_only_cal_tl02_sp04x04_w025",
                        },
                        "top_tubelet_sync_candidates": [
                            {"method_variant": target_method_variant},
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    event_records = [
        _build_local_clip_surface_event_record(
            stage_run_root=stage_run_root,
            method_config=target_method_config,
            sample_id="sample_surface_target_000001",
            clip_length=4,
        ),
        _build_local_clip_surface_event_record(
            stage_run_root=stage_run_root,
            method_config=other_method_config,
            sample_id="sample_surface_other_000001",
            clip_length=8,
        ),
    ]
    (records_root / "event_scores.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in event_records),
        encoding="utf-8",
    )

    summary = write_probe_stage2_local_clip_sync_candidate_surface_forensics(
        run_root=run_root,
        method_variant=target_method_variant,
    )

    assert summary["surface_target_mode"] == "method_variant"
    assert summary["requested_method_variant"] == target_method_variant
    assert summary["resolved_method_variants"] == [target_method_variant]
    assert summary["record_count"] == 1
    assert summary["surface_event_count"] == 1

    surface_csv_path = Path(summary["output_surface_csv_path"])
    surface_summary_path = Path(summary["output_surface_summary_path"])
    assert surface_csv_path.exists()
    assert surface_summary_path.exists()

    with surface_csv_path.open("r", encoding="utf-8", newline="") as handle:
        surface_rows = list(csv.DictReader(handle))
    assert surface_rows
    assert {row["method_variant"] for row in surface_rows} == {target_method_variant}

    surface_summary_payload = json.loads(surface_summary_path.read_text(encoding="utf-8"))
    assert surface_summary_payload["requested_method_variant"] == target_method_variant
    assert surface_summary_payload["resolved_method_variants"] == [target_method_variant]


@pytest.mark.unit
def test_write_probe_stage2_local_clip_sync_candidate_surface_forensics_exports_anchor_variants(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "stage2_calibration"
    artifacts_root = run_root / "artifacts"
    stage_run_root = run_root / "stages" / "sync_wide_scan"
    records_root = stage_run_root / "records"
    stage_workspace_root = tmp_path / "workspace" / "sync_wide_scan"
    method_config_root = stage_workspace_root / "method_configs"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    records_root.mkdir(parents=True, exist_ok=True)
    method_config_root.mkdir(parents=True, exist_ok=True)

    anchor_key = "tl02_sp04x04_w025"
    matching_method_variants = [
        "tubelet_sync_cal_tl02_sp04x04_w025_sr04_ls000_mg120_cv250_mc01_frsync_rescue",
        "tubelet_sync_cal_tl02_sp04x04_w025_sr12_ls000_mg000_cv500_mc01_frsync_rescue",
    ]
    nonmatching_method_variant = (
        "tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg120_cv250_mc01_frsync_rescue"
    )

    method_configs = {
        matching_method_variants[0]: _build_local_clip_surface_candidate_config(
            matching_method_variants[0],
            lambda_sync=0.1,
            min_sync_positive_margin=0.12,
            min_sync_alignment_coverage_ratio=0.25,
        ),
        matching_method_variants[1]: _build_local_clip_surface_candidate_config(
            matching_method_variants[1],
            lambda_sync=0.0,
            min_sync_positive_margin=0.0,
            min_sync_alignment_coverage_ratio=0.5,
        ),
        nonmatching_method_variant: _build_local_clip_surface_candidate_config(
            nonmatching_method_variant,
            lambda_sync=0.05,
            min_sync_positive_margin=0.06,
            min_sync_alignment_coverage_ratio=0.125,
        ),
    }
    method_config_paths: dict[str, str] = {}
    for method_variant_name, method_config in method_configs.items():
        method_config_path = method_config_root / f"{method_variant_name}.json"
        method_config_path.write_text(
            json.dumps(method_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        method_config_paths[method_variant_name] = str(method_config_path)

    stage_ablation_config_path = stage_workspace_root / "sync_wide_scan_ablation.json"
    stage_ablation_config_path.write_text(
        json.dumps(
            {
                "method_config_paths": method_config_paths,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    calibration_summary_path = artifacts_root / "stage2_mechanism_calibration_summary.json"
    calibration_summary_path.write_text(
        json.dumps(
            {
                "selected_tubelet_sync_candidate": None,
                "search_stage_summaries": [
                    {
                        "stage_name": "sync_wide_scan",
                        "selection_scope": "tubelet_sync",
                        "run_root": str(stage_run_root),
                        "ablation_config_path": str(stage_ablation_config_path),
                        "selected_tubelet_only_candidate": {
                            "method_variant": f"tubelet_only_cal_{anchor_key}",
                        },
                        "top_tubelet_sync_candidates": [
                            {"method_variant": matching_method_variants[0]},
                            {"method_variant": matching_method_variants[1]},
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    event_records = [
        _build_local_clip_surface_event_record(
            stage_run_root=stage_run_root,
            method_config=method_configs[matching_method_variants[0]],
            sample_id="sample_surface_anchor_000001",
            clip_length=4,
        ),
        _build_local_clip_surface_event_record(
            stage_run_root=stage_run_root,
            method_config=method_configs[matching_method_variants[1]],
            sample_id="sample_surface_anchor_000002",
            clip_length=8,
        ),
        _build_local_clip_surface_event_record(
            stage_run_root=stage_run_root,
            method_config=method_configs[nonmatching_method_variant],
            sample_id="sample_surface_other_000003",
            clip_length=12,
        ),
    ]
    (records_root / "event_scores.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in event_records),
        encoding="utf-8",
    )

    summary = write_probe_stage2_local_clip_sync_candidate_surface_forensics(
        run_root=run_root,
        anchor_key=anchor_key,
    )

    assert summary["surface_target_mode"] == "anchor_key"
    assert summary["requested_anchor_key"] == anchor_key
    assert summary["resolved_method_variants"] == sorted(matching_method_variants)
    assert summary["record_count"] == 2
    assert summary["surface_event_count"] == 2

    surface_csv_path = Path(summary["output_surface_csv_path"])
    surface_summary_path = Path(summary["output_surface_summary_path"])
    assert surface_csv_path.exists()
    assert surface_summary_path.exists()

    with surface_csv_path.open("r", encoding="utf-8", newline="") as handle:
        surface_rows = list(csv.DictReader(handle))
    assert {row["method_variant"] for row in surface_rows} == set(matching_method_variants)

    surface_summary_payload = json.loads(surface_summary_path.read_text(encoding="utf-8"))
    assert surface_summary_payload["requested_anchor_key"] == anchor_key
    assert surface_summary_payload["resolved_method_variants"] == sorted(
        matching_method_variants
    )
    assert surface_summary_payload["events"][0]["recomputed_matches_recorded_selection"] is True
    assert (
        surface_summary_payload["events"][0]["recomputed_selected_candidate"][
            "offset_candidate"
        ]
        == surface_summary_payload["events"][0]["sync_result"]["sync_estimated_offset"]
    )


@pytest.mark.unit
def test_package_probe_non_formal_audit_bundle_persists_selected_audit_files(
    tmp_path: Path,
) -> None:
    """Validate non-formal audit bundle packaging lands a zip without registry writes.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    family_root = tmp_path / "family_root"
    notebook_run_root = tmp_path / "notebook_run"
    calibration_run_root = tmp_path / "calibration_run"
    selected_stage_run_root = calibration_run_root / "stages" / "sync_refine_scan"

    (notebook_run_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (notebook_run_root / "runtime_profile").mkdir(parents=True, exist_ok=True)
    (calibration_run_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (selected_stage_run_root / "records").mkdir(parents=True, exist_ok=True)
    (selected_stage_run_root / "thresholds").mkdir(parents=True, exist_ok=True)
    (selected_stage_run_root / "artifacts").mkdir(parents=True, exist_ok=True)

    notebook_runtime_config_path = notebook_run_root / "artifacts" / "runtime_config.json"
    notebook_runtime_config_path.write_text(
        json.dumps({"run_mode": "formal"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    session_model_manifest_path = notebook_run_root / "artifacts" / "session_model_manifest.json"
    session_model_manifest_path.write_text(
        json.dumps({"models": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    runtime_profile_plan_path = (
        notebook_run_root / "runtime_profile" / "runtime_profile_plan.json"
    )
    runtime_profile_plan_path.write_text(
        json.dumps({"execution_runtime_profile": "l4_formal"}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    candidate_config_path = (
        calibration_run_root / "artifacts" / "tubelet_sync_real_video_vae_candidate.json"
    )
    candidate_config_path.write_text(
        json.dumps({"method_variant": "tubelet_sync_real_video_vae_candidate"}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    diagnostics_csv_path = (
        calibration_run_root / "artifacts" / "selected_candidate_local_clip_sync_diagnostics.csv"
    )
    diagnostics_csv_path.write_text(
        "event_id,sample_id\nlocal_clip_event,sample_001\n",
        encoding="utf-8",
    )
    diagnostics_surface_csv_path = (
        calibration_run_root
        / "artifacts"
        / "selected_candidate_local_clip_sync_candidate_surface.csv"
    )
    diagnostics_surface_csv_path.write_text(
        "event_id,offset_candidate\nlocal_clip_event,-8\n",
        encoding="utf-8",
    )
    diagnostics_surface_summary_path = (
        calibration_run_root
        / "artifacts"
        / "selected_candidate_local_clip_sync_candidate_surface_summary.json"
    )
    diagnostics_surface_summary_path.write_text(
        json.dumps({"surface_event_count": 1}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    anchor_forensics_csv_path = (
        calibration_run_root / "artifacts" / "selected_tubelet_anchor_forensics.csv"
    )
    anchor_forensics_csv_path.write_text(
        "event_id,method_variant\nanchor_event,tubelet_only_cal_tl02_sp04x04_w025\n",
        encoding="utf-8",
    )
    anchor_forensics_summary_path = (
        calibration_run_root
        / "artifacts"
        / "selected_tubelet_anchor_forensics_summary.json"
    )
    anchor_forensics_summary_path.write_text(
        json.dumps({"record_count": 1}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    protocol_config_path = calibration_run_root / "artifacts" / "protocol_config.json"
    protocol_config_path.write_text(
        json.dumps({"splits": ["dev", "calibration"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    runtime_config_path = calibration_run_root / "artifacts" / "runtime_config.json"
    runtime_config_path.write_text(
        json.dumps({"batch_size_frames": 256}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    search_stage_plan_path = calibration_run_root / "artifacts" / "search_stage_plan.json"
    search_stage_plan_path.write_text(
        json.dumps({"search_stage_count": 3}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    selected_candidate_output_path = (
        calibration_run_root / "artifacts" / "selected_candidate_output.json"
    )
    selected_candidate_output_path.write_text(
        json.dumps({"candidate_status": "insufficient_signal"}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    selected_report_path = calibration_run_root / "artifacts" / "selected_report.json"
    selected_report_path.write_text(
        json.dumps({"report_status": "ok"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    selected_grid_output_path = calibration_run_root / "artifacts" / "selected_grid_output.json"
    selected_grid_output_path.write_text(
        json.dumps({"grid_status": "ok"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    timing_summary_path = (
        calibration_run_root / "artifacts" / "stage2_mechanism_calibration_timing_summary.json"
    )
    timing_summary_path.write_text(
        json.dumps(
            {
                "stage_timing_summaries": [
                    {
                        "stage_name": "sync_refine_scan",
                        "top_timing_events": [
                            {
                                "event_name": "runner_attack_video",
                                "elapsed_seconds": 12.0,
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    event_scores_path = selected_stage_run_root / "records" / "event_scores.jsonl"
    event_scores_path.write_text(
        json.dumps({"event_id": "local_clip_event"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    selected_stage_threshold_path = selected_stage_run_root / "thresholds" / "thresholds.json"
    selected_stage_threshold_path.write_text(
        json.dumps({"threshold": 1.1}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    selected_stage_artifact_path = selected_stage_run_root / "artifacts" / "selector_trace.json"
    selected_stage_artifact_path.write_text(
        json.dumps({"trace": "ok"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    calibration_summary_path = (
        calibration_run_root / "artifacts" / "stage2_mechanism_calibration_summary.json"
    )
    calibration_summary_path.write_text(
        json.dumps(
            {
                "protocol_config_path": str(protocol_config_path),
                "runtime_config_path": str(runtime_config_path),
                "search_stage_plan_path": str(search_stage_plan_path),
                "selected_candidate_output_path": str(selected_candidate_output_path),
                "selected_report_path": str(selected_report_path),
                "selected_grid_output_path": str(selected_grid_output_path),
                "timing_summary_path": str(timing_summary_path),
                "generated_tubelet_sync_candidate_config_path": str(candidate_config_path),
                "selected_tubelet_sync_candidate": {
                    "method_variant": "tubelet_sync_real_video_vae_candidate",
                },
                "search_stage_summaries": [
                    {
                        "stage_name": "sync_refine_scan",
                        "selection_scope": "tubelet_sync",
                        "run_root": str(selected_stage_run_root),
                        "selected_tubelet_sync_candidate": {
                            "method_variant": "tubelet_sync_real_video_vae_candidate",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = package_probe_non_formal_audit_bundle(
        family_root=family_root,
        notebook_run_root=notebook_run_root,
        calibration_run_root=calibration_run_root,
        diagnostics_csv_path=diagnostics_csv_path,
        bundle_name="stage2_mechanism_calibration_audit",
    )

    archive_path = Path(summary["archive_path"])
    manifest_path = Path(summary["manifest_path"])
    summary_path = Path(summary["summary_path"])
    assert archive_path.exists()
    assert manifest_path.exists()
    assert summary_path.exists()
    assert summary["bundle_kind"] == "non_formal_audit"
    assert summary["selected_stage_name"] == "sync_refine_scan"
    assert summary["included_file_count"] >= 9
    assert "notebook_run" in summary["included_sections"]
    assert "calibration_run" in summary["included_sections"]
    assert "selected_stage" in summary["included_sections"]

    with zipfile.ZipFile(archive_path, mode="r") as archive:
        archive_names = set(archive.namelist())
    assert "notebook_run/artifacts/runtime_config.json" in archive_names
    assert "calibration_run/artifacts/stage2_mechanism_calibration_summary.json" in archive_names
    assert "calibration_run/artifacts/stage2_mechanism_calibration_timing_summary.json" in archive_names
    assert (
        "calibration_run/artifacts/selected_candidate_local_clip_sync_diagnostics.csv"
        in archive_names
    )
    assert (
        "calibration_run/artifacts/selected_candidate_local_clip_sync_candidate_surface.csv"
        in archive_names
    )
    assert (
        "calibration_run/artifacts/selected_candidate_local_clip_sync_candidate_surface_summary.json"
        in archive_names
    )
    assert (
        "calibration_run/artifacts/selected_tubelet_anchor_forensics.csv"
        in archive_names
    )
    assert (
        "calibration_run/artifacts/selected_tubelet_anchor_forensics_summary.json"
        in archive_names
    )
    assert "selected_stage/records/event_scores.jsonl" in archive_names
    assert "selected_stage/thresholds/thresholds.json" in archive_names


@pytest.mark.unit
def test_merge_probe_method_variant_split_outputs_combines_records_and_runtime_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate split merging writes combined governed records and runtime metadata.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    run_root = tmp_path / "merged_run"
    split_a_root = run_root / "method_variant_splits" / "split_01_main_variants"
    split_b_root = run_root / "method_variant_splits" / "split_02_tubelet_sweep"
    runtime_config_path = tmp_path / "runtime_config.json"
    runtime_config_path.write_text(
        json.dumps({"run_mode": "formal", "runtime_profile": "formal"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    record_store: dict[str, dict[str, object]] = {
        str(split_a_root): {
            "event_score_records": [
                {"method_variant": "frame_prc", "attack_name": "no_attack"},
                {"method_variant": "tubelet_only", "attack_name": "no_attack"},
            ],
            "threshold_records": [{"threshold_id": "frame_prc:threshold"}],
        },
        str(split_b_root): {
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

    for split_root, method_variant in (
        (split_a_root, "frame_prc"),
        (split_b_root, "tubelet_only_lt01"),
    ):
        output_paths = workflow_module.build_real_video_vae_latent_output_paths(split_root)
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
            json.dumps({"run_id": split_root.name, "runtime_profile": "formal"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output_paths.run_manifest_path.write_text(
            json.dumps(
                {
                    "run_id": split_root.name,
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

    summary = merge_probe_method_variant_split_outputs(
        run_root=run_root,
        split_run_roots=[split_a_root, split_b_root],
        runtime_config_path=runtime_config_path,
        method_variant_split_plan=[
            {"split_name": "split_01_main_variants", "method_variants": ["frame_prc", "tubelet_only"]},
            {"split_name": "split_02_tubelet_sweep", "method_variants": ["tubelet_only_lt01"]},
        ],
    )

    assert len(record_store[str(run_root)]["written_event_score_records"]) == 3
    assert len(record_store[str(run_root)]["written_threshold_records"]) == 2
    merged_runtime_config = json.loads(
        (run_root / "artifacts" / "runtime_config.json").read_text(encoding="utf-8")
    )
    assert merged_runtime_config["method_variant_split_mode"] == "legacy_parallel_method_variants"
    assert merged_runtime_config["method_variant_split_count"] == 2
    assert merged_runtime_config["method_variants"] == [
        "frame_prc",
        "tubelet_only",
        "tubelet_only_lt01",
    ]
    assert len(summary["method_variant_split_schedule"]) == 2

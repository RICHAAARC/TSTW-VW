"""
文件用途：验证阶段 2 scaffold event records 的扩展字段与产物布局。
File purpose: Validate extended fields and artifact layout for stage-two scaffold event records.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from main.core.digest import compute_object_digest
from main.core.records import RecordWriter
from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner
from tests.real_video_vae_latent_test_support import run_real_video_vae_latent_tiny


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.smoke
def test_real_video_vae_latent_event_records_include_quality_and_temporal_payloads(tmp_path: Path) -> None:
    """Validate that stage-two event records include quality and temporal payloads.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = run_real_video_vae_latent_tiny(tmp_path)
    record_writer = RecordWriter(output_root)
    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    run_manifest = json.loads(
        (output_root / "artifacts" / "run_manifest.json").read_text(encoding="utf-8")
    )
    runtime_manifest = json.loads(
        (output_root / "artifacts" / "runtime_manifest.json").read_text(encoding="utf-8")
    )
    runtime_config = json.loads(
        (output_root / "artifacts" / "runtime_config.json").read_text(encoding="utf-8")
    )

    assert event_score_records
    assert threshold_records
    assert run_manifest["construction_phase"] == "real_video_vae_latent_probe"
    assert runtime_manifest["notebook_entrypoint_present"] is True
    assert run_manifest["runtime_config_digest"] == compute_object_digest(runtime_config)
    for event_score_record in event_score_records:
        assert event_score_record["evidence_scores"]["S_traj"] is None
        assert "quality_metrics" in event_score_record
        assert "temporal_metrics" in event_score_record
        assert event_score_record["mechanism_trace"]["construction_phase"] == "real_video_vae_latent_probe"
        assert event_score_record["mechanism_trace"]["encoded_latent_digest"]
        assert event_score_record["mechanism_trace"]["video_source_digest"]
        assert event_score_record["mechanism_trace"]["decoded_video_relpath"].endswith(".npy")
        assert event_score_record["mechanism_trace"]["reencoded_latent_relpath"].endswith(".npy")
        assert (
            event_score_record["input_artifact_trace"]["artifact_digest"]
            == event_score_record["mechanism_trace"]["reencoded_latent_digest"]
        )
        assert not Path(event_score_record["mechanism_trace"]["video_source_relpath"]).is_absolute()
    assert all(
        threshold_record["threshold_id"].endswith(":real_video_vae_latent_probe")
        for threshold_record in threshold_records
    )


@pytest.mark.smoke
def test_real_video_vae_latent_runtime_manifest_tracks_runtime_config_and_notebook_entrypoint(
    tmp_path: Path,
) -> None:
    """Validate that stage-two runtime config is persisted and digested.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_probe_runtime_config"
    runtime_config_path = tmp_path / "runtime_config.json"
    runtime_config_payload = {
        "git_commit": "colab-test-commit",
        "drive_results_dir": "/content/drive/MyDrive/tstw_stage2/results",
        "vae_model_id": "configured_by_user",
    }
    runtime_config_path.write_text(
        json.dumps(runtime_config_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    RealVideoVaeLatentRunner(ROOT).run(
        output_root=output_root,
        run_mode="smoke",
        samples_per_role=1,
        runtime_profile_override="tiny",
        runtime_config_path=runtime_config_path,
    )

    merged_runtime_config = json.loads(
        (output_root / "artifacts" / "runtime_config.json").read_text(
            encoding="utf-8"
        )
    )
    runtime_manifest = json.loads(
        (output_root / "artifacts" / "runtime_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    run_manifest = json.loads(
        (output_root / "artifacts" / "run_manifest.json").read_text(encoding="utf-8")
    )

    assert merged_runtime_config["git_commit"] == "colab-test-commit"
    assert merged_runtime_config["run_mode"] == "smoke"
    assert runtime_manifest["git_commit"] == "colab-test-commit"
    assert runtime_manifest["notebook_entrypoint_present"] is True
    assert run_manifest["runtime_config_digest"] == compute_object_digest(merged_runtime_config)

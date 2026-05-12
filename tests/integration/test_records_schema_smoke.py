"""
文件用途：验证 active formal stage 的 runtime records smoke schema。
File purpose: Validate active-stage runtime record, threshold, and manifest smoke schemas.
Module type: Integration test module
"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.synthetic_tubelet_sync_probe.ablation_runner import AblationRunner
from main.core.records import RecordWriter
from main.core.schema import (
    EVIDENCE_SCORE_NAMES,
    validate_event_score_record,
    validate_run_manifest_record,
    validate_threshold_record,
)


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


@pytest.mark.smoke
def test_active_stage_records_schema_is_complete(tmp_path: Path) -> None:
    """Validate that active-stage runtime writes complete governed records.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2, runtime_profile_override="smoke")
    record_writer = RecordWriter(output_root)

    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    run_manifest = record_writer.read_run_manifest()

    assert event_score_records
    assert threshold_records
    assert record_writer.output_paths.main_metrics_path.exists()
    assert record_writer.output_paths.ablation_table_path.exists()
    assert record_writer.output_paths.local_clip_curve_path.exists()
    assert record_writer.output_paths.temporal_attack_curve_path.exists()
    assert record_writer.output_paths.tubelet_length_ablation_path.exists()
    assert record_writer.output_paths.sync_peak_examples_path.exists()
    assert record_writer.output_paths.report_path.exists()

    for event_score_record in event_score_records:
        validate_event_score_record(event_score_record)
        mechanism_trace = event_score_record["mechanism_trace"]
        assert set(event_score_record["evidence_scores"].keys()) == EVIDENCE_SCORE_NAMES
        assert "placeholder_fields" in event_score_record
        assert "random_fields" in event_score_record
        assert event_score_record["base_method_variant"]
        assert isinstance(event_score_record["derived_variant"], bool)
        assert isinstance(event_score_record["tubelet_length"], int)
        assert isinstance(mechanism_trace, dict)
        assert mechanism_trace["construction_phase"] == "synthetic_tubelet_sync_probe"
        assert mechanism_trace["latent_backend_name"] == event_score_record["latent_backend_name"]
        assert mechanism_trace["latent_artifact_digest"] == event_score_record["latent_tensor_digest_random"]
        assert mechanism_trace["latent_artifact_relpath"].endswith(".npy")
        assert mechanism_trace["tubelet_length"] == event_score_record["tubelet_length"]
        if event_score_record["derived_variant"]:
            assert event_score_record["base_method_variant"] == "tubelet_only"
            assert event_score_record["ablation_axis"] == "tubelet_length"
        else:
            assert event_score_record["base_method_variant"] == event_score_record["method_variant"]
            assert event_score_record["ablation_axis"] is None
        assert (
            event_score_record["input_artifact_trace"]["backend_name"]
            == event_score_record["latent_backend_name"]
        )
        assert (
            event_score_record["input_artifact_trace"]["backend_status"]
            == event_score_record["latent_backend_status"]
        )
        assert (
            event_score_record["input_artifact_trace"]["artifact_digest"]
            == event_score_record["latent_tensor_digest_random"]
        )
        assert (
            event_score_record["input_artifact_trace"]["generation_seed_random"]
            == event_score_record["latent_generation_seed_random"]
        )
        assert {
            "latent_generation_seed_random",
            "latent_tensor_digest_random",
        }.issubset(set(event_score_record["random_fields"]))
        if event_score_record["attack_name"] == "no_attack":
            assert event_score_record["sample_role"] in {
                "clean_negative",
                "watermarked_positive",
            }
        else:
            assert event_score_record["sample_role"] in {
                "attacked_negative",
                "attacked_positive",
            }

    frame_prc_record = next(
        event_score_record
        for event_score_record in event_score_records
        if event_score_record["method_variant"] == "frame_prc"
        and event_score_record["split"] == "test"
        and event_score_record["sample_role"] == "watermarked_positive"
        and event_score_record["attack_name"] == "no_attack"
    )
    assert frame_prc_record["evidence_scores"]["S_tubelet"] is not None
    assert frame_prc_record["evidence_scores"]["S_sync"] is None
    assert frame_prc_record["evidence_scores"]["S_traj"] is None
    assert frame_prc_record["placeholder_fields"] == ["trajectory_observation_placeholder"]
    assert frame_prc_record["mechanism_trace"]["tubelet_length"] == 1
    assert frame_prc_record["random_fields"] == [
        "latent_generation_seed_random",
        "latent_tensor_digest_random",
    ]

    tubelet_sync_record = next(
        event_score_record
        for event_score_record in event_score_records
        if event_score_record["method_variant"] == "tubelet_sync"
        and event_score_record["split"] == "test"
        and event_score_record["sample_role"] == "watermarked_positive"
        and event_score_record["attack_name"] == "no_attack"
    )
    assert tubelet_sync_record["evidence_scores"]["S_tubelet"] is not None
    assert tubelet_sync_record["evidence_scores"]["S_sync"] is not None
    assert tubelet_sync_record["evidence_scores"]["S_traj"] is None
    assert tubelet_sync_record["placeholder_fields"] == ["trajectory_observation_placeholder"]
    assert tubelet_sync_record["mechanism_trace"]["embedding_rule"] == "projection_margin"
    assert tubelet_sync_record["mechanism_trace"]["tubelet_length"] == 4
    assert tubelet_sync_record["mechanism_trace"]["mean_projection_after"] >= tubelet_sync_record["mechanism_trace"]["embedding_margin"]
    assert tubelet_sync_record["evidence_scores"]["S_final"] >= frame_prc_record["evidence_scores"]["S_final"]
    assert tubelet_sync_record["random_fields"] == [
        "latent_generation_seed_random",
        "latent_tensor_digest_random",
    ]

    for threshold_record in threshold_records:
        validate_threshold_record(threshold_record)
        assert threshold_record["runtime_profile"] == "smoke"
        assert isinstance(threshold_record["validation_target_fpr"], float)
        assert isinstance(threshold_record["sync_threshold_guard_band_multiplier"], float)
        assert isinstance(
            threshold_record["tubelet_length_threshold_guard_band_multiplier"],
            float,
        )
        assert isinstance(
            threshold_record["applied_threshold_guard_band_multiplier"],
            float,
        )

    validate_run_manifest_record(run_manifest)
    assert "figures_digest" in run_manifest
    assert "figures_digest_placeholder" not in run_manifest

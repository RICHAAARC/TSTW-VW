"""
文件用途：验证 active formal stage 的 event records、thresholds 与 manifest schema。
File purpose: Validate active-stage event record, threshold, and manifest schemas.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.attacks.attack_registry import build_attack_registry
from main.backends.synthetic_video_latent import (
    build_synthetic_video_latent_backend_from_support_config,
)
from main.core.records import RecordWriter
from main.core.registry import load_json_config
from main.core.schema import (
    EVIDENCE_SCORE_NAMES,
    build_input_artifact_trace,
    validate_event_score_record,
    validate_run_manifest_record,
    validate_threshold_record,
)
from main.protocol.ablation_runner import AblationRunner


ROOT = Path(__file__).resolve().parents[1]


def test_active_stage_records_schema_is_complete(tmp_path: Path) -> None:
    """Validate that active-stage runtime writes complete governed records.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2)
    record_writer = RecordWriter(output_root)

    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    run_manifest = record_writer.read_run_manifest()
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "synthetic_tubelet_sync_probe.json"
    )
    attack_config = load_json_config(
        ROOT / "configs" / "attacks" / "temporal_attack_matrix.json"
    )
    latent_backend = build_synthetic_video_latent_backend_from_support_config(protocol_config)
    attack_map = {
        attack.attack_name: attack for attack in build_attack_registry(attack_config)
    }

    assert event_score_records
    assert threshold_records

    for event_score_record in event_score_records:
        validate_event_score_record(event_score_record)
        expected_clean_sample = latent_backend.build_sample(
            event_score_record["sample_id"],
            event_score_record["split"],
            event_score_record["sample_role"],
        )
        expected_attacked_sample = attack_map[event_score_record["attack_name"]].apply(
            expected_clean_sample
        )
        expected_input_artifact_trace = build_input_artifact_trace(expected_attacked_sample)
        assert set(event_score_record["evidence_scores"].keys()) == EVIDENCE_SCORE_NAMES
        assert "placeholder_fields" in event_score_record
        assert "random_fields" in event_score_record
        assert event_score_record["input_artifact_trace"] == expected_input_artifact_trace
        assert event_score_record["latent_backend_name"] == expected_attacked_sample.latent_backend_name
        assert event_score_record["latent_backend_status"] == expected_attacked_sample.latent_backend_status
        assert (
            event_score_record["latent_tensor_digest_random"]
            == expected_attacked_sample.latent_tensor_digest_random
        )
        assert (
            event_score_record["latent_generation_seed_random"]
            == expected_attacked_sample.latent_generation_seed_random
        )
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
    assert tubelet_sync_record["evidence_scores"]["S_final"] >= frame_prc_record["evidence_scores"]["S_final"]
    assert tubelet_sync_record["random_fields"] == [
        "latent_generation_seed_random",
        "latent_tensor_digest_random",
    ]

    for threshold_record in threshold_records:
        validate_threshold_record(threshold_record)

    validate_run_manifest_record(run_manifest)
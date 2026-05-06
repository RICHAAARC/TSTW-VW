"""
文件用途：验证阶段 0 event records、thresholds 与 manifest schema。
File purpose: Validate stage-0 event record, threshold, and manifest schemas.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.backends.synthetic_latent_backend_random import SyntheticLatentBackendRandom
from main.core.records import RecordWriter
from main.core.schema import (
    EVIDENCE_SCORE_NAMES,
    validate_event_score_record,
    validate_run_manifest_record,
    validate_threshold_record,
)
from main.protocol.ablation_runner import AblationRunner


ROOT = Path(__file__).resolve().parents[1]


def test_stage0_records_schema_is_complete(tmp_path: Path) -> None:
    """Validate that stage-0 runtime writes complete governed records.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "protocol_skeleton_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2)
    record_writer = RecordWriter(output_root)

    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    run_manifest = record_writer.read_run_manifest()
    latent_backend = SyntheticLatentBackendRandom()

    assert event_score_records
    assert threshold_records

    for event_score_record in event_score_records:
        validate_event_score_record(event_score_record)
        expected_latent_sample = latent_backend.build_sample(
            event_score_record["sample_id"],
            event_score_record["split"],
            event_score_record["sample_role"],
        )
        assert set(event_score_record["evidence_scores"].keys()) == EVIDENCE_SCORE_NAMES
        assert "placeholder_fields" in event_score_record
        assert "random_fields" in event_score_record
        assert event_score_record["latent_backend_name"] == expected_latent_sample.latent_backend_name
        assert event_score_record["latent_backend_status"] == expected_latent_sample.latent_backend_status
        assert (
            event_score_record["latent_tensor_digest_random"]
            == expected_latent_sample.latent_tensor_digest_random
        )
        assert (
            event_score_record["latent_generation_seed_random"]
            == expected_latent_sample.latent_generation_seed_random
        )
        assert {
            "latent_generation_seed_random",
            "latent_tensor_digest_random",
        }.issubset(set(event_score_record["random_fields"]))

    empty_method_record = next(
        event_score_record
        for event_score_record in event_score_records
        if event_score_record["method_variant"] == "empty_watermark_method_placeholder"
        and event_score_record["split"] == "test"
        and event_score_record["sample_role"] == "watermarked_positive"
    )
    assert empty_method_record["evidence_scores"]["S_tubelet"] is None
    assert empty_method_record["evidence_scores"]["S_sync"] is None
    assert empty_method_record["evidence_scores"]["S_traj"] is None
    assert empty_method_record["evidence_scores"]["S_final"] == 0.0
    assert empty_method_record["random_fields"] == [
        "latent_generation_seed_random",
        "latent_tensor_digest_random",
    ]

    random_method_record = next(
        event_score_record
        for event_score_record in event_score_records
        if event_score_record["method_variant"] == "random_score_detector_random"
        and event_score_record["split"] == "test"
        and event_score_record["sample_role"] == "clean_negative"
    )
    assert random_method_record["evidence_scores"]["S_tubelet"] is not None
    assert random_method_record["evidence_scores"]["S_sync"] is not None
    assert random_method_record["evidence_scores"]["S_traj"] is None
    assert random_method_record["random_fields"] == [
        "latent_generation_seed_random",
        "latent_tensor_digest_random",
        "S_tubelet",
        "S_sync",
        "S_final",
    ]

    for threshold_record in threshold_records:
        validate_threshold_record(threshold_record)

    validate_run_manifest_record(run_manifest)
"""
文件用途：验证阶段 0 threshold calibration 不发生 test leakage。
File purpose: Validate that stage-0 threshold calibration does not leak test data.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.core.digest import compute_object_digest
from main.core.records import RecordWriter
from main.protocol.ablation_runner import AblationRunner


ROOT = Path(__file__).resolve().parents[1]


def test_threshold_source_digest_uses_only_calibration_negatives(tmp_path: Path) -> None:
    """Validate that threshold traceability uses only calibration-negative records.

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

    for threshold_record in threshold_records:
        method_variant = threshold_record["method_variant"]
        calibration_negative_records = [
            event_score_record
            for event_score_record in event_score_records
            if event_score_record["method_variant"] == method_variant
            and event_score_record["split"] == "calibration"
            and event_score_record["sample_role"] in {"clean_negative", "attacked_negative"}
        ]
        test_records = [
            event_score_record
            for event_score_record in event_score_records
            if event_score_record["method_variant"] == method_variant
            and event_score_record["split"] == "test"
        ]
        expected_digest = compute_object_digest(
            sorted(event_score_record["event_id"] for event_score_record in calibration_negative_records)
        )
        test_digest = compute_object_digest(
            sorted(event_score_record["event_id"] for event_score_record in test_records)
        )

        assert threshold_record["threshold_source_record_digest"] == expected_digest
        assert threshold_record["threshold_source_record_digest"] != test_digest
        assert all(event_score_record["threshold_id"] is None for event_score_record in calibration_negative_records)
        assert all(
            event_score_record["threshold_id"] == threshold_record["threshold_id"]
            for event_score_record in test_records
        )
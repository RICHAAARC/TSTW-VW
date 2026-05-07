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


def _build_threshold_source_payload(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Build the expected threshold source payload for test assertions.

    Args:
        records: Candidate threshold source records.

    Returns:
        The ordered payload expected by threshold tracing.
    """
    return [
        {
            "event_id": record["event_id"],
            "sample_id": record["sample_id"],
            "split": record["split"],
            "sample_role": record["sample_role"],
            "method_variant": record["method_variant"],
            "attack_name": record["attack_name"],
            "S_final": record["evidence_scores"]["S_final"],
        }
        for record in sorted(records, key=lambda item: item["event_id"])
    ]


def test_threshold_source_digest_uses_only_calibration_negatives(tmp_path: Path) -> None:
    """Validate that threshold traceability uses only calibration-negative records.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "protocol_skeleton_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2, runtime_profile_override="tiny")
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
        expected_payload = _build_threshold_source_payload(calibration_negative_records)
        expected_digest = compute_object_digest(expected_payload)
        digest_with_test_records = compute_object_digest(
            _build_threshold_source_payload(calibration_negative_records + test_records)
        )
        mutated_payload = [
            {
                **payload_item,
                "S_final": round(float(payload_item["S_final"]) + 1.0, 6),
            }
            if payload_index == 0
            else payload_item
            for payload_index, payload_item in enumerate(expected_payload)
        ]

        assert expected_payload
        assert set(expected_payload[0].keys()) == {
            "event_id",
            "sample_id",
            "split",
            "sample_role",
            "method_variant",
            "attack_name",
            "S_final",
        }
        assert all(payload_item["split"] == "calibration" for payload_item in expected_payload)
        assert threshold_record["threshold_source_record_digest"] == expected_digest
        assert threshold_record["threshold_source_record_digest"] != digest_with_test_records
        assert compute_object_digest(mutated_payload) != expected_digest
        assert all(event_score_record["threshold_id"] is None for event_score_record in calibration_negative_records)
        assert all(
            event_score_record["threshold_id"] == threshold_record["threshold_id"]
            for event_score_record in test_records
        )
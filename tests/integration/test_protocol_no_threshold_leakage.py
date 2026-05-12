"""
文件用途：验证阶段 0 threshold calibration 不发生 test leakage。
File purpose: Validate that protocol skeleton runtime threshold calibration does not leak test data.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from experiments.protocol_skeleton.ablation_runner import AblationRunner as StageZeroAblationRunner
from experiments.synthetic_tubelet_sync_probe.ablation_runner import (
    AblationRunner as SyntheticTubeletSyncAblationRunner,
)
from main.core.digest import compute_object_digest
from main.core.records import RecordWriter


ROOT = Path(__file__).resolve().parents[2]


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


@pytest.mark.smoke
def test_threshold_source_digest_uses_only_calibration_negatives(tmp_path: Path) -> None:
    """Validate that threshold traceability uses only calibration-negative records.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "protocol_skeleton_run"
    StageZeroAblationRunner(ROOT).run(
        output_root,
        samples_per_role=2,
        runtime_profile_override="tiny",
    )
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


@pytest.mark.smoke
def test_threshold_guard_bands_are_config_declared_and_calibration_only(tmp_path: Path) -> None:
    """Validate that guard-band fields are materialized from protocol config.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "protocol_guard_band_run"
    SyntheticTubeletSyncAblationRunner(ROOT).run(
        output_root,
        samples_per_role=2,
        runtime_profile_override="tiny",
    )
    record_writer = RecordWriter(output_root)
    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    protocol_config = json.loads(
        (
            ROOT
            / "experiments"
            / "synthetic_tubelet_sync_probe"
            / "configs"
            / "protocol"
            / "synthetic_tubelet_sync_probe.json"
        ).read_text(encoding="utf-8")
    )
    threshold_protocol = protocol_config["threshold_protocol"]
    runtime_profile = "tiny"
    sync_guard_band = threshold_protocol["sync_threshold_guard_band_multiplier_by_profile"][
        runtime_profile
    ]
    tubelet_guard_band_map = threshold_protocol[
        "tubelet_length_threshold_guard_band_multiplier_by_profile"
    ][runtime_profile]

    for threshold_record in threshold_records:
        method_variant = threshold_record["method_variant"]
        variant_records = [
            event_score_record
            for event_score_record in event_score_records
            if event_score_record["method_variant"] == method_variant
        ]
        assert variant_records
        base_method_variant = variant_records[0]["base_method_variant"]
        tubelet_length = int(variant_records[0]["tubelet_length"])
        expected_sync_guard = sync_guard_band if base_method_variant == "tubelet_sync" else 0.0
        expected_tubelet_guard = float(tubelet_guard_band_map["default"])
        if tubelet_length >= 16:
            expected_tubelet_guard = float(tubelet_guard_band_map["length_ge_16"])
        elif tubelet_length >= 8:
            expected_tubelet_guard = float(tubelet_guard_band_map["length_ge_08"])

        assert threshold_record["sync_threshold_guard_band_multiplier"] == expected_sync_guard
        assert (
            threshold_record["tubelet_length_threshold_guard_band_multiplier"]
            == expected_tubelet_guard
        )
        assert threshold_record["applied_threshold_guard_band_multiplier"] == max(
            expected_sync_guard,
            expected_tubelet_guard,
        )

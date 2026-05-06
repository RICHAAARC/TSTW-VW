"""
文件用途：实现阶段 0 的 threshold calibrator 骨架。
File purpose: Implement the stage-0 threshold calibrator scaffold.
Module type: General module
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from main.core.digest import compute_object_digest
from main.core.schema import METHOD_FAMILY_NAME, NEGATIVE_SAMPLE_ROLES, PROTOCOL_NAME, validate_threshold_record


class ThresholdCalibrator:
    """功能：根据 calibration negative records 生成固定阈值。

    Calibrator for stage-0 fixed low-FPR thresholds.

    Args:
        None.

    Returns:
        None.
    """

    def calibrate(
        self,
        run_id: str,
        method_config: dict[str, Any],
        protocol_config: dict[str, Any],
        calibration_event_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """功能：从 calibration negative records 生成 threshold record。

        Build a threshold record using calibration-negative event records only.

        Args:
            run_id: Stable run identifier.
            method_config: Parsed method config.
            protocol_config: Parsed protocol config.
            calibration_event_records: Candidate calibration event records.

        Returns:
            A governed threshold record.
        """
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id must be a non-empty string")
        if not isinstance(method_config, dict):
            raise TypeError("method_config must be a dictionary")
        if not isinstance(protocol_config, dict):
            raise TypeError("protocol_config must be a dictionary")
        if not isinstance(calibration_event_records, list) or not calibration_event_records:
            raise ValueError("calibration_event_records must be a non-empty list")

        threshold_protocol = protocol_config["threshold_protocol"]
        target_fpr = float(threshold_protocol["target_fpr_placeholder"])
        calibration_negative_records = [
            event_record
            for event_record in calibration_event_records
            if event_record["split"] == threshold_protocol["calibration_split"]
            and event_record["sample_role"] in NEGATIVE_SAMPLE_ROLES
        ]
        if not calibration_negative_records:
            raise ValueError("no calibration negative records were provided")

        calibration_scores = [
            float(event_record["evidence_scores"]["S_final"])
            for event_record in calibration_negative_records
            if event_record["evidence_scores"]["S_final"] is not None
        ]
        if not calibration_scores:
            raise ValueError("calibration scores must not be empty")

        threshold_quantile = 1.0 - target_fpr
        threshold_index = max(
            0,
            min(
                len(calibration_scores) - 1,
                math.ceil(threshold_quantile * len(calibration_scores)) - 1,
            ),
        )
        threshold_value = sorted(calibration_scores)[threshold_index]
        threshold_source_record_digest = compute_object_digest(
            sorted(event_record["event_id"] for event_record in calibration_negative_records)
        )

        threshold_record = {
            "threshold_id": (
                f"{PROTOCOL_NAME}:S_final:{method_config['method_variant']}"
            ),
            "run_id": run_id,
            "method_family": METHOD_FAMILY_NAME,
            "method_variant": method_config["method_variant"],
            "score_name": "S_final",
            "target_fpr": target_fpr,
            "calibration_split": threshold_protocol["calibration_split"],
            "calibration_negative_roles": threshold_protocol["calibration_negative_roles"],
            "threshold_value": round(threshold_value, 6),
            "threshold_quantile": threshold_quantile,
            "num_calibration_negatives": len(calibration_negative_records),
            "threshold_source_record_digest": threshold_source_record_digest,
            "fusion_rule": method_config["fusion_rule"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        validate_threshold_record(threshold_record)
        return threshold_record
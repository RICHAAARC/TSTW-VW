"""
File purpose: Implement the governed threshold calibrator for protocol skeleton and synthetic tubelet-sync probe.
Module type: General module
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import pstdev
from typing import Any

from main.core.digest import compute_object_digest
from main.core.schema import NEGATIVE_SAMPLE_ROLES, PROTOCOL_NAME, validate_threshold_record


def _build_threshold_source_payload(
    calibration_negative_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """功能：构建阈值来源的最小稳定 payload。

    Build the minimal stable payload used to trace threshold construction.

    Args:
        calibration_negative_records: Calibration-negative event records.

    Returns:
        An ordered source payload for digest construction.
    """
    if not isinstance(calibration_negative_records, list) or not calibration_negative_records:
        raise ValueError("calibration_negative_records must be a non-empty list")

    return [
        {
            "event_id": event_record["event_id"],
            "sample_id": event_record["sample_id"],
            "split": event_record["split"],
            "sample_role": event_record["sample_role"],
            "method_variant": event_record["method_variant"],
            "attack_name": event_record["attack_name"],
            "S_final": event_record["evidence_scores"]["S_final"],
        }
        for event_record in sorted(
            calibration_negative_records,
            key=lambda item: item["event_id"],
        )
    ]


def _resolve_profile_float(
    profile_values: dict[str, Any],
    runtime_profile: str,
    default_value: float,
) -> float:
    if not isinstance(profile_values, dict):
        return float(default_value)
    resolved_value = profile_values.get(runtime_profile, default_value)
    if not isinstance(resolved_value, (int, float)):
        return float(default_value)
    return float(resolved_value)


def _resolve_profile_mapping(
    profile_values: dict[str, Any],
    runtime_profile: str,
) -> dict[str, Any]:
    if not isinstance(profile_values, dict):
        return {}
    resolved_value = profile_values.get(runtime_profile, {})
    if not isinstance(resolved_value, dict):
        return {}
    return resolved_value


def _resolve_tubelet_length_guard_band_multiplier(
    threshold_protocol: dict[str, Any],
    runtime_profile: str,
    method_config: dict[str, Any],
) -> float:
    profile_mapping = _resolve_profile_mapping(
        threshold_protocol.get(
            "tubelet_length_threshold_guard_band_multiplier_by_profile",
            {},
        ),
        runtime_profile,
    )
    default_value = profile_mapping.get("default", 0.0)
    if not isinstance(default_value, (int, float)):
        default_value = 0.0

    tubelet_length = method_config.get("tubelet_length", 1)
    if not isinstance(tubelet_length, int) or tubelet_length < 1:
        tubelet_length = 1

    if tubelet_length >= 16:
        resolved_value = profile_mapping.get("length_ge_16", default_value)
        if isinstance(resolved_value, (int, float)):
            return float(resolved_value)
    if tubelet_length >= 8:
        resolved_value = profile_mapping.get("length_ge_08", default_value)
        if isinstance(resolved_value, (int, float)):
            return float(resolved_value)
    return float(default_value)


class ThresholdCalibrator:
    """功能：根据 calibration negative records 生成固定阈值。

    Calibrator for governed fixed low-FPR thresholds.

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
        runtime_profile_override: str | None = None,
    ) -> dict[str, Any]:
        """功能：从 calibration negative records 生成 threshold record。

        Build a threshold record using calibration-negative event records only.

        Args:
            run_id: Stable run identifier.
            method_config: Parsed method config.
            protocol_config: Parsed protocol config.
            calibration_event_records: Candidate calibration event records.
            runtime_profile_override: Optional explicit runtime profile for threshold semantics.

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
        if runtime_profile_override is not None:
            if not isinstance(runtime_profile_override, str) or not runtime_profile_override.strip():
                # 显式 runtime profile 覆盖必须可解析，避免阈值语义回落到错误 profile。
                raise ValueError(
                    "runtime_profile_override must be a non-empty string when provided"
                )
        if not isinstance(method_config.get("method_family"), str) or not method_config[
            "method_family"
        ]:
            raise ValueError("method_config method_family must be a non-empty string")
        if not isinstance(method_config.get("method_variant"), str) or not method_config[
            "method_variant"
        ]:
            raise ValueError("method_config method_variant must be a non-empty string")

        threshold_protocol = protocol_config["threshold_protocol"]
        target_fpr = float(threshold_protocol["target_fpr_placeholder"])
        runtime_profile = (
            runtime_profile_override.strip()
            if runtime_profile_override is not None
            else str(protocol_config.get("runtime_profile", "smoke"))
        )
        validation_target_fpr = _resolve_profile_float(
            threshold_protocol.get("validation_target_fpr_by_profile", {}),
            runtime_profile,
            target_fpr,
        )
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
        sync_guard_band_multiplier = 0.0
        if bool(method_config.get("enable_sync", False)) or (
            method_config.get("fusion_rule") == "calibrated_tubelet_sync"
        ):
            sync_guard_band_multiplier = _resolve_profile_float(
                threshold_protocol.get("sync_threshold_guard_band_multiplier_by_profile", {}),
                runtime_profile,
                0.0,
            )
        tubelet_length_guard_band_multiplier = (
            _resolve_tubelet_length_guard_band_multiplier(
                threshold_protocol,
                runtime_profile,
                method_config,
            )
        )
        applied_guard_band_multiplier = max(
            sync_guard_band_multiplier,
            tubelet_length_guard_band_multiplier,
        )
        if applied_guard_band_multiplier > 0.0 and len(calibration_scores) > 1:
            threshold_value += pstdev(calibration_scores) * applied_guard_band_multiplier
        threshold_source_record_digest = compute_object_digest(
            _build_threshold_source_payload(calibration_negative_records)
        )

        threshold_record = {
            "threshold_id": (
                f"{PROTOCOL_NAME}:S_final:{method_config['method_variant']}"
            ),
            "run_id": run_id,
            "method_family": method_config["method_family"],
            "method_variant": method_config["method_variant"],
            "score_name": "S_final",
            "target_fpr": target_fpr,
            "validation_target_fpr": round(validation_target_fpr, 6),
            "runtime_profile": runtime_profile,
            "calibration_split": threshold_protocol["calibration_split"],
            "calibration_negative_roles": threshold_protocol["calibration_negative_roles"],
            "threshold_value": round(threshold_value, 6),
            "threshold_quantile": threshold_quantile,
            "sync_threshold_guard_band_multiplier": round(sync_guard_band_multiplier, 6),
            "tubelet_length_threshold_guard_band_multiplier": round(
                tubelet_length_guard_band_multiplier,
                6,
            ),
            "applied_threshold_guard_band_multiplier": round(
                applied_guard_band_multiplier,
                6,
            ),
            "num_calibration_negatives": len(calibration_negative_records),
            "threshold_source_record_digest": threshold_source_record_digest,
            "fusion_rule": method_config["fusion_rule"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        validate_threshold_record(threshold_record)
        return threshold_record

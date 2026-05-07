"""
文件用途：根据 event records 生成阶段 0 统计指标。
File purpose: Build stage-0 metrics from governed event records.
Module type: General module
"""

from __future__ import annotations

from typing import Any


MAIN_METRICS_COLUMNS = [
    "run_id",
    "method_family",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "target_fpr",
    "threshold_id",
    "split",
    "attack_name",
    "clean_negative_count",
    "attacked_negative_count",
    "watermarked_positive_count",
    "attacked_positive_count",
    "clean_negative_FPR",
    "attacked_negative_FPR",
    "clean_positive_TPR",
    "attacked_positive_TPR",
]
ABLATION_TABLE_COLUMNS = [
    "run_id",
    "method_family",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "enabled_tubelet_evidence",
    "enabled_sync_evidence",
    "enabled_trajectory_evidence",
    "fusion_rule",
    "threshold_id",
    "clean_negative_FPR",
    "attacked_negative_FPR",
    "clean_positive_TPR",
    "attacked_positive_TPR",
]
LOCAL_CLIP_CURVE_COLUMNS = [
    "run_id",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "clip_length",
    "local_clip_TPR",
    "local_clip_FPR",
    "positive_count",
    "negative_count",
    "threshold_id",
]
TEMPORAL_ATTACK_CURVE_COLUMNS = [
    "run_id",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "attack_name",
    "attack_strength",
    "sample_role",
    "TPR",
    "FPR",
    "count",
    "threshold_id",
]
TUBELET_LENGTH_ABLATION_COLUMNS = [
    "run_id",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "attack_name",
    "attacked_positive_TPR",
    "attacked_negative_FPR",
    "sync_alignment_error_mean",
    "sync_peak_rank_median",
]


def _safe_rate(true_count: int, total_count: int) -> float:
    if total_count == 0:
        return 0.0
    return round(true_count / total_count, 6)


def build_main_metrics_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """功能：构建主指标表行。

    Build rows for the governed main metrics table.

    Args:
        event_score_records: Governed event score records.
        threshold_records: Governed threshold records.

    Returns:
        A list of main-metrics row dictionaries.
    """
    if not isinstance(event_score_records, list):
        raise TypeError("event_score_records must be a list")
    if not isinstance(threshold_records, list):
        raise TypeError("threshold_records must be a list")

    threshold_map = {
        threshold_record["method_variant"]: threshold_record
        for threshold_record in threshold_records
    }
    rows: list[dict[str, Any]] = []

    for method_variant in sorted({record["method_variant"] for record in event_score_records}):
        variant_test_records = [
            record
            for record in event_score_records
            if record["method_variant"] == method_variant and record["split"] == "test"
        ]
        if not variant_test_records:
            continue
        for attack_name in sorted({record["attack_name"] for record in variant_test_records}):
            attack_records = [
                record for record in variant_test_records if record["attack_name"] == attack_name
            ]
            threshold_record = threshold_map[method_variant]
            variant_metadata = _build_variant_metadata(attack_records[0])
            rows.append(
                {
                    "run_id": attack_records[0]["run_id"],
                    "method_family": attack_records[0]["method_family"],
                    "method_variant": method_variant,
                    **variant_metadata,
                    "target_fpr": attack_records[0]["target_fpr"],
                    "threshold_id": threshold_record["threshold_id"],
                    "split": "test",
                    "attack_name": attack_name,
                    "clean_negative_count": _count_role(attack_records, "clean_negative"),
                    "attacked_negative_count": _count_role(attack_records, "attacked_negative"),
                    "watermarked_positive_count": _count_role(
                        attack_records, "watermarked_positive"
                    ),
                    "attacked_positive_count": _count_role(attack_records, "attacked_positive"),
                    "clean_negative_FPR": _rate_for_role(attack_records, "clean_negative"),
                    "attacked_negative_FPR": _rate_for_role(
                        attack_records, "attacked_negative"
                    ),
                    "clean_positive_TPR": _rate_for_role(
                        attack_records, "watermarked_positive"
                    ),
                    "attacked_positive_TPR": _rate_for_role(
                        attack_records, "attacked_positive"
                    ),
                }
            )
    return rows


def build_ablation_table_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """功能：构建消融表行。

    Build rows for the governed ablation table.

    Args:
        event_score_records: Governed event score records.
        threshold_records: Governed threshold records.

    Returns:
        A list of ablation-table row dictionaries.
    """
    if not isinstance(event_score_records, list):
        raise TypeError("event_score_records must be a list")
    if not isinstance(threshold_records, list):
        raise TypeError("threshold_records must be a list")

    threshold_map = {
        threshold_record["method_variant"]: threshold_record
        for threshold_record in threshold_records
    }
    rows: list[dict[str, Any]] = []

    for method_variant in sorted({record["method_variant"] for record in event_score_records}):
        variant_test_records = [
            record
            for record in event_score_records
            if record["method_variant"] == method_variant and record["split"] == "test"
        ]
        if not variant_test_records:
            continue
        threshold_record = threshold_map[method_variant]
        variant_metadata = _build_variant_metadata(variant_test_records[0])
        rows.append(
            {
                "run_id": variant_test_records[0]["run_id"],
                "method_family": variant_test_records[0]["method_family"],
                "method_variant": method_variant,
                **variant_metadata,
                "enabled_tubelet_evidence": _is_evidence_enabled(
                    variant_test_records, "S_tubelet"
                ),
                "enabled_sync_evidence": _is_evidence_enabled(variant_test_records, "S_sync"),
                "enabled_trajectory_evidence": _is_evidence_enabled(
                    variant_test_records, "S_traj"
                ),
                "fusion_rule": threshold_record["fusion_rule"],
                "threshold_id": threshold_record["threshold_id"],
                "clean_negative_FPR": _rate_for_role(variant_test_records, "clean_negative"),
                "attacked_negative_FPR": _rate_for_role(
                    variant_test_records, "attacked_negative"
                ),
                "clean_positive_TPR": _rate_for_role(
                    variant_test_records, "watermarked_positive"
                ),
                "attacked_positive_TPR": _rate_for_role(
                    variant_test_records, "attacked_positive"
                ),
            }
        )
    return rows


def build_local_clip_curve_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """功能：构建 local clip curve 表行。

    Build rows for the governed local-clip curve table.

    Args:
        event_score_records: Governed event score records.
        threshold_records: Governed threshold records.

    Returns:
        A list of local-clip curve row dictionaries.
    """
    threshold_map = {
        threshold_record["method_variant"]: threshold_record
        for threshold_record in threshold_records
    }
    rows: list[dict[str, Any]] = []
    local_clip_records = [
        record
        for record in event_score_records
        if record["split"] == "test" and record["attack_name"] == "local_clip"
    ]
    for method_variant in sorted({record["method_variant"] for record in local_clip_records}):
        variant_records = [
            record for record in local_clip_records if record["method_variant"] == method_variant
        ]
        for clip_length in sorted(
            {
                int(record["attack_params"].get("clip_length", 0))
                for record in variant_records
            }
        ):
            grouped_records = [
                record
                for record in variant_records
                if int(record["attack_params"].get("clip_length", 0)) == clip_length
            ]
            positive_records = [
                record for record in grouped_records if record["sample_role"] == "attacked_positive"
            ]
            negative_records = [
                record for record in grouped_records if record["sample_role"] == "attacked_negative"
            ]
            rows.append(
                {
                    "run_id": grouped_records[0]["run_id"],
                    "method_variant": method_variant,
                    **_build_variant_metadata(grouped_records[0]),
                    "clip_length": clip_length,
                    "local_clip_TPR": _safe_rate(
                        sum(1 for record in positive_records if record["decision"]),
                        len(positive_records),
                    ),
                    "local_clip_FPR": _safe_rate(
                        sum(1 for record in negative_records if record["decision"]),
                        len(negative_records),
                    ),
                    "positive_count": len(positive_records),
                    "negative_count": len(negative_records),
                    "threshold_id": threshold_map[method_variant]["threshold_id"],
                }
            )
    return rows


def build_temporal_attack_curve_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """功能：构建 temporal attack curve 表行。

    Build rows for the governed temporal-attack curve table.

    Args:
        event_score_records: Governed event score records.
        threshold_records: Governed threshold records.

    Returns:
        A list of temporal-attack curve row dictionaries.
    """
    threshold_map = {
        threshold_record["method_variant"]: threshold_record
        for threshold_record in threshold_records
    }
    rows: list[dict[str, Any]] = []
    curve_records = [record for record in event_score_records if record["split"] == "test"]
    for method_variant in sorted({record["method_variant"] for record in curve_records}):
        variant_records = [
            record for record in curve_records if record["method_variant"] == method_variant
        ]
        for attack_name in sorted({record["attack_name"] for record in variant_records}):
            attack_records = [
                record for record in variant_records if record["attack_name"] == attack_name
            ]
            attack_strengths = sorted(
                {
                    _derive_attack_strength(record)
                    for record in attack_records
                }
            )
            for attack_strength in attack_strengths:
                strength_records = [
                    record
                    for record in attack_records
                    if _derive_attack_strength(record) == attack_strength
                ]
                for sample_role in sorted({record["sample_role"] for record in strength_records}):
                    grouped_records = [
                        record for record in strength_records if record["sample_role"] == sample_role
                    ]
                    rows.append(
                        {
                            "run_id": grouped_records[0]["run_id"],
                            "method_variant": method_variant,
                            **_build_variant_metadata(grouped_records[0]),
                            "attack_name": attack_name,
                            "attack_strength": attack_strength,
                            "sample_role": sample_role,
                            "TPR": (
                                _safe_rate(
                                    sum(1 for record in grouped_records if record["decision"]),
                                    len(grouped_records),
                                )
                                if sample_role.endswith("positive")
                                else None
                            ),
                            "FPR": (
                                _safe_rate(
                                    sum(1 for record in grouped_records if record["decision"]),
                                    len(grouped_records),
                                )
                                if sample_role.endswith("negative")
                                else None
                            ),
                            "count": len(grouped_records),
                            "threshold_id": threshold_map[method_variant]["threshold_id"],
                        }
                    )
    return rows


def build_tubelet_length_ablation_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """功能：构建 tubelet length ablation 表行。

    Build rows for the governed tubelet-length ablation table.

    Args:
        event_score_records: Governed event score records.
        threshold_records: Governed threshold records.

    Returns:
        A list of tubelet-length ablation row dictionaries.
    """
    del threshold_records
    rows: list[dict[str, Any]] = []
    curve_records = [record for record in event_score_records if record["split"] == "test"]
    for method_variant in sorted({record["method_variant"] for record in curve_records}):
        variant_records = [
            record for record in curve_records if record["method_variant"] == method_variant
        ]
        tubelet_length = int(
            next(
                record["mechanism_trace"]["tubelet_length"]
                for record in variant_records
                if record["mechanism_trace"].get("tubelet_length") is not None
            )
        )
        for attack_name in sorted({record["attack_name"] for record in variant_records}):
            attack_records = [
                record for record in variant_records if record["attack_name"] == attack_name
            ]
            attacked_positive_records = [
                record for record in attack_records if record["sample_role"] == "attacked_positive"
            ]
            attacked_negative_records = [
                record for record in attack_records if record["sample_role"] == "attacked_negative"
            ]
            positive_sync_records = [
                record
                for record in attacked_positive_records
                if record["mechanism_trace"].get("sync_alignment_error") is not None
            ]
            rows.append(
                {
                    "run_id": attack_records[0]["run_id"],
                    "method_variant": method_variant,
                    **_build_variant_metadata(attack_records[0]),
                    "tubelet_length": tubelet_length,
                    "attack_name": attack_name,
                    "attacked_positive_TPR": _safe_rate(
                        sum(1 for record in attacked_positive_records if record["decision"]),
                        len(attacked_positive_records),
                    ),
                    "attacked_negative_FPR": _safe_rate(
                        sum(1 for record in attacked_negative_records if record["decision"]),
                        len(attacked_negative_records),
                    ),
                    "sync_alignment_error_mean": _mean_numeric_field(
                        positive_sync_records,
                        "sync_alignment_error",
                    ),
                    "sync_peak_rank_median": _median_numeric_field(
                        positive_sync_records,
                        "sync_peak_rank",
                    ),
                }
            )
    return rows


def _count_role(event_score_records: list[dict[str, Any]], sample_role: str) -> int:
    return sum(1 for record in event_score_records if record["sample_role"] == sample_role)


def _rate_for_role(event_score_records: list[dict[str, Any]], sample_role: str) -> float:
    role_records = [record for record in event_score_records if record["sample_role"] == sample_role]
    return _safe_rate(sum(1 for record in role_records if record["decision"]), len(role_records))


def _is_evidence_enabled(event_score_records: list[dict[str, Any]], score_name: str) -> bool:
    return any(record["evidence_scores"][score_name] is not None for record in event_score_records)


def _build_variant_metadata(event_score_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "base_method_variant": event_score_record["base_method_variant"],
        "derived_variant": event_score_record["derived_variant"],
        "ablation_axis": event_score_record["ablation_axis"],
        "tubelet_length": event_score_record["tubelet_length"],
    }


def _derive_attack_strength(event_score_record: list[dict[str, Any]] | dict[str, Any]) -> float | int:
    record = event_score_record[0] if isinstance(event_score_record, list) else event_score_record
    attack_params = record.get("attack_params", {})
    attack_name = record.get("attack_name")
    if attack_name == "local_clip":
        return int(attack_params.get("clip_length", 0))
    if attack_name == "temporal_crop":
        return int(attack_params.get("crop_length", 0))
    if attack_name == "frame_dropping":
        return float(attack_params.get("drop_rate", 0.0))
    if attack_name == "speed_change":
        return float(attack_params.get("speed_ratio", 0.0))
    if attack_name == "latent_gaussian_noise":
        return float(attack_params.get("sigma", 0.0))
    return 0


def _mean_numeric_field(event_score_records: list[dict[str, Any]], field_name: str) -> float | None:
    values = [
        float(record["mechanism_trace"][field_name])
        for record in event_score_records
        if record["mechanism_trace"].get(field_name) is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _median_numeric_field(event_score_records: list[dict[str, Any]], field_name: str) -> float | int | None:
    values = sorted(
        record["mechanism_trace"][field_name]
        for record in event_score_records
        if record["mechanism_trace"].get(field_name) is not None
    )
    if not values:
        return None
    middle_index = len(values) // 2
    if len(values) % 2 == 1:
        return values[middle_index]
    return round((float(values[middle_index - 1]) + float(values[middle_index])) / 2.0, 6)
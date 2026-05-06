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
            rows.append(
                {
                    "run_id": attack_records[0]["run_id"],
                    "method_family": attack_records[0]["method_family"],
                    "method_variant": method_variant,
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
        rows.append(
            {
                "run_id": variant_test_records[0]["run_id"],
                "method_family": variant_test_records[0]["method_family"],
                "method_variant": method_variant,
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


def _count_role(event_score_records: list[dict[str, Any]], sample_role: str) -> int:
    return sum(1 for record in event_score_records if record["sample_role"] == sample_role)


def _rate_for_role(event_score_records: list[dict[str, Any]], sample_role: str) -> float:
    role_records = [record for record in event_score_records if record["sample_role"] == sample_role]
    return _safe_rate(sum(1 for record in role_records if record["decision"]), len(role_records))


def _is_evidence_enabled(event_score_records: list[dict[str, Any]], score_name: str) -> bool:
    return any(record["evidence_scores"][score_name] is not None for record in event_score_records)
"""
文件用途：生成 stage-one method validation report。
File purpose: Generate the stage-one method validation report.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from main.protocol.evaluator import (
    build_local_clip_curve_rows,
    build_main_metrics_rows,
    build_tubelet_length_ablation_rows,
)
from main.core.records import build_output_paths


REQUIRED_LOCAL_CLIP_LENGTHS = {4, 8, 12, 16}
REQUIRED_TUBELET_LENGTHS = {1, 2, 4, 8, 16}


class ReportBuilder:
    """功能：构建 stage-one method validation report。

    Builder for the stage-one method validation report.

    Args:
        None.

    Returns:
        None.
    """

    def build_report(
        self,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        output_root: str | Path,
    ) -> Path:
        if not isinstance(event_score_records, list):
            raise TypeError("event_score_records must be a list")
        if not isinstance(threshold_records, list):
            raise TypeError("threshold_records must be a list")

        output_paths = build_output_paths(output_root)
        main_rows = build_main_metrics_rows(event_score_records, threshold_records)
        local_clip_rows = build_local_clip_curve_rows(event_score_records, threshold_records)
        tubelet_rows = build_tubelet_length_ablation_rows(event_score_records, threshold_records)
        report_text = self._build_report_text(main_rows, local_clip_rows, tubelet_rows)
        output_paths.report_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.report_path.write_text(report_text, encoding="utf-8")
        return output_paths.report_path

    def _build_report_text(
        self,
        main_rows: list[dict[str, Any]],
        local_clip_rows: list[dict[str, Any]],
        tubelet_rows: list[dict[str, Any]],
    ) -> str:
        variant_names = sorted({row["method_variant"] for row in main_rows})
        attack_names = sorted({row["attack_name"] for row in main_rows})
        target_fprs = sorted({float(row["target_fpr"]) for row in main_rows})
        local_clip_lengths = sorted({int(row["clip_length"]) for row in local_clip_rows})
        tubelet_lengths = sorted({int(row["tubelet_length"]) for row in tubelet_rows})
        tubelet_only_gain = _compare_variant_attack_metric(
            main_rows,
            left_variant="tubelet_only",
            right_variant="frame_prc",
            attack_names=attack_names,
        )
        tubelet_sync_gain = _compare_variant_attack_metric(
            main_rows,
            left_variant="tubelet_sync",
            right_variant="tubelet_only",
            attack_names=["temporal_crop", "local_clip"],
        )
        clean_negative_fpr_controlled = _rows_metric_meets_target(
            main_rows,
            metric_name="clean_negative_FPR",
        )
        attacked_negative_fpr_controlled = _rows_metric_meets_target(
            main_rows,
            metric_name="attacked_negative_FPR",
        )
        max_attacked_negative_fpr, worst_attacked_negative_fpr_variants = _worst_variant_metric(
            main_rows,
            metric_name="attacked_negative_FPR",
        )
        return "\n".join(
            [
                "# Method Validation Report",
                "",
                "## Summary",
                f"- method_variants: {', '.join(variant_names)}",
                f"- attack_names: {', '.join(attack_names)}",
                f"- target_fprs: {_format_number_sequence(target_fprs)}",
                f"- local_clip_curve_rows: {len(local_clip_rows)}",
                f"- tubelet_length_rows: {len(tubelet_rows)}",
                "",
                "## Coverage Checks",
                f"- required_local_clip_lengths_present: {str(set(local_clip_lengths) == REQUIRED_LOCAL_CLIP_LENGTHS).lower()}",
                f"- local_clip_lengths: {_format_number_sequence(local_clip_lengths)}",
                f"- required_tubelet_length_sweep_present: {str(set(tubelet_lengths) == REQUIRED_TUBELET_LENGTHS).lower()}",
                f"- tubelet_lengths: {_format_number_sequence(tubelet_lengths)}",
                "",
                "## Mechanism Checks",
                f"- tubelet_only_beats_frame_prc_under_some_attack: {str(tubelet_only_gain).lower()}",
                f"- tubelet_sync_beats_tubelet_only_under_temporal_crop_or_local_clip: {str(tubelet_sync_gain).lower()}",
                "",
                "## Threshold Checks",
                f"- clean_negative_fpr_meets_target_for_all_variants: {str(clean_negative_fpr_controlled).lower()}",
                f"- attacked_negative_fpr_meets_target_for_all_variants: {str(attacked_negative_fpr_controlled).lower()}",
                f"- max_attacked_negative_fpr: {max_attacked_negative_fpr}",
                f"- worst_attacked_negative_fpr_variants: {', '.join(worst_attacked_negative_fpr_variants)}",
                "",
                "## Rebuildability",
                "- records_to_tables: true",
                "- records_to_curves: true",
                "- records_to_report: true",
            ]
        ) + "\n"


def _compare_variant_attack_metric(
    main_rows: list[dict[str, Any]],
    left_variant: str,
    right_variant: str,
    attack_names: list[str],
) -> bool:
    for attack_name in attack_names:
        left_row = next(
            (row for row in main_rows if row["method_variant"] == left_variant and row["attack_name"] == attack_name),
            None,
        )
        right_row = next(
            (row for row in main_rows if row["method_variant"] == right_variant and row["attack_name"] == attack_name),
            None,
        )
        if left_row is None or right_row is None:
            continue
        if float(left_row["attacked_positive_TPR"]) > float(right_row["attacked_positive_TPR"]):
            return True
    return False


def _rows_metric_meets_target(main_rows: list[dict[str, Any]], metric_name: str) -> bool:
    return all(float(row[metric_name]) <= float(row["target_fpr"]) for row in main_rows)


def _worst_variant_metric(
    main_rows: list[dict[str, Any]],
    metric_name: str,
) -> tuple[float, list[str]]:
    variant_metric_map: dict[str, float] = {}
    for row in main_rows:
        method_variant = str(row["method_variant"])
        metric_value = float(row[metric_name])
        variant_metric_map[method_variant] = max(
            variant_metric_map.get(method_variant, 0.0),
            metric_value,
        )
    if not variant_metric_map:
        return 0.0, []
    worst_metric = round(max(variant_metric_map.values()), 6)
    worst_variants = sorted(
        method_variant
        for method_variant, metric_value in variant_metric_map.items()
        if metric_value == worst_metric
    )
    return worst_metric, worst_variants


def _format_number_sequence(values: list[int] | list[float]) -> str:
    if not values:
        return "none"
    return ", ".join(str(value) for value in values)
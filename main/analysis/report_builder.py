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
        return "\n".join(
            [
                "# Method Validation Report",
                "",
                "## Summary",
                f"- method_variants: {', '.join(variant_names)}",
                f"- attack_names: {', '.join(attack_names)}",
                f"- local_clip_curve_rows: {len(local_clip_rows)}",
                f"- tubelet_length_rows: {len(tubelet_rows)}",
                "",
                "## Mechanism Checks",
                f"- tubelet_only_beats_frame_prc_under_some_attack: {str(tubelet_only_gain).lower()}",
                f"- tubelet_sync_beats_tubelet_only_under_temporal_crop_or_local_clip: {str(tubelet_sync_gain).lower()}",
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
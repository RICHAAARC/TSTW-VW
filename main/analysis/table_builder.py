"""
文件用途：提供当前 formal stage 的表格、曲线与报告重建能力。
File purpose: Provide table, curve, and report rebuilding capabilities for the active formal stage.
Module type: General module
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from main.analysis.curve_builder import CurveBuilder
from main.analysis.report_builder import ReportBuilder
from main.core.records import RecordWriter, build_output_paths
from main.protocol.evaluator import (
    ABLATION_TABLE_COLUMNS,
    MAIN_METRICS_COLUMNS,
    TUBELET_LENGTH_ABLATION_COLUMNS,
    build_ablation_table_rows,
    build_main_metrics_rows,
    build_tubelet_length_ablation_rows,
)


class TableBuilder:
    """功能：构建与重建当前 formal stage 的表格、曲线与报告。

    Builder for the active-stage tables, curves, and report artifacts.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        self._curve_builder = CurveBuilder()
        self._report_builder = ReportBuilder()

    def build_tables(
        self,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        output_root: str | Path,
    ) -> dict[str, Path]:
        """功能：从 records 构建表格、曲线与报告产物。

        Build the active-stage tables, curves, and report from governed records.

        Args:
            event_score_records: Event score record list.
            threshold_records: Threshold record list.
            output_root: Run root path.

        Returns:
            A dictionary containing the written table paths.
        """
        if not isinstance(event_score_records, list):
            raise TypeError("event_score_records must be a list")
        if not isinstance(threshold_records, list):
            raise TypeError("threshold_records must be a list")
        output_paths = build_output_paths(output_root)
        output_paths.main_metrics_path.parent.mkdir(parents=True, exist_ok=True)

        main_metrics_rows = build_main_metrics_rows(event_score_records, threshold_records)
        ablation_table_rows = build_ablation_table_rows(event_score_records, threshold_records)
        tubelet_length_rows = build_tubelet_length_ablation_rows(
            event_score_records,
            threshold_records,
        )
        self._write_csv(output_paths.main_metrics_path, MAIN_METRICS_COLUMNS, main_metrics_rows)
        self._write_csv(
            output_paths.ablation_table_path,
            ABLATION_TABLE_COLUMNS,
            ablation_table_rows,
        )
        self._write_csv(
            output_paths.tubelet_length_ablation_path,
            TUBELET_LENGTH_ABLATION_COLUMNS,
            tubelet_length_rows,
        )
        self._curve_builder.build_curves(event_score_records, threshold_records, output_root)
        self._report_builder.build_report(event_score_records, threshold_records, output_root)
        return {
            "main_metrics_path": output_paths.main_metrics_path,
            "ablation_table_path": output_paths.ablation_table_path,
            "tubelet_length_ablation_path": output_paths.tubelet_length_ablation_path,
            "local_clip_curve_path": output_paths.local_clip_curve_path,
            "temporal_attack_curve_path": output_paths.temporal_attack_curve_path,
            "report_path": output_paths.report_path,
        }

    def rebuild_tables(self, output_root: str | Path) -> dict[str, Path]:
        """功能：仅根据 records 与 thresholds 重建表格、曲线与报告。

        Rebuild the active-stage tables, curves, and report from persisted records and thresholds.

        Args:
            output_root: Run root path.

        Returns:
            A dictionary containing the rebuilt table paths.
        """
        record_writer = RecordWriter(output_root)
        return self.build_tables(
            record_writer.read_event_score_records(),
            record_writer.read_threshold_records(),
            output_root,
        )

    def _write_csv(
        self,
        file_path: Path,
        field_names: list[str],
        rows: list[dict[str, Any]],
    ) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=field_names)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
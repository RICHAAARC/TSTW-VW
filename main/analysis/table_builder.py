"""
文件用途：提供阶段 0 最小表格构建与重建能力。
File purpose: Provide stage-0 table building and rebuilding capabilities.
Module type: General module
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from main.core.records import RecordWriter, build_output_paths
from main.protocol.evaluator import (
    ABLATION_TABLE_COLUMNS,
    MAIN_METRICS_COLUMNS,
    build_ablation_table_rows,
    build_main_metrics_rows,
)


class TableBuilder:
    """功能：构建与重建阶段 0 表格。

    Table builder for stage-0 metrics and ablation tables.

    Args:
        None.

    Returns:
        None.
    """

    def build_tables(
        self,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        output_root: str | Path,
    ) -> dict[str, Path]:
        """功能：从 records 构建主指标表与消融表。

        Build the stage-0 tables from governed records.

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
        self._write_csv(output_paths.main_metrics_path, MAIN_METRICS_COLUMNS, main_metrics_rows)
        self._write_csv(
            output_paths.ablation_table_path,
            ABLATION_TABLE_COLUMNS,
            ablation_table_rows,
        )
        return {
            "main_metrics_path": output_paths.main_metrics_path,
            "ablation_table_path": output_paths.ablation_table_path,
        }

    def rebuild_tables(self, output_root: str | Path) -> dict[str, Path]:
        """功能：仅根据 records 与 thresholds 重建表格。

        Rebuild the stage-0 tables from persisted records and thresholds.

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
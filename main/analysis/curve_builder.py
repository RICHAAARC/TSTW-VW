"""
文件用途：构建 stage-one 的攻击曲线 CSV 产物。
File purpose: Build the stage-one attack-curve CSV artifacts.
Module type: General module
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from main.core.records import build_output_paths
from main.protocol.evaluator import (
    LOCAL_CLIP_CURVE_COLUMNS,
    TEMPORAL_ATTACK_CURVE_COLUMNS,
    build_local_clip_curve_rows,
    build_temporal_attack_curve_rows,
)


class CurveBuilder:
    """功能：构建 stage-one curve CSV 产物。

    Builder for the stage-one curve CSV artifacts.

    Args:
        None.

    Returns:
        None.
    """

    def build_curves(
        self,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        output_root: str | Path,
    ) -> dict[str, Path]:
        if not isinstance(event_score_records, list):
            raise TypeError("event_score_records must be a list")
        if not isinstance(threshold_records, list):
            raise TypeError("threshold_records must be a list")
        output_paths = build_output_paths(output_root)
        local_clip_rows = build_local_clip_curve_rows(event_score_records, threshold_records)
        temporal_attack_rows = build_temporal_attack_curve_rows(
            event_score_records,
            threshold_records,
        )
        self._write_csv(
            output_paths.local_clip_curve_path,
            LOCAL_CLIP_CURVE_COLUMNS,
            local_clip_rows,
        )
        self._write_csv(
            output_paths.temporal_attack_curve_path,
            TEMPORAL_ATTACK_CURVE_COLUMNS,
            temporal_attack_rows,
        )
        return {
            "local_clip_curve_path": output_paths.local_clip_curve_path,
            "temporal_attack_curve_path": output_paths.temporal_attack_curve_path,
        }

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
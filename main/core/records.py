"""
文件用途：提供阶段 0 records、thresholds 与 manifest 的读写能力。
File purpose: Provide record, threshold, and manifest IO for the stage-0 runtime skeleton.
Module type: General module
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from main.core.schema import (
    validate_event_score_record,
    validate_run_manifest_record,
    validate_threshold_record,
)


@dataclass(frozen=True)
class ProtocolOutputPaths:
    """功能：定义阶段 0 运行产物的固定输出路径。

    Stage-0 output layout.

    Args:
        root_path: Run root path.
        event_scores_path: Event score JSONL path.
        thresholds_path: Threshold JSON path.
        run_manifest_path: Run manifest JSON path.
        main_metrics_path: Main metrics CSV path.
        ablation_table_path: Ablation table CSV path.

    Returns:
        None.
    """

    root_path: Path
    event_scores_path: Path
    thresholds_path: Path
    run_manifest_path: Path
    main_metrics_path: Path
    ablation_table_path: Path

    def table_paths(self) -> list[Path]:
        """功能：返回受治理表格路径列表。

        Return the governed table artifact paths.

        Args:
            None.

        Returns:
            A list containing the main metrics and ablation table paths.
        """
        return [self.main_metrics_path, self.ablation_table_path]


def build_output_paths(output_root: str | Path) -> ProtocolOutputPaths:
    """功能：根据 run root 构建固定输出布局。

    Build the governed output layout for a run root.

    Args:
        output_root: Run root path.

    Returns:
        A `ProtocolOutputPaths` instance.
    """
    output_root_path = Path(output_root)
    return ProtocolOutputPaths(
        root_path=output_root_path,
        event_scores_path=output_root_path / "records" / "event_scores.jsonl",
        thresholds_path=output_root_path / "thresholds" / "thresholds.json",
        run_manifest_path=output_root_path / "artifacts" / "run_manifest.json",
        main_metrics_path=output_root_path / "tables" / "main_metrics.csv",
        ablation_table_path=output_root_path / "tables" / "ablation_table.csv",
    )


class RecordWriter:
    """功能：统一写入阶段 0 的 records、thresholds 与 manifest。

    Unified writer for stage-0 records, thresholds, and manifest artifacts.

    Args:
        output_root: Run root path.

    Returns:
        None.
    """

    def __init__(self, output_root: str | Path) -> None:
        self.output_paths = build_output_paths(output_root)

    def write_event_score_records(self, event_score_records: list[dict[str, Any]]) -> None:
        """功能：写入 event-level score records。

        Write the governed event-level score records.

        Args:
            event_score_records: Event score record list.

        Returns:
            None.
        """
        if not isinstance(event_score_records, list):
            raise TypeError("event_score_records must be a list")
        self._ensure_parent_directory(self.output_paths.event_scores_path)
        with self.output_paths.event_scores_path.open("w", encoding="utf-8") as handle:
            for event_score_record in event_score_records:
                validate_event_score_record(event_score_record)
                handle.write(json.dumps(event_score_record, ensure_ascii=False) + "\n")

    def write_threshold_records(self, threshold_records: list[dict[str, Any]]) -> None:
        """功能：写入 threshold records。

        Write the governed threshold records.

        Args:
            threshold_records: Threshold record list.

        Returns:
            None.
        """
        if not isinstance(threshold_records, list):
            raise TypeError("threshold_records must be a list")
        for threshold_record in threshold_records:
            validate_threshold_record(threshold_record)
        self._ensure_parent_directory(self.output_paths.thresholds_path)
        self.output_paths.thresholds_path.write_text(
            json.dumps(threshold_records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_run_manifest(self, run_manifest_record: dict[str, Any]) -> None:
        """功能：写入 run manifest。

        Write the governed run manifest.

        Args:
            run_manifest_record: Manifest payload.

        Returns:
            None.
        """
        validate_run_manifest_record(run_manifest_record)
        self._ensure_parent_directory(self.output_paths.run_manifest_path)
        self.output_paths.run_manifest_path.write_text(
            json.dumps(run_manifest_record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def read_event_score_records(self) -> list[dict[str, Any]]:
        """功能：读取 event-level score records。

        Read governed event-level score records.

        Args:
            None.

        Returns:
            A list of event score records.
        """
        if not self.output_paths.event_scores_path.exists():
            raise FileNotFoundError(self.output_paths.event_scores_path)
        records: list[dict[str, Any]] = []
        for raw_line in self.output_paths.event_scores_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            records.append(json.loads(raw_line))
        return records

    def read_threshold_records(self) -> list[dict[str, Any]]:
        """功能：读取 threshold records。

        Read governed threshold records.

        Args:
            None.

        Returns:
            A list of threshold records.
        """
        if not self.output_paths.thresholds_path.exists():
            raise FileNotFoundError(self.output_paths.thresholds_path)
        return json.loads(self.output_paths.thresholds_path.read_text(encoding="utf-8"))

    def read_run_manifest(self) -> dict[str, Any]:
        """功能：读取 run manifest。

        Read the governed run manifest.

        Args:
            None.

        Returns:
            The run manifest dictionary.
        """
        if not self.output_paths.run_manifest_path.exists():
            raise FileNotFoundError(self.output_paths.run_manifest_path)
        return json.loads(self.output_paths.run_manifest_path.read_text(encoding="utf-8"))

    def _ensure_parent_directory(self, file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
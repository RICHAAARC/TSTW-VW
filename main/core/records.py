"""
鏂囦欢鐢ㄩ€旓細鎻愪緵闃舵 0 records銆乼hresholds 涓?manifest 鐨勮鍐欒兘鍔涖€?
File purpose: Provide record, threshold, and manifest IO for the protocol skeleton runtime runtime skeleton.
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
    """鍔熻兘锛氬畾涔夊綋鍓?formal stage 杩愯浜х墿鐨勫浐瀹氳緭鍑鸿矾寰勩€?

    Output layout for the active formal stage.

    Args:
        root_path: Run root path.
        event_scores_path: Event score JSONL path.
        thresholds_path: Threshold JSON path.
        run_manifest_path: Run manifest JSON path.
        main_metrics_path: Main TPR/FPR CSV path.
        ablation_table_path: Ablation table CSV path.
        local_clip_curve_path: Local-clip curve CSV path.
        temporal_attack_curve_path: Temporal-attack curve CSV path.
        tubelet_length_ablation_path: Tubelet-length ablation CSV path.
        sync_peak_examples_path: Sync-peak figure PNG path.
        report_path: Method validation report path.

    Returns:
        None.
    """

    root_path: Path
    event_scores_path: Path
    thresholds_path: Path
    run_manifest_path: Path
    main_metrics_path: Path
    ablation_table_path: Path
    local_clip_curve_path: Path
    temporal_attack_curve_path: Path
    tubelet_length_ablation_path: Path
    sync_peak_examples_path: Path
    report_path: Path

    def table_paths(self) -> list[Path]:
        """鍔熻兘锛氳繑鍥炲彈娌荤悊 CSV 浜х墿璺緞鍒楄〃銆?

        Return the governed CSV artifact paths.

        Args:
            None.

        Returns:
            A list containing all governed CSV table and curve paths.
        """
        return [
            self.main_metrics_path,
            self.ablation_table_path,
            self.local_clip_curve_path,
            self.temporal_attack_curve_path,
            self.tubelet_length_ablation_path,
        ]

    def figure_paths(self) -> list[Path]:
        """鍔熻兘锛氳繑鍥炲彈娌荤悊 figure 浜х墿璺緞鍒楄〃銆?

        Return the governed figure artifact paths.

        Args:
            None.

        Returns:
            A list containing all governed figure paths.
        """
        return [self.sync_peak_examples_path]


def build_output_paths(output_root: str | Path) -> ProtocolOutputPaths:
    """鍔熻兘锛氭牴鎹?run root 鏋勫缓褰撳墠 formal stage 鐨勫浐瀹氳緭鍑哄竷灞€銆?

    Build the governed output layout for an active-stage run root.

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
        main_metrics_path=output_root_path / "tables" / "main_tpr_fpr_table.csv",
        ablation_table_path=output_root_path / "tables" / "ablation_table.csv",
        local_clip_curve_path=output_root_path / "tables" / "local_clip_curve.csv",
        temporal_attack_curve_path=output_root_path / "tables" / "temporal_attack_curve.csv",
        tubelet_length_ablation_path=output_root_path / "tables" / "tubelet_length_ablation.csv",
        sync_peak_examples_path=output_root_path / "figures" / "sync_peak_examples.png",
        report_path=output_root_path / "reports" / "method_validation_report.md",
    )


class RecordWriter:
    """鍔熻兘锛氱粺涓€鍐欏叆闃舵 0 鐨?records銆乼hresholds 涓?manifest銆?

    Unified writer for protocol skeleton runtime records, thresholds, and manifest artifacts.

    Args:
        output_root: Run root path.

    Returns:
        None.
    """

    def __init__(self, output_root: str | Path) -> None:
        self.output_paths = build_output_paths(output_root)

    def write_event_score_records(self, event_score_records: list[dict[str, Any]]) -> None:
        """鍔熻兘锛氬啓鍏?event-level score records銆?

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
        """鍔熻兘锛氬啓鍏?threshold records銆?

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
        """鍔熻兘锛氬啓鍏?run manifest銆?

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
        """鍔熻兘锛氳鍙?event-level score records銆?

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
        """鍔熻兘锛氳鍙?threshold records銆?

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
        """鍔熻兘锛氳鍙?run manifest銆?

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
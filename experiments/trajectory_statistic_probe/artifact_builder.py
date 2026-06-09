"""
文件用途：从阶段 3 records 重建表格与报告。
File purpose: Rebuild stage-three tables and report artifacts from records.
Module type: General module
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any

from experiments.trajectory_statistic_probe.output_layout import (
    build_trajectory_statistic_probe_output_paths,
)
from main.core.records import RecordWriter
from main.protocol.evaluator import build_ablation_table_rows


SCORE_CORRELATION_PAIRS = (
    ("S_traj", "S_tubelet"),
    ("S_traj", "S_sync"),
    ("S_traj", "S_final"),
)

TRAJECTORY_ABLATION_COLUMNS = [
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
SCORE_CORRELATION_COLUMNS = [
    "run_id",
    "method_variant",
    "attack_name",
    "sample_role",
    "left_score_name",
    "right_score_name",
    "correlation_value",
    "record_count",
]
TRAJECTORY_GAIN_COLUMNS = [
    "run_id",
    "method_variant",
    "base_method_variant",
    "attack_name",
    "baseline_attacked_positive_TPR",
    "attacked_positive_TPR",
    "delta_traj",
    "baseline_attacked_positive_margin",
    "attacked_positive_margin",
    "delta_positive_margin_traj",
]
TRAJECTORY_CONTROL_COLUMNS = [
    "run_id",
    "method_variant",
    "sample_role",
    "trajectory_control_kind",
    "S_traj_velocity",
    "record_count",
]
RUNTIME_BREAKDOWN_COLUMNS = [
    "run_id",
    "method_variant",
    "trajectory_runtime_ms",
    "trajectory_reconstruction_ms",
    "trajectory_scoring_ms",
    "record_count",
]


class TrajectoryStatisticArtifactBuilder:
    """功能：构建阶段 3 scaffold 产物。

    Builder for stage-three scaffold artifacts.

    Args:
        None.

    Returns:
        None.
    """

    def build_artifacts(
        self,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        output_root: str | Path,
        mechanism_decision: dict[str, Any] | None = None,
    ) -> dict[str, Path]:
        """功能：从 governed records 构建阶段 3 产物。

        Build stage-three artifacts from governed records.

        Args:
            event_score_records: Event score record list.
            threshold_records: Threshold record list.
            output_root: Run root path.

        Returns:
            A dictionary containing artifact paths.
        """
        output_paths = build_trajectory_statistic_probe_output_paths(output_root)
        ablation_rows = build_ablation_table_rows(event_score_records, threshold_records)
        correlation_rows = build_score_correlation_rows(event_score_records)
        gain_rows = build_trajectory_gain_rows(event_score_records, threshold_records)
        control_rows = build_trajectory_control_rows(event_score_records)
        runtime_rows = build_runtime_breakdown_rows(event_score_records)

        self._write_csv(
            output_paths.trajectory_ablation_table_path,
            TRAJECTORY_ABLATION_COLUMNS,
            ablation_rows,
        )
        self._write_csv(
            output_paths.score_correlation_matrix_path,
            SCORE_CORRELATION_COLUMNS,
            correlation_rows,
        )
        self._write_csv(
            output_paths.trajectory_gain_by_attack_path,
            TRAJECTORY_GAIN_COLUMNS,
            gain_rows,
        )
        self._write_csv(
            output_paths.trajectory_control_table_path,
            TRAJECTORY_CONTROL_COLUMNS,
            control_rows,
        )
        self._write_csv(
            output_paths.runtime_breakdown_path,
            RUNTIME_BREAKDOWN_COLUMNS,
            runtime_rows,
        )
        output_paths.trajectory_probe_report_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.trajectory_probe_report_path.write_text(
            build_trajectory_probe_report_text(
                event_score_records,
                gain_rows,
                correlation_rows,
                runtime_rows,
                mechanism_decision,
            ),
            encoding="utf-8",
        )
        return {
            "trajectory_ablation_table_path": output_paths.trajectory_ablation_table_path,
            "score_correlation_matrix_path": output_paths.score_correlation_matrix_path,
            "trajectory_gain_by_attack_path": output_paths.trajectory_gain_by_attack_path,
            "trajectory_control_table_path": output_paths.trajectory_control_table_path,
            "runtime_breakdown_path": output_paths.runtime_breakdown_path,
            "trajectory_probe_report_path": output_paths.trajectory_probe_report_path,
        }

    def rebuild_artifacts(self, output_root: str | Path) -> dict[str, Path]:
        """功能：仅根据 persisted records 与 thresholds 重建阶段 3 产物。

        Rebuild stage-three artifacts from persisted records and thresholds only.

        Args:
            output_root: Run root path.

        Returns:
            A dictionary containing artifact paths.
        """
        record_writer = RecordWriter(output_root)
        output_paths = build_trajectory_statistic_probe_output_paths(output_root)
        mechanism_decision = None
        if output_paths.trajectory_mechanism_decision_path.exists():
            mechanism_decision = json.loads(
                output_paths.trajectory_mechanism_decision_path.read_text(
                    encoding="utf-8"
                )
            )
        return self.build_artifacts(
            record_writer.read_event_score_records(),
            record_writer.read_threshold_records(),
            output_root,
            mechanism_decision,
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


def build_score_correlation_rows(
    event_score_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    test_records = [record for record in event_score_records if record["split"] == "test"]
    for method_variant in sorted({record["method_variant"] for record in test_records}):
        variant_records = [
            record for record in test_records if record["method_variant"] == method_variant
        ]
        grouped_keys = {
            (record["attack_name"], record["sample_role"])
            for record in variant_records
        }
        for attack_name, sample_role in sorted(grouped_keys):
            grouped_records = [
                record
                for record in variant_records
                if record["attack_name"] == attack_name
                and record["sample_role"] == sample_role
            ]
            for left_score_name, right_score_name in SCORE_CORRELATION_PAIRS:
                paired_values = [
                    (
                        float(record["evidence_scores"][left_score_name]),
                        float(record["evidence_scores"][right_score_name]),
                    )
                    for record in grouped_records
                    if record["evidence_scores"].get(left_score_name) is not None
                    and record["evidence_scores"].get(right_score_name) is not None
                ]
                rows.append(
                    {
                        "run_id": grouped_records[0]["run_id"],
                        "method_variant": method_variant,
                        "attack_name": attack_name,
                        "sample_role": sample_role,
                        "left_score_name": left_score_name,
                        "right_score_name": right_score_name,
                        "correlation_value": _compute_correlation(paired_values),
                        "record_count": len(paired_values),
                    }
                )
    return rows


def build_trajectory_gain_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    test_records = [record for record in event_score_records if record["split"] == "test"]
    threshold_value_by_variant = _build_threshold_value_by_variant(threshold_records)
    comparisons = (
        ("tubelet_traj", "tubelet_only"),
        ("tubelet_sync_trajectory_fusion", "tubelet_sync"),
    )
    for method_variant, base_method_variant in comparisons:
        method_records = [
            record for record in test_records if record["method_variant"] == method_variant
        ]
        base_records = [
            record
            for record in test_records
            if record["method_variant"] == base_method_variant
        ]
        if not method_records or not base_records:
            continue
        for attack_name in sorted({record["attack_name"] for record in method_records}):
            method_positive_records = [
                record
                for record in method_records
                if record["attack_name"] == attack_name
                and record["sample_role"] == "attacked_positive"
            ]
            base_positive_records = [
                record
                for record in base_records
                if record["attack_name"] == attack_name
                and record["sample_role"] == "attacked_positive"
            ]
            if not method_positive_records or not base_positive_records:
                continue
            method_tpr = _decision_rate(method_positive_records)
            base_tpr = _decision_rate(base_positive_records)
            method_margin = _mean_positive_margin(
                method_positive_records,
                threshold_value_by_variant.get(method_variant),
            )
            base_margin = _mean_positive_margin(
                base_positive_records,
                threshold_value_by_variant.get(base_method_variant),
            )
            rows.append(
                {
                    "run_id": method_positive_records[0]["run_id"],
                    "method_variant": method_variant,
                    "base_method_variant": base_method_variant,
                    "attack_name": attack_name,
                    "baseline_attacked_positive_TPR": base_tpr,
                    "attacked_positive_TPR": method_tpr,
                    "delta_traj": round(method_tpr - base_tpr, 6),
                    "baseline_attacked_positive_margin": base_margin,
                    "attacked_positive_margin": method_margin,
                    "delta_positive_margin_traj": round(method_margin - base_margin, 6),
                }
            )
    return rows


def build_trajectory_control_rows(
    event_score_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    test_records = [record for record in event_score_records if record["split"] == "test"]
    grouped_pairs = {
        (record["method_variant"], record["sample_role"])
        for record in test_records
        if isinstance(record["mechanism_trace"].get("trajectory_control_scores"), dict)
    }
    for method_variant, sample_role in sorted(grouped_pairs):
        grouped_records = [
            record
            for record in test_records
            if record["method_variant"] == method_variant
            and record["sample_role"] == sample_role
            and isinstance(record["mechanism_trace"].get("trajectory_control_scores"), dict)
        ]
        control_kinds = {
            control_kind
            for record in grouped_records
            for control_kind in record["mechanism_trace"]["trajectory_control_scores"].keys()
        }
        for control_kind in sorted(control_kinds):
            control_values = [
                float(record["mechanism_trace"]["trajectory_control_scores"][control_kind])
                for record in grouped_records
                if control_kind in record["mechanism_trace"]["trajectory_control_scores"]
            ]
            rows.append(
                {
                    "run_id": grouped_records[0]["run_id"],
                    "method_variant": method_variant,
                    "sample_role": sample_role,
                    "trajectory_control_kind": control_kind,
                    "S_traj_velocity": round(mean(control_values), 6)
                    if control_values
                    else 0.0,
                    "record_count": len(control_values),
                }
            )
    return rows


def build_runtime_breakdown_rows(
    event_score_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    test_records = [record for record in event_score_records if record["split"] == "test"]
    for method_variant in sorted({record["method_variant"] for record in test_records}):
        variant_records = [
            record for record in test_records if record["method_variant"] == method_variant
        ]
        runtime_values = [
            float(record["mechanism_trace"]["trajectory_runtime_ms"])
            for record in variant_records
            if record["mechanism_trace"].get("trajectory_runtime_ms") is not None
        ]
        reconstruction_values = [
            float(record["mechanism_trace"]["trajectory_reconstruction_ms"])
            for record in variant_records
            if record["mechanism_trace"].get("trajectory_reconstruction_ms") is not None
        ]
        scoring_values = [
            float(record["mechanism_trace"]["trajectory_scoring_ms"])
            for record in variant_records
            if record["mechanism_trace"].get("trajectory_scoring_ms") is not None
        ]
        rows.append(
            {
                "run_id": variant_records[0]["run_id"],
                "method_variant": method_variant,
                "trajectory_runtime_ms": round(mean(runtime_values), 6)
                if runtime_values
                else 0.0,
                "trajectory_reconstruction_ms": round(mean(reconstruction_values), 6)
                if reconstruction_values
                else 0.0,
                "trajectory_scoring_ms": round(mean(scoring_values), 6)
                if scoring_values
                else 0.0,
                "record_count": len(runtime_values),
            }
        )
    return rows


def build_trajectory_probe_report_text(
    event_score_records: list[dict[str, Any]],
    gain_rows: list[dict[str, Any]],
    correlation_rows: list[dict[str, Any]],
    runtime_rows: list[dict[str, Any]],
    mechanism_decision: dict[str, Any] | None = None,
) -> str:
    method_variants = ", ".join(
        sorted({record["method_variant"] for record in event_score_records})
    )
    attack_names = ", ".join(
        sorted({record["attack_name"] for record in event_score_records})
    )
    max_delta_traj = max((float(row["delta_traj"]) for row in gain_rows), default=0.0)
    max_delta_positive_margin = max(
        (float(row["delta_positive_margin_traj"]) for row in gain_rows),
        default=0.0,
    )
    mean_runtime_ms = mean([float(row["trajectory_runtime_ms"]) for row in runtime_rows]) if runtime_rows else 0.0
    mechanism_status = _resolve_stage3_mechanism_status(mechanism_decision)
    implementation_status = _resolve_decision_text(
        mechanism_decision,
        "Stage3ImplementationDecision",
        "NOT_AVAILABLE",
    )
    dependency_status = _resolve_decision_text(
        mechanism_decision,
        "Stage2DependencyStatus",
        "NOT_AVAILABLE",
    )
    next_allowed_stage = _resolve_decision_text(
        mechanism_decision,
        "NextAllowedStageByTrajectory",
        "NOT_AVAILABLE",
    )
    return "\n".join(
        [
            "# Trajectory Probe Report",
            "",
            f"method_variants: {method_variants}",
            f"attack_names: {attack_names}",
            f"event_record_count: {len(event_score_records)}",
            f"max_delta_traj: {round(max_delta_traj, 6)}",
            f"max_delta_positive_margin_traj: {round(max_delta_positive_margin, 6)}",
            f"correlation_row_count: {len(correlation_rows)}",
            f"mean_runtime_ms: {round(mean_runtime_ms, 6)}",
            f"stage2_dependency_status: {dependency_status}",
            f"stage3_implementation_status: {implementation_status}",
            f"stage3_mechanism_status: {mechanism_status}",
            f"next_allowed_stage_by_trajectory: {next_allowed_stage}",
            "",
            (
                "This report is rebuilt from governed records, thresholds, and the "
                "trajectory mechanism decision artifact; the repository project stage "
                "is still controlled by the separate project contract."
            ),
            "",
        ]
    )


def _resolve_stage3_mechanism_status(
    mechanism_decision: dict[str, Any] | None,
) -> str:
    """功能：从机制决策产物解析报告中的阶段 3 机制状态。

    该函数属于通用报告防漂移写法。报告不再硬编码旧状态, 而是优先复用
    `trajectory_mechanism_decision.json` 中的正式门禁结论；当重建旧产物且决策文件缺失时,
    明确写出 `NOT_AVAILABLE`, 避免误导为已经通过或被阶段 2 阻断。
    """
    return _resolve_decision_text(
        mechanism_decision,
        "Stage3MechanismDecision",
        "NOT_AVAILABLE",
    )


def _resolve_decision_text(
    mechanism_decision: dict[str, Any] | None,
    field_name: str,
    default_value: str,
) -> str:
    if not mechanism_decision:
        return default_value
    value = mechanism_decision.get(field_name)
    if value is None:
        return default_value
    normalized_value = str(value).strip()
    return normalized_value if normalized_value else default_value


def _decision_rate(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    return round(sum(1 for record in records if record["decision"]) / len(records), 6)


def _build_threshold_value_by_variant(
    threshold_records: list[dict[str, Any]],
) -> dict[str, float]:
    return {
        str(record["method_variant"]): float(record["threshold_value"])
        for record in threshold_records
        if isinstance(record.get("method_variant"), str)
        and isinstance(record.get("threshold_value"), (int, float))
    }


def _mean_positive_margin(
    records: list[dict[str, Any]],
    threshold_value: float | None,
) -> float:
    if threshold_value is None:
        return 0.0
    margins = [
        float(record["evidence_scores"]["S_final"]) - threshold_value
        for record in records
        if isinstance(record.get("evidence_scores", {}).get("S_final"), (int, float))
    ]
    return round(mean(margins), 6) if margins else 0.0


def _compute_correlation(paired_values: list[tuple[float, float]]) -> float:
    if len(paired_values) < 2:
        return 0.0
    left_values = [value[0] for value in paired_values]
    right_values = [value[1] for value in paired_values]
    left_mean = mean(left_values)
    right_mean = mean(right_values)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in paired_values
    )
    left_denominator = sum((left_value - left_mean) ** 2 for left_value in left_values)
    right_denominator = sum((right_value - right_mean) ** 2 for right_value in right_values)
    if left_denominator <= 0.0 or right_denominator <= 0.0:
        return 0.0
    return round(numerator / ((left_denominator * right_denominator) ** 0.5), 6)

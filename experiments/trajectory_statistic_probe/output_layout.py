"""
文件用途：定义阶段 3 trajectory statistic probe 的输出布局。
File purpose: Define the governed output layout for the trajectory statistic probe.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from main.protocol.output_layout import BaseRunOutputPaths, build_base_run_output_paths


@dataclass(frozen=True)
class TrajectoryStatisticProbeOutputPaths(BaseRunOutputPaths):
    """Output layout for the trajectory statistic probe.

    Args:
        root_path: Run root path.
        event_scores_path: Event score JSONL path.
        thresholds_path: Threshold JSON path.
        run_manifest_path: Run manifest JSON path.
        artifact_manifest_path: Artifact manifest JSON path.
        runtime_manifest_path: Runtime manifest JSON path.
        runtime_config_path: Runtime-config JSON path.
        trajectory_ablation_table_path: Stage-three ablation table path.
        score_correlation_matrix_path: Score-correlation table path.
        trajectory_gain_by_attack_path: Gain-by-attack table path.
        trajectory_control_table_path: Control table path.
        runtime_breakdown_path: Runtime-breakdown table path.
        trajectory_probe_report_path: Report path.
        trajectory_mechanism_decision_path: Mechanism-decision artifact path.
        stage2_frozen_baseline_manifest_path: Frozen baseline manifest path.

    Returns:
        None.
    """

    trajectory_ablation_table_path: Path
    score_correlation_matrix_path: Path
    trajectory_gain_by_attack_path: Path
    trajectory_control_table_path: Path
    runtime_breakdown_path: Path
    trajectory_probe_report_path: Path
    trajectory_mechanism_decision_path: Path
    stage2_frozen_baseline_manifest_path: Path

    def table_paths(self) -> list[Path]:
        return [
            self.trajectory_ablation_table_path,
            self.score_correlation_matrix_path,
            self.trajectory_gain_by_attack_path,
            self.trajectory_control_table_path,
            self.runtime_breakdown_path,
        ]

    def figure_paths(self) -> list[Path]:
        return []


def build_trajectory_statistic_probe_output_paths(
    output_root: str | Path,
) -> TrajectoryStatisticProbeOutputPaths:
    """功能：构建阶段 3 trajectory statistic probe 的固定输出布局。

    Build the fixed output layout for the trajectory statistic probe.

    Args:
        output_root: Run root path.

    Returns:
        A `TrajectoryStatisticProbeOutputPaths` instance.
    """
    output_root_path = Path(output_root)
    base_paths = build_base_run_output_paths(output_root_path)
    return TrajectoryStatisticProbeOutputPaths(
        root_path=base_paths.root_path,
        event_scores_path=base_paths.event_scores_path,
        thresholds_path=base_paths.thresholds_path,
        run_manifest_path=base_paths.run_manifest_path,
        artifact_manifest_path=base_paths.artifact_manifest_path,
        runtime_manifest_path=base_paths.runtime_manifest_path,
        runtime_config_path=base_paths.runtime_config_path,
        trajectory_ablation_table_path=(
            output_root_path / "tables" / "trajectory_ablation_table.csv"
        ),
        score_correlation_matrix_path=(
            output_root_path / "tables" / "score_correlation_matrix.csv"
        ),
        trajectory_gain_by_attack_path=(
            output_root_path / "tables" / "trajectory_gain_by_attack.csv"
        ),
        trajectory_control_table_path=(
            output_root_path / "tables" / "trajectory_control_table.csv"
        ),
        runtime_breakdown_path=(
            output_root_path / "tables" / "runtime_breakdown.csv"
        ),
        trajectory_probe_report_path=(
            output_root_path / "reports" / "trajectory_probe_report.md"
        ),
        trajectory_mechanism_decision_path=(
            output_root_path / "artifacts" / "trajectory_mechanism_decision.json"
        ),
        stage2_frozen_baseline_manifest_path=(
            output_root_path / "artifacts" / "stage2_frozen_baseline_manifest.json"
        ),
    )

"""
文件用途：定义 trajectory-aware sampling probe 的输出布局。
File purpose: Define the governed output layout for the trajectory-aware sampling probe.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from main.protocol.output_layout import BaseRunOutputPaths, build_base_run_output_paths


@dataclass(frozen=True)
class TrajectoryAwareSamplingProbeOutputPaths(BaseRunOutputPaths):
    """功能：记录下一阶段 decision-only scaffold 的固定输出路径。

    该布局属于项目特定写法。它只为后续构建预留受治理的决策与报告位置,
    不表示当前已经允许真实生成、真实采样调度或真实 watermark 集成。
    """

    sampling_readiness_decision_path: Path
    sampling_policy_manifest_path: Path
    sampling_selection_plan_path: Path
    sampling_probe_report_path: Path

    def table_paths(self) -> list[Path]:
        return []

    def figure_paths(self) -> list[Path]:
        return []


def build_trajectory_aware_sampling_probe_output_paths(
    output_root: str | Path,
) -> TrajectoryAwareSamplingProbeOutputPaths:
    """功能：构建 trajectory-aware sampling probe 的固定输出布局。

    此处复用通用 `BaseRunOutputPaths`, 使未来真正写出 records / thresholds 时仍能保持
    与现有协议布局一致；当前 scaffold 只使用 artifacts 与 reports 下的决策文件。
    """
    output_root_path = Path(output_root)
    base_paths = build_base_run_output_paths(output_root_path)
    return TrajectoryAwareSamplingProbeOutputPaths(
        root_path=base_paths.root_path,
        event_scores_path=base_paths.event_scores_path,
        thresholds_path=base_paths.thresholds_path,
        run_manifest_path=base_paths.run_manifest_path,
        artifact_manifest_path=base_paths.artifact_manifest_path,
        runtime_manifest_path=base_paths.runtime_manifest_path,
        runtime_config_path=base_paths.runtime_config_path,
        sampling_readiness_decision_path=(
            output_root_path / "artifacts" / "sampling_readiness_decision.json"
        ),
        sampling_policy_manifest_path=(
            output_root_path / "artifacts" / "sampling_policy_manifest.json"
        ),
        sampling_selection_plan_path=(
            output_root_path / "artifacts" / "sampling_selection_plan.json"
        ),
        sampling_probe_report_path=(
            output_root_path / "reports" / "trajectory_aware_sampling_probe_report.md"
        ),
    )

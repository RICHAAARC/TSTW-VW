"""
文件用途：提供 trajectory statistic probe 的最小 formal replay 入口。
File purpose: Provide the minimal formal replay entrypoint for the trajectory statistic probe.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from experiments.trajectory_statistic_probe.runner import (
    TrajectoryStatisticProbeRunResult,
    TrajectoryStatisticProbeRunner,
)


@dataclass(frozen=True)
class FormalReplayRequest:
    """功能：定义 formal replay 所需的最小输入。

    该对象的作用是把输出目录、冻结 baseline 目录和样本规模显式绑定,
    避免 runner 在缺少前置 gate 的情况下静默生成形式化结论。
    """

    repository_root: Path
    output_root: Path
    frozen_baseline_root: Path
    samples_per_role: int = 2
    runtime_profile: str = "smoke"


def run_trajectory_statistic_formal_replay(
    request: FormalReplayRequest,
) -> TrajectoryStatisticProbeRunResult:
    """功能：在冻结 baseline 通过后运行最小 replay 闭环。

    Args:
        request: formal replay 请求。

    Returns:
        `TrajectoryStatisticProbeRunResult` 运行结果。
    """
    if not isinstance(request, FormalReplayRequest):
        raise TypeError("request must be a FormalReplayRequest instance")
    return TrajectoryStatisticProbeRunner(request.repository_root).run(
        request.output_root,
        samples_per_role=request.samples_per_role,
        runtime_profile_override=request.runtime_profile,
        frozen_baseline_root=request.frozen_baseline_root,
    )

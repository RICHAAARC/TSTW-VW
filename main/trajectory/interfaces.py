"""
文件用途：定义阶段 3 trajectory scaffold 的共享数据结构。
File purpose: Define shared data structures for the stage-three trajectory scaffold.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass

from main.core.tensor_artifact import FloatTensorArtifact


def validate_trajectory_time_grid(
    time_grid: list[float] | tuple[float, ...],
) -> tuple[float, ...]:
    """功能：校验并标准化 trajectory time grid。

    Validate and normalize a trajectory time grid.

    Args:
        time_grid: Candidate normalized time grid.

    Returns:
        A strictly increasing normalized time grid.
    """
    if not isinstance(time_grid, (list, tuple)) or len(time_grid) < 2:
        raise ValueError("time_grid must contain at least two values")
    normalized: list[float] = []
    previous_value: float | None = None
    for raw_value in time_grid:
        if not isinstance(raw_value, (int, float)):
            raise TypeError("time_grid entries must be numeric")
        time_value = float(raw_value)
        if time_value < 0.0 or time_value > 1.0:
            raise ValueError("time_grid entries must stay within [0, 1]")
        if previous_value is not None and time_value <= previous_value:
            raise ValueError("time_grid must be strictly increasing")
        normalized.append(time_value)
        previous_value = time_value
    return tuple(normalized)


@dataclass(frozen=True)
class TrajectoryFrame:
    """功能：表示一个离散 trajectory 时间点。

    Discrete trajectory frame used by the stage-three scaffold.

    Args:
        time_value: Normalized time value in [0, 1].
        tensor_artifact: Tensor snapshot at the requested time.

    Returns:
        None.
    """

    time_value: float
    tensor_artifact: FloatTensorArtifact


@dataclass(frozen=True)
class TrajectoryObservation:
    """功能：表示 detector 侧可见的离散 trajectory 观测。

    Discrete trajectory observation visible to the detector side.

    Args:
        source_kind: Semantic trajectory source identifier.
        time_grid: Ordered normalized time grid.
        frames: Ordered trajectory frames.

    Returns:
        None.
    """

    source_kind: str
    time_grid: tuple[float, ...]
    frames: tuple[TrajectoryFrame, ...]


@dataclass(frozen=True)
class TrajectoryStatisticResult:
    """功能：表示 trajectory 统计量的物化结果。

    Materialized result of the stage-three trajectory statistics.

    Args:
        trajectory_statistic_kind: Primary statistic identifier.
        S_traj_velocity: Velocity-projection statistic where larger indicates stronger evidence.
        S_traj_displacement: Displacement-projection statistic where larger indicates stronger evidence.
        trajectory_curvature_residual: Residual curvature magnitude where smaller indicates a more linear path.
        trajectory_projection_count: Total number of projection evaluations.
        trajectory_valid_segment_ratio: Ratio of valid segments over all requested segments.

    Returns:
        None.
    """

    trajectory_statistic_kind: str
    S_traj_velocity: float
    S_traj_displacement: float
    trajectory_curvature_residual: float
    trajectory_projection_count: int
    trajectory_valid_segment_ratio: float


@dataclass(frozen=True)
class TrajectoryRuntimeSummary:
    """功能：表示 trajectory 重建与打分的运行时摘要。

    Runtime summary for trajectory reconstruction and scoring.

    Args:
        trajectory_runtime_ms: End-to-end runtime in milliseconds.
        trajectory_reconstruction_ms: Observation construction runtime in milliseconds.
        trajectory_scoring_ms: Statistic scoring runtime in milliseconds.

    Returns:
        None.
    """

    trajectory_runtime_ms: float
    trajectory_reconstruction_ms: float
    trajectory_scoring_ms: float
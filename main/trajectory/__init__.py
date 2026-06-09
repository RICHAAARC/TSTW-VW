"""
文件用途：导出阶段 3 trajectory statistic scaffold 的公共接口。
File purpose: Export the public interfaces for the stage-three trajectory statistic scaffold.
Module type: General module
"""

from main.trajectory.interfaces import (
    TrajectoryFrame,
    TrajectoryObservation,
    TrajectoryRuntimeSummary,
    TrajectoryStatisticResult,
)
from main.trajectory.trajectory_backend_registry import build_trajectory_backend_from_config
from main.trajectory.trajectory_controls import (
    SUPPORTED_TRAJECTORY_CONTROL_KINDS,
    apply_trajectory_control,
)
from main.trajectory.trajectory_observation import (
    build_interpolated_observation,
    build_latent_interpolation_surrogate,
    build_stage2_frozen_endpoint_replay,
    build_synthetic_flow_trajectory,
)
from main.trajectory.trajectory_runtime import measure_trajectory_runtime
from main.trajectory.trajectory_statistic import build_velocity_projection_statistic

__all__ = [
    "SUPPORTED_TRAJECTORY_CONTROL_KINDS",
    "TrajectoryFrame",
    "TrajectoryObservation",
    "TrajectoryRuntimeSummary",
    "TrajectoryStatisticResult",
    "apply_trajectory_control",
    "build_interpolated_observation",
    "build_latent_interpolation_surrogate",
    "build_stage2_frozen_endpoint_replay",
    "build_synthetic_flow_trajectory",
    "build_trajectory_backend_from_config",
    "build_velocity_projection_statistic",
    "measure_trajectory_runtime",
]

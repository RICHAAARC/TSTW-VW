"""
文件用途：封装阶段 3 surrogate trajectory reconstruction 入口。
File purpose: Wrap surrogate trajectory reconstruction entrypoints for the stage-three scaffold.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.schema import LatentSample
from main.trajectory.interfaces import TrajectoryObservation
from main.trajectory.trajectory_observation import (
    build_latent_interpolation_surrogate,
    build_synthetic_flow_trajectory,
)


def reconstruct_trajectory_observation(
    sample: LatentSample,
    backend_config: dict[str, Any],
) -> TrajectoryObservation:
    """功能：根据 backend config 构建阶段 3 trajectory observation。

    Reconstruct a stage-three trajectory observation from backend config.

    Args:
        sample: Observed latent sample.
        backend_config: Parsed trajectory backend config.

    Returns:
        A `TrajectoryObservation` instance.
    """
    if not isinstance(sample, LatentSample):
        raise TypeError("sample must be a LatentSample instance")
    if not isinstance(backend_config, dict):
        raise TypeError("backend_config must be a dictionary")

    trajectory_source_kind = str(
        backend_config.get("trajectory_source_kind", "latent_interpolation_surrogate")
    )
    if bool(backend_config.get("fail_on_positive_only_artifact_access", False)):
        mechanism_trace = sample.mechanism_trace or {}
        if bool(mechanism_trace.get("positive_only_artifact_access")):
            raise ValueError("positive_only_artifact_access_forbidden")
    time_grid = backend_config.get(
        "trajectory_time_grid",
        backend_config.get("time_grid", [0.0, 0.25, 0.5, 0.75, 1.0]),
    )
    if trajectory_source_kind == "latent_interpolation_surrogate":
        return build_latent_interpolation_surrogate(sample, time_grid)
    if trajectory_source_kind == "synthetic_flow_trajectory":
        return build_synthetic_flow_trajectory(sample, time_grid)
    raise ValueError(f"unsupported trajectory_source_kind: {trajectory_source_kind}")

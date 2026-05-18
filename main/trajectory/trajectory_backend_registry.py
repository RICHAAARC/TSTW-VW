"""
文件用途：解析阶段 3 trajectory backend 配置并构建 backend 入口。
File purpose: Resolve stage-three trajectory backend configs and construct backend entrypoints.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from main.core.schema import LatentSample
from main.trajectory.interfaces import TrajectoryObservation
from main.trajectory.trajectory_reconstruction import reconstruct_trajectory_observation


@dataclass(frozen=True)
class SurrogateTrajectoryBackend:
    """功能：提供基于 config 的 surrogate trajectory backend。

    Config-driven surrogate trajectory backend.

    Args:
        backend_config: Parsed trajectory backend config.

    Returns:
        None.
    """

    backend_config: dict[str, Any]

    def build_observation(self, sample: LatentSample) -> TrajectoryObservation:
        """功能：构建 surrogate trajectory observation。

        Build a surrogate trajectory observation.

        Args:
            sample: Observed latent sample.

        Returns:
            A `TrajectoryObservation` instance.
        """
        return reconstruct_trajectory_observation(sample, self.backend_config)


def build_trajectory_backend_from_config(
    backend_config: dict[str, Any],
) -> SurrogateTrajectoryBackend:
    """功能：根据配置构建阶段 3 surrogate trajectory backend。

    Build the stage-three surrogate trajectory backend from config.

    Args:
        backend_config: Parsed trajectory backend config.

    Returns:
        A `SurrogateTrajectoryBackend` instance.
    """
    if not isinstance(backend_config, dict):
        raise TypeError("backend_config must be a dictionary")
    return SurrogateTrajectoryBackend(backend_config=dict(backend_config))
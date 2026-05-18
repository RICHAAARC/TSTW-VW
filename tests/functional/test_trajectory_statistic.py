"""
文件用途：验证阶段 3 trajectory 统计核心的快速功能语义。
File purpose: Validate quick functional semantics for the stage-three trajectory statistic core.
Module type: General module
"""

from __future__ import annotations

from array import array

import pytest

from main.core.tensor_artifact import FloatTensorArtifact
from main.methods.temporal_tubelet_watermark.tubelet_partition import (
    build_tubelet_descriptors,
    build_tubelet_partition_config,
)
from main.trajectory.trajectory_controls import apply_trajectory_control
from main.trajectory.trajectory_observation import build_interpolated_observation
from main.trajectory.trajectory_statistic import build_velocity_projection_statistic


pytestmark = [pytest.mark.quick]


def test_velocity_projection_matches_linear_interpolation() -> None:
    """Validate velocity and displacement statistics on a linear surrogate path.

    Args:
        None.

    Returns:
        None.
    """
    start_artifact = FloatTensorArtifact(shape=(1, 1, 1, 1), values=array("f", [0.0]))
    end_artifact = FloatTensorArtifact(shape=(1, 1, 1, 1), values=array("f", [1.0]))
    observation = build_interpolated_observation(
        start_artifact,
        end_artifact,
        time_grid=[0.0, 0.5, 1.0],
        source_kind="latent_interpolation_surrogate",
    )
    descriptors = build_tubelet_descriptors(
        (1, 1, 1, 1),
        build_tubelet_partition_config(
            tubelet_length=1,
            spatial_patch_size=(1, 1),
            allow_partial_tubelet=False,
        ),
    )
    directions = {descriptors[0].tubelet_index: (1.0,)}
    codes = {descriptors[0].tubelet_index: 1}

    result = build_velocity_projection_statistic(
        observation,
        descriptors,
        directions,
        codes,
    )

    assert result.S_traj_velocity == 1.0
    assert result.S_traj_displacement == 1.0
    assert result.trajectory_curvature_residual == 0.0
    assert result.trajectory_projection_count == 2
    assert result.trajectory_valid_segment_ratio == 1.0


def test_time_reversed_control_flips_linear_velocity_sign() -> None:
    """Validate that the time-reversed control inverts the linear velocity statistic.

    Args:
        None.

    Returns:
        None.
    """
    start_artifact = FloatTensorArtifact(shape=(1, 1, 1, 1), values=array("f", [0.0]))
    end_artifact = FloatTensorArtifact(shape=(1, 1, 1, 1), values=array("f", [1.0]))
    observation = build_interpolated_observation(
        start_artifact,
        end_artifact,
        time_grid=[0.0, 0.5, 1.0],
        source_kind="latent_interpolation_surrogate",
    )
    descriptors = build_tubelet_descriptors(
        (1, 1, 1, 1),
        build_tubelet_partition_config(
            tubelet_length=1,
            spatial_patch_size=(1, 1),
            allow_partial_tubelet=False,
        ),
    )
    directions = {descriptors[0].tubelet_index: (1.0,)}
    codes = {descriptors[0].tubelet_index: 1}

    reversed_observation, reversed_directions, reversed_codes = apply_trajectory_control(
        observation,
        directions,
        codes,
        sample_id="sample_test_watermarked_positive_000001",
        control_kind="traj_time_reversed",
    )
    result = build_velocity_projection_statistic(
        reversed_observation,
        descriptors,
        reversed_directions,
        reversed_codes,
    )

    assert result.S_traj_velocity == -1.0
    assert result.S_traj_displacement == -1.0
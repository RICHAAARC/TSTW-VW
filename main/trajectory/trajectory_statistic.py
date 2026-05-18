"""
文件用途：实现阶段 3 trajectory 统计量。
File purpose: Implement trajectory statistics for the stage-three scaffold.
Module type: Semi-general module
"""

from __future__ import annotations

from array import array
import math

from main.core.tensor_artifact import FloatTensorArtifact
from main.methods.temporal_tubelet_watermark.tubelet_partition import (
    TubeletDescriptor,
    dot_tubelet_direction,
)
from main.trajectory.interfaces import TrajectoryObservation, TrajectoryStatisticResult


def build_velocity_projection_statistic(
    observation: TrajectoryObservation,
    tubelet_descriptors: list[TubeletDescriptor],
    directions: dict[int, tuple[float, ...]],
    codes: dict[int, int],
) -> TrajectoryStatisticResult:
    """功能：计算 velocity / displacement / curvature 统计量。

    Compute velocity, displacement, and curvature statistics from a trajectory observation.

    Args:
        observation: Ordered trajectory observation.
        tubelet_descriptors: Tubelet descriptor list.
        directions: Key-conditioned projection directions.
        codes: Key-conditioned sign codes.

    Returns:
        A `TrajectoryStatisticResult` instance.
    """
    if not isinstance(observation, TrajectoryObservation):
        raise TypeError("observation must be a TrajectoryObservation instance")
    if not isinstance(tubelet_descriptors, list) or not tubelet_descriptors:
        raise ValueError("tubelet_descriptors must be a non-empty list")
    if not isinstance(directions, dict) or not directions:
        raise ValueError("directions must be a non-empty dictionary")
    if not isinstance(codes, dict) or not codes:
        raise ValueError("codes must be a non-empty dictionary")
    if len(observation.frames) < 2:
        raise ValueError("observation must contain at least two frames")

    segment_artifacts: list[FloatTensorArtifact] = []
    for current_frame, next_frame in zip(observation.frames, observation.frames[1:]):
        delta_t = float(next_frame.time_value) - float(current_frame.time_value)
        if delta_t <= 0.0:
            raise ValueError("trajectory observation time values must be strictly increasing")
        segment_artifacts.append(
            _build_delta_artifact(
                current_frame.tensor_artifact,
                next_frame.tensor_artifact,
                delta_t,
            )
        )

    displacement_artifact = _build_delta_artifact(
        observation.frames[0].tensor_artifact,
        observation.frames[-1].tensor_artifact,
        1.0,
    )
    curvature_artifacts = [
        _build_second_difference_artifact(
            previous_frame.tensor_artifact,
            current_frame.tensor_artifact,
            next_frame.tensor_artifact,
        )
        for previous_frame, current_frame, next_frame in zip(
            observation.frames,
            observation.frames[1:],
            observation.frames[2:],
        )
    ]

    velocity_total = 0.0
    displacement_total = 0.0
    curvature_total = 0.0
    descriptor_count = len(tubelet_descriptors)
    for tubelet_descriptor in tubelet_descriptors:
        direction = directions.get(tubelet_descriptor.tubelet_index)
        code_value = codes.get(tubelet_descriptor.tubelet_index)
        if direction is None or code_value is None:
            raise ValueError("directions and codes must cover every tubelet_descriptor")
        displacement_total += float(code_value) * dot_tubelet_direction(
            displacement_artifact,
            tubelet_descriptor,
            direction,
        )
        for segment_artifact in segment_artifacts:
            velocity_total += float(code_value) * dot_tubelet_direction(
                segment_artifact,
                tubelet_descriptor,
                direction,
            )
        for curvature_artifact in curvature_artifacts:
            curvature_total += _compute_descriptor_l2_norm(
                curvature_artifact,
                tubelet_descriptor,
            )

    projection_count = descriptor_count * len(segment_artifacts)
    velocity_denominator = max(1, projection_count)
    displacement_denominator = max(1, descriptor_count)
    curvature_denominator = max(1, descriptor_count * max(1, len(curvature_artifacts)))
    return TrajectoryStatisticResult(
        trajectory_statistic_kind="velocity_projection",
        S_traj_velocity=round(velocity_total / velocity_denominator, 6),
        S_traj_displacement=round(displacement_total / displacement_denominator, 6),
        trajectory_curvature_residual=round(curvature_total / curvature_denominator, 6),
        trajectory_projection_count=projection_count,
        trajectory_valid_segment_ratio=1.0,
    )


def _build_delta_artifact(
    start_artifact: FloatTensorArtifact,
    end_artifact: FloatTensorArtifact,
    delta_t: float,
) -> FloatTensorArtifact:
    if start_artifact.shape != end_artifact.shape:
        raise ValueError("start_artifact and end_artifact must share the same shape")
    if not isinstance(delta_t, (int, float)) or float(delta_t) <= 0.0:
        raise ValueError("delta_t must be positive")
    return FloatTensorArtifact(
        shape=start_artifact.shape,
        values=array(
            "f",
            [
                (float(end_value) - float(start_value)) / float(delta_t)
                for start_value, end_value in zip(
                    start_artifact.values,
                    end_artifact.values,
                )
            ],
        ),
    )


def _build_second_difference_artifact(
    previous_artifact: FloatTensorArtifact,
    current_artifact: FloatTensorArtifact,
    next_artifact: FloatTensorArtifact,
) -> FloatTensorArtifact:
    if (
        previous_artifact.shape != current_artifact.shape
        or current_artifact.shape != next_artifact.shape
    ):
        raise ValueError("all trajectory artifacts must share the same shape")
    return FloatTensorArtifact(
        shape=current_artifact.shape,
        values=array(
            "f",
            [
                float(next_value) - (2.0 * float(current_value)) + float(previous_value)
                for previous_value, current_value, next_value in zip(
                    previous_artifact.values,
                    current_artifact.values,
                    next_artifact.values,
                )
            ],
        ),
    )


def _compute_descriptor_l2_norm(
    tensor_artifact: FloatTensorArtifact,
    tubelet_descriptor: TubeletDescriptor,
) -> float:
    squared_norm = 0.0
    for flat_index in tubelet_descriptor.flat_indices:
        value = float(tensor_artifact.values[flat_index])
        squared_norm += value * value
    return math.sqrt(squared_norm)
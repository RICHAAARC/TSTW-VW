"""
文件用途：实现阶段 3 trajectory negative control。
File purpose: Implement trajectory negative controls for the stage-three scaffold.
Module type: Semi-general module
"""

from __future__ import annotations

import math
import random

from main.core.digest import compute_object_digest
from main.trajectory.interfaces import TrajectoryFrame, TrajectoryObservation


SUPPORTED_TRAJECTORY_CONTROL_KINDS = (
    "none",
    "traj_shuffled_key",
    "traj_time_reversed",
    "traj_random_projection_control",
    "traj_group_permutation_control",
)


def apply_trajectory_control(
    observation: TrajectoryObservation,
    directions: dict[int, tuple[float, ...]],
    codes: dict[int, int],
    sample_id: str,
    control_kind: str,
) -> tuple[TrajectoryObservation, dict[int, tuple[float, ...]], dict[int, int]]:
    """功能：对 trajectory 观测或 key 条件量施加 control。

    Apply a negative control to the observation or key-conditioned statistics.

    Args:
        observation: Source trajectory observation.
        directions: Key-conditioned direction map.
        codes: Key-conditioned sign map.
        sample_id: Stable sample identifier used for deterministic controls.
        control_kind: Requested control kind.

    Returns:
        A tuple containing the controlled observation, directions, and codes.
    """
    if not isinstance(observation, TrajectoryObservation):
        raise TypeError("observation must be a TrajectoryObservation instance")
    if not isinstance(directions, dict):
        raise TypeError("directions must be a dictionary")
    if not isinstance(codes, dict):
        raise TypeError("codes must be a dictionary")
    if not isinstance(sample_id, str) or not sample_id:
        raise ValueError("sample_id must be a non-empty string")
    if control_kind not in SUPPORTED_TRAJECTORY_CONTROL_KINDS:
        raise ValueError(f"unsupported control_kind: {control_kind}")

    if control_kind == "none":
        return observation, dict(directions), dict(codes)
    if control_kind == "traj_time_reversed":
        return _reverse_trajectory_observation(observation), dict(directions), dict(codes)
    if control_kind == "traj_shuffled_key":
        return observation, dict(directions), _shuffle_codes(codes, sample_id, control_kind)
    if control_kind == "traj_random_projection_control":
        return observation, _build_random_projection_directions(directions, sample_id, control_kind), dict(codes)
    return observation, _permute_directions_by_group(directions, sample_id, control_kind), dict(codes)


def _reverse_trajectory_observation(
    observation: TrajectoryObservation,
) -> TrajectoryObservation:
    reversed_frames = tuple(
        TrajectoryFrame(
            time_value=observation.time_grid[index],
            tensor_artifact=frame.tensor_artifact,
        )
        for index, frame in enumerate(reversed(observation.frames))
    )
    return TrajectoryObservation(
        source_kind=observation.source_kind,
        time_grid=observation.time_grid,
        frames=reversed_frames,
    )


def _shuffle_codes(
    codes: dict[int, int],
    sample_id: str,
    control_kind: str,
) -> dict[int, int]:
    ordered_keys = sorted(codes)
    ordered_values = [codes[key] for key in ordered_keys]
    generator = random.Random(_build_control_seed(sample_id, control_kind, "codes"))
    generator.shuffle(ordered_values)
    return {
        key: int(value)
        for key, value in zip(ordered_keys, ordered_values)
    }


def _build_random_projection_directions(
    directions: dict[int, tuple[float, ...]],
    sample_id: str,
    control_kind: str,
) -> dict[int, tuple[float, ...]]:
    randomized: dict[int, tuple[float, ...]] = {}
    for key, direction in directions.items():
        generator = random.Random(
            _build_control_seed(sample_id, control_kind, f"direction:{key}")
        )
        values = [generator.uniform(-1.0, 1.0) for _ in range(len(direction))]
        l2_norm = math.sqrt(sum(value * value for value in values))
        if l2_norm == 0.0:
            raise ValueError("random projection control produced a zero vector")
        randomized[key] = tuple(round(value / l2_norm, 8) for value in values)
    return randomized


def _permute_directions_by_group(
    directions: dict[int, tuple[float, ...]],
    sample_id: str,
    control_kind: str,
) -> dict[int, tuple[float, ...]]:
    grouped_keys: dict[int, list[int]] = {}
    for key, direction in directions.items():
        grouped_keys.setdefault(len(direction), []).append(key)
    permuted = dict(directions)
    for vector_length, keys in grouped_keys.items():
        if len(keys) < 2:
            continue
        shuffled_keys = list(keys)
        generator = random.Random(
            _build_control_seed(sample_id, control_kind, f"group:{vector_length}")
        )
        generator.shuffle(shuffled_keys)
        for destination_key, source_key in zip(keys, shuffled_keys):
            permuted[destination_key] = directions[source_key]
    return permuted


def _build_control_seed(sample_id: str, control_kind: str, scope: str) -> int:
    return int(
        compute_object_digest(
            {
                "sample_id": sample_id,
                "control_kind": control_kind,
                "scope": scope,
            }
        )[:16],
        16,
    )
"""
文件用途：构建阶段 3 surrogate trajectory 观测。
File purpose: Build surrogate trajectory observations for the stage-three scaffold.
Module type: Semi-general module
"""

from __future__ import annotations

from array import array
from pathlib import Path
import random

from main.core.digest import compute_object_digest
from main.core.schema import LatentSample
from main.core.tensor_artifact import (
    FloatTensorArtifact,
    compute_numel,
    read_float_tensor_npy,
)
from main.trajectory.interfaces import (
    TrajectoryFrame,
    TrajectoryObservation,
    validate_trajectory_time_grid,
)


def build_interpolated_observation(
    start_artifact: FloatTensorArtifact,
    end_artifact: FloatTensorArtifact,
    time_grid: list[float] | tuple[float, ...],
    source_kind: str,
) -> TrajectoryObservation:
    """功能：根据起止 tensor 构建线性插值 trajectory。

    Build a linear-interpolation trajectory observation from start and end tensors.

    Args:
        start_artifact: Start tensor artifact.
        end_artifact: End tensor artifact.
        time_grid: Ordered normalized time grid.
        source_kind: Semantic source identifier.

    Returns:
        A `TrajectoryObservation` instance.
    """
    if not isinstance(start_artifact, FloatTensorArtifact):
        raise TypeError("start_artifact must be a FloatTensorArtifact instance")
    if not isinstance(end_artifact, FloatTensorArtifact):
        raise TypeError("end_artifact must be a FloatTensorArtifact instance")
    if start_artifact.shape != end_artifact.shape:
        raise ValueError("start_artifact and end_artifact must share the same shape")
    if not isinstance(source_kind, str) or not source_kind:
        raise ValueError("source_kind must be a non-empty string")

    normalized_time_grid = validate_trajectory_time_grid(time_grid)
    frames: list[TrajectoryFrame] = []
    for time_value in normalized_time_grid:
        interpolated_values = array(
            "f",
            [
                ((1.0 - time_value) * float(start_value))
                + (time_value * float(end_value))
                for start_value, end_value in zip(
                    start_artifact.values,
                    end_artifact.values,
                )
            ],
        )
        frames.append(
            TrajectoryFrame(
                time_value=float(time_value),
                tensor_artifact=FloatTensorArtifact(
                    shape=start_artifact.shape,
                    values=interpolated_values,
                ),
            )
        )
    return TrajectoryObservation(
        source_kind=source_kind,
        time_grid=normalized_time_grid,
        frames=tuple(frames),
    )


def build_latent_interpolation_surrogate(
    sample: LatentSample,
    time_grid: list[float] | tuple[float, ...],
) -> TrajectoryObservation:
    """功能：基于观测 latent 构建 detector 侧 surrogate trajectory。

    Build a detector-side surrogate trajectory from the observed latent tensor.

    Args:
        sample: Observed latent sample carrying a persisted tensor artifact.
        time_grid: Ordered normalized time grid.

    Returns:
        A `TrajectoryObservation` instance.
    """
    observed_artifact = _load_sample_artifact(sample)
    seed_artifact = _build_seed_artifact(
        observed_artifact.shape,
        sample.latent_generation_seed_random,
        source_kind="latent_interpolation_surrogate",
    )
    return build_interpolated_observation(
        seed_artifact,
        observed_artifact,
        time_grid,
        source_kind="latent_interpolation_surrogate",
    )


def build_stage2_frozen_endpoint_replay(
    sample: LatentSample,
    time_grid: list[float] | tuple[float, ...],
    stage2_frozen_baseline_manifest_digest: str,
) -> TrajectoryObservation:
    """功能：基于阶段 2 冻结 baseline digest 构建可审计 endpoint replay trajectory。

    该函数属于项目特定写法。它不接入真实 Flow Matching 或真实视频生成流程, 而是把阶段 2
    frozen baseline manifest digest 作为只读前置依赖, 构建一个可复现的 endpoint replay
    观测。通用工程可复用的部分是“把上游冻结依赖的 digest 写入 source provenance, 再用该
    provenance 约束后续 records”的设计。

    Args:
        sample: 当前 replay 样本。
        time_grid: 受治理的归一化时间网格。
        stage2_frozen_baseline_manifest_digest: 阶段 2 frozen baseline manifest digest。

    Returns:
        `TrajectoryObservation` 实例。
    """
    observed_artifact = _load_sample_artifact(sample)
    source_kind = "stage2_frozen_endpoint_replay"
    endpoint_seed_artifact = _build_digest_seed_artifact(
        observed_artifact.shape,
        {
            "sample_id": sample.sample_id,
            "sample_role": sample.sample_role,
            "split": sample.split,
            "latent_tensor_digest_random": sample.latent_tensor_digest_random,
            "stage2_frozen_baseline_manifest_digest": stage2_frozen_baseline_manifest_digest,
        },
        source_kind=source_kind,
    )
    return build_interpolated_observation(
        endpoint_seed_artifact,
        observed_artifact,
        time_grid,
        source_kind=source_kind,
    )


def build_synthetic_flow_trajectory(
    sample: LatentSample,
    time_grid: list[float] | tuple[float, ...],
) -> TrajectoryObservation:
    """功能：构建 synthetic-flow 风格的 scaffold trajectory。

    Build a synthetic-flow style scaffold trajectory for smoke and unit checks.

    Args:
        sample: Observed latent sample carrying a persisted tensor artifact.
        time_grid: Ordered normalized time grid.

    Returns:
        A `TrajectoryObservation` instance.
    """
    observed_artifact = _load_sample_artifact(sample)
    seed_artifact = _build_seed_artifact(
        observed_artifact.shape,
        sample.latent_generation_seed_random,
        source_kind="synthetic_flow_trajectory",
    )
    return build_interpolated_observation(
        seed_artifact,
        observed_artifact,
        time_grid,
        source_kind="synthetic_flow_trajectory",
    )


def _build_digest_seed_artifact(
    shape: tuple[int, ...],
    seed_material: dict[str, object],
    source_kind: str,
) -> FloatTensorArtifact:
    if not isinstance(seed_material, dict) or not seed_material:
        raise TypeError("seed_material must be a non-empty dictionary")
    derived_seed = int(
        compute_object_digest(
            {
                "seed_material": seed_material,
                "shape": list(shape),
                "source_kind": source_kind,
            }
        )[:16],
        16,
    )
    return _build_seed_artifact(shape, derived_seed, source_kind)


def _load_sample_artifact(sample: LatentSample) -> FloatTensorArtifact:
    if not isinstance(sample, LatentSample):
        raise TypeError("sample must be a LatentSample instance")
    if sample.latent_artifact_path is None:
        raise ValueError("sample must carry latent_artifact_path")
    artifact_path = Path(sample.latent_artifact_path)
    if not artifact_path.exists():
        raise FileNotFoundError(artifact_path)
    return read_float_tensor_npy(artifact_path)


def _build_seed_artifact(
    shape: tuple[int, ...],
    seed_value: int,
    source_kind: str,
) -> FloatTensorArtifact:
    if not isinstance(shape, tuple) or not shape:
        raise TypeError("shape must be a non-empty tuple")
    if not isinstance(seed_value, int):
        raise TypeError("seed_value must be an integer")
    if not isinstance(source_kind, str) or not source_kind:
        raise ValueError("source_kind must be a non-empty string")
    derived_seed = int(
        compute_object_digest(
            {
                "seed_value": seed_value,
                "shape": list(shape),
                "source_kind": source_kind,
            }
        )[:16],
        16,
    )
    generator = random.Random(derived_seed)
    return FloatTensorArtifact(
        shape=shape,
        values=array(
            "f",
            [
                generator.gauss(0.0, 1.0)
                for _ in range(compute_numel(shape))
            ],
        ),
    )

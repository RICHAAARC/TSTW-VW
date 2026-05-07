"""
文件用途：提供阶段 1 synthetic video latent backend 的受治理默认值与可运行占位实现。
File purpose: Provide governed defaults and a runnable placeholder implementation for the stage-1 synthetic video latent backend.
Module type: Semi-general module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest
from main.core.schema import (
    LatentSample,
    ensure_supported_sample_role,
    ensure_supported_split,
)
from main.methods.temporal_tubelet_watermark.interfaces import LatentBackend


PROJECT_STAGE = "protocol_skeleton"
TARGET_CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"
LATENT_BACKEND_NAME = "synthetic_video_latent"
LATENT_BACKEND_STATUS = "placeholder_runtime"
LATENT_DISTRIBUTION = "standard_normal"
LATENT_STORAGE = "npy_artifact"
DEFAULT_LATENT_SHAPE = {
    "frames": 32,
    "channels": 4,
    "height": 32,
    "width": 32,
}
DEFAULT_LATENT_GENERATION_SEED = 20260507


def build_synthetic_video_latent_support_defaults() -> dict[str, object]:
    """功能：返回阶段 1 synthetic latent backend 的冻结默认值。

    Build the governed default payload for the stage-1 synthetic latent backend.

    Args:
        None.

    Returns:
        A dictionary containing the frozen support defaults.
    """
    return {
        "project_stage": PROJECT_STAGE,
        "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
        "latent_backend_name": LATENT_BACKEND_NAME,
        "latent_distribution": LATENT_DISTRIBUTION,
        "latent_shape": dict(DEFAULT_LATENT_SHAPE),
        "latent_generation_seed": DEFAULT_LATENT_GENERATION_SEED,
        "latent_storage": LATENT_STORAGE,
    }


def _normalize_latent_shape(
    latent_shape: dict[str, int] | tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """功能：标准化并校验 latent shape 配置。

    Normalize and validate the governed latent shape payload.

    Args:
        latent_shape: Dict-based or tuple-based latent shape payload.

    Returns:
        A normalized 4-tuple of `(frames, channels, height, width)`.
    """
    if isinstance(latent_shape, tuple):
        normalized_shape = latent_shape
    elif isinstance(latent_shape, dict):
        normalized_shape = (
            latent_shape.get("frames", 0),
            latent_shape.get("channels", 0),
            latent_shape.get("height", 0),
            latent_shape.get("width", 0),
        )
    else:
        raise TypeError("latent_shape must be a dict or a 4-tuple")

    if len(normalized_shape) != 4:
        raise ValueError("latent_shape must contain four dimensions")
    if any(
        not isinstance(dimension, int) or dimension < 1
        for dimension in normalized_shape
    ):
        raise ValueError("latent_shape dimensions must be positive integers")
    return normalized_shape


class SyntheticVideoLatentPlaceholder(LatentBackend):
    """功能：提供阶段 1 synthetic video latent 的可运行占位 backend。

    Runnable placeholder backend for the stage-1 synthetic video latent entry.

    Args:
        latent_shape: Governed latent shape.
        latent_generation_seed: Base seed used for deterministic derivation.
        latent_distribution: Governed latent distribution name.
        latent_storage: Governed latent artifact storage name.

    Returns:
        None.
    """

    def __init__(
        self,
        latent_shape: dict[str, int] | tuple[int, int, int, int] = DEFAULT_LATENT_SHAPE,
        latent_generation_seed: int = DEFAULT_LATENT_GENERATION_SEED,
        latent_distribution: str = LATENT_DISTRIBUTION,
        latent_storage: str = LATENT_STORAGE,
    ) -> None:
        self._latent_shape = _normalize_latent_shape(latent_shape)
        if not isinstance(latent_generation_seed, int):
            raise TypeError("latent_generation_seed must be an integer")
        if not isinstance(latent_distribution, str) or not latent_distribution:
            raise ValueError("latent_distribution must be a non-empty string")
        if not isinstance(latent_storage, str) or not latent_storage:
            raise ValueError("latent_storage must be a non-empty string")

        self._latent_generation_seed = latent_generation_seed
        self._latent_distribution = latent_distribution
        self._latent_storage = latent_storage

    def build_sample(self, sample_id: str, split: str, sample_role: str) -> LatentSample:
        """功能：构建 deterministic synthetic video latent 样本元数据。

        Build deterministic synthetic video latent sample metadata.

        Args:
            sample_id: Stable sample identifier.
            split: Governed split name.
            sample_role: Governed sample role name.

        Returns:
            A `LatentSample` instance.
        """
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError("sample_id must be a non-empty string")
        ensure_supported_split(split)
        ensure_supported_sample_role(sample_role)

        derived_seed = self._derive_seed(sample_id, split, sample_role)
        latent_tensor_digest_random = compute_object_digest(
            {
                "latent_backend_name": LATENT_BACKEND_NAME,
                "latent_distribution": self._latent_distribution,
                "latent_storage": self._latent_storage,
                "latent_shape": list(self._latent_shape),
                "sample_id": sample_id,
                "split": split,
                "sample_role": sample_role,
                "latent_generation_seed": derived_seed,
            }
        )
        return LatentSample(
            sample_id=sample_id,
            split=split,
            sample_role=sample_role,
            latent_shape=self._latent_shape,
            latent_tensor_digest_random=latent_tensor_digest_random,
            latent_generation_seed_random=derived_seed,
            latent_backend_name=LATENT_BACKEND_NAME,
            latent_backend_status=LATENT_BACKEND_STATUS,
        )

    def _derive_seed(self, sample_id: str, split: str, sample_role: str) -> int:
        seed_digest = compute_object_digest(
            {
                "latent_backend_name": LATENT_BACKEND_NAME,
                "latent_generation_seed": self._latent_generation_seed,
                "latent_distribution": self._latent_distribution,
                "latent_storage": self._latent_storage,
                "latent_shape": list(self._latent_shape),
                "sample_id": sample_id,
                "split": split,
                "sample_role": sample_role,
            }
        )
        return int(seed_digest[:12], 16)


def build_synthetic_video_latent_backend_from_support_config(
    support_config: dict[str, Any],
) -> SyntheticVideoLatentPlaceholder:
    """功能：根据 support config 构建 synthetic video latent backend。

    Build a synthetic video latent backend from the reserved support config.

    Args:
        support_config: Parsed stage-1 support config.

    Returns:
        A configured `SyntheticVideoLatentPlaceholder` instance.
    """
    if not isinstance(support_config, dict):
        raise TypeError("support_config must be a dictionary")
    return SyntheticVideoLatentPlaceholder(
        latent_shape=support_config.get("latent_shape", DEFAULT_LATENT_SHAPE),
        latent_generation_seed=support_config.get(
            "latent_generation_seed",
            DEFAULT_LATENT_GENERATION_SEED,
        ),
        latent_distribution=support_config.get(
            "latent_distribution",
            LATENT_DISTRIBUTION,
        ),
        latent_storage=support_config.get("latent_storage", LATENT_STORAGE),
    )
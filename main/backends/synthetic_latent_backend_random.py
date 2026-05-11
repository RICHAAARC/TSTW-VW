"""
文件用途：提供阶段 0 的随机 latent backend 骨架。File purpose: Provide the random latent backend scaffold for stage 0.
Module type: General module
"""

from __future__ import annotations

from main.core.digest import compute_object_digest
from main.core.schema import (
    DEFAULT_LATENT_SHAPE,
    LatentSample,
    ensure_supported_sample_role,
    ensure_supported_split,
)
from main.methods.temporal_tubelet_watermark.interfaces import LatentBackend


class SyntheticLatentBackendRandom(LatentBackend):
    """功能：构建可复现的随机 latent 样本骨架。
    Reproducible random latent backend for the protocol skeleton runtime scaffold.

    Args:
        latent_shape: Declared latent shape.
        base_seed_random: Base seed used for deterministic seed derivation.

    Returns:
        None.
    """

    def __init__(
        self,
        latent_shape: tuple[int, int, int, int] = DEFAULT_LATENT_SHAPE,
        base_seed_random: int = 20260506,
    ) -> None:
        if not isinstance(latent_shape, tuple) or len(latent_shape) != 4:
            raise ValueError("latent_shape must be a 4-tuple")
        if not isinstance(base_seed_random, int):
            raise TypeError("base_seed_random must be an integer")
        self._latent_shape = latent_shape
        self._base_seed_random = base_seed_random

    def build_sample(self, sample_id: str, split: str, sample_role: str) -> LatentSample:
        """功能：构建随机 latent 样本元数据。
        Build reproducible random latent sample metadata.

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

        latent_generation_seed_random = self._derive_seed(sample_id, split, sample_role)
        latent_tensor_digest_random = compute_object_digest(
            {
                "sample_id": sample_id,
                "split": split,
                "sample_role": sample_role,
                "latent_shape": list(self._latent_shape),
                "latent_generation_seed_random": latent_generation_seed_random,
            }
        )
        return LatentSample(
            sample_id=sample_id,
            split=split,
            sample_role=sample_role,
            latent_shape=self._latent_shape,
            latent_tensor_digest_random=latent_tensor_digest_random,
            latent_generation_seed_random=latent_generation_seed_random,
            latent_backend_name="synthetic_latent_backend_random",
            latent_backend_status="random",
        )

    def _derive_seed(self, sample_id: str, split: str, sample_role: str) -> int:
        seed_digest = compute_object_digest(
            {
                "base_seed_random": self._base_seed_random,
                "sample_id": sample_id,
                "split": split,
                "sample_role": sample_role,
            }
        )
        return int(seed_digest[:12], 16)
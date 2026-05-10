"""
File purpose: Provide governed defaults and runtime implementation for the synthetic video latent backend.
Module type: Semi-general module
"""

from __future__ import annotations

from array import array
from pathlib import Path
import random
import tempfile
from typing import Any

from main.core.digest import compute_file_digest, compute_object_digest
from main.core.schema import (
    CONSTRUCTION_PHASE,
    LatentSample,
    ensure_supported_sample_role,
    ensure_supported_split,
)
from main.core.tensor_artifact import compute_numel, write_float_tensor_npy
from main.methods.temporal_tubelet_watermark.interfaces import LatentBackend


PROJECT_STAGE = "synthetic_tubelet_sync_probe"
TARGET_CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"
LATENT_BACKEND_NAME = "synthetic_video_latent"
LATENT_BACKEND_STATUS = "tensor_artifact_runtime"
LATENT_DISTRIBUTION = "standard_normal"
LATENT_STORAGE = "npy_artifact"
DEFAULT_RUNTIME_PROFILE = "smoke"
FORMAL_RUNTIME_PROFILE = "formal"
TINY_RUNTIME_PROFILE = "tiny"
PROOF_RUNTIME_PROFILE = "proof"
SUPPORTED_RUNTIME_PROFILES = (
    TINY_RUNTIME_PROFILE,
    DEFAULT_RUNTIME_PROFILE,
    PROOF_RUNTIME_PROFILE,
    FORMAL_RUNTIME_PROFILE,
)
DEFAULT_LATENT_SHAPE = {
    "frames": 16,
    "channels": 4,
    "height": 16,
    "width": 16,
}
FORMAL_LATENT_SHAPE = {
    "frames": 32,
    "channels": 4,
    "height": 32,
    "width": 32,
}
PROOF_LATENT_SHAPE = {
    "frames": 16,
    "channels": 4,
    "height": 16,
    "width": 16,
}
TINY_LATENT_SHAPE = {
    "frames": 8,
    "channels": 2,
    "height": 8,
    "width": 8,
}
DEFAULT_LATENT_GENERATION_SEED = 20260507


def build_synthetic_video_latent_support_defaults() -> dict[str, object]:
    """鍔熻兘锛氳繑鍥為樁娈?1 synthetic latent backend 鐨勫喕缁撻粯璁ゅ€笺€?

    Build the governed default payload for the synthetic_tubelet_sync_probe synthetic latent backend.

    Args:
        None.

    Returns:
        A dictionary containing the frozen support defaults.
    """
    return {
        "project_stage": PROJECT_STAGE,
        "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
        "latent_backend_name": LATENT_BACKEND_NAME,
        "runtime_profile": DEFAULT_RUNTIME_PROFILE,
        "latent_distribution": LATENT_DISTRIBUTION,
        "latent_shape": dict(DEFAULT_LATENT_SHAPE),
        "formal_latent_shape": dict(FORMAL_LATENT_SHAPE),
        "proof_latent_shape": dict(PROOF_LATENT_SHAPE),
        "tiny_latent_shape": dict(TINY_LATENT_SHAPE),
        "latent_generation_seed": DEFAULT_LATENT_GENERATION_SEED,
        "latent_storage": LATENT_STORAGE,
    }


def _normalize_latent_shape(
    latent_shape: dict[str, int] | tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """鍔熻兘锛氭爣鍑嗗寲骞舵牎楠?latent shape 閰嶇疆銆?

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
    """鍔熻兘锛氭彁渚?synthetic video latent 鐨?tensor artifact backend 鍏煎绫诲悕銆?

    Compatibility class name for the governed synthetic video latent backend.

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
        self._output_root = Path(tempfile.gettempdir()) / "tstw_vw_synthetic_probe_cache"
        self._sample_cache: dict[tuple[str, str, str], LatentSample] = {}

    def set_output_root(self, output_root: str | Path) -> None:
        """鍔熻兘锛氳缃綋鍓?run 鐨?artifact 杈撳嚭鏍圭洰褰曘€?

        Set the artifact output root for the current run.

        Args:
            output_root: Run output root path.

        Returns:
            None.
        """
        resolved_output_root = Path(output_root)
        if resolved_output_root != self._output_root:
            self._sample_cache.clear()
        self._output_root = resolved_output_root

    def build_sample(self, sample_id: str, split: str, sample_role: str) -> LatentSample:
        """鍔熻兘锛氭瀯寤?deterministic synthetic video latent tensor artifact銆?

        Build a deterministic synthetic video latent tensor artifact.

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

        cache_key = (sample_id, split, sample_role)
        cached_sample = self._sample_cache.get(cache_key)
        if (
            cached_sample is not None
            and cached_sample.latent_artifact_path is not None
            and Path(cached_sample.latent_artifact_path).exists()
        ):
            return cached_sample
        derived_seed = self._derive_seed(sample_id, split, sample_role)
        artifact_relpath = (
            Path("artifacts")
            / "latents"
            / split
            / sample_role
            / f"{sample_id}.npy"
        )
        artifact_path = self._output_root / artifact_relpath
        if artifact_path.exists():
            latent_artifact_digest = compute_file_digest(artifact_path)
        else:
            latent_values = self._build_tensor_values(derived_seed)
            write_float_tensor_npy(artifact_path, self._latent_shape, latent_values)
            latent_artifact_digest = compute_file_digest(artifact_path)

        sample = self._build_latent_sample(
            sample_id=sample_id,
            split=split,
            sample_role=sample_role,
            derived_seed=derived_seed,
            artifact_relpath=artifact_relpath,
            artifact_path=artifact_path,
            latent_artifact_digest=latent_artifact_digest,
        )
        self._sample_cache[cache_key] = sample
        return sample

    def _build_latent_sample(
        self,
        sample_id: str,
        split: str,
        sample_role: str,
        derived_seed: int,
        artifact_relpath: Path,
        artifact_path: Path,
        latent_artifact_digest: str,
    ) -> LatentSample:
        return LatentSample(
            sample_id=sample_id,
            split=split,
            sample_role=sample_role,
            latent_shape=self._latent_shape,
            latent_tensor_digest_random=latent_artifact_digest,
            latent_generation_seed_random=derived_seed,
            latent_backend_name=LATENT_BACKEND_NAME,
            latent_backend_status=LATENT_BACKEND_STATUS,
            latent_artifact_relpath=artifact_relpath.as_posix(),
            latent_artifact_path=str(artifact_path),
            latent_artifact_digest=latent_artifact_digest,
            run_root_path=str(self._output_root),
            mechanism_trace={
                "construction_phase": CONSTRUCTION_PHASE,
                "latent_backend_name": LATENT_BACKEND_NAME,
                "reference_latent_shape": list(self._latent_shape),
                "latent_shape": list(self._latent_shape),
                "latent_generation_seed": self._latent_generation_seed,
                "latent_artifact_relpath": artifact_relpath.as_posix(),
                "latent_artifact_digest": latent_artifact_digest,
                "tubelet_length": None,
                "spatial_patch_size": None,
                "partition_digest": None,
                "embedding_rule": None,
                "embedding_margin": None,
                "mean_projection_before": None,
                "mean_projection_after": None,
                "mean_embedding_delta_norm": None,
                "codebook_digest": None,
                "sync_code_digest": None,
                "payload_digest": None,
                "sync_search_enabled": False,
                "sync_estimated_offset": None,
                "sync_ground_truth_offset": None,
                "sync_alignment_error": None,
                "sync_peak_rank": None,
                "sync_search_space_size": None,
                "sync_search_space_digest": None,
                "sync_estimated_scale": None,
                "sync_ground_truth_scale": 1.0,
                "sync_scale_error": None,
                "sync_alignment_mode": None,
                "clip_length": None,
            },
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

    def _build_tensor_values(self, derived_seed: int) -> array:
        generator = random.Random(derived_seed)
        return array(
            "f",
            [generator.gauss(0.0, 1.0) for _ in range(compute_numel(self._latent_shape))],
        )


SyntheticVideoLatentBackend = SyntheticVideoLatentPlaceholder


def build_synthetic_video_latent_backend_from_support_config(
    support_config: dict[str, Any],
) -> SyntheticVideoLatentBackend:
    """鍔熻兘锛氭牴鎹?support config 鏋勫缓 synthetic video latent backend銆?

    Build a synthetic video latent backend from the reserved support config.

    Args:
        support_config: Parsed synthetic_tubelet_sync_probe support config.

    Returns:
        A configured `SyntheticVideoLatentPlaceholder` instance.
    """
    if not isinstance(support_config, dict):
        raise TypeError("support_config must be a dictionary")
    return SyntheticVideoLatentBackend(
        latent_shape=_resolve_support_config_latent_shape(support_config),
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


def _resolve_support_config_latent_shape(
    support_config: dict[str, Any],
) -> dict[str, int] | tuple[int, int, int, int]:
    runtime_profile = support_config.get("runtime_profile", DEFAULT_RUNTIME_PROFILE)
    if runtime_profile == TINY_RUNTIME_PROFILE:
        return support_config.get("tiny_latent_shape", TINY_LATENT_SHAPE)
    if runtime_profile == DEFAULT_RUNTIME_PROFILE:
        return support_config.get("latent_shape", DEFAULT_LATENT_SHAPE)
    if runtime_profile == PROOF_RUNTIME_PROFILE:
        return support_config.get("proof_latent_shape", PROOF_LATENT_SHAPE)
    if runtime_profile == FORMAL_RUNTIME_PROFILE:
        return support_config.get("formal_latent_shape", FORMAL_LATENT_SHAPE)
    raise ValueError(f"unsupported runtime_profile: {runtime_profile}")

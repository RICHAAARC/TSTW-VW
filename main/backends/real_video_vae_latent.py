"""
文件用途：提供阶段 2 real-video VAE latent probe 的受治理 backend。
File purpose: Provide the governed backend for the stage-two real-video VAE latent probe.
Module type: Semi-general module
"""

from __future__ import annotations

from array import array
import math
from pathlib import Path
from typing import Any

from main.backends.synthetic_video_latent import (
    DEFAULT_LATENT_GENERATION_SEED,
    DEFAULT_LATENT_SHAPE,
    DEFAULT_RUNTIME_PROFILE,
    SyntheticVideoLatentBackend,
)
from main.core.digest import compute_file_digest, compute_object_digest
from main.core.schema import LatentSample, ensure_supported_sample_role, ensure_supported_split
from main.core.tensor_artifact import read_float_tensor_npy, write_float_tensor_npy
from main.methods.temporal_tubelet_watermark.interfaces import LatentBackend


PROJECT_STAGE = "synthetic_tubelet_sync_probe"
TARGET_CONSTRUCTION_PHASE = "real_video_vae_latent_probe"
LATENT_BACKEND_NAME = "real_video_vae_latent"
LATENT_BACKEND_STATUS = "video_vae_tensor_scaffold_runtime"
DEFAULT_VIDEO_FPS = 8
DEFAULT_VAE_BACKEND_NAME = "video_vae_tensor_runtime"
DEFAULT_VAE_BACKEND_VERSION = "framewise_tensor_runtime"
DEFAULT_VAE_ENCODE_MODE = "framewise"
DEFAULT_VAE_DECODE_MODE = "framewise"


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


def build_real_video_vae_latent_support_defaults() -> dict[str, object]:
    """功能：返回阶段 2 scaffold backend 的冻结默认值。

    Build the governed default payload for the stage-two scaffold backend.

    Args:
        None.

    Returns:
        A dictionary containing the frozen support defaults.
    """
    return {
        "project_stage": PROJECT_STAGE,
        "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
        "latent_backend_name": LATENT_BACKEND_NAME,
        "latent_backend_status": LATENT_BACKEND_STATUS,
        "runtime_profile": DEFAULT_RUNTIME_PROFILE,
        "latent_shape": dict(DEFAULT_LATENT_SHAPE),
        "latent_generation_seed": DEFAULT_LATENT_GENERATION_SEED,
        "video_fps": DEFAULT_VIDEO_FPS,
        "vae_backend_name": DEFAULT_VAE_BACKEND_NAME,
        "vae_backend_version": DEFAULT_VAE_BACKEND_VERSION,
        "vae_encode_mode": DEFAULT_VAE_ENCODE_MODE,
        "vae_decode_mode": DEFAULT_VAE_DECODE_MODE,
    }


class RealVideoVAELatentBackend(LatentBackend):
    """功能：构建阶段 2 source video 与 encoded latent artifact。

    Build source-video and encoded-latent artifacts for the stage-two real-video
    VAE latent probe scaffold.

    Args:
        latent_shape: Governed latent shape shared with the synthetic latent runtime.
        latent_generation_seed: Deterministic seed used by the underlying synthetic runtime.
        runtime_profile: Active runtime profile label.
        video_fps: Declared scaffold video frame rate.
        vae_backend_name: Stage-two VAE backend identifier.
        vae_backend_version: Stage-two VAE backend version string.
        vae_encode_mode: Declared encode mode.
        vae_decode_mode: Declared decode mode.

    Returns:
        None.
    """

    def __init__(
        self,
        latent_shape: dict[str, int] | tuple[int, int, int, int] = DEFAULT_LATENT_SHAPE,
        latent_generation_seed: int = DEFAULT_LATENT_GENERATION_SEED,
        runtime_profile: str = DEFAULT_RUNTIME_PROFILE,
        video_fps: int = DEFAULT_VIDEO_FPS,
        vae_backend_name: str = DEFAULT_VAE_BACKEND_NAME,
        vae_backend_version: str = DEFAULT_VAE_BACKEND_VERSION,
        vae_encode_mode: str = DEFAULT_VAE_ENCODE_MODE,
        vae_decode_mode: str = DEFAULT_VAE_DECODE_MODE,
    ) -> None:
        normalized_latent_shape = _normalize_latent_shape(latent_shape)
        if not isinstance(latent_generation_seed, int):
            raise TypeError("latent_generation_seed must be an integer")
        if not isinstance(runtime_profile, str) or not runtime_profile:
            raise ValueError("runtime_profile must be a non-empty string")
        if not isinstance(video_fps, int) or video_fps < 1:
            raise ValueError("video_fps must be a positive integer")
        if not isinstance(vae_backend_name, str) or not vae_backend_name:
            raise ValueError("vae_backend_name must be a non-empty string")
        if not isinstance(vae_backend_version, str) or not vae_backend_version:
            raise ValueError("vae_backend_version must be a non-empty string")
        if not isinstance(vae_encode_mode, str) or not vae_encode_mode:
            raise ValueError("vae_encode_mode must be a non-empty string")
        if not isinstance(vae_decode_mode, str) or not vae_decode_mode:
            raise ValueError("vae_decode_mode must be a non-empty string")

        self._runtime_profile = runtime_profile
        self._video_fps = video_fps
        self._vae_backend_name = vae_backend_name
        self._vae_backend_version = vae_backend_version
        self._vae_encode_mode = vae_encode_mode
        self._vae_decode_mode = vae_decode_mode
        self._synthetic_backend = SyntheticVideoLatentBackend(
            latent_shape=normalized_latent_shape,
            latent_generation_seed=latent_generation_seed,
        )
        self._output_root: Path | None = None
        self._sample_cache: dict[tuple[str, str, str], LatentSample] = {}
        self._vae_config_digest = compute_object_digest(
            {
                "latent_shape": list(normalized_latent_shape),
                "latent_generation_seed": latent_generation_seed,
                "runtime_profile": runtime_profile,
                "video_fps": video_fps,
                "vae_backend_name": vae_backend_name,
                "vae_backend_version": vae_backend_version,
                "vae_encode_mode": vae_encode_mode,
                "vae_decode_mode": vae_decode_mode,
            }
        )

    def set_output_root(self, output_root: str | Path) -> None:
        """功能：设置当前 run 的 artifact 输出根目录。

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
        self._synthetic_backend.set_output_root(resolved_output_root)

    def build_sample(self, sample_id: str, split: str, sample_role: str) -> LatentSample:
        """功能：构建阶段 2 source sample。

        Build the source sample for the stage-two scaffold.

        Args:
            sample_id: Stable sample identifier.
            split: Governed split name.
            sample_role: Governed sample role name.

        Returns:
            A `LatentSample` instance carrying stage-two scaffold artifacts.
        """
        if self._output_root is None:
            raise ValueError("output_root must be set before build_sample")
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

        source_sample = self._synthetic_backend.build_sample(sample_id, split, sample_role)
        source_video_relpath = (
            Path("artifacts") / "videos" / "source" / split / sample_role / f"{sample_id}.npy"
        )
        source_video_path = self._output_root / source_video_relpath
        source_video_digest = self._materialize_source_video(source_sample, source_video_path)

        encoded_latent_relpath = (
            Path("artifacts") / "latents" / "encoded" / split / sample_role / f"{sample_id}.npy"
        )
        encoded_latent_path = self._output_root / encoded_latent_relpath
        encoded_latent_digest = self._materialize_encoded_latent(
            source_sample,
            encoded_latent_path,
        )

        frames, _, height, width = source_sample.latent_shape
        mechanism_trace = {
            "construction_phase": TARGET_CONSTRUCTION_PHASE,
            "latent_backend_name": LATENT_BACKEND_NAME,
            "video_source_id": sample_id,
            "video_source_relpath": source_video_relpath.as_posix(),
            "video_source_digest": source_video_digest,
            "video_frame_count": frames,
            "video_fps": self._video_fps,
            "video_resolution": [height, width],
            "vae_backend_name": self._vae_backend_name,
            "vae_backend_version": self._vae_backend_version,
            "vae_config_digest": self._vae_config_digest,
            "vae_encode_mode": self._vae_encode_mode,
            "vae_decode_mode": self._vae_decode_mode,
            "encoded_latent_relpath": encoded_latent_relpath.as_posix(),
            "encoded_latent_digest": encoded_latent_digest,
            "watermarked_latent_relpath": None,
            "watermarked_latent_digest": None,
            "decoded_video_relpath": None,
            "decoded_video_digest": None,
            "attacked_video_relpath": None,
            "attacked_video_digest": None,
            "reencoded_latent_relpath": None,
            "reencoded_latent_digest": None,
            "tubelet_length": None,
            "spatial_patch_size": None,
            "embedding_margin": None,
            "codebook_digest": None,
            "sync_code_digest": None,
            "sync_search_enabled": False,
            "sync_estimated_offset": None,
            "sync_ground_truth_offset": None,
            "sync_alignment_error": None,
            "sync_peak_rank": None,
        }
        stage_two_sample = LatentSample(
            sample_id=sample_id,
            split=split,
            sample_role=sample_role,
            latent_shape=source_sample.latent_shape,
            latent_tensor_digest_random=encoded_latent_digest,
            latent_generation_seed_random=source_sample.latent_generation_seed_random,
            latent_backend_name=LATENT_BACKEND_NAME,
            latent_backend_status=LATENT_BACKEND_STATUS,
            latent_artifact_relpath=encoded_latent_relpath.as_posix(),
            latent_artifact_path=str(encoded_latent_path),
            latent_artifact_digest=encoded_latent_digest,
            run_root_path=source_sample.run_root_path,
            mechanism_trace=mechanism_trace,
            applied_attack_params=source_sample.applied_attack_params,
        )
        self._sample_cache[cache_key] = stage_two_sample
        return stage_two_sample

    def _materialize_source_video(
        self,
        source_sample: LatentSample,
        source_video_path: Path,
    ) -> str:
        if source_video_path.exists():
            return compute_file_digest(source_video_path)

        tensor_artifact = read_float_tensor_npy(source_sample.latent_artifact_path)
        frames, channels, height, width = tensor_artifact.shape
        spatial_size = height * width
        frame_size = channels * spatial_size
        video_values = array("f")
        for frame_index in range(frames):
            frame_offset = frame_index * frame_size
            for target_channel in range(3):
                source_channel = target_channel % channels
                channel_offset = frame_offset + source_channel * spatial_size
                for spatial_index in range(spatial_size):
                    latent_value = float(tensor_artifact.values[channel_offset + spatial_index])
                    video_values.append((math.tanh(latent_value) + 1.0) / 2.0)

        write_float_tensor_npy(source_video_path, (frames, 3, height, width), video_values)
        return compute_file_digest(source_video_path)

    def _materialize_encoded_latent(
        self,
        source_sample: LatentSample,
        encoded_latent_path: Path,
    ) -> str:
        if encoded_latent_path.exists():
            return compute_file_digest(encoded_latent_path)

        encoded_latent_path.parent.mkdir(parents=True, exist_ok=True)
        encoded_latent_path.write_bytes(Path(source_sample.latent_artifact_path).read_bytes())
        return compute_file_digest(encoded_latent_path)


RealVideoVAELatentPlaceholder = RealVideoVAELatentBackend


def build_real_video_vae_latent_backend_from_support_config(
    support_config: dict[str, Any],
) -> RealVideoVAELatentBackend:
    """功能：根据 support config 构建阶段 2 scaffold backend。

    Build the stage-two scaffold backend from a governed support config.

    Args:
        support_config: Parsed backend support config.

    Returns:
        A configured `RealVideoVAELatentBackend` instance.
    """
    if not isinstance(support_config, dict):
        raise TypeError("support_config must be a dictionary")

    return RealVideoVAELatentBackend(
        latent_shape=support_config.get("latent_shape", DEFAULT_LATENT_SHAPE),
        latent_generation_seed=int(
            support_config.get("latent_generation_seed", DEFAULT_LATENT_GENERATION_SEED)
        ),
        runtime_profile=str(support_config.get("runtime_profile", DEFAULT_RUNTIME_PROFILE)),
        video_fps=int(support_config.get("video_fps", DEFAULT_VIDEO_FPS)),
        vae_backend_name=str(
            support_config.get("vae_backend_name", DEFAULT_VAE_BACKEND_NAME)
        ),
        vae_backend_version=str(
            support_config.get("vae_backend_version", DEFAULT_VAE_BACKEND_VERSION)
        ),
        vae_encode_mode=str(
            support_config.get("vae_encode_mode", DEFAULT_VAE_ENCODE_MODE)
        ),
        vae_decode_mode=str(
            support_config.get("vae_decode_mode", DEFAULT_VAE_DECODE_MODE)
        ),
    )
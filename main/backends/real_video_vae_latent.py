"""
文件用途：提供阶段 2 real-video VAE latent probe 的受治理 backend。
File purpose: Provide the governed backend for the stage-two real-video VAE latent probe runtime.
Module type: Semi-general module
"""

from __future__ import annotations

from array import array
import importlib.util
from pathlib import Path
import random
from typing import Any

from main.core.digest import compute_file_digest, compute_object_digest
from main.core.schema import LatentSample, ensure_supported_sample_role, ensure_supported_split
from main.core.tensor_artifact import read_float_tensor_npy, write_float_tensor_npy
from main.methods.temporal_tubelet_watermark.interfaces import LatentBackend
from main.vae.vae_registry import resolve_vae_backend
from main.video.dataset_manifest import load_dataset_manifest, resolve_manifest_samples
from main.video.frame_preprocess import standardize_video_frames
from main.video.video_io import write_video_mp4


PROJECT_STAGE = "synthetic_tubelet_sync_probe"
TARGET_CONSTRUCTION_PHASE = "real_video_vae_latent_probe"
LATENT_BACKEND_NAME = "real_video_vae_latent"
LATENT_BACKEND_STATUS = "real_video_vae_formal_runtime"
LATENT_BACKEND_STATUS_SCAFFOLD = "video_vae_tensor_scaffold_runtime"
DEFAULT_VIDEO_FPS = 8
DEFAULT_VAE_BACKEND_NAME = "video_vae_tensor_runtime"
DEFAULT_VAE_BACKEND_VERSION = "framewise_tensor_runtime"
DEFAULT_VAE_ENCODE_MODE = "framewise"
DEFAULT_VAE_DECODE_MODE = "framewise"
DEFAULT_RUNTIME_PROFILE = "smoke"
DEFAULT_LATENT_GENERATION_SEED = 20260510
DEFAULT_LATENT_SHAPE = {
    "frames": 16,
    "channels": 4,
    "height": 16,
    "width": 16,
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


def build_real_video_vae_latent_support_defaults() -> dict[str, object]:
    """功能：返回阶段 2 runtime backend 的冻结默认值。

    Build the governed default payload for the stage-two runtime backend.

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
    VAE latent probe runtime.

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
        target_frame_count: int | None = None,
        target_resolution: tuple[int, int] | list[int] | None = None,
        frame_sampling_policy: str = "deterministic_uniform",
        local_dataset_root: str | Path | None = None,
        dataset_manifest_path: str | Path | None = None,
        vae_model_local_path: str | Path | None = None,
        allow_mock_vae_backend: bool = True,
        latent_downsample_factor: int = 8,
        batch_size_frames: int = 8,
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
        if not isinstance(frame_sampling_policy, str) or not frame_sampling_policy:
            raise ValueError("frame_sampling_policy must be a non-empty string")
        if target_resolution is not None:
            if (
                not isinstance(target_resolution, (tuple, list))
                or len(target_resolution) != 2
                or any(not isinstance(v, int) or v < 1 for v in target_resolution)
            ):
                raise ValueError("target_resolution must be a pair of positive integers")
        if target_frame_count is not None and (
            not isinstance(target_frame_count, int) or target_frame_count < 1
        ):
            raise ValueError("target_frame_count must be a positive integer")
        if (
            not isinstance(latent_downsample_factor, int)
            or isinstance(latent_downsample_factor, bool)
            or latent_downsample_factor < 1
        ):
            raise ValueError("latent_downsample_factor must be a positive integer")
        if not isinstance(batch_size_frames, int) or batch_size_frames < 1:
            raise ValueError("batch_size_frames must be a positive integer")

        self._runtime_profile = runtime_profile
        self._video_fps = video_fps
        self._vae_backend_name = vae_backend_name
        self._vae_backend_version = vae_backend_version
        self._vae_encode_mode = vae_encode_mode
        self._vae_decode_mode = vae_decode_mode
        self._latent_shape = normalized_latent_shape
        self._latent_generation_seed = latent_generation_seed
        self._latent_downsample_factor = int(latent_downsample_factor)
        self._target_frame_count = int(target_frame_count or normalized_latent_shape[0])
        if target_resolution is None:
            if runtime_profile == "formal":
                self._target_resolution = (
                    int(normalized_latent_shape[2]) * self._latent_downsample_factor,
                    int(normalized_latent_shape[3]) * self._latent_downsample_factor,
                )
            else:
                self._target_resolution = (int(normalized_latent_shape[2]), int(normalized_latent_shape[3]))
        else:
            self._target_resolution = (int(target_resolution[0]), int(target_resolution[1]))
        self._frame_sampling_policy = frame_sampling_policy
        self._batch_size_frames = batch_size_frames
        self._mp4_runtime_available = importlib.util.find_spec("imageio_ffmpeg") is not None
        self._local_dataset_root = None if local_dataset_root is None else Path(local_dataset_root)
        self._dataset_manifest_path = None if dataset_manifest_path is None else Path(dataset_manifest_path)
        self._resolved_samples_by_split: dict[str, list[Any]] = {}
        if self._dataset_manifest_path is not None and self._local_dataset_root is not None:
            manifest_payload = load_dataset_manifest(self._dataset_manifest_path)
            resolved_samples = resolve_manifest_samples(
                manifest_payload,
                self._local_dataset_root,
                formal_mode=self._runtime_profile == "formal",
            )
            for resolved_sample in resolved_samples:
                self._resolved_samples_by_split.setdefault(resolved_sample.split, []).append(
                    resolved_sample
                )

        vae_config = {
            "runtime_profile": runtime_profile,
            "vae_backend_name": vae_backend_name,
            "vae_backend_version": vae_backend_version,
            "vae_encode_mode": vae_encode_mode,
            "vae_decode_mode": vae_decode_mode,
            "allow_mock_vae_backend": bool(allow_mock_vae_backend),
            "latent_downsample_factor": int(latent_downsample_factor),
            "batch_size_frames": int(batch_size_frames),
        }
        if vae_model_local_path is not None:
            vae_config["vae_model_local_path"] = str(vae_model_local_path)
        self._vae_backend = resolve_vae_backend(vae_config)
        self._vae_metadata = self._vae_backend.backend_metadata()
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
                "target_frame_count": self._target_frame_count,
                "target_resolution": list(self._target_resolution),
                "latent_downsample_factor": self._latent_downsample_factor,
                "frame_sampling_policy": self._frame_sampling_policy,
                "batch_size_frames": self._batch_size_frames,
                "dataset_manifest_path": None if self._dataset_manifest_path is None else str(self._dataset_manifest_path),
                "local_dataset_root": None if self._local_dataset_root is None else str(self._local_dataset_root),
                "vae_model_local_path": None if vae_model_local_path is None else str(vae_model_local_path),
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

    def build_sample(self, sample_id: str, split: str, sample_role: str) -> LatentSample:
        """功能：构建阶段 2 source sample。

        Build the source sample for the governed stage-two runtime.

        Args:
            sample_id: Stable sample identifier.
            split: Governed split name.
            sample_role: Governed sample role name.

        Returns:
            A `LatentSample` instance carrying stage-two runtime artifacts.
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
            self._validate_encoded_latent_shape(
                cached_sample.latent_shape,
                Path(cached_sample.latent_artifact_path),
                "memory_sample_cache",
            )
            return cached_sample

        source_video_relpath = (
            Path("artifacts")
            / "videos"
            / "source"
            / split
            / sample_role
            / f"{sample_id}.{self._select_source_container_extension()}"
        )
        source_video_path = self._output_root / source_video_relpath
        source_video_metadata, source_video_id = self._materialize_source_video(
            sample_id,
            split,
            source_video_path,
        )

        encoded_latent_relpath = (
            Path("artifacts") / "latents" / "encoded" / split / sample_role / f"{sample_id}.npy"
        )
        encoded_latent_path = self._output_root / encoded_latent_relpath
        encoded_latent_digest, encoded_latent_shape = self._materialize_encoded_latent(
            source_video_metadata,
            encoded_latent_path,
        )

        frames, channels, height, width = encoded_latent_shape
        latent_backend_status = (
            LATENT_BACKEND_STATUS if self._runtime_profile == "formal" else LATENT_BACKEND_STATUS_SCAFFOLD
        )
        latent_generation_seed_random = self._derive_runtime_seed(sample_id, split)
        mechanism_trace = {
            "construction_phase": TARGET_CONSTRUCTION_PHASE,
            "latent_backend_name": LATENT_BACKEND_NAME,
            "latent_backend_status": latent_backend_status,
            "reference_latent_shape": [frames, channels, height, width],
            "latent_shape": [frames, channels, height, width],
            "latent_artifact_relpath": encoded_latent_relpath.as_posix(),
            "latent_artifact_digest": encoded_latent_digest,
            "video_runtime_status": (
                "real_mp4_runtime"
                if source_video_metadata["container"] == "mp4"
                else "tensor_video_fallback_runtime"
            ),
            "video_source_id": source_video_id,
            "video_source_relpath": source_video_relpath.as_posix(),
            "video_source_digest": source_video_metadata["video_digest"],
            "video_frame_count": int(source_video_metadata["frame_count"]),
            "video_fps": self._video_fps,
            "video_resolution": [source_video_metadata["height"], source_video_metadata["width"]],
            "video_container": source_video_metadata["container"],
            "video_codec": source_video_metadata["codec"],
            "vae_backend_name": self._vae_backend_name,
            "vae_backend_version": self._vae_backend_version,
            "vae_model_digest": self._vae_metadata.get("vae_model_digest"),
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
            latent_shape=(frames, channels, height, width),
            latent_tensor_digest_random=encoded_latent_digest,
            latent_generation_seed_random=latent_generation_seed_random,
            latent_backend_name=LATENT_BACKEND_NAME,
            latent_backend_status=latent_backend_status,
            latent_artifact_relpath=encoded_latent_relpath.as_posix(),
            latent_artifact_path=str(encoded_latent_path),
            latent_artifact_digest=encoded_latent_digest,
            run_root_path=str(self._output_root),
            mechanism_trace=mechanism_trace,
            applied_attack_params=None,
        )
        self._sample_cache[cache_key] = stage_two_sample
        return stage_two_sample

    def _materialize_source_video(
        self,
        sample_id: str,
        split: str,
        source_video_path: Path,
    ) -> tuple[dict[str, Any], str]:
        resolved_sample = self._resolve_dataset_sample(sample_id, split)
        if source_video_path.exists():
            source_video_metadata = self._read_existing_source_video_metadata(
                source_video_path
            )
            self._validate_source_video_metadata(
                source_video_metadata,
                source_video_path,
            )
            source_video_id = (
                sample_id
                if resolved_sample is None
                else str(resolved_sample.video_source_id)
            )
            return source_video_metadata, source_video_id

        if resolved_sample is None:
            if self._runtime_profile == "formal":
                raise RuntimeError(
                    "formal runtime requires a resolved dataset sample; fallback video generation is disabled"
                )
            source_video_id = sample_id
            video_frames = self._build_fallback_video_frames(sample_id, split)
        else:
            source_video_id = resolved_sample.video_source_id
            from main.video.video_io import read_video_frames

            loaded_video = read_video_frames(resolved_sample.resolved_path)
            video_frames = loaded_video.frames

        standardized_frames = standardize_video_frames(
            video_frames,
            target_frame_count=self._target_frame_count,
            target_fps=self._video_fps,
            target_resolution=self._target_resolution,
            frame_sampling_policy=self._frame_sampling_policy,
        )
        if source_video_path.suffix.lower() == ".mp4":
            source_video_metadata = write_video_mp4(
                standardized_frames,
                source_video_path,
                fps=self._video_fps,
                codec="libx264",
                crf=18,
            )
            source_video_metadata["video_relpath"] = str(
                source_video_path.relative_to(self._output_root)
            ).replace("\\", "/")
            return source_video_metadata, source_video_id

        tensor_frames = standardized_frames.transpose(0, 3, 1, 2)
        write_float_tensor_npy(
            source_video_path,
            (
                int(tensor_frames.shape[0]),
                int(tensor_frames.shape[1]),
                int(tensor_frames.shape[2]),
                int(tensor_frames.shape[3]),
            ),
            array("f", tensor_frames.reshape(-1).tolist()),
        )
        return {
            "video_relpath": str(source_video_path.relative_to(self._output_root)).replace("\\", "/"),
            "video_digest": compute_file_digest(source_video_path),
            "frame_count": int(tensor_frames.shape[0]),
            "fps": int(self._video_fps),
            "height": int(tensor_frames.shape[2]),
            "width": int(tensor_frames.shape[3]),
            "codec": "tensor_npy",
            "container": "npy",
            "pixel_format": "float32_nchw",
        }, source_video_id

    def _materialize_encoded_latent(
        self,
        source_video_metadata: dict[str, Any],
        encoded_latent_path: Path,
    ) -> tuple[str, tuple[int, int, int, int]]:
        if encoded_latent_path.exists():
            cached_artifact = read_float_tensor_npy(encoded_latent_path)
            cached_shape = (
                int(cached_artifact.shape[0]),
                int(cached_artifact.shape[1]),
                int(cached_artifact.shape[2]),
                int(cached_artifact.shape[3]),
            )
            self._validate_encoded_latent_shape(
                cached_shape,
                encoded_latent_path,
                "disk_encoded_latent_cache",
            )
            return compute_file_digest(encoded_latent_path), cached_shape

        from main.video.video_io import read_video_frames

        source_video_path = self._output_root / source_video_metadata["video_relpath"]
        if str(source_video_metadata.get("container")) == "npy":
            tensor_artifact = read_float_tensor_npy(source_video_path)
            import numpy as np

            standardized_video = np.asarray(tensor_artifact.values, dtype=np.float32).reshape(
                tensor_artifact.shape
            ).transpose(0, 2, 3, 1)
        else:
            standardized_video = read_video_frames(source_video_path).frames
        encoded_latent = self._vae_backend.encode_video(standardized_video)
        normalized_latent = self._normalize_encoded_latent(encoded_latent)
        normalized_shape = (
            int(normalized_latent.shape[0]),
            int(normalized_latent.shape[1]),
            int(normalized_latent.shape[2]),
            int(normalized_latent.shape[3]),
        )
        self._validate_encoded_latent_shape(
            normalized_shape,
            encoded_latent_path,
            "fresh_encoded_latent",
        )

        encoded_latent_path.parent.mkdir(parents=True, exist_ok=True)
        write_float_tensor_npy(
            encoded_latent_path,
            normalized_shape,
            array("f", normalized_latent.astype("float32").reshape(-1).tolist()),
        )
        return compute_file_digest(encoded_latent_path), normalized_shape

    def _read_existing_source_video_metadata(self, source_video_path: Path) -> dict[str, Any]:
        """读取已存在的 source artifact 真实元数据, 避免用当前配置伪造旧缓存属性."""
        if self._output_root is None:
            raise ValueError("output_root must be set before reading source video metadata")
        source_relpath = str(source_video_path.relative_to(self._output_root)).replace("\\", "/")
        suffix = source_video_path.suffix.lower()
        if suffix == ".mp4":
            from main.video.video_io import read_video_frames

            loaded_video = read_video_frames(source_video_path)
            video_frames = loaded_video.frames
            return {
                "video_relpath": source_relpath,
                "video_digest": compute_file_digest(source_video_path),
                "frame_count": int(video_frames.shape[0]),
                "fps": int(loaded_video.fps),
                "height": int(video_frames.shape[1]),
                "width": int(video_frames.shape[2]),
                "codec": "libx264",
                "container": "mp4",
                "pixel_format": "yuv420p",
            }
        if suffix == ".npy":
            tensor_artifact = read_float_tensor_npy(source_video_path)
            if len(tensor_artifact.shape) != 4:
                raise RuntimeError(
                    f"cached source tensor must be 4D: path={source_video_path}, shape={tensor_artifact.shape}"
                )
            return {
                "video_relpath": source_relpath,
                "video_digest": compute_file_digest(source_video_path),
                "frame_count": int(tensor_artifact.shape[0]),
                "fps": int(self._video_fps),
                "height": int(tensor_artifact.shape[2]),
                "width": int(tensor_artifact.shape[3]),
                "codec": "tensor_npy",
                "container": "npy",
                "pixel_format": "float32_nchw",
            }
        raise ValueError(f"unsupported cached source video suffix: {source_video_path.suffix}")

    def _validate_source_video_metadata(
        self,
        source_video_metadata: dict[str, Any],
        source_video_path: Path,
    ) -> None:
        """校验 source artifact 的真实输入尺寸, 阻断旧 run root 对新运行的污染."""
        actual_shape = (
            int(source_video_metadata["frame_count"]),
            int(source_video_metadata["height"]),
            int(source_video_metadata["width"]),
        )
        expected_shape = (
            self._target_frame_count,
            int(self._target_resolution[0]),
            int(self._target_resolution[1]),
        )
        if actual_shape != expected_shape:
            raise RuntimeError(
                "cached source video metadata does not match the current runtime contract; "
                f"path={source_video_path}, actual={actual_shape}, expected={expected_shape}"
            )

    def _strict_encoded_latent_shape_required(self) -> bool:
        """判断当前 backend 是否必须把 encoded latent 形状绑定到正式 VAE 合同."""
        return (
            self._runtime_profile == "formal"
            or self._vae_backend_name == "diffusers_autoencoder_kl_framewise"
        )

    def _expected_encoded_latent_shape(self) -> tuple[int, int, int, int]:
        """根据视频目标分辨率与 VAE 下采样倍率计算正式 encoded latent 形状."""
        target_height, target_width = self._target_resolution
        if target_height % self._latent_downsample_factor != 0:
            raise RuntimeError(
                "target_resolution height must be divisible by latent_downsample_factor"
            )
        if target_width % self._latent_downsample_factor != 0:
            raise RuntimeError(
                "target_resolution width must be divisible by latent_downsample_factor"
            )
        expected_shape = (
            self._target_frame_count,
            int(self._latent_shape[1]),
            int(target_height // self._latent_downsample_factor),
            int(target_width // self._latent_downsample_factor),
        )
        configured_shape = (
            self._target_frame_count,
            int(self._latent_shape[1]),
            int(self._latent_shape[2]),
            int(self._latent_shape[3]),
        )
        if expected_shape != configured_shape:
            raise RuntimeError(
                "configured latent_shape does not match target_resolution / latent_downsample_factor; "
                f"configured={configured_shape}, expected={expected_shape}"
            )
        return expected_shape

    def _validate_encoded_latent_shape(
        self,
        latent_shape: tuple[int, int, int, int],
        artifact_path: Path,
        artifact_source: str,
    ) -> None:
        """校验 encoded latent 输入输出合同, 防止低分辨率缓存继续流入机制记录."""
        if len(latent_shape) != 4 or any(int(dimension) < 1 for dimension in latent_shape):
            raise RuntimeError(
                f"encoded latent must be a positive 4D tensor: source={artifact_source}, "
                f"path={artifact_path}, shape={latent_shape}"
            )
        if not self._strict_encoded_latent_shape_required():
            return
        expected_shape = self._expected_encoded_latent_shape()
        actual_shape = tuple(int(dimension) for dimension in latent_shape)
        if actual_shape != expected_shape:
            raise RuntimeError(
                "encoded latent shape does not match the current formal runtime contract; "
                f"source={artifact_source}, path={artifact_path}, "
                f"actual={actual_shape}, expected={expected_shape}. "
                "Reset the run root before rerunning the notebook."
            )

    def _resolve_dataset_sample(self, sample_id: str, split: str) -> Any | None:
        split_samples = self._resolved_samples_by_split.get(split, [])
        if not split_samples:
            return None
        stable_index = self._derive_runtime_seed(sample_id, split) % len(split_samples)
        return split_samples[stable_index]

    def _select_source_container_extension(self) -> str:
        if self._mp4_runtime_available:
            return "mp4"
        if self._runtime_profile == "formal":
            # 中文注释：formal 模式要求真实 mp4 运行时，不允许回退为 tensor artifact。
            raise RuntimeError("formal runtime requires mp4 support via imageio_ffmpeg")
        return "npy"

    def _derive_runtime_seed(self, sample_id: str, split: str) -> int:
        seed_digest = compute_object_digest(
            {
                "sample_id": sample_id,
                "split": split,
                "latent_generation_seed": self._latent_generation_seed,
            }
        )
        return int(seed_digest[:12], 16)

    def _build_fallback_video_frames(self, sample_id: str, split: str) -> Any:
        runtime_seed = self._derive_runtime_seed(sample_id, split)
        generator = random.Random(runtime_seed)
        frame_count = self._target_frame_count
        height, width = self._target_resolution
        import numpy as np

        frames = np.zeros((frame_count, height, width, 3), dtype=np.float32)
        for frame_index in range(frame_count):
            for row_index in range(height):
                for col_index in range(width):
                    base_value = (
                        (frame_index + 1) * 0.01
                        + (row_index + 1) * 0.001
                        + (col_index + 1) * 0.0001
                    )
                    noise = generator.random() * 0.02
                    value = min(1.0, max(0.0, base_value + noise))
                    frames[frame_index, row_index, col_index, 0] = value
                    frames[frame_index, row_index, col_index, 1] = min(1.0, value * 0.9 + 0.03)
                    frames[frame_index, row_index, col_index, 2] = min(1.0, value * 0.8 + 0.05)
        return frames

    def _normalize_encoded_latent(self, encoded_latent: Any) -> Any:
        import numpy as np

        if not isinstance(encoded_latent, np.ndarray):
            raise TypeError("encoded latent must be a numpy ndarray")
        if encoded_latent.ndim != 4:
            raise ValueError("encoded latent must have four dimensions")
        if encoded_latent.shape[-1] == 3:
            return np.transpose(encoded_latent.astype(np.float32), (0, 3, 1, 2))
        return encoded_latent.astype(np.float32)


RealVideoVAELatentPlaceholder = RealVideoVAELatentBackend


def build_real_video_vae_latent_backend_from_support_config(
    support_config: dict[str, Any],
) -> RealVideoVAELatentBackend:
    """功能：根据 support config 构建阶段 2 runtime backend。

    Build the stage-two runtime backend from a governed support config.

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
        target_frame_count=support_config.get("target_frame_count"),
        target_resolution=support_config.get("target_resolution"),
        frame_sampling_policy=str(
            support_config.get("frame_sampling_policy", "deterministic_uniform")
        ),
        local_dataset_root=support_config.get("local_dataset_root"),
        dataset_manifest_path=support_config.get("dataset_manifest_path"),
        vae_model_local_path=support_config.get("vae_model_local_path"),
        allow_mock_vae_backend=bool(support_config.get("allow_mock_vae_backend", True)),
        latent_downsample_factor=int(support_config.get("latent_downsample_factor", 8)),
        batch_size_frames=int(support_config.get("batch_size_frames", 8)),
    )

"""
文件用途：提供阶段 2 的 framewise AutoencoderKL VAE backend。
File purpose: Provide the framewise AutoencoderKL VAE backend for stage-two runtime.
Module type: Semi-general module
"""

from __future__ import annotations

import importlib
from typing import Any

import numpy as np

from main.vae.model_localizer import compute_model_root_digest, resolve_vae_model_root
from main.vae.vae_backend import VAEBackend
from main.vae.vae_tensor_codec import (
    downsample_nchw_mean,
    ensure_latent_batch,
    ensure_video_batch,
    nchw_minus1_1_to_rgb_video,
    rgb_video_to_nchw_minus1_1,
    upsample_nchw_nearest,
)


class DiffusersAutoencoderKLFramewiseBackend(VAEBackend):
    """功能：在受治理阶段提供 framewise AutoencoderKL 编解码接口。

    Framewise AutoencoderKL backend with deterministic encode/decode semantics.

    Args:
        config: Backend configuration payload.

    Returns:
        None.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise TypeError("config must be a dictionary")

        self._config = dict(config)
        self._runtime_profile = str(config.get("runtime_profile", "smoke"))
        self._vae_backend_name = str(
            config.get("vae_backend_name", "diffusers_autoencoder_kl_framewise")
        )
        self._vae_backend_version = str(
            config.get("vae_backend_version", "autoencoder_kl_local_formal")
        )
        self._vae_encode_mode = str(
            config.get("vae_encode_mode", "framewise_deterministic_mode")
        )
        self._vae_decode_mode = str(config.get("vae_decode_mode", "framewise_decode"))
        self._latent_channels = int(config.get("latent_channels", 4))
        self._latent_downsample_factor = int(config.get("latent_downsample_factor", 8))
        self._allow_mock_vae_backend = bool(config.get("allow_mock_vae_backend", True))
        self._vae_dtype = str(
            config.get("vae_dtype", "float16_on_cuda_float32_on_cpu")
        )
        self._batch_size_frames = int(config.get("batch_size_frames", 8))
        if self._batch_size_frames < 1:
            raise ValueError("batch_size_frames must be a positive integer")

        required_model = self._runtime_profile == "formal"
        self._model_root = resolve_vae_model_root(config, required=required_model)
        self._vae_model_digest = compute_model_root_digest(self._model_root)
        self._runtime_impl = "mock_numpy"
        self._device = "cpu"

        self._torch = None
        self._vae_model = None
        try:
            torch_module = importlib.import_module("torch")
            diffusers_module = importlib.import_module("diffusers")
        except Exception:
            if required_model and not self._allow_mock_vae_backend:
                # 中文注释：formal 且关闭 mock 时，不允许在缺失依赖下继续。
                raise RuntimeError("diffusers backend dependencies are unavailable")
        else:
            self._torch = torch_module
            model_class = getattr(diffusers_module, "AutoencoderKL")
            if self._model_root is not None:
                model_loader = getattr(model_class, "from_pretrained")
                try:
                    self._vae_model = model_loader(
                        str(self._model_root),
                        local_files_only=True,
                    )
                except Exception as exc:
                    self._vae_model = None
                    if required_model and not self._allow_mock_vae_backend:
                        raise RuntimeError(
                            "formal mode requires a valid local AutoencoderKL model"
                        ) from exc
                else:
                    cuda_available = bool(torch_module.cuda.is_available())
                    if cuda_available and "float16" in self._vae_dtype:
                        self._device = "cuda"
                        self._vae_model = self._vae_model.to(device=self._device, dtype=torch_module.float16)
                    else:
                        self._device = "cpu"
                        self._vae_model = self._vae_model.to(device=self._device, dtype=torch_module.float32)
                    self._vae_model.eval()
                    self._runtime_impl = "diffusers_autoencoder_kl"
            elif required_model and not self._allow_mock_vae_backend:
                raise RuntimeError("formal mode requires a valid local AutoencoderKL model")

    def encode_video(
        self,
        video_batch: np.ndarray,
        *,
        config: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """功能：将视频帧编码为 latent 张量。

        Encode video frames into latent tensors.

        Args:
            video_batch: Video frames in `[F, H, W, 3]`.
            config: Optional runtime overrides.

        Returns:
            Latent tensor in `[F, C, H_lat, W_lat]`.
        """
        del config
        normalized_video = ensure_video_batch(video_batch)
        if self._runtime_impl == "diffusers_autoencoder_kl":
            return self._encode_with_diffusers(normalized_video)
        return self._encode_with_mock(normalized_video)

    def decode_video(
        self,
        latent_batch: np.ndarray,
        *,
        config: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """功能：将 latent 张量解码为视频帧。

        Decode latent tensors into video frames.

        Args:
            latent_batch: Latent tensor in `[F, C, H_lat, W_lat]`.
            config: Optional runtime overrides.

        Returns:
            Video frames in `[F, H, W, 3]`.
        """
        decode_config = config or {}
        normalized_latent = ensure_latent_batch(latent_batch)
        if self._runtime_impl == "diffusers_autoencoder_kl":
            return self._decode_with_diffusers(normalized_latent)

        target_resolution = decode_config.get("target_resolution")
        if isinstance(target_resolution, (list, tuple)) and len(target_resolution) == 2:
            target_height = int(target_resolution[0])
            target_width = int(target_resolution[1])
        else:
            target_height = int(normalized_latent.shape[2] * self._latent_downsample_factor)
            target_width = int(normalized_latent.shape[3] * self._latent_downsample_factor)
        return self._decode_with_mock(normalized_latent, (target_height, target_width))

    def backend_metadata(self) -> dict[str, Any]:
        """功能：返回受治理 backend 元数据。

        Return governed backend metadata payload.

        Args:
            None.

        Returns:
            Backend metadata dictionary.
        """
        return {
            "vae_backend_name": self._vae_backend_name,
            "vae_backend_version": self._vae_backend_version,
            "vae_model_digest": self._vae_model_digest,
            "vae_encode_mode": self._vae_encode_mode,
            "vae_decode_mode": self._vae_decode_mode,
            "device": self._device,
            "dtype": self._vae_dtype,
            "batch_size_frames": self._batch_size_frames,
            "runtime_impl": self._runtime_impl,
            "deterministic_encode": True,
        }

    def _encode_with_mock(self, video_batch: np.ndarray) -> np.ndarray:
        video_nchw = rgb_video_to_nchw_minus1_1(video_batch)
        latent = downsample_nchw_mean(video_nchw, self._latent_downsample_factor)
        channels = latent.shape[1]
        if channels == self._latent_channels:
            return latent.astype(np.float32)
        if channels > self._latent_channels:
            return latent[:, : self._latent_channels].astype(np.float32)

        repeated = np.zeros(
            (
                latent.shape[0],
                self._latent_channels,
                latent.shape[2],
                latent.shape[3],
            ),
            dtype=np.float32,
        )
        for channel_index in range(self._latent_channels):
            repeated[:, channel_index] = latent[:, channel_index % channels]
        return repeated

    def _decode_with_mock(
        self,
        latent_batch: np.ndarray,
        target_resolution: tuple[int, int],
    ) -> np.ndarray:
        if latent_batch.shape[1] < 3:
            padding = np.zeros(
                (
                    latent_batch.shape[0],
                    3 - latent_batch.shape[1],
                    latent_batch.shape[2],
                    latent_batch.shape[3],
                ),
                dtype=np.float32,
            )
            latent_batch = np.concatenate([latent_batch, padding], axis=1)
        rgb_like = latent_batch[:, :3]
        upsampled = upsample_nchw_nearest(rgb_like, target_resolution)
        return nchw_minus1_1_to_rgb_video(np.clip(upsampled, -1.0, 1.0))

    def _encode_with_diffusers(self, video_batch: np.ndarray) -> np.ndarray:
        if self._torch is None or self._vae_model is None:
            raise RuntimeError("diffusers runtime is not initialized")

        torch = self._torch
        video_nchw = rgb_video_to_nchw_minus1_1(video_batch)
        latent_batches: list[np.ndarray] = []
        for frame_start in range(0, int(video_nchw.shape[0]), self._batch_size_frames):
            frame_stop = frame_start + self._batch_size_frames
            tensor = torch.from_numpy(video_nchw[frame_start:frame_stop]).to(device=self._device)
            if self._device == "cuda" and "float16" in self._vae_dtype:
                tensor = tensor.to(dtype=torch.float16)
            else:
                tensor = tensor.to(dtype=torch.float32)
            with torch.no_grad():
                posterior = self._vae_model.encode(tensor).latent_dist
                latents = posterior.mode()
                scaling_factor = float(getattr(self._vae_model.config, "scaling_factor", 1.0))
                latents = latents * scaling_factor
            latent_batches.append(latents.detach().float().cpu().numpy())
        if not latent_batches:
            raise RuntimeError("encode_video requires at least one frame")
        return np.concatenate(latent_batches, axis=0)

    def _decode_with_diffusers(self, latent_batch: np.ndarray) -> np.ndarray:
        if self._torch is None or self._vae_model is None:
            raise RuntimeError("diffusers runtime is not initialized")

        torch = self._torch
        decoded_batches: list[np.ndarray] = []
        scaling_factor = float(getattr(self._vae_model.config, "scaling_factor", 1.0))
        for frame_start in range(0, int(latent_batch.shape[0]), self._batch_size_frames):
            frame_stop = frame_start + self._batch_size_frames
            tensor = torch.from_numpy(latent_batch[frame_start:frame_stop]).to(device=self._device)
            if self._device == "cuda" and "float16" in self._vae_dtype:
                tensor = tensor.to(dtype=torch.float16)
            else:
                tensor = tensor.to(dtype=torch.float32)
            with torch.no_grad():
                decoded = self._vae_model.decode(tensor / scaling_factor).sample
            decoded_batches.append(decoded.detach().float().cpu().numpy())
        if not decoded_batches:
            raise RuntimeError("decode_video requires at least one latent frame")
        decoded_np = np.concatenate(decoded_batches, axis=0)
        return nchw_minus1_1_to_rgb_video(decoded_np)

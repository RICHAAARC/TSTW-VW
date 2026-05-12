"""
文件用途：提供阶段 2 VAE backend registry。
File purpose: Provide the governed stage-two VAE backend registry for scaffold and formal runtimes.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.vae.diffusers_autoencoder_kl_framewise import DiffusersAutoencoderKLFramewiseBackend
from main.vae.video_vae_tensor_runtime import VideoVAETensorRuntimeBackend


PLACEHOLDER_VAE_BACKEND_NAMES = {
    "video_vae_tensor_runtime",
    "video_vae_backend_placeholder",
}


def resolve_vae_backend(config: dict[str, Any]) -> Any:
    """功能：根据配置解析阶段 2 VAE backend。

    Resolve the governed stage-two VAE backend from configuration.

    Args:
        config: Parsed backend configuration payload.

    Returns:
        A configured VAE backend instance.
    """
    if not isinstance(config, dict):
        raise TypeError("config must be a dictionary")
    vae_backend_name = str(config.get("vae_backend_name", "video_vae_tensor_runtime"))
    runtime_profile = str(config.get("runtime_profile", "smoke"))

    if runtime_profile == "formal" and vae_backend_name in PLACEHOLDER_VAE_BACKEND_NAMES:
        raise ValueError("formal runtime cannot use placeholder VAE backend")

    if vae_backend_name in PLACEHOLDER_VAE_BACKEND_NAMES:
        return VideoVAETensorRuntimeBackend(config)
    if vae_backend_name == "diffusers_autoencoder_kl_framewise":
        return DiffusersAutoencoderKLFramewiseBackend(config)

    raise ValueError(f"unsupported vae_backend_name: {vae_backend_name}")
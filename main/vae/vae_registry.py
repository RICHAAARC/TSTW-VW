"""
文件用途：提供阶段 2 tensor-runtime VAE backend registry。
File purpose: Provide the tensor-runtime VAE backend registry for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.vae.video_vae_backend_placeholder import VideoVAETensorRuntimeBackend


def resolve_vae_backend(config: dict[str, Any]) -> VideoVAETensorRuntimeBackend:
    """功能：根据配置解析阶段 2 tensor-runtime VAE backend。

    Resolve the tensor-runtime stage-two VAE backend from configuration.

    Args:
        config: Parsed backend configuration payload.

    Returns:
        A configured `VideoVAETensorRuntimeBackend` instance.
    """
    if not isinstance(config, dict):
        raise TypeError("config must be a dictionary")
    vae_backend_name = str(config.get("vae_backend_name", "video_vae_tensor_runtime"))
    if vae_backend_name not in {"video_vae_tensor_runtime", "video_vae_backend_placeholder"}:
        raise ValueError(f"unsupported vae_backend_name: {vae_backend_name}")
    return VideoVAETensorRuntimeBackend(config)
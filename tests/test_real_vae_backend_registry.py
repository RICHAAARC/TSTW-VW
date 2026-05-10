"""
文件用途：验证阶段 2 VAE registry 的 backend 解析行为。
File purpose: Validate backend resolution behavior for stage-two VAE registry.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

from main.vae.diffusers_autoencoder_kl_framewise import DiffusersAutoencoderKLFramewiseBackend
from main.vae.vae_registry import resolve_vae_backend
from main.vae.video_vae_backend_placeholder import VideoVAETensorRuntimeBackend


@pytest.mark.unit
def test_vae_registry_resolves_diffusers_backend_with_smoke_mock(tmp_path: Path) -> None:
    """Validate registry resolves diffusers backend in smoke mode.

    Args:
        tmp_path: Temporary model root.

    Returns:
        None.
    """
    model_root = tmp_path / "models" / "vae"
    model_root.mkdir(parents=True, exist_ok=True)
    backend = resolve_vae_backend(
        {
            "runtime_profile": "smoke",
            "vae_backend_name": "diffusers_autoencoder_kl_framewise",
            "vae_backend_version": "autoencoder_kl_local_formal",
            "vae_model_local_path": str(model_root),
            "allow_mock_vae_backend": True,
        }
    )

    assert isinstance(backend, DiffusersAutoencoderKLFramewiseBackend)
    metadata = backend.backend_metadata()
    assert metadata["vae_backend_name"] == "diffusers_autoencoder_kl_framewise"


@pytest.mark.unit
def test_vae_registry_resolves_placeholder_backend_in_smoke() -> None:
    """Validate registry keeps placeholder backend for non-formal runtime.

    Args:
        None.

    Returns:
        None.
    """
    backend = resolve_vae_backend(
        {
            "runtime_profile": "smoke",
            "vae_backend_name": "video_vae_tensor_runtime",
        }
    )
    assert isinstance(backend, VideoVAETensorRuntimeBackend)


@pytest.mark.unit
def test_vae_registry_blocks_placeholder_backend_in_formal() -> None:
    """Validate formal runtime blocks placeholder VAE backend.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(ValueError):
        resolve_vae_backend(
            {
                "runtime_profile": "formal",
                "vae_backend_name": "video_vae_backend_placeholder",
            }
        )

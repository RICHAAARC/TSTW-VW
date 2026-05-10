"""
文件用途：验证 framewise AutoencoderKL backend 的基础编解码行为。
File purpose: Validate basic encode/decode behavior of framewise AutoencoderKL backend.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from main.vae.diffusers_autoencoder_kl_framewise import DiffusersAutoencoderKLFramewiseBackend


@pytest.mark.unit
def test_diffusers_autoencoder_kl_framewise_backend_metadata_and_shapes(tmp_path: Path) -> None:
    """Validate backend metadata completeness and tensor shape contracts.

    Args:
        tmp_path: Temporary model root.

    Returns:
        None.
    """
    model_root = tmp_path / "models" / "vae"
    model_root.mkdir(parents=True, exist_ok=True)
    backend = DiffusersAutoencoderKLFramewiseBackend(
        {
            "runtime_profile": "smoke",
            "vae_backend_name": "diffusers_autoencoder_kl_framewise",
            "vae_backend_version": "autoencoder_kl_local_formal",
            "vae_model_local_path": str(model_root),
            "vae_encode_mode": "framewise_deterministic_mode",
            "vae_decode_mode": "framewise_decode",
            "latent_downsample_factor": 8,
            "allow_mock_vae_backend": True,
        }
    )

    video_batch = np.random.default_rng(20260510).random((4, 32, 32, 3), dtype=np.float32)
    first_latent = backend.encode_video(video_batch)
    second_latent = backend.encode_video(video_batch)
    decoded_video = backend.decode_video(first_latent, config={"target_resolution": (32, 32)})

    assert first_latent.shape == (4, 4, 4, 4)
    assert decoded_video.shape == (4, 32, 32, 3)
    assert np.array_equal(first_latent, second_latent)

    metadata = backend.backend_metadata()
    for key in (
        "vae_backend_name",
        "vae_backend_version",
        "vae_model_digest",
        "vae_encode_mode",
        "vae_decode_mode",
        "device",
        "dtype",
    ):
        assert key in metadata


@pytest.mark.unit
def test_diffusers_autoencoder_kl_framewise_backend_formal_requires_model_path() -> None:
    """Validate formal mode requires an existing model path.

    Args:
        None.

    Returns:
        None.
    """
    with pytest.raises(FileNotFoundError):
        DiffusersAutoencoderKLFramewiseBackend(
            {
                "runtime_profile": "formal",
                "vae_backend_name": "diffusers_autoencoder_kl_framewise",
                "vae_model_local_path": "missing_model_path",
                "allow_mock_vae_backend": False,
            }
        )

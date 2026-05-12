"""
文件用途：验证 framewise AutoencoderKL backend 的基础编解码行为。
File purpose: Validate basic encode/decode behavior of framewise AutoencoderKL backend.
Module type: General module
"""

from __future__ import annotations

import types
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.quick

import main.vae.diffusers_autoencoder_kl_framewise as backend_module

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


@pytest.mark.unit
def test_diffusers_autoencoder_kl_framewise_backend_formal_accepts_autoencoder_root_without_model_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate formal mode accepts a local AutoencoderKL root without model_index.json.

    Args:
        tmp_path: Temporary model root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    model_root = tmp_path / "models" / "vae"
    model_root.mkdir(parents=True, exist_ok=True)
    (model_root / "config.json").write_text("{}\n", encoding="utf-8")
    captured_loader_call: dict[str, object] = {}

    class DummyModel:
        def to(self, *, device: str, dtype: object) -> "DummyModel":
            captured_loader_call["device"] = device
            captured_loader_call["dtype"] = dtype
            return self

        def eval(self) -> None:
            captured_loader_call["eval_called"] = True

    class DummyAutoencoderKL:
        @staticmethod
        def from_pretrained(model_path: str, *, local_files_only: bool) -> DummyModel:
            captured_loader_call["model_path"] = model_path
            captured_loader_call["local_files_only"] = local_files_only
            return DummyModel()

    dummy_torch = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: False),
        float16="float16",
        float32="float32",
    )
    dummy_diffusers = types.SimpleNamespace(AutoencoderKL=DummyAutoencoderKL)

    def _fake_import_module(module_name: str) -> object:
        if module_name == "torch":
            return dummy_torch
        if module_name == "diffusers":
            return dummy_diffusers
        raise ImportError(module_name)

    monkeypatch.setattr(backend_module.importlib, "import_module", _fake_import_module)

    backend = DiffusersAutoencoderKLFramewiseBackend(
        {
            "runtime_profile": "formal",
            "vae_backend_name": "diffusers_autoencoder_kl_framewise",
            "vae_model_local_path": str(model_root),
            "allow_mock_vae_backend": False,
        }
    )

    assert captured_loader_call["model_path"] == str(model_root)
    assert captured_loader_call["local_files_only"] is True
    assert captured_loader_call["device"] == "cpu"
    assert captured_loader_call["eval_called"] is True
    assert backend.backend_metadata()["runtime_impl"] == "diffusers_autoencoder_kl"

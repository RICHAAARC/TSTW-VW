"""
文件用途：验证 formal 阶段 2 backend 禁止回退为 synthetic fallback video。
File purpose: Validate that the formal stage-two backend forbids synthetic fallback video generation.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

import main.backends.real_video_vae_latent as real_video_backend_module

from main.backends.real_video_vae_latent import RealVideoVAELatentBackend


class _FakeVaeBackend:
    def backend_metadata(self) -> dict[str, str]:
        return {"vae_model_digest": "fake-model-digest"}

    def encode_video(self, video_batch):
        raise AssertionError("encode_video should not be reached when formal fallback is disabled")


@pytest.mark.unit
def test_formal_backend_raises_when_dataset_sample_cannot_be_resolved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate formal runtime fails before generating fallback video frames.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    monkeypatch.setattr(
        real_video_backend_module,
        "resolve_vae_backend",
        lambda config: _FakeVaeBackend(),
    )

    backend = RealVideoVAELatentBackend(
        latent_shape=(4, 2, 4, 4),
        runtime_profile="formal",
        vae_backend_name="diffusers_autoencoder_kl_framewise",
        vae_backend_version="formal_fake_backend",
        vae_encode_mode="framewise_deterministic_mode",
        vae_decode_mode="framewise_decode",
        allow_mock_vae_backend=False,
    )
    backend.set_output_root(tmp_path / "run_root")

    with pytest.raises(RuntimeError, match="fallback video generation is disabled"):
        backend.build_sample("missing_sample", "test", "clean_negative")
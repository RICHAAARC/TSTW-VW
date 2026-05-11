"""
文件用途：验证阶段 2 VAE registry 的 backend 解析行为。
File purpose: Validate backend resolution behavior for stage-two VAE registry.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import experiments.real_video_vae_latent_probe.runner as real_video_runner_module
from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner
from main.vae.diffusers_autoencoder_kl_framewise import DiffusersAutoencoderKLFramewiseBackend
from main.vae.vae_registry import resolve_vae_backend
from main.vae.video_vae_tensor_runtime import VideoVAETensorRuntimeBackend


ROOT = Path(__file__).resolve().parents[1]


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


@pytest.mark.unit
@pytest.mark.parametrize(
    ("runtime_field_name", "runtime_field_value"),
    [
        ("local_vae_model_root", "mapped_from_local_vae_model_root"),
        ("vae_model_local_path", "mapped_from_vae_model_local_path"),
    ],
)
def test_runner_maps_runtime_vae_model_root_to_backend_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runtime_field_name: str,
    runtime_field_value: str,
) -> None:
    """Validate runtime config maps VAE local path into backend config.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.
        runtime_field_name: Runtime config key name.
        runtime_field_value: Runtime config path value.

    Returns:
        None.
    """
    captured_backend_config: dict[str, object] = {}

    class DummyVaeBackend:
        """Lightweight backend stub for runner configuration tests."""

        def backend_metadata(self) -> dict[str, object]:
            return {
                "vae_backend_name": "video_vae_tensor_runtime",
                "vae_backend_version": "framewise_tensor_runtime",
                "vae_encode_mode": "framewise",
                "vae_decode_mode": "framewise",
            }

    def _fake_resolve_vae_backend(config: dict[str, object]) -> DummyVaeBackend:
        captured_backend_config.clear()
        captured_backend_config.update(config)
        return DummyVaeBackend()

    def _stop_after_backend_mapping(support_config: dict[str, object]) -> object:
        del support_config
        raise RuntimeError("stop_after_backend_mapping")

    monkeypatch.setattr(
        real_video_runner_module,
        "resolve_vae_backend",
        _fake_resolve_vae_backend,
    )
    monkeypatch.setattr(
        real_video_runner_module,
        "build_real_video_vae_latent_backend_from_support_config",
        _stop_after_backend_mapping,
    )

    runtime_config_path = tmp_path / "runtime_config.json"
    runtime_config_path.write_text(
        json.dumps({runtime_field_name: runtime_field_value}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="stop_after_backend_mapping"):
        RealVideoVaeLatentRunner(ROOT).run(
            output_root=tmp_path / "outputs" / "runs" / "runtime_config_mapping",
            run_mode="smoke",
            samples_per_role=1,
            runtime_profile_override="tiny",
            runtime_config_path=runtime_config_path,
        )

    assert captured_backend_config["vae_model_local_path"] == runtime_field_value

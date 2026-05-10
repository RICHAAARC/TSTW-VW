"""
文件用途：验证阶段 2 VAE encode/decode 元数据与 digest 稳定性。
File purpose: Validate metadata and digest stability for the stage-two VAE path.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.backends.real_video_vae_latent import RealVideoVAELatentBackend


def test_stage2_vae_placeholder_metadata_and_digest_are_stable(tmp_path: Path) -> None:
    """Validate stage-two VAE metadata and encoded digests remain stable.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "stage2_vae_repro"
    backend = RealVideoVAELatentBackend(latent_shape=(8, 2, 8, 8), runtime_profile="tiny")
    backend.set_output_root(output_root)
    first_sample = backend.build_sample("rvp_vae_same", "test", "clean_negative")
    second_sample = backend.build_sample("rvp_vae_same", "test", "clean_negative")

    assert first_sample.latent_tensor_digest_random == second_sample.latent_tensor_digest_random
    assert first_sample.mechanism_trace["vae_config_digest"] == second_sample.mechanism_trace["vae_config_digest"]
    assert first_sample.mechanism_trace["vae_backend_name"] == "video_vae_tensor_runtime"

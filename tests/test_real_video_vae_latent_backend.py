"""
文件用途：验证阶段 2 backend 的 source video 与 encoded latent artifact 行为。
File purpose: Validate source-video and encoded-latent artifacts for the stage-two backend.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

from main.backends.real_video_vae_latent import RealVideoVAELatentBackend
from main.core.tensor_artifact import read_float_tensor_npy


@pytest.mark.smoke
def test_real_video_vae_latent_backend_materializes_placeholder_artifacts(
    tmp_path: Path,
) -> None:
    """功能：验证阶段 2 backend 生成稳定 source video 与 encoded latent artifact。

    Validate that the stage-two backend materializes stable source-video
    and encoded-latent artifacts.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_probe_scaffold"
    backend = RealVideoVAELatentBackend(latent_shape=(8, 2, 8, 8), runtime_profile="tiny")
    backend.set_output_root(output_root)

    sample = backend.build_sample(
        sample_id="rvp_calibration_clean_negative_000001",
        split="calibration",
        sample_role="clean_negative",
    )
    repeated_sample = backend.build_sample(
        sample_id="rvp_calibration_clean_negative_000001",
        split="calibration",
        sample_role="clean_negative",
    )

    assert sample.latent_backend_name == "real_video_vae_latent"
    assert sample.latent_backend_status == "video_vae_tensor_scaffold_runtime"
    assert sample.latent_tensor_digest_random == repeated_sample.latent_tensor_digest_random
    assert sample.latent_generation_seed_random == repeated_sample.latent_generation_seed_random
    assert sample.latent_artifact_relpath == repeated_sample.latent_artifact_relpath
    assert sample.latent_artifact_path is not None
    assert Path(sample.latent_artifact_path).exists()

    mechanism_trace = sample.mechanism_trace
    assert mechanism_trace is not None
    assert mechanism_trace["construction_phase"] == "real_video_vae_latent_probe"
    assert mechanism_trace["latent_backend_name"] == "real_video_vae_latent"
    assert mechanism_trace["encoded_latent_digest"] == sample.latent_tensor_digest_random
    assert mechanism_trace["encoded_latent_relpath"].endswith(".npy")
    assert mechanism_trace["video_source_relpath"].endswith(".npy")
    assert not Path(mechanism_trace["video_source_relpath"]).is_absolute()
    assert mechanism_trace["video_source_id"] == "rvp_calibration_clean_negative_000001"
    assert mechanism_trace["video_frame_count"] == 8
    assert mechanism_trace["video_resolution"] == [8, 8]
    assert mechanism_trace["vae_backend_name"] == "video_vae_tensor_runtime"

    source_video_path = output_root / mechanism_trace["video_source_relpath"]
    assert source_video_path.exists()
    source_video = read_float_tensor_npy(source_video_path)
    assert source_video.shape == (8, 3, 8, 8)
    assert all(0.0 <= float(value) <= 1.0 for value in source_video.values[:16])
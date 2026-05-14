"""
文件用途：验证阶段 2 VAE encode/decode 元数据与 digest 稳定性。File purpose: Validate metadata and digest stability for the stage-two VAE path.
Module type: General module
"""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import numpy as np
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.smoke]

from main.backends.real_video_vae_latent import RealVideoVAELatentBackend
from main.video.video_io import write_video_mp4


def test_real_video_vae_latent_vae_placeholder_metadata_and_digest_are_stable(tmp_path: Path) -> None:
    """Validate stage-two VAE metadata and encoded digests remain stable.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("imageio_ffmpeg is unavailable")

    dataset_root = tmp_path / "datasets" / "real_video_probe"
    dataset_root.mkdir(parents=True, exist_ok=True)
    source_root = dataset_root / "source"
    source_root.mkdir(parents=True, exist_ok=True)
    source_frames = np.random.default_rng(20260510).random((6, 10, 12, 3), dtype=np.float32)
    write_video_mp4(
        source_frames,
        source_root / "rvp_000001.mp4",
        fps=8,
        codec="libx264",
        crf=20,
    )
    manifest_path = dataset_root / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_name": "tiny_dataset",
                "dataset_version": "v1",
                "samples": [
                    {
                        "video_source_id": "rvp_000000",
                        "relpath": "source/rvp_000001.mp4",
                        "split": "dev",
                    },
                    {
                        "video_source_id": "rvp_000001",
                        "relpath": "source/rvp_000001.mp4",
                        "split": "test",
                    },
                    {
                        "video_source_id": "rvp_000101",
                        "relpath": "source/rvp_000001.mp4",
                        "split": "calibration",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    output_root = tmp_path / "outputs" / "runs" / "real_video_vae_repro"
    backend = RealVideoVAELatentBackend(
        latent_shape=(8, 2, 8, 8),
        runtime_profile="tiny",
        dataset_manifest_path=manifest_path,
        local_dataset_root=dataset_root,
        target_frame_count=8,
        target_resolution=(8, 8),
        allow_mock_vae_backend=True,
    )
    backend.set_output_root(output_root)
    first_sample = backend.build_sample("rvp_vae_same", "test", "clean_negative")
    second_sample = backend.build_sample("rvp_vae_same", "test", "clean_negative")

    assert first_sample.latent_tensor_digest_random == second_sample.latent_tensor_digest_random
    assert first_sample.mechanism_trace["vae_config_digest"] == second_sample.mechanism_trace["vae_config_digest"]
    assert first_sample.mechanism_trace["vae_backend_name"] == "video_vae_tensor_runtime"
    assert first_sample.mechanism_trace["video_runtime_status"] == "real_mp4_runtime"

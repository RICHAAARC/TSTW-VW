"""
文件用途：验证阶段 2 backend 会使用 manifest 中的 mp4 样本构建 source artifact。
File purpose: Validate that stage-two backend uses manifest mp4 samples for source artifacts.
Module type: General module
"""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from main.backends.real_video_vae_latent import RealVideoVAELatentBackend
from main.video.video_io import probe_video_metadata, write_video_mp4


@pytest.mark.unit
def test_real_video_vae_latent_backend_reads_mp4_from_manifest(tmp_path: Path) -> None:
    """Validate backend resolves mp4 input from local manifest mapping.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("imageio_ffmpeg is unavailable")

    dataset_root = tmp_path / "datasets" / "real_video_probe"
    source_root = dataset_root / "source"
    source_root.mkdir(parents=True, exist_ok=True)

    source_frames = np.random.default_rng(20260510).random((6, 10, 12, 3), dtype=np.float32)
    source_path = source_root / "rvp_000001.mp4"
    write_video_mp4(source_frames, source_path, fps=8, codec="libx264", crf=20)

    manifest_path = dataset_root / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_name": "tiny_dataset",
                "dataset_version": "v1",
                "samples": [
                    {
                        "video_source_id": "rvp_000001",
                        "relpath": "source/rvp_000001.mp4",
                        "split": "calibration",
                    },
                    {
                        "video_source_id": "rvp_000101",
                        "relpath": "source/rvp_000001.mp4",
                        "split": "test",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    backend = RealVideoVAELatentBackend(
        latent_shape=(8, 4, 8, 8),
        runtime_profile="tiny",
        dataset_manifest_path=manifest_path,
        local_dataset_root=dataset_root,
        target_frame_count=8,
        target_resolution=(8, 8),
        allow_mock_vae_backend=True,
    )
    output_root = tmp_path / "outputs" / "runs" / "real_video_backend_mp4_manifest"
    backend.set_output_root(output_root)

    sample = backend.build_sample("rvp_calibration_clean_negative_000001", "calibration", "clean_negative")

    mechanism_trace = sample.mechanism_trace
    assert mechanism_trace is not None
    assert mechanism_trace["video_source_id"] == "rvp_000001"
    assert mechanism_trace["video_source_relpath"].endswith(".mp4")
    assert mechanism_trace["encoded_latent_relpath"].endswith(".npy")
    assert mechanism_trace["video_runtime_status"] == "real_mp4_runtime"

    source_video_path = output_root / mechanism_trace["video_source_relpath"]
    assert source_video_path.exists()
    metadata = probe_video_metadata(source_video_path)
    assert metadata["height"] == 8
    assert metadata["width"] == 8
    assert metadata["channels"] == 3

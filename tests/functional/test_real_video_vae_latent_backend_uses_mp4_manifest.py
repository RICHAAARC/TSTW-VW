"""
文件用途：验证阶段 2 backend 会使用 manifest 中的 mp4 样本构建 source artifact。
File purpose: Validate that stage-two backend uses manifest mp4 samples for source artifacts.
Module type: General module
"""

from __future__ import annotations

import json
import importlib.util
from array import array
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.quick

from main.backends.real_video_vae_latent import RealVideoVAELatentBackend
from main.core.tensor_artifact import write_float_tensor_npy
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
                        "video_source_id": "rvp_000000",
                        "relpath": "source/rvp_000001.mp4",
                        "split": "dev",
                    },
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
    assert mechanism_trace["reference_latent_shape"] == list(sample.latent_shape)
    assert mechanism_trace["latent_shape"] == list(sample.latent_shape)
    assert mechanism_trace["latent_artifact_relpath"] == sample.latent_artifact_relpath
    assert mechanism_trace["latent_artifact_digest"] == sample.latent_artifact_digest
    assert mechanism_trace["video_source_relpath"].endswith(".mp4")
    assert mechanism_trace["encoded_latent_relpath"].endswith(".npy")
    assert mechanism_trace["video_runtime_status"] == "real_mp4_runtime"

    source_video_path = output_root / mechanism_trace["video_source_relpath"]
    assert source_video_path.exists()
    metadata = probe_video_metadata(source_video_path)
    assert metadata["height"] == 8
    assert metadata["width"] == 8
    assert metadata["channels"] == 3


@pytest.mark.unit
def test_formal_backend_derives_video_resolution_from_latent_shape_when_missing(
    tmp_path: Path,
) -> None:
    """校验 formal backend 不再把 latent 空间尺寸误当作 video 分辨率。

    Args:
        tmp_path: 临时输出根目录。

    Returns:
        None。
    """
    model_root = tmp_path / "session_models" / "autoencoder_kl"
    model_root.mkdir(parents=True, exist_ok=True)

    backend = RealVideoVAELatentBackend(
        latent_shape=(32, 4, 32, 32),
        runtime_profile="formal",
        vae_backend_name="diffusers_autoencoder_kl_framewise",
        vae_model_local_path=model_root,
        allow_mock_vae_backend=True,
        latent_downsample_factor=8,
    )

    assert backend._target_resolution == (256, 256)
    assert backend._expected_encoded_latent_shape() == (32, 4, 32, 32)


@pytest.mark.unit
def test_formal_backend_rejects_stale_low_resolution_encoded_latent_cache(
    tmp_path: Path,
) -> None:
    """校验 formal encoded latent 缓存形状错误时会立即阻断运行。

    Args:
        tmp_path: 临时输出根目录。

    Returns:
        None。
    """
    model_root = tmp_path / "session_models" / "autoencoder_kl"
    model_root.mkdir(parents=True, exist_ok=True)
    backend = RealVideoVAELatentBackend(
        latent_shape=(32, 4, 32, 32),
        runtime_profile="formal",
        vae_backend_name="diffusers_autoencoder_kl_framewise",
        vae_model_local_path=model_root,
        target_frame_count=32,
        target_resolution=(256, 256),
        allow_mock_vae_backend=True,
        latent_downsample_factor=8,
    )
    output_root = tmp_path / "runs" / "formal_backend_shape_guard"
    backend.set_output_root(output_root)
    stale_encoded_latent_path = (
        output_root
        / "artifacts"
        / "latents"
        / "encoded"
        / "calibration"
        / "clean_negative"
        / "sample.npy"
    )
    write_float_tensor_npy(
        stale_encoded_latent_path,
        (32, 4, 4, 4),
        array("f", [0.0] * (32 * 4 * 4 * 4)),
    )

    with pytest.raises(RuntimeError, match="encoded latent shape"):
        backend._materialize_encoded_latent(
            {
                "video_relpath": "artifacts/videos/source/calibration/clean_negative/sample.mp4",
                "container": "mp4",
            },
            stale_encoded_latent_path,
        )


@pytest.mark.unit
def test_backend_rejects_stale_source_tensor_cache_shape(
    tmp_path: Path,
) -> None:
    """校验旧 source video tensor 不能伪装成当前 runtime 的目标分辨率。

    Args:
        tmp_path: 临时输出根目录。

    Returns:
        None。
    """
    backend = RealVideoVAELatentBackend(
        latent_shape=(4, 4, 4, 4),
        runtime_profile="smoke",
        target_frame_count=4,
        target_resolution=(16, 16),
        allow_mock_vae_backend=True,
    )
    output_root = tmp_path / "runs" / "source_cache_shape_guard"
    backend.set_output_root(output_root)
    stale_source_path = (
        output_root
        / "artifacts"
        / "videos"
        / "source"
        / "dev"
        / "clean_negative"
        / "sample.npy"
    )
    write_float_tensor_npy(
        stale_source_path,
        (4, 3, 4, 4),
        array("f", [0.0] * (4 * 3 * 4 * 4)),
    )

    with pytest.raises(RuntimeError, match="cached source video metadata"):
        backend._materialize_source_video(
            "sample_dev_clean_negative_000001",
            "dev",
            stale_source_path,
        )

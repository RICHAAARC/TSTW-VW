"""
文件用途：测试阶段 2 真实视频帧级质量指标。
File purpose: Test frame-based video quality metrics for stage-two real video runtime.
Module type: General module
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.integration

from main.analysis.real_video_quality_metrics import build_real_video_quality_metrics_payload
from main.video.video_io import write_video_mp4

# 检查 ffmpeg 是否可用
HAS_FFMPEG = shutil.which("ffmpeg") is not None


def _create_test_video(frames: np.ndarray, output_path: Path, fps: int = 8) -> None:
    """创建测试视频的辅助函数。

    Helper to create test videos. Falls back to numpy array if ffmpeg unavailable.
    """
    if not HAS_FFMPEG:
        # 占位实现：只保存为 numpy 数组
        np.save(output_path.with_suffix(".npy"), frames)
    else:
        write_video_mp4(frames, output_path, fps=fps)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_quality_metrics_identical_videos() -> None:
    """功能：测试相同视频的质量指标应该接近理想值。

    Test that identical videos produce high-quality scores.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 生成测试视频：8 帧，256x256，固定内容
        frames = np.random.RandomState(42).uniform(0.2, 0.8, size=(8, 256, 256, 3)).astype(
            np.float32
        )
        frames = np.clip(frames, 0.0, 1.0)

        video1_path = tmpdir_path / "video1.mp4"
        video2_path = tmpdir_path / "video2.mp4"

        write_video_mp4(frames, video1_path, fps=8)
        write_video_mp4(frames, video2_path, fps=8)

        payload = build_real_video_quality_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["quality_metrics_runtime"] == "real_video_frame_metrics"
        assert payload["vae_reconstruction_psnr"] is not None
        assert payload["vae_reconstruction_ssim"] is not None
        # 相同视频的 PSNR 应该很高（> 40）
        assert payload["vae_reconstruction_psnr"] > 40.0
        # SSIM 应该接近 1.0
        assert payload["vae_reconstruction_ssim"] > 0.99
        assert payload["quality_failure_reason"] is None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_quality_metrics_noisy_videos() -> None:
    """功能：测试加噪视频的质量指标应该下降。

    Test that noisy videos produce lower quality scores.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 生成基础视频
        base_frames = np.random.RandomState(42).uniform(0.2, 0.8, size=(8, 256, 256, 3)).astype(
            np.float32
        )
        base_frames = np.clip(base_frames, 0.0, 1.0)

        # 添加高斯噪声
        noisy_frames = base_frames + np.random.RandomState(43).normal(
            0, 0.1, size=base_frames.shape
        )
        noisy_frames = np.clip(noisy_frames, 0.0, 1.0)

        video1_path = tmpdir_path / "video_clean.mp4"
        video2_path = tmpdir_path / "video_noisy.mp4"

        write_video_mp4(base_frames, video1_path, fps=8)
        write_video_mp4(noisy_frames, video2_path, fps=8)

        payload = build_real_video_quality_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["quality_metrics_runtime"] == "real_video_frame_metrics"
        assert payload["vae_reconstruction_psnr"] is not None
        assert payload["vae_reconstruction_ssim"] is not None
        # 加噪视频的 PSNR 应该低于相同视频
        assert payload["vae_reconstruction_psnr"] < 40.0
        # SSIM 应该低于相同视频
        assert payload["vae_reconstruction_ssim"] < 0.99


@pytest.mark.smoke
def test_real_video_quality_metrics_missing_video() -> None:
    """功能：测试缺失视频文件的错误处理。

    Test that missing video files are handled gracefully.
    """
    payload = build_real_video_quality_metrics_payload(
        Path("/nonexistent/video1.mp4"),
        Path("/nonexistent/video2.mp4"),
        runtime_config={},
    )

    assert payload["quality_metrics_runtime"] == "real_video_frame_metrics"
    assert payload["vae_reconstruction_psnr"] is None
    assert payload["quality_failure_reason"] is not None
    assert "video_io_error" in payload["quality_failure_reason"]


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_quality_metrics_psnr_in_valid_range() -> None:
    """功能：测试 PSNR 值在合理范围内。

    Test that PSNR values are in reasonable range.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 生成测试视频
        frames1 = np.random.RandomState(42).uniform(0.3, 0.7, size=(4, 128, 128, 3)).astype(
            np.float32
        )
        frames2 = frames1 + np.random.RandomState(43).normal(
            0, 0.05, size=frames1.shape
        )
        frames1 = np.clip(frames1, 0.0, 1.0)
        frames2 = np.clip(frames2, 0.0, 1.0)

        video1_path = tmpdir_path / "v1.mp4"
        video2_path = tmpdir_path / "v2.mp4"

        write_video_mp4(frames1, video1_path, fps=8)
        write_video_mp4(frames2, video2_path, fps=8)

        payload = build_real_video_quality_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["vae_reconstruction_psnr"] is not None
        # PSNR 应该在合理范围内 [0, 100]
        assert 0 <= payload["vae_reconstruction_psnr"] <= 100


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_quality_metrics_ssim_in_valid_range() -> None:
    """功能：测试 SSIM 值在 [0, 1] 范围内。

    Test that SSIM values are in [0, 1] range.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames1 = np.random.RandomState(42).uniform(0.3, 0.7, size=(4, 128, 128, 3)).astype(
            np.float32
        )
        frames2 = frames1 + np.random.RandomState(43).normal(
            0, 0.05, size=frames1.shape
        )
        frames1 = np.clip(frames1, 0.0, 1.0)
        frames2 = np.clip(frames2, 0.0, 1.0)

        video1_path = tmpdir_path / "v1.mp4"
        video2_path = tmpdir_path / "v2.mp4"

        write_video_mp4(frames1, video1_path, fps=8)
        write_video_mp4(frames2, video2_path, fps=8)

        payload = build_real_video_quality_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["vae_reconstruction_ssim"] is not None
        # SSIM 应该在 [0, 1] 范围内
        assert 0 <= payload["vae_reconstruction_ssim"] <= 1


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_quality_metrics_different_frame_counts() -> None:
    """功能：测试不同帧数视频的对齐处理。

    Test that videos with different frame counts are handled correctly.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames1 = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
            np.float32
        )
        frames2 = np.random.RandomState(43).uniform(0.3, 0.7, size=(4, 128, 128, 3)).astype(
            np.float32
        )
        frames1 = np.clip(frames1, 0.0, 1.0)
        frames2 = np.clip(frames2, 0.0, 1.0)

        video1_path = tmpdir_path / "v1.mp4"
        video2_path = tmpdir_path / "v2.mp4"

        write_video_mp4(frames1, video1_path, fps=8)
        write_video_mp4(frames2, video2_path, fps=8)

        payload = build_real_video_quality_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["quality_metrics_runtime"] == "real_video_frame_metrics"
        # 应该使用最小帧数进行对齐，不应该失败
        assert payload["vae_reconstruction_psnr"] is not None

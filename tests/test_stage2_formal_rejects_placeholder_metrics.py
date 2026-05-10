"""
文件用途：测试 formal 模式拒绝占位质量与时序指标。
File purpose: Test that formal mode rejects placeholder quality and temporal metrics.
Module type: General module
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

from main.analysis.quality_metrics import build_quality_metrics_payload
from main.analysis.temporal_metrics import build_temporal_metrics_payload
from main.video.video_io import write_video_mp4

# 检查 ffmpeg 是否可用
HAS_FFMPEG = shutil.which("ffmpeg") is not None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_formal_mode_uses_real_quality_metrics() -> None:
    """功能：测试 formal 模式使用真实质量指标。

    Test that formal mode selects real video quality metrics.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
            np.float32
        )
        frames = np.clip(frames, 0.0, 1.0)

        video1_path = tmpdir_path / "v1.mp4"
        video2_path = tmpdir_path / "v2.mp4"

        write_video_mp4(frames, video1_path, fps=8)
        write_video_mp4(frames, video2_path, fps=8)

        # 使用 formal 模式（real_video_frame_metrics）
        payload = build_quality_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={"quality_metrics_mode": "real_video_frame_metrics"},
        )

        assert payload["quality_metrics_runtime"] == "real_video_frame_metrics"
        assert payload["vae_reconstruction_psnr"] is not None


@pytest.mark.smoke
def test_placeholder_mode_uses_placeholder_quality_metrics() -> None:
    """功能：测试占位模式使用占位质量指标。

    Test that placeholder mode uses placeholder quality metrics.
    """
    if HAS_FFMPEG:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            frames = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
                np.float32
            )
            frames = np.clip(frames, 0.0, 1.0)

            video1_path = tmpdir_path / "v1.mp4"
            video2_path = tmpdir_path / "v2.mp4"

            write_video_mp4(frames, video1_path, fps=8)
            write_video_mp4(frames, video2_path, fps=8)

            # 使用占位模式
            payload = build_quality_metrics_payload(
                video1_path,
                video2_path,
                runtime_config={"quality_metrics_mode": "placeholder"},
            )

            assert payload["quality_metrics_runtime"] == "placeholder_tensor_video_metrics"


@pytest.mark.smoke
def test_default_mode_is_placeholder() -> None:
    """功能：测试默认模式为占位实现。

    Test that default mode uses placeholder implementation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
            np.float32
        )
        frames = np.clip(frames, 0.0, 1.0)

        video1_path = tmpdir_path / "v1.mp4"
        video2_path = tmpdir_path / "v2.mp4"

        write_video_mp4(frames, video1_path, fps=8)
        write_video_mp4(frames, video2_path, fps=8)

        # 使用默认配置（无 runtime_config）
        payload = build_quality_metrics_payload(
            video1_path,
            video2_path,
        )

        assert payload["quality_metrics_runtime"] == "placeholder_tensor_video_metrics"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_formal_temporal_metrics_real_video_mode() -> None:
    """功能：测试 formal 模式时序指标使用真实实现。

    Test that formal mode temporal metrics use real video implementation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
            np.float32
        )
        frames = np.clip(frames, 0.0, 1.0)

        video1_path = tmpdir_path / "v1.mp4"
        video2_path = tmpdir_path / "v2.mp4"

        write_video_mp4(frames, video1_path, fps=8)
        write_video_mp4(frames, video2_path, fps=8)

        # 使用 formal 模式
        payload = build_temporal_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={"temporal_metrics_mode": "real_video_frame_metrics"},
        )

        assert payload["temporal_metrics_runtime"] == "real_video_frame_metrics"


@pytest.mark.smoke
def test_placeholder_temporal_metrics_mode() -> None:
    """功能：测试占位时序指标模式。

    Test that placeholder temporal metrics mode works correctly.
    """
    if HAS_FFMPEG:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            frames = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
                np.float32
            )
            frames = np.clip(frames, 0.0, 1.0)

            video1_path = tmpdir_path / "v1.mp4"
            video2_path = tmpdir_path / "v2.mp4"

            write_video_mp4(frames, video1_path, fps=8)
            write_video_mp4(frames, video2_path, fps=8)

            payload = build_temporal_metrics_payload(
                video1_path,
                video2_path,
                runtime_config={"temporal_metrics_mode": "placeholder"},
            )

            assert payload["temporal_metrics_runtime"] == "placeholder_tensor_video_metrics"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_quality_metrics_payload_fields_required() -> None:
    """功能：测试质量指标负载包含所需字段。

    Test that quality metrics payload contains required fields.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
            np.float32
        )
        frames = np.clip(frames, 0.0, 1.0)

        video1_path = tmpdir_path / "v1.mp4"
        video2_path = tmpdir_path / "v2.mp4"

        write_video_mp4(frames, video1_path, fps=8)
        write_video_mp4(frames, video2_path, fps=8)

        payload = build_quality_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={"quality_metrics_mode": "real_video_frame_metrics"},
        )

        required_fields = [
            "quality_metrics_runtime",
            "vae_reconstruction_psnr",
            "vae_reconstruction_ssim",
            "watermarked_video_psnr",
            "watermarked_video_ssim",
            "watermarked_video_lpips",
            "clip_similarity_score",
            "disabled_quality_metrics",
            "quality_failure_reason",
        ]
        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_temporal_metrics_payload_fields_required() -> None:
    """功能：测试时序指标负载包含所需字段。

    Test that temporal metrics payload contains required fields.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
            np.float32
        )
        frames = np.clip(frames, 0.0, 1.0)

        video1_path = tmpdir_path / "v1.mp4"
        video2_path = tmpdir_path / "v2.mp4"

        write_video_mp4(frames, video1_path, fps=8)
        write_video_mp4(frames, video2_path, fps=8)

        payload = build_temporal_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={"temporal_metrics_mode": "real_video_frame_metrics"},
        )

        required_fields = [
            "temporal_metrics_runtime",
            "temporal_consistency_score",
            "flicker_score",
            "motion_consistency_score",
            "disabled_temporal_metrics",
        ]
        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"

"""
文件用途：测试阶段 2 真实视频帧级时序指标。
File purpose: Test frame-based temporal metrics for stage-two real video runtime.
Module type: General module
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.integration

from main.analysis.real_video_temporal_metrics import build_real_video_temporal_metrics_payload
from main.video.video_io import write_video_mp4

# 检查 ffmpeg 是否可用
HAS_FFMPEG = shutil.which("ffmpeg") is not None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_temporal_metrics_static_videos() -> None:
    """功能：测试静止视频的时序指标。

    Test that static videos produce zero flicker scores.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 生成完全相同的帧序列（静止视频）
        static_frame = np.ones((256, 256, 3), dtype=np.float32) * 0.5
        static_frames = np.repeat(static_frame[np.newaxis, :, :, :], 8, axis=0)

        video1_path = tmpdir_path / "static1.mp4"
        video2_path = tmpdir_path / "static2.mp4"

        write_video_mp4(static_frames, video1_path, fps=8)
        write_video_mp4(static_frames, video2_path, fps=8)

        payload = build_real_video_temporal_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["temporal_metrics_runtime"] == "real_video_frame_metrics"
        assert payload["temporal_consistency_score"] is not None
        assert payload["flicker_score"] is not None
        # 完全相同的静止视频应该有零或接近零的闪烁分数
        assert payload["flicker_score"] < 0.01
        # 时序一致性分数应该接近 1.0
        assert payload["temporal_consistency_score"] > 0.99


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_temporal_metrics_moving_videos() -> None:
    """功能：测试运动视频的时序指标。

    Test that moving videos produce non-zero flicker scores.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 生成有运动的视频帧
        frames1 = []
        for t in range(8):
            frame = np.ones((256, 256, 3), dtype=np.float32) * 0.5
            # 添加随时间变化的运动
            frame[t * 30 : (t + 1) * 30, :, :] = 0.8
            frames1.append(frame)
        frames1 = np.stack(frames1, axis=0)

        frames2 = []
        for t in range(8):
            frame = np.ones((256, 256, 3), dtype=np.float32) * 0.5
            # 相似但略有不同的运动
            frame[t * 30 + 5 : (t + 1) * 30 + 5, :, :] = 0.7
            frames2.append(frame)
        frames2 = np.stack(frames2, axis=0)

        video1_path = tmpdir_path / "moving1.mp4"
        video2_path = tmpdir_path / "moving2.mp4"

        write_video_mp4(frames1, video1_path, fps=8)
        write_video_mp4(frames2, video2_path, fps=8)

        payload = build_real_video_temporal_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["temporal_metrics_runtime"] == "real_video_frame_metrics"
        assert payload["temporal_consistency_score"] is not None
        assert payload["flicker_score"] is not None
        # 运动方式不同的视频应该有非零的闪烁分数
        assert payload["flicker_score"] > 0.0


@pytest.mark.smoke
def test_real_video_temporal_metrics_insufficient_frames() -> None:
    """功能：测试帧数不足的错误处理。

    Test that insufficient frames are handled gracefully.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 创建只有 1 帧的视频
        frames = np.ones((1, 128, 128, 3), dtype=np.float32) * 0.5

        video1_path = tmpdir_path / "short1.mp4"
        video2_path = tmpdir_path / "short2.mp4"

        if HAS_FFMPEG:
            write_video_mp4(frames, video1_path, fps=8)
            write_video_mp4(frames, video2_path, fps=8)

            payload = build_real_video_temporal_metrics_payload(
                video1_path,
                video2_path,
                runtime_config={},
            )

            assert payload["temporal_metrics_runtime"] == "real_video_frame_metrics"
            assert payload["temporal_consistency_score"] is None
            assert payload["temporal_failure_reason"] is not None


@pytest.mark.smoke
def test_real_video_temporal_metrics_missing_videos() -> None:
    """功能：测试缺失视频文件的错误处理。

    Test that missing video files are handled gracefully.
    """
    payload = build_real_video_temporal_metrics_payload(
        Path("/nonexistent/video1.mp4"),
        Path("/nonexistent/video2.mp4"),
        runtime_config={},
    )

    assert payload["temporal_metrics_runtime"] == "real_video_frame_metrics"
    assert payload["temporal_consistency_score"] is None
    assert payload["temporal_failure_reason"] is not None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_temporal_metrics_scores_in_valid_range() -> None:
    """功能：测试时序指标分数在有效范围内。

    Test that temporal scores are in valid ranges.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames1 = np.random.RandomState(42).uniform(0.3, 0.7, size=(8, 128, 128, 3)).astype(
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

        payload = build_real_video_temporal_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["temporal_consistency_score"] is not None
        assert payload["flicker_score"] is not None
        # 时序一致性分数应该在 [0, 1] 范围内
        assert 0 <= payload["temporal_consistency_score"] <= 1
        # 闪烁分数应该非负
        assert payload["flicker_score"] >= 0


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not available")
@pytest.mark.smoke
def test_real_video_temporal_metrics_different_frame_counts() -> None:
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

        payload = build_real_video_temporal_metrics_payload(
            video1_path,
            video2_path,
            runtime_config={},
        )

        assert payload["temporal_metrics_runtime"] == "real_video_frame_metrics"
        # 应该使用最小帧数进行对齐，不应该失败
        assert payload["temporal_consistency_score"] is not None

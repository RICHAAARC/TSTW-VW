"""
文件用途：验证真实视频压缩攻击功能。
File purpose: Validate real video compression attack functionality.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

pytestmark = pytest.mark.quick

from main.attacks.compression import H264CompressionAttack, H265CompressionAttack
from main.video.video_io import write_video_mp4


@pytest.fixture
def tiny_video_frames() -> np.ndarray:
    """生成 tiny test video frames (4 frames, 256x256)。"""
    return np.random.randint(0, 256, (4, 256, 256, 3), dtype=np.uint8).astype(np.float32) / 255.0


@pytest.fixture
def test_video_file(tiny_video_frames: np.ndarray, tmp_path: Path) -> Path:
    """创建测试视频文件。"""
    video_path = tmp_path / "test_video.mp4"
    try:
        write_video_mp4(tiny_video_frames, video_path, fps=8, crf=18)
        if video_path.exists():
            return video_path
    except Exception:
        pass
    # Fallback: 如果无法创建 mp4，返回路径（测试会 skip）
    return video_path


def test_h264_compression_attack_initialization() -> None:
    """验证 H264 压缩攻击初始化。"""
    attack_params = {"crf": 28, "preset": "medium"}
    attack = H264CompressionAttack(attack_params)
    assert attack.attack_name == "h264_compression"
    assert attack.attack_params["crf"] == 28


def test_h265_compression_attack_initialization() -> None:
    """验证 H265 压缩攻击初始化。"""
    attack_params = {"crf": 30, "preset": "fast"}
    attack = H265CompressionAttack(attack_params)
    assert attack.attack_name == "h265_compression"
    assert attack.attack_params["crf"] == 30


def test_h264_get_ffmpeg_codec() -> None:
    """验证 H264 codec 名称。"""
    attack = H264CompressionAttack({})
    assert attack.get_ffmpeg_codec() == "libx264"


def test_h265_get_ffmpeg_codec() -> None:
    """验证 H265 codec 名称。"""
    attack = H265CompressionAttack({})
    assert attack.get_ffmpeg_codec() == "libx265"


def test_h264_apply_video_with_missing_input() -> None:
    """验证缺失输入文件时的错误处理。"""
    attack = H264CompressionAttack({})
    with pytest.raises(FileNotFoundError):
        attack.apply_video(
            "/nonexistent/input.mp4",
            "/tmp/output.mp4",
            fps=8,
        )


def test_compression_attack_invalid_name() -> None:
    """验证无效 attack name 的处理。"""
    with pytest.raises(ValueError, match="unsupported compression attack"):
        from main.attacks.compression import CompressionAttackBase
        CompressionAttackBase("invalid_attack", {})

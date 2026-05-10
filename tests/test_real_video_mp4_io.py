"""
文件用途：验证真实 mp4 读写与帧标准化工具。
File purpose: Validate real mp4 IO and frame standardization helpers.
Module type: General module
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from main.video.frame_preprocess import standardize_video_frames
from main.video.video_io import probe_video_metadata, read_video_frames, write_video_mp4


@pytest.mark.unit
def test_real_video_mp4_io_roundtrip_and_probe(tmp_path: Path) -> None:
    """Validate mp4 write/read/probe workflow with tiny synthetic frames.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("imageio_ffmpeg is unavailable")

    source_frames = np.random.default_rng(20260510).random((6, 12, 16, 3), dtype=np.float32)
    output_path = tmp_path / "tiny_source.mp4"
    metadata = write_video_mp4(source_frames, output_path, fps=8, codec="libx264", crf=20)

    assert output_path.exists()
    assert metadata["container"] == "mp4"
    loaded = read_video_frames(output_path)
    probed = probe_video_metadata(output_path)

    assert loaded.frames.ndim == 4
    assert loaded.frames.shape[-1] == 3
    assert loaded.frames.shape[0] >= 1
    assert loaded.fps >= 1
    assert probed["frame_count"] == loaded.frames.shape[0]


@pytest.mark.unit
def test_real_video_mp4_io_preserves_8x8_resolution(tmp_path: Path) -> None:
    """Validate mp4 writer keeps non-16-multiple resolution unchanged.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("imageio_ffmpeg is unavailable")

    source_frames = np.random.default_rng(20260510).random((4, 8, 8, 3), dtype=np.float32)
    output_path = tmp_path / "tiny_8x8_source.mp4"
    write_video_mp4(source_frames, output_path, fps=8, codec="libx264", crf=20)

    probed = probe_video_metadata(output_path)
    assert probed["height"] == 8
    assert probed["width"] == 8


@pytest.mark.unit
def test_standardize_video_frames_outputs_fixed_shape(tmp_path: Path) -> None:
    """Validate deterministic frame standardization outputs fixed shape.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    del tmp_path
    source_frames = np.random.default_rng(42).random((5, 15, 21, 3), dtype=np.float32)
    standardized = standardize_video_frames(
        source_frames,
        target_frame_count=8,
        target_fps=8,
        target_resolution=(16, 16),
        frame_sampling_policy="deterministic_uniform",
    )
    assert standardized.shape == (8, 16, 16, 3)
    assert standardized.dtype == np.float32
    assert float(standardized.min()) >= 0.0
    assert float(standardized.max()) <= 1.0

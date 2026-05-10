"""
文件用途：提供真实视频帧标准化与重采样工具。
File purpose: Provide frame standardization and resampling helpers for real-video runtime.
Module type: General module
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


def _resize_frames_nearest(frames: np.ndarray, target_height: int, target_width: int) -> np.ndarray:
    """功能：使用确定性最近邻策略重采样空间分辨率。

    Resize frames with a deterministic nearest-neighbor policy.

    Args:
        frames: Input frame tensor `[F, H, W, 3]`.
        target_height: Target height.
        target_width: Target width.

    Returns:
        Resized frame tensor.
    """
    source_height = frames.shape[1]
    source_width = frames.shape[2]
    row_indices = np.linspace(0, source_height - 1, num=target_height).round().astype(np.int32)
    col_indices = np.linspace(0, source_width - 1, num=target_width).round().astype(np.int32)
    return frames[:, row_indices][:, :, col_indices]


def standardize_video_frames(
    frames: np.ndarray,
    *,
    target_frame_count: int,
    target_fps: int,
    target_resolution: Tuple[int, int],
    frame_sampling_policy: str,
) -> np.ndarray:
    """功能：将视频帧标准化为受治理协议输入。

    Standardize video frames to governed runtime requirements.

    Args:
        frames: Input frame tensor `[F, H, W, 3]`.
        target_frame_count: Target frame count.
        target_fps: Target frame rate placeholder for runtime semantics.
        target_resolution: Target `(height, width)`.
        frame_sampling_policy: Sampling policy name.

    Returns:
        Standardized frame tensor `[target_frame_count, H, W, 3]`, float32 in `[0, 1]`.

    Raises:
        ValueError: Raised when inputs are invalid.
    """
    if not isinstance(frames, np.ndarray):
        raise TypeError("frames must be a numpy ndarray")
    if frames.ndim != 4 or frames.shape[-1] != 3:
        raise ValueError("frames must have shape [F, H, W, 3]")
    if frames.shape[0] < 1:
        raise ValueError("frames must contain at least one frame")
    if frame_sampling_policy != "deterministic_uniform":
        raise ValueError("frame_sampling_policy must be deterministic_uniform")
    if not isinstance(target_frame_count, int) or target_frame_count < 1:
        raise ValueError("target_frame_count must be a positive integer")
    if not isinstance(target_fps, int) or target_fps < 1:
        raise ValueError("target_fps must be a positive integer")
    target_height, target_width = target_resolution
    if not isinstance(target_height, int) or not isinstance(target_width, int):
        raise ValueError("target_resolution must contain integer values")
    if target_height < 1 or target_width < 1:
        raise ValueError("target_resolution must be positive")

    clipped_frames = np.clip(frames.astype(np.float32), 0.0, 1.0)
    source_frame_count = clipped_frames.shape[0]
    sampled_indices = np.linspace(0, source_frame_count - 1, num=target_frame_count).round().astype(np.int32)
    sampled_frames = clipped_frames[sampled_indices]
    resized_frames = _resize_frames_nearest(sampled_frames, target_height, target_width)
    return resized_frames.astype(np.float32)

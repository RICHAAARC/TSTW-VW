"""
文件用途：提供视频张量与 latent 张量的基础编解码辅助函数。
File purpose: Provide helper conversions between video tensors and latent tensors.
Module type: General module
"""

from __future__ import annotations

from typing import Tuple

import numpy as np


def ensure_video_batch(video_batch: np.ndarray) -> np.ndarray:
    """功能：校验并标准化视频批次输入。

    Validate and normalize a video batch tensor.

    Args:
        video_batch: Candidate video tensor in `[F, H, W, 3]`.

    Returns:
        A float32 tensor in `[F, H, W, 3]` and range `[0, 1]`.
    """
    if not isinstance(video_batch, np.ndarray):
        raise TypeError("video_batch must be a numpy ndarray")
    if video_batch.ndim != 4 or video_batch.shape[-1] != 3:
        raise ValueError("video_batch must have shape [F, H, W, 3]")
    if video_batch.shape[0] < 1:
        raise ValueError("video_batch must contain at least one frame")
    return np.clip(video_batch.astype(np.float32), 0.0, 1.0)


def ensure_latent_batch(latent_batch: np.ndarray) -> np.ndarray:
    """功能：校验 latent 批次输入。

    Validate a latent batch tensor.

    Args:
        latent_batch: Candidate latent tensor in `[F, C, H_lat, W_lat]`.

    Returns:
        A float32 latent tensor.
    """
    if not isinstance(latent_batch, np.ndarray):
        raise TypeError("latent_batch must be a numpy ndarray")
    if latent_batch.ndim != 4:
        raise ValueError("latent_batch must have shape [F, C, H_lat, W_lat]")
    if latent_batch.shape[0] < 1 or latent_batch.shape[1] < 1:
        raise ValueError("latent_batch must contain positive frame and channel dimensions")
    return latent_batch.astype(np.float32)


def rgb_video_to_nchw_minus1_1(video_batch: np.ndarray) -> np.ndarray:
    """功能：将 RGB 视频从 `[0, 1]` 映射到 NCHW `[-1, 1]`。

    Convert RGB video from `[0, 1]` to NCHW `[-1, 1]`.

    Args:
        video_batch: Video tensor in `[F, H, W, 3]`.

    Returns:
        Converted tensor in `[F, 3, H, W]`.
    """
    normalized = ensure_video_batch(video_batch)
    nchw = np.transpose(normalized, (0, 3, 1, 2))
    return (nchw * 2.0 - 1.0).astype(np.float32)


def nchw_minus1_1_to_rgb_video(tensor_nchw: np.ndarray) -> np.ndarray:
    """功能：将 NCHW `[-1, 1]` 映射回 RGB `[0, 1]`。

    Convert NCHW `[-1, 1]` back to RGB `[0, 1]`.

    Args:
        tensor_nchw: Tensor in `[F, 3, H, W]`.

    Returns:
        Converted tensor in `[F, H, W, 3]`.
    """
    if not isinstance(tensor_nchw, np.ndarray):
        raise TypeError("tensor_nchw must be a numpy ndarray")
    if tensor_nchw.ndim != 4 or tensor_nchw.shape[1] != 3:
        raise ValueError("tensor_nchw must have shape [F, 3, H, W]")
    restored = np.clip((tensor_nchw.astype(np.float32) + 1.0) / 2.0, 0.0, 1.0)
    return np.transpose(restored, (0, 2, 3, 1)).astype(np.float32)


def downsample_nchw_mean(tensor_nchw: np.ndarray, factor: int) -> np.ndarray:
    """功能：使用均值池化策略对 NCHW 做整数倍降采样。

    Downsample NCHW by integer factor with mean pooling.

    Args:
        tensor_nchw: Tensor in `[F, C, H, W]`.
        factor: Integer downsample factor.

    Returns:
        Downsampled tensor.
    """
    if not isinstance(tensor_nchw, np.ndarray):
        raise TypeError("tensor_nchw must be a numpy ndarray")
    if tensor_nchw.ndim != 4:
        raise ValueError("tensor_nchw must have shape [F, C, H, W]")
    if not isinstance(factor, int) or factor < 1:
        raise ValueError("factor must be a positive integer")
    if factor == 1:
        return tensor_nchw.astype(np.float32)

    frames, channels, height, width = tensor_nchw.shape
    target_height = max(1, height // factor)
    target_width = max(1, width // factor)
    row_bins = np.linspace(0, height, num=target_height + 1).round().astype(np.int32)
    col_bins = np.linspace(0, width, num=target_width + 1).round().astype(np.int32)
    downsampled = np.zeros((frames, channels, target_height, target_width), dtype=np.float32)
    for row_index in range(target_height):
        row_start = row_bins[row_index]
        row_end = max(row_start + 1, row_bins[row_index + 1])
        for col_index in range(target_width):
            col_start = col_bins[col_index]
            col_end = max(col_start + 1, col_bins[col_index + 1])
            patch = tensor_nchw[:, :, row_start:row_end, col_start:col_end]
            downsampled[:, :, row_index, col_index] = patch.mean(axis=(2, 3), dtype=np.float32)
    return downsampled


def upsample_nchw_nearest(
    tensor_nchw: np.ndarray,
    target_resolution: Tuple[int, int],
) -> np.ndarray:
    """功能：使用最近邻策略上采样 NCHW 张量。

    Upsample NCHW tensor with nearest-neighbor interpolation.

    Args:
        tensor_nchw: Tensor in `[F, C, H, W]`.
        target_resolution: Target `(height, width)`.

    Returns:
        Upsampled tensor in `[F, C, target_height, target_width]`.
    """
    if not isinstance(tensor_nchw, np.ndarray):
        raise TypeError("tensor_nchw must be a numpy ndarray")
    if tensor_nchw.ndim != 4:
        raise ValueError("tensor_nchw must have shape [F, C, H, W]")
    target_height, target_width = target_resolution
    if not isinstance(target_height, int) or not isinstance(target_width, int):
        raise ValueError("target_resolution must contain integer values")
    if target_height < 1 or target_width < 1:
        raise ValueError("target_resolution must be positive")

    source_height = tensor_nchw.shape[2]
    source_width = tensor_nchw.shape[3]
    row_indices = np.linspace(0, source_height - 1, num=target_height).round().astype(np.int32)
    col_indices = np.linspace(0, source_width - 1, num=target_width).round().astype(np.int32)
    return tensor_nchw[:, :, row_indices][:, :, :, col_indices].astype(np.float32)

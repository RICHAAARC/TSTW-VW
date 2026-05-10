"""
文件用途：计算阶段 2 视频质量指标（占位或真实实现）。
File purpose: Compute video-quality metrics for stage-two (placeholder or real video runtime).
Module type: General module
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from main.video.video_artifact import load_video_artifact


def build_quality_metrics_payload(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
    *,
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """功能：根据 runtime_config 选择真实或占位质量指标实现。

    Build the quality-metrics payload using real or placeholder implementation.

    Args:
        reference_video_path: Reference video artifact path.
        comparison_video_path: Comparison video artifact path.
        runtime_config: Runtime configuration with optional mode selector.

    Returns:
        A quality-metrics payload compatible with stage-two records.
    """
    runtime_config = runtime_config or {}

    # 检查是否使用真实实现
    quality_metrics_mode = runtime_config.get("quality_metrics_mode", "placeholder")
    if quality_metrics_mode == "real_video_frame_metrics":
        try:
            from main.analysis.real_video_quality_metrics import (
                build_real_video_quality_metrics_payload,
            )

            return build_real_video_quality_metrics_payload(
                reference_video_path,
                comparison_video_path,
                runtime_config=runtime_config,
            )
        except Exception:
            # 若真实实现失败，降级到占位实现
            pass

    # 使用占位实现
    return _build_placeholder_quality_metrics_payload(
        reference_video_path,
        comparison_video_path,
    )


def _build_placeholder_quality_metrics_payload(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
) -> dict[str, Any]:
    """功能：占位质量指标实现。

    Build the placeholder quality-metrics payload from video artifacts.

    Args:
        reference_video_path: Reference video artifact path.
        comparison_video_path: Comparison video artifact path.

    Returns:
        A quality-metrics payload compatible with stage-two records.
    """
    reference_values, comparison_values = _collect_comparable_values(
        reference_video_path,
        comparison_video_path,
    )
    if not reference_values:
        return {
            "quality_metrics_runtime": "placeholder_tensor_video_metrics",
            "vae_reconstruction_psnr": None,
            "vae_reconstruction_ssim": None,
            "watermarked_video_psnr": None,
            "watermarked_video_ssim": None,
            "watermarked_video_lpips": None,
            "clip_similarity_score": None,
            "disabled_quality_metrics": [
                "watermarked_video_lpips",
                "clip_similarity",
            ],
            "quality_failure_reason": "no_comparable_video_samples",
        }

    squared_error_sum = 0.0
    absolute_error_sum = 0.0
    for reference_value, comparison_value in zip(reference_values, comparison_values):
        delta = float(reference_value) - float(comparison_value)
        squared_error_sum += delta * delta
        absolute_error_sum += abs(delta)
    mse = squared_error_sum / len(reference_values)
    mae = absolute_error_sum / len(reference_values)
    psnr = 99.0 if mse <= 1e-12 else 20.0 * math.log10(1.0 / math.sqrt(mse))
    ssim_proxy = max(0.0, min(1.0, 1.0 - mae))
    quality_failure_reason = None
    if psnr < 18.0:
        quality_failure_reason = "psnr_below_placeholder_threshold"
    return {
        "quality_metrics_runtime": "placeholder_tensor_video_metrics",
        "vae_reconstruction_psnr": round(psnr, 6),
        "vae_reconstruction_ssim": round(ssim_proxy, 6),
        "watermarked_video_psnr": round(psnr, 6),
        "watermarked_video_ssim": round(ssim_proxy, 6),
        "watermarked_video_lpips": None,
        "clip_similarity_score": None,
        "disabled_quality_metrics": [
            "watermarked_video_lpips",
            "clip_similarity",
        ],
        "quality_failure_reason": quality_failure_reason,
    }


def _collect_comparable_values(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
) -> tuple[list[float], list[float]]:
    """加载视频数据并提取可比较的值。
    
    Load video data and extract comparable values.
    Supports both .npy artifacts and .mp4 files.
    """
    ref_path = Path(reference_video_path)
    cmp_path = Path(comparison_video_path)
    
    # 根据文件类型加载视频数据
    if ref_path.suffix.lower() == ".mp4":
        from main.video.video_io import read_video_frames
        try:
            ref_video = read_video_frames(ref_path)
            reference_artifact = ref_video.frames  # [F, H, W, 3]
        except Exception:
            return [], []
    else:
        # 尝试作为 npy artifact 加载
        try:
            reference_artifact = load_video_artifact(ref_path)
        except Exception:
            return [], []
    
    if cmp_path.suffix.lower() == ".mp4":
        from main.video.video_io import read_video_frames
        try:
            cmp_video = read_video_frames(cmp_path)
            comparison_artifact = cmp_video.frames  # [F, H, W, 3]
        except Exception:
            return [], []
    else:
        try:
            comparison_artifact = load_video_artifact(cmp_path)
        except Exception:
            return [], []
    
    reference_shape = tuple(int(dimension) for dimension in reference_artifact.shape)
    comparison_shape = tuple(int(dimension) for dimension in comparison_artifact.shape)
    if len(reference_shape) != 4 or len(comparison_shape) != 4:
        raise ValueError("video artifacts must use 4D tensors")

    comparable_frames = min(reference_shape[0], comparison_shape[0])
    comparable_channels = min(reference_shape[1], comparison_shape[1])
    comparable_height = min(reference_shape[2], comparison_shape[2])
    comparable_width = min(reference_shape[3], comparison_shape[3])
    if min(comparable_frames, comparable_channels, comparable_height, comparable_width) < 1:
        return [], []

    reference_values: list[float] = []
    comparison_values: list[float] = []
    reference_index = 0
    comparison_index = 0
    reference_frame_size = reference_shape[1] * reference_shape[2] * reference_shape[3]
    comparison_frame_size = comparison_shape[1] * comparison_shape[2] * comparison_shape[3]
    reference_channel_size = reference_shape[2] * reference_shape[3]
    comparison_channel_size = comparison_shape[2] * comparison_shape[3]
    for frame_index in range(comparable_frames):
        for channel_index in range(comparable_channels):
            for row_index in range(comparable_height):
                for column_index in range(comparable_width):
                    reference_index = (
                        frame_index * reference_frame_size
                        + channel_index * reference_channel_size
                        + row_index * reference_shape[3]
                        + column_index
                    )
                    comparison_index = (
                        frame_index * comparison_frame_size
                        + channel_index * comparison_channel_size
                        + row_index * comparison_shape[3]
                        + column_index
                    )
                    # 支持 numpy 数组和 artifact 对象
                    if isinstance(reference_artifact, np.ndarray):
                        ref_value = float(reference_artifact.flat[reference_index])
                    else:
                        ref_value = float(reference_artifact.values[reference_index])
                    
                    if isinstance(comparison_artifact, np.ndarray):
                        cmp_value = float(comparison_artifact.flat[comparison_index])
                    else:
                        cmp_value = float(comparison_artifact.values[comparison_index])
                    
                    reference_values.append(ref_value)
                    comparison_values.append(cmp_value)
    return reference_values, comparison_values
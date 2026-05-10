"""
文件用途：计算阶段 2 占位视频质量指标。
File purpose: Compute placeholder video-quality metrics for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from main.video.video_artifact import load_video_artifact


def build_quality_metrics_payload(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
) -> dict[str, Any]:
    """功能：从两个占位视频 artifact 构建质量指标负载。

    Build the stage-two quality-metrics payload from two placeholder video artifacts.

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
    reference_artifact = load_video_artifact(reference_video_path)
    comparison_artifact = load_video_artifact(comparison_video_path)
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
                    reference_values.append(float(reference_artifact.values[reference_index]))
                    comparison_values.append(float(comparison_artifact.values[comparison_index]))
    return reference_values, comparison_values
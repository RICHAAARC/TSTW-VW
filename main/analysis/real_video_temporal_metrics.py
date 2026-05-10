"""
文件用途：计算阶段 2 真实视频帧级时序一致性指标。
File purpose: Compute frame-based temporal consistency metrics for stage-two real video runtime.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from main.video.video_io import read_video_frames


def build_real_video_temporal_metrics_payload(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
    *,
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """功能：从两个真实视频文件构建帧级时序一致性指标。

    Build frame-based temporal-metrics payload from two real video files.

    Args:
        reference_video_path: Reference video path (e.g., decoded watermarked video).
        comparison_video_path: Comparison video path (e.g., attacked video).
        runtime_config: Runtime configuration (unused for temporal metrics).

    Returns:
        A temporal-metrics payload with temporal consistency and flicker scores.

    Raises:
        FileNotFoundError: Raised when video files are missing.
        ValueError: Raised when frame counts are too small.
    """
    runtime_config = runtime_config or {}

    try:
        reference_video = read_video_frames(reference_video_path)
        comparison_video = read_video_frames(comparison_video_path)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": ["motion_consistency"],
            "temporal_failure_reason": f"video_io_error: {str(exc)}",
        }

    ref_frames = reference_video.frames
    cmp_frames = comparison_video.frames

    if ref_frames.ndim != 4 or cmp_frames.ndim != 4:
        return {
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": ["motion_consistency"],
            "temporal_failure_reason": "invalid_frame_tensor_shape",
        }

    # 对齐帧数并检查最小帧数要求
    frame_count = min(ref_frames.shape[0], cmp_frames.shape[0])
    if frame_count < 2:
        return {
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": ["motion_consistency"],
            "temporal_failure_reason": "insufficient_frames_for_temporal_metrics",
        }

    # 计算帧间差异
    ref_frame_diffs = _compute_frame_differences(ref_frames[:frame_count])
    cmp_frame_diffs = _compute_frame_differences(cmp_frames[:frame_count])

    if not ref_frame_diffs or not cmp_frame_diffs:
        return {
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": ["motion_consistency"],
            "temporal_failure_reason": "frame_difference_computation_failed",
        }

    # 计算闪烁分数（flicker score）
    # flicker_score = mean(|ref_diff - cmp_diff|) 按空间意义衡量帧间运动的变化
    flicker_diffs = np.abs(
        np.array(ref_frame_diffs, dtype=np.float32)
        - np.array(cmp_frame_diffs, dtype=np.float32)
    )
    flicker_score = float(np.mean(flicker_diffs))

    # 计算时序一致性分数
    # temporal_consistency_score = max(0, 1 - normalized_flicker_score)
    normalized_flicker = min(1.0, flicker_score)
    temporal_consistency_score = max(0.0, 1.0 - normalized_flicker)

    return {
        "temporal_metrics_runtime": "real_video_frame_metrics",
        "temporal_consistency_score": round(temporal_consistency_score, 6),
        "flicker_score": round(flicker_score, 6),
        "motion_consistency_score": None,
        "disabled_temporal_metrics": ["motion_consistency"],
        "temporal_failure_reason": None,
    }


def _compute_frame_differences(frames: np.ndarray) -> list[float]:
    """功能：计算连续帧间的平均绝对差异。

    Compute mean absolute difference between consecutive frames.

    Args:
        frames: Video frames in `[F, H, W, 3]`, float32, range [0, 1].

    Returns:
        List of mean absolute differences between consecutive frames.
    """
    if frames.shape[0] < 2:
        return []

    frame_count = frames.shape[0]
    diffs: list[float] = []

    for frame_idx in range(frame_count - 1):
        current_frame = np.clip(frames[frame_idx], 0.0, 1.0)
        next_frame = np.clip(frames[frame_idx + 1], 0.0, 1.0)

        # 按像素计算绝对差异的平均值
        absolute_diff = np.abs(next_frame.astype(np.float32) - current_frame.astype(np.float32))
        mean_diff = float(np.mean(absolute_diff))
        diffs.append(mean_diff)

    return diffs

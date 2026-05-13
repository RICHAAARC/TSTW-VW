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
    temporal_config = runtime_config.get("temporal_metrics", {})
    enable_motion_consistency = bool(temporal_config.get("enable_motion_consistency"))
    disabled_temporal_metrics = []
    motion_consistency_failure_reason = None
    if not enable_motion_consistency:
        disabled_temporal_metrics.append("motion_consistency")
        motion_consistency_failure_reason = "motion_consistency_disabled_by_config"

    try:
        reference_video = read_video_frames(reference_video_path)
        comparison_video = read_video_frames(comparison_video_path)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": disabled_temporal_metrics,
            "temporal_failure_reason": f"video_io_error: {str(exc)}",
            "motion_consistency_failure_reason": motion_consistency_failure_reason,
        }

    ref_frames = reference_video.frames
    cmp_frames = comparison_video.frames

    if ref_frames.ndim != 4 or cmp_frames.ndim != 4:
        return {
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": disabled_temporal_metrics,
            "temporal_failure_reason": "invalid_frame_tensor_shape",
            "motion_consistency_failure_reason": motion_consistency_failure_reason,
        }

    # 对齐帧数并检查最小帧数要求
    frame_count = min(ref_frames.shape[0], cmp_frames.shape[0])
    if frame_count < 2:
        return {
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": disabled_temporal_metrics,
            "temporal_failure_reason": "insufficient_frames_for_temporal_metrics",
            "motion_consistency_failure_reason": motion_consistency_failure_reason,
        }

    # 计算帧间差异
    ref_frame_diff_tensors = _compute_frame_difference_tensors(ref_frames[:frame_count])
    cmp_frame_diff_tensors = _compute_frame_difference_tensors(cmp_frames[:frame_count])
    ref_frame_diffs = _reduce_frame_differences(ref_frame_diff_tensors)
    cmp_frame_diffs = _reduce_frame_differences(cmp_frame_diff_tensors)

    if not ref_frame_diffs or not cmp_frame_diffs:
        return {
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": disabled_temporal_metrics,
            "temporal_failure_reason": "frame_difference_computation_failed",
            "motion_consistency_failure_reason": motion_consistency_failure_reason,
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

    motion_consistency_score = None
    if enable_motion_consistency:
        motion_consistency_score = _compute_motion_consistency_score(
            ref_frame_diff_tensors,
            cmp_frame_diff_tensors,
        )
        if motion_consistency_score is None:
            motion_consistency_failure_reason = "motion_consistency_computation_failed"

    return {
        "temporal_metrics_runtime": "real_video_frame_metrics",
        "temporal_consistency_score": round(temporal_consistency_score, 6),
        "flicker_score": round(flicker_score, 6),
        "motion_consistency_score": (
            round(motion_consistency_score, 6)
            if motion_consistency_score is not None
            else None
        ),
        "disabled_temporal_metrics": disabled_temporal_metrics,
        "temporal_failure_reason": None,
        "motion_consistency_failure_reason": motion_consistency_failure_reason,
    }


def _compute_frame_difference_tensors(frames: np.ndarray) -> list[np.ndarray]:
    """功能：计算连续帧间的绝对差异张量。

    Compute absolute difference tensors between consecutive frames.

    Args:
        frames: Video frames in `[F, H, W, 3]`, float32, range [0, 1].

    Returns:
        List of absolute difference tensors between consecutive frames.
    """
    if frames.shape[0] < 2:
        return []

    frame_count = frames.shape[0]
    diffs: list[np.ndarray] = []

    for frame_idx in range(frame_count - 1):
        current_frame = np.clip(frames[frame_idx], 0.0, 1.0)
        next_frame = np.clip(frames[frame_idx + 1], 0.0, 1.0)

        absolute_diff = np.abs(next_frame.astype(np.float32) - current_frame.astype(np.float32))
        diffs.append(absolute_diff)

    return diffs


def _reduce_frame_differences(frame_diff_tensors: list[np.ndarray]) -> list[float]:
    """功能：将帧差异张量规约为逐帧平均值。

    Reduce frame-difference tensors to per-frame scalar means.

    Args:
        frame_diff_tensors: Absolute frame-difference tensors.

    Returns:
        Mean absolute difference for each temporal transition.
    """
    return [float(np.mean(diff_tensor)) for diff_tensor in frame_diff_tensors]


def _compute_motion_consistency_score(
    reference_frame_diffs: list[np.ndarray],
    comparison_frame_diffs: list[np.ndarray],
) -> float | None:
    """功能：计算 motion consistency 的轻量代理分数。

    Compute a lightweight proxy for motion-consistency alignment.

    Args:
        reference_frame_diffs: Reference absolute frame-difference tensors.
        comparison_frame_diffs: Comparison absolute frame-difference tensors.

    Returns:
        A score in `[0, 1]`, where larger indicates more similar motion energy.
    """
    aligned_pairs = list(zip(reference_frame_diffs, comparison_frame_diffs))
    if not aligned_pairs:
        return None

    normalized_errors: list[float] = []
    for reference_diff, comparison_diff in aligned_pairs:
        reference_motion = float(np.mean(reference_diff))
        comparison_motion = float(np.mean(comparison_diff))
        motion_scale = max(reference_motion, comparison_motion, 1e-6)
        normalized_errors.append(
            min(1.0, abs(reference_motion - comparison_motion) / motion_scale)
        )

    return max(0.0, 1.0 - float(np.mean(normalized_errors)))

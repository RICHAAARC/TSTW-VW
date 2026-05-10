"""
文件用途：计算阶段 2 时序一致性指标（占位或真实实现）。
File purpose: Compute temporal-consistency metrics for stage-two (placeholder or real video runtime).
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from main.video.video_artifact import load_video_artifact


def build_temporal_metrics_payload(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
    *,
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """功能：根据 runtime_config 选择真实或占位时序指标实现。

    Build the temporal-metrics payload using real or placeholder implementation.

    Args:
        reference_video_path: Reference video artifact path.
        comparison_video_path: Comparison video artifact path.
        runtime_config: Runtime configuration with optional mode selector.

    Returns:
        A temporal-metrics payload compatible with stage-two records.
    """
    runtime_config = runtime_config or {}

    # 检查是否使用真实实现
    temporal_metrics_mode = runtime_config.get("temporal_metrics_mode", "placeholder")
    if temporal_metrics_mode == "real_video_frame_metrics":
        try:
            from main.analysis.real_video_temporal_metrics import (
                build_real_video_temporal_metrics_payload,
            )

            return build_real_video_temporal_metrics_payload(
                reference_video_path,
                comparison_video_path,
                runtime_config=runtime_config,
            )
        except Exception:
            # 若真实实现失败，降级到占位实现
            pass

    # 使用占位实现
    return _build_placeholder_temporal_metrics_payload(
        reference_video_path,
        comparison_video_path,
    )


def _build_placeholder_temporal_metrics_payload(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
) -> dict[str, Any]:
    """功能：占位时序指标实现。

    Build the placeholder temporal-metrics payload from video artifacts.

    Args:
        reference_video_path: Reference video artifact path.
        comparison_video_path: Comparison video artifact path.

    Returns:
        A temporal-metrics payload compatible with stage-two records.
    """
    ref_path = Path(reference_video_path)
    cmp_path = Path(comparison_video_path)

    # 加载参考视频
    if ref_path.suffix.lower() == ".mp4":
        from main.video.video_io import read_video_frames
        try:
            ref_video = read_video_frames(ref_path)
            reference_artifact = ref_video.frames
        except Exception:
            return {
                "temporal_metrics_runtime": "placeholder_tensor_video_metrics",
                "temporal_consistency_score": None,
                "flicker_score": None,
                "motion_consistency_score": None,
                "disabled_temporal_metrics": ["motion_consistency"],
            }
    else:
        try:
            reference_artifact = load_video_artifact(ref_path)
        except Exception:
            return {
                "temporal_metrics_runtime": "placeholder_tensor_video_metrics",
                "temporal_consistency_score": None,
                "flicker_score": None,
                "motion_consistency_score": None,
                "disabled_temporal_metrics": ["motion_consistency"],
            }

    # 加载比较视频
    if cmp_path.suffix.lower() == ".mp4":
        from main.video.video_io import read_video_frames
        try:
            cmp_video = read_video_frames(cmp_path)
            comparison_artifact = cmp_video.frames
        except Exception:
            return {
                "temporal_metrics_runtime": "placeholder_tensor_video_metrics",
                "temporal_consistency_score": None,
                "flicker_score": None,
                "motion_consistency_score": None,
                "disabled_temporal_metrics": ["motion_consistency"],
            }
    else:
        try:
            comparison_artifact = load_video_artifact(cmp_path)
        except Exception:
            return {
                "temporal_metrics_runtime": "placeholder_tensor_video_metrics",
                "temporal_consistency_score": None,
                "flicker_score": None,
                "motion_consistency_score": None,
                "disabled_temporal_metrics": ["motion_consistency"],
            }

    comparable_frames = min(reference_artifact.shape[0], comparison_artifact.shape[0])
    if comparable_frames < 2:
        return {
            "temporal_metrics_runtime": "placeholder_tensor_video_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": ["motion_consistency"],
        }

    reference_diffs = _frame_difference_means(reference_artifact, comparable_frames)
    comparison_diffs = _frame_difference_means(comparison_artifact, comparable_frames)
    if not reference_diffs:
        return {
            "temporal_metrics_runtime": "placeholder_tensor_video_metrics",
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": ["motion_consistency"],
        }

    flicker_score = sum(
        abs(reference_diff - comparison_diff)
        for reference_diff, comparison_diff in zip(reference_diffs, comparison_diffs)
    ) / len(reference_diffs)
    temporal_consistency_score = max(0.0, 1.0 - flicker_score)
    return {
        "temporal_metrics_runtime": "placeholder_tensor_video_metrics",
        "temporal_consistency_score": round(temporal_consistency_score, 6),
        "flicker_score": round(flicker_score, 6),
        "motion_consistency_score": None,
        "disabled_temporal_metrics": ["motion_consistency"],
    }


def _frame_difference_means(video_artifact: Any, comparable_frames: int) -> list[float]:
    """计算连续帧间的平均绝对差异。
    
    Compute mean absolute difference between consecutive frames.
    Supports both numpy arrays and artifact objects.
    """
    frame_count, channels, height, width = video_artifact.shape
    if comparable_frames > frame_count:
        comparable_frames = frame_count
    spatial_size = channels * height * width

    # 支持 numpy 数组和 artifact 对象
    if isinstance(video_artifact, np.ndarray):
        frame_values = video_artifact.flatten()
    else:
        frame_values = video_artifact.values

    diffs: list[float] = []
    for frame_index in range(comparable_frames - 1):
        current_offset = frame_index * spatial_size
        next_offset = (frame_index + 1) * spatial_size
        absolute_delta_sum = 0.0
        for value_index in range(spatial_size):
            absolute_delta_sum += abs(
                float(frame_values[next_offset + value_index])
                - float(frame_values[current_offset + value_index])
            )
        diffs.append(absolute_delta_sum / spatial_size)
    return diffs
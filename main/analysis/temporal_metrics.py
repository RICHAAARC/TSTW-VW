"""
文件用途：计算阶段 2 占位时序一致性指标。
File purpose: Compute placeholder temporal-consistency metrics for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from main.video.video_artifact import load_video_artifact


def build_temporal_metrics_payload(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
) -> dict[str, Any]:
    """功能：从两个占位视频 artifact 构建时序一致性指标。

    Build the stage-two temporal-metrics payload from two placeholder video artifacts.

    Args:
        reference_video_path: Reference video artifact path.
        comparison_video_path: Comparison video artifact path.

    Returns:
        A temporal-metrics payload compatible with stage-two records.
    """
    reference_artifact = load_video_artifact(reference_video_path)
    comparison_artifact = load_video_artifact(comparison_video_path)
    comparable_frames = min(reference_artifact.shape[0], comparison_artifact.shape[0])
    if comparable_frames < 2:
        return {
            "temporal_consistency_score": None,
            "flicker_score": None,
            "motion_consistency_score": None,
            "disabled_temporal_metrics": ["motion_consistency"],
        }

    reference_diffs = _frame_difference_means(reference_artifact, comparable_frames)
    comparison_diffs = _frame_difference_means(comparison_artifact, comparable_frames)
    if not reference_diffs:
        return {
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
        "temporal_consistency_score": round(temporal_consistency_score, 6),
        "flicker_score": round(flicker_score, 6),
        "motion_consistency_score": None,
        "disabled_temporal_metrics": ["motion_consistency"],
    }


def _frame_difference_means(video_artifact: Any, comparable_frames: int) -> list[float]:
    frame_count, channels, height, width = video_artifact.shape
    if comparable_frames > frame_count:
        comparable_frames = frame_count
    spatial_size = channels * height * width
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
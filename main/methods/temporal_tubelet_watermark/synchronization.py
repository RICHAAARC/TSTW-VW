"""
文件用途：提供 stage-one offset search 的最小同步实现。
File purpose: Provide the minimal stage-one implementation of offset-search synchronization.
Module type: Semi-general module
"""

from __future__ import annotations

import math
from statistics import median

from main.core.digest import compute_object_digest


OFFSET_SEARCH_MIN = -16
OFFSET_SEARCH_MAX = 16


def search_best_offset(
    temporal_scores: dict[int, float],
    sync_codes: dict[int, int],
    offset_search_min: int = OFFSET_SEARCH_MIN,
    offset_search_max: int = OFFSET_SEARCH_MAX,
    ground_truth_offset: int | None = None,
) -> dict[str, float | int | None]:
    """功能：在受治理 offset 范围内搜索最佳同步偏移。

    Search the best synchronization offset within the governed range.

    Args:
        temporal_scores: Observed temporal score series keyed by frame-start index.
        sync_codes: Sync-code series keyed by frame-start index.
        offset_search_min: Minimum candidate offset.
        offset_search_max: Maximum candidate offset.
        ground_truth_offset: Optional known ground-truth offset.

    Returns:
        A dictionary containing the synchronization diagnostics.
    """
    if not isinstance(temporal_scores, dict) or not temporal_scores:
        raise ValueError("temporal_scores must be a non-empty dictionary")
    if not isinstance(sync_codes, dict) or not sync_codes:
        raise ValueError("sync_codes must be a non-empty dictionary")
    if not isinstance(offset_search_min, int) or not isinstance(offset_search_max, int):
        raise TypeError("offset search bounds must be integers")
    if offset_search_min > offset_search_max:
        raise ValueError("offset_search_min must not exceed offset_search_max")

    offset_scores: dict[int, float] = {}
    for offset_candidate in range(offset_search_min, offset_search_max + 1):
        offset_scores[offset_candidate] = round(
            sum(
                float(temporal_score)
                * float(sync_codes.get(temporal_index - offset_candidate, 0))
                for temporal_index, temporal_score in temporal_scores.items()
            ),
            6,
        )

    ranked_offsets = sorted(
        offset_scores.items(),
        key=lambda item: (-float(item[1]), abs(item[0])),
    )
    best_offset, best_raw_score = ranked_offsets[0]
    normalized_score = _normalize_sync_score(list(offset_scores.values()), best_raw_score)
    peak_rank = None
    alignment_error = None
    if ground_truth_offset is not None:
        alignment_error = abs(best_offset - ground_truth_offset)
        peak_rank = next(
            (
                rank
                for rank, (offset_candidate, _) in enumerate(ranked_offsets, start=1)
                if offset_candidate == ground_truth_offset
            ),
            None,
        )

    return {
        "sync_search_enabled": True,
        "sync_estimated_offset": best_offset,
        "sync_ground_truth_offset": ground_truth_offset,
        "sync_alignment_error": alignment_error,
        "sync_peak_rank": peak_rank,
        "sync_score": normalized_score,
        "sync_search_space_size": len(offset_scores),
        "sync_search_space_digest": compute_object_digest(offset_scores),
        "sync_score_median": round(median(offset_scores.values()), 6),
    }


def _normalize_sync_score(all_scores: list[float], best_score: float) -> float:
    if len(all_scores) == 1:
        return round(float(best_score), 6)
    mean_score = sum(all_scores) / len(all_scores)
    variance = sum((score - mean_score) ** 2 for score in all_scores) / len(all_scores)
    if variance == 0.0:
        return round(float(best_score), 6)
    return round((float(best_score) - mean_score) / math.sqrt(variance), 6)
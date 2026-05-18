"""
文件用途：记录阶段 3 trajectory reconstruction 与 scoring 的轻量运行时摘要。
File purpose: Record lightweight runtime summaries for stage-three trajectory reconstruction and scoring.
Module type: General module
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable, TypeVar

from main.trajectory.interfaces import TrajectoryRuntimeSummary


ReturnT = TypeVar("ReturnT")


def measure_trajectory_runtime(
    reconstruction_callable: Callable[[], ReturnT],
    scoring_callable: Callable[[], Any],
) -> tuple[ReturnT, Any, TrajectoryRuntimeSummary]:
    """功能：测量 reconstruction 与 scoring 的分段运行时间。

    Measure reconstruction and scoring wall-clock time for the trajectory scaffold.

    Args:
        reconstruction_callable: Callable returning the trajectory observation.
        scoring_callable: Callable returning the statistic result.

    Returns:
        A tuple of reconstruction result, scoring result, and runtime summary.
    """
    reconstruction_start = perf_counter()
    reconstruction_result = reconstruction_callable()
    reconstruction_seconds = perf_counter() - reconstruction_start

    scoring_start = perf_counter()
    scoring_result = scoring_callable()
    scoring_seconds = perf_counter() - scoring_start

    runtime_summary = TrajectoryRuntimeSummary(
        trajectory_runtime_ms=round(
            (reconstruction_seconds + scoring_seconds) * 1000.0,
            6,
        ),
        trajectory_reconstruction_ms=round(reconstruction_seconds * 1000.0, 6),
        trajectory_scoring_ms=round(scoring_seconds * 1000.0, 6),
    )
    return reconstruction_result, scoring_result, runtime_summary
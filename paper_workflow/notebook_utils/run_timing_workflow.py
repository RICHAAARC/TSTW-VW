"""
文件用途：为 notebook 提供运行时间记录器与汇总 wrapper。
File purpose: Provide timing-recorder and timing-summary wrappers for notebooks.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.profile_runtime.profile_run_timing import RunTimingRecorder
from scripts.profile_runtime.summarize_run_timing import summarize_run_timing as _summarize_run_timing


def start_run_timing(*, run_root: str | Path, run_id: str | None = None) -> RunTimingRecorder:
    """功能：启动 notebook 用运行时间记录器。

    Start the runtime timing recorder for notebook use.

    Args:
        run_root: Run-root path.
        run_id: Optional run identifier.

    Returns:
        The initialized timing recorder.
    """
    return RunTimingRecorder(run_root=run_root, run_id=run_id)


def summarize_run_timing(*, run_root: str | Path) -> dict[str, Any]:
    """功能：汇总 notebook timing 事件。

    Summarize notebook timing events.

    Args:
        run_root: Run-root path.

    Returns:
        The timing-summary payload.
    """
    run_root_path = Path(run_root)
    runtime_profile_dir = run_root_path / "runtime_profile"
    return _summarize_run_timing(
        run_root=run_root_path,
        events_jsonl=runtime_profile_dir / "run_timing_events.jsonl",
        output_json=runtime_profile_dir / "run_timing_summary.json",
        output_md=runtime_profile_dir / "run_timing_report.md",
    )

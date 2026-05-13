"""
文件用途：汇总 run_timing_events.jsonl 并生成 JSON 与 Markdown 报告。
File purpose: Summarize run_timing_events.jsonl into JSON and Markdown reports.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.profile_runtime import write_json_file, write_markdown_file


def summarize_run_timing(
    *,
    run_root: str | Path,
    events_jsonl: str | Path,
    output_json: str | Path,
    output_md: str | Path,
) -> dict[str, Any]:
    """功能：汇总 timing event 并写出报告。

    Summarize timing events and write JSON plus Markdown reports.

    Args:
        run_root: Run-root path.
        events_jsonl: Input events JSONL path.
        output_json: Output summary JSON path.
        output_md: Output summary Markdown path.

    Returns:
        The timing summary payload.
    """
    events_path = Path(events_jsonl)
    events: list[dict[str, Any]] = []
    if events_path.exists():
        with events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                normalized_line = line.strip()
                if not normalized_line:
                    continue
                events.append(json.loads(normalized_line))

    events_by_name: dict[str, float] = {}
    failed_event_count = 0
    total_recorded_seconds = 0.0
    slowest_event_name = ""
    slowest_event_seconds = 0.0
    for event in events:
        event_name = str(event.get("event_name", "unknown_event"))
        elapsed_seconds = float(event.get("elapsed_seconds", 0.0) or 0.0)
        total_recorded_seconds += elapsed_seconds
        events_by_name[event_name] = round(events_by_name.get(event_name, 0.0) + elapsed_seconds, 6)
        if str(event.get("status", "ok")) == "failed":
            failed_event_count += 1
        if elapsed_seconds > slowest_event_seconds:
            slowest_event_seconds = elapsed_seconds
            slowest_event_name = event_name

    if total_recorded_seconds < 1800:
        estimated_work_planning_label = "short_run"
    elif total_recorded_seconds < 7200:
        estimated_work_planning_label = "medium_run"
    elif total_recorded_seconds < 28800:
        estimated_work_planning_label = "multi_hour_run"
    else:
        estimated_work_planning_label = "long_run"

    summary = {
        "run_root": str(Path(run_root)),
        "event_count": len(events),
        "failed_event_count": failed_event_count,
        "total_recorded_seconds": round(total_recorded_seconds, 6),
        "events_by_name": events_by_name,
        "slowest_event_name": slowest_event_name,
        "slowest_event_seconds": round(slowest_event_seconds, 6),
        "estimated_work_planning_label": estimated_work_planning_label,
    }
    report_lines = [
        "# Run Timing Report",
        "",
        f"- run_root: {Path(run_root)}",
        f"- event_count: {summary['event_count']}",
        f"- failed_event_count: {summary['failed_event_count']}",
        f"- total_recorded_seconds: {summary['total_recorded_seconds']}",
        f"- slowest_event_name: {summary['slowest_event_name']}",
        f"- slowest_event_seconds: {summary['slowest_event_seconds']}",
        f"- estimated_work_planning_label: {summary['estimated_work_planning_label']}",
        "",
        "## Events By Name",
        "",
    ]
    for event_name, elapsed_seconds in sorted(events_by_name.items()):
        report_lines.append(f"- {event_name}: {round(elapsed_seconds, 6)}")

    write_json_file(output_json, summary)
    write_markdown_file(output_md, "\n".join(report_lines))
    return summary


def main(argv: list[str] | None = None) -> int:
    """功能：执行 timing 汇总 CLI。

    Execute the timing summary CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Summarize runtime timing events.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--events-jsonl", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args(argv)
    summarize_run_timing(
        run_root=args.run_root,
        events_jsonl=args.events_jsonl,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

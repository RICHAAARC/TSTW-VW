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


RUNNER_PREPARATION_EVENT_NAMES = (
    "runner_prepare_split_plan",
    "runner_prepare_attack_registry",
    "runner_prepare_event_plan",
    "runner_prepare_runtime_method_configs",
)
THRESHOLD_MATERIALIZATION_EVENT_NAMES = (
    "runner_materialize_dev_threshold_decisions",
    "runner_materialize_calibration_threshold_decisions",
    "runner_materialize_test_threshold_decisions",
)
RECORD_PERSISTENCE_EVENT_NAMES = (
    "runner_write_event_score_records",
    "runner_write_threshold_records",
)
MANIFEST_WRITE_EVENT_NAMES = (
    "runner_write_runtime_config",
    "runner_write_runtime_manifest",
    "runner_write_artifact_manifest",
    "runner_write_run_manifest",
    "runner_write_cross_event_vae_batching_outputs",
)


def _sum_event_durations(
    events_by_name: dict[str, float],
    event_names: tuple[str, ...],
) -> float:
    """功能：按事件名集合汇总耗时。

    Sum elapsed seconds across a defined event-name group.

    Args:
        events_by_name: Event-duration mapping.
        event_names: Event names included in the group.

    Returns:
        The aggregated elapsed seconds.
    """
    return round(sum(float(events_by_name.get(event_name, 0.0)) for event_name in event_names), 6)


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
    events_by_group: dict[str, float] = {}
    event_counts_by_group: dict[str, int] = {}
    runner_substage_counts: dict[str, int] = {}
    failed_event_count = 0
    total_recorded_seconds = 0.0
    slowest_event_name = ""
    slowest_event_seconds = 0.0
    for event in events:
        event_name = str(event.get("event_name", "unknown_event"))
        elapsed_seconds = float(event.get("elapsed_seconds", 0.0) or 0.0)
        total_recorded_seconds += elapsed_seconds
        events_by_name[event_name] = round(events_by_name.get(event_name, 0.0) + elapsed_seconds, 6)
        metadata = event.get("metadata", {})
        event_group = str(event.get("event_group", "unknown_event_group"))
        events_by_group[event_group] = round(
            events_by_group.get(event_group, 0.0) + elapsed_seconds,
            6,
        )
        event_counts_by_group[event_group] = event_counts_by_group.get(event_group, 0) + 1
        if isinstance(metadata, dict) and metadata.get("event_group") == "runner_substage":
            runner_substage_counts[event_name] = int(
                runner_substage_counts.get(event_name, 0)
                + int(metadata.get("invocation_count", 0) or 0)
            )
        if str(event.get("status", "ok")) == "failed":
            failed_event_count += 1
        if elapsed_seconds > slowest_event_seconds:
            slowest_event_seconds = elapsed_seconds
            slowest_event_name = event_name

    top_timing_events = [
        {
            "event_name": event_name,
            "elapsed_seconds": round(elapsed_seconds, 6),
        }
        for event_name, elapsed_seconds in sorted(
            events_by_name.items(),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    ]

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
        "events_by_group": events_by_group,
        "event_counts_by_group": event_counts_by_group,
        "runner_substage_counts": runner_substage_counts,
        "decode_video_seconds": events_by_name.get("runner_decode_video", 0.0),
        "video_attack_seconds": round(
            events_by_name.get("runner_attack_video", 0.0)
            + events_by_name.get("runner_attack_materialization", 0.0),
            6,
        ),
        "vae_reencode_seconds": events_by_name.get("runner_reencode_latent", 0.0),
        "quality_metrics_seconds": events_by_name.get("runner_quality_metrics", 0.0),
        "temporal_metrics_seconds": events_by_name.get("runner_temporal_metrics", 0.0),
        "metric_frame_loading_seconds": events_by_name.get("runner_load_metric_frames", 0.0),
        "runner_preparation_seconds": _sum_event_durations(
            events_by_name,
            RUNNER_PREPARATION_EVENT_NAMES,
        ),
        "threshold_calibration_seconds": events_by_name.get(
            "runner_threshold_calibration",
            0.0,
        ),
        "threshold_materialization_seconds": _sum_event_durations(
            events_by_name,
            THRESHOLD_MATERIALIZATION_EVENT_NAMES,
        ),
        "record_persistence_seconds": _sum_event_durations(
            events_by_name,
            RECORD_PERSISTENCE_EVENT_NAMES,
        ),
        "artifact_build_seconds": events_by_name.get("runner_build_artifacts", 0.0),
        "manifest_write_seconds": _sum_event_durations(
            events_by_name,
            MANIFEST_WRITE_EVENT_NAMES,
        ),
        "slowest_event_name": slowest_event_name,
        "slowest_event_seconds": round(slowest_event_seconds, 6),
        "estimated_work_planning_label": estimated_work_planning_label,
        "top_timing_events": top_timing_events,
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
        f"- video_attack_seconds: {summary['video_attack_seconds']}",
        f"- vae_reencode_seconds: {summary['vae_reencode_seconds']}",
        f"- quality_metrics_seconds: {summary['quality_metrics_seconds']}",
        f"- temporal_metrics_seconds: {summary['temporal_metrics_seconds']}",
        f"- runner_preparation_seconds: {summary['runner_preparation_seconds']}",
        f"- threshold_calibration_seconds: {summary['threshold_calibration_seconds']}",
        f"- threshold_materialization_seconds: {summary['threshold_materialization_seconds']}",
        f"- record_persistence_seconds: {summary['record_persistence_seconds']}",
        f"- artifact_build_seconds: {summary['artifact_build_seconds']}",
        f"- manifest_write_seconds: {summary['manifest_write_seconds']}",
        "",
        "## Events By Name",
        "",
    ]
    for event_name, elapsed_seconds in sorted(events_by_name.items()):
        report_lines.append(f"- {event_name}: {round(elapsed_seconds, 6)}")

    report_lines.extend(["", "## Top Timing Events", ""])
    for event_payload in top_timing_events:
        report_lines.append(
            f"- {event_payload['event_name']}: {event_payload['elapsed_seconds']}"
        )

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

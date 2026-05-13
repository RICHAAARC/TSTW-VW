"""
文件用途：汇总 run_root 中的失败原因，并输出机器可读与人工可读摘要。
File purpose: Summarize run-root failures into machine-readable and human-readable reports.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.profile_runtime import write_json_file, write_markdown_file


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    """功能：读取存在的 JSON 文件。

    Load a JSON file when it exists.

    Args:
        path: Input JSON path.

    Returns:
        The parsed JSON payload, or an empty dictionary.
    """
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_run_failures(
    *,
    run_root: str | Path,
    output_json: str | Path,
    output_md: str | Path,
) -> dict[str, Any]:
    """功能：汇总 run_root 中的失败原因。

    Summarize failure reasons from the run root.

    Args:
        run_root: Run-root path.
        output_json: Output JSON path.
        output_md: Output Markdown path.

    Returns:
        The failure-summary payload.
    """
    run_root_path = Path(run_root)
    records_path = run_root_path / "records" / "event_scores.jsonl"
    runtime_profile_dir = run_root_path / "runtime_profile"
    timing_events_path = runtime_profile_dir / "run_timing_events.jsonl"
    formal_validation_path = runtime_profile_dir / "formal_validation_summary.json"

    failure_reason_counts: Counter[str] = Counter()
    if records_path.exists():
        with records_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                normalized_line = line.strip()
                if not normalized_line:
                    continue
                record = json.loads(normalized_line)
                failure_reason = record.get("failure_reason")
                if failure_reason:
                    failure_reason_counts[str(failure_reason)] += 1

    runtime_profile_failures: list[str] = []
    if timing_events_path.exists():
        with timing_events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                normalized_line = line.strip()
                if not normalized_line:
                    continue
                event = json.loads(normalized_line)
                if str(event.get("status", "ok")) == "failed":
                    runtime_profile_failures.append(str(event.get("event_name", "unknown_event")))

    formal_validation_summary = _load_json_if_exists(formal_validation_path)
    checker_status = formal_validation_summary.get("status")
    checker_blocking_reasons = list(formal_validation_summary.get("BlockingReasons", [])) if formal_validation_summary else []

    record_failure_count = int(sum(failure_reason_counts.values()))
    if checker_blocking_reasons:
        dominant_failure_category = "checker_blocking_reason"
        recommended_next_action = "inspect checker blocking reasons"
    elif record_failure_count > 0:
        dominant_failure_category = "record_failure_reason"
        recommended_next_action = "inspect failure_reason counts in records"
    elif runtime_profile_failures:
        dominant_failure_category = "runtime_profile_failure"
        recommended_next_action = "inspect runtime profiling failures"
    else:
        dominant_failure_category = "no_failure_detected"
        recommended_next_action = "no blocking failure detected"

    payload = {
        "run_root": str(run_root_path),
        "record_failure_count": record_failure_count,
        "failure_reason_counts": dict(failure_reason_counts),
        "checker_status": checker_status,
        "checker_blocking_reasons": checker_blocking_reasons,
        "runtime_profile_failures": runtime_profile_failures,
        "dominant_failure_category": dominant_failure_category,
        "recommended_next_action": recommended_next_action,
    }
    report_lines = [
        "# Run Failure Summary",
        "",
        f"- run_root: {run_root_path}",
        f"- record_failure_count: {record_failure_count}",
        f"- checker_status: {checker_status}",
        f"- checker_blocking_reasons: {checker_blocking_reasons}",
        f"- runtime_profile_failures: {runtime_profile_failures}",
        f"- dominant_failure_category: {dominant_failure_category}",
        f"- recommended_next_action: {recommended_next_action}",
        "",
        "## failure_reason_counts",
        "",
    ]
    for failure_reason, count in sorted(failure_reason_counts.items()):
        report_lines.append(f"- {failure_reason}: {count}")

    write_json_file(output_json, payload)
    write_markdown_file(output_md, "\n".join(report_lines))
    return payload


def main(argv: list[str] | None = None) -> int:
    """功能：执行运行失败摘要 CLI。

    Execute the run-failure summary CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Summarize run failures from records and runtime_profile artifacts.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args(argv)
    summarize_run_failures(
        run_root=args.run_root,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

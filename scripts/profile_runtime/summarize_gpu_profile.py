"""
文件用途：汇总 GPU runtime trace，并生成 JSON 与 Markdown 报告。
File purpose: Summarize the GPU runtime trace and generate JSON plus Markdown reports.
Module type: General module
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median
from typing import Any

from scripts.profile_runtime import write_json_file, write_markdown_file


_NUMERIC_FIELDS = {
    "elapsed_seconds",
    "gpu_util_percent",
    "memory_used_mb",
    "memory_total_mb",
    "memory_util_percent",
    "power_draw_w",
    "temperature_c",
}


def _to_float(value: str) -> float | None:
    """功能：将字符串解析为浮点数。

    Parse a string value into a float when possible.

    Args:
        value: Raw text value.

    Returns:
        The parsed float, or None when parsing fails.
    """
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def summarize_gpu_runtime_profile(
    *,
    run_root: str | Path,
    trace_csv: str | Path,
    output_json: str | Path,
    output_md: str | Path,
) -> dict[str, Any]:
    """功能：汇总 GPU runtime trace。

    Summarize the GPU runtime trace.

    Args:
        run_root: Run-root path.
        trace_csv: Input trace CSV path.
        output_json: Output summary JSON path.
        output_md: Output summary Markdown path.

    Returns:
        The GPU runtime summary payload.
    """
    trace_path = Path(trace_csv)
    rows: list[dict[str, str]] = []
    if trace_path.exists():
        with trace_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]

    numeric_rows: list[dict[str, float]] = []
    for row in rows:
        parsed_row: dict[str, float] = {}
        for field_name in _NUMERIC_FIELDS:
            parsed_value = _to_float(row.get(field_name, ""))
            if parsed_value is not None:
                parsed_row[field_name] = parsed_value
        if parsed_row:
            numeric_rows.append(parsed_row)

    gpu_util_values = [row["gpu_util_percent"] for row in numeric_rows if "gpu_util_percent" in row]
    memory_util_values = [row["memory_util_percent"] for row in numeric_rows if "memory_util_percent" in row]
    memory_used_values = [row["memory_used_mb"] for row in numeric_rows if "memory_used_mb" in row]
    memory_total_values = [row["memory_total_mb"] for row in numeric_rows if "memory_total_mb" in row]
    power_values = [row["power_draw_w"] for row in numeric_rows if "power_draw_w" in row]
    temperature_values = [row["temperature_c"] for row in numeric_rows if "temperature_c" in row]
    elapsed_values = [row["elapsed_seconds"] for row in numeric_rows if "elapsed_seconds" in row]

    trace_available = bool(rows)
    usable_sample_count = len(gpu_util_values)
    unavailable_sample_count = sum(
        1
        for row in rows
        if "unavailable" in str(row.get("gpu_name", "")).lower()
        or "sample_failure" in str(row.get("gpu_name", "")).lower()
    )
    if usable_sample_count > 0:
        profiling_status = "sampled"
        profiling_failure_reason = None
    elif trace_available:
        profiling_status = "unavailable"
        profiling_failure_reason = "gpu_runtime_samples_unavailable"
    else:
        profiling_status = "not_sampled"
        profiling_failure_reason = "gpu_runtime_trace_empty"
    total_memory_mb = max(memory_total_values) if memory_total_values else 0.0
    peak_memory_used_mb = max(memory_used_values) if memory_used_values else 0.0
    peak_memory_ratio = (peak_memory_used_mb / total_memory_mb) if total_memory_mb > 0 else 0.0
    mean_gpu_util_percent = mean(gpu_util_values) if gpu_util_values else 0.0
    median_gpu_util_percent = median(gpu_util_values) if gpu_util_values else 0.0
    low_utilization_ratio = (
        sum(1 for value in gpu_util_values if value < 50.0) / len(gpu_util_values)
        if gpu_util_values
        else 0.0
    )
    mean_memory_util_percent = mean(memory_util_values) if memory_util_values else 0.0
    peak_power_draw_w = max(power_values) if power_values else 0.0
    peak_temperature_c = max(temperature_values) if temperature_values else 0.0
    total_profile_seconds = (
        max(elapsed_values) - min(elapsed_values)
        if len(elapsed_values) >= 2
        else (elapsed_values[0] if elapsed_values else 0.0)
    )
    gpu_name = next(
        (
            str(row.get("gpu_name", ""))
            for row in rows
            if str(row.get("gpu_name", "")).strip()
            and "unavailable" not in str(row.get("gpu_name", ""))
            and "sample_failure" not in str(row.get("gpu_name", ""))
        ),
        "unavailable",
    )

    if not trace_available or not gpu_util_values:
        estimated_gpu_usage_status = "unavailable"
    elif peak_memory_ratio > 0.90:
        estimated_gpu_usage_status = "memory_pressure"
    elif mean_gpu_util_percent < 50.0 and low_utilization_ratio > 0.50:
        estimated_gpu_usage_status = "low_utilization"
    elif mean_gpu_util_percent < 85.0:
        estimated_gpu_usage_status = "moderate_utilization"
    else:
        estimated_gpu_usage_status = "high_utilization"

    if peak_memory_ratio > 0.90:
        recommended_batch_size_direction = "decrease"
    elif peak_memory_ratio < 0.45 and mean_gpu_util_percent < 50.0:
        recommended_batch_size_direction = "increase_or_check_io"
    elif 0.45 <= peak_memory_ratio <= 0.85:
        recommended_batch_size_direction = "increase_or_keep"
    else:
        recommended_batch_size_direction = "keep"

    summary = {
        "trace_available": trace_available,
        "sample_count": len(rows),
        "usable_sample_count": usable_sample_count,
        "unavailable_sample_count": unavailable_sample_count,
        "profiling_status": profiling_status,
        "profiling_failure_reason": profiling_failure_reason,
        "gpu_name": gpu_name,
        "total_memory_mb": round(total_memory_mb, 6),
        "peak_memory_used_mb": round(peak_memory_used_mb, 6),
        "peak_memory_ratio": round(peak_memory_ratio, 6),
        "mean_gpu_util_percent": round(mean_gpu_util_percent, 6),
        "median_gpu_util_percent": round(median_gpu_util_percent, 6),
        "low_utilization_ratio": round(low_utilization_ratio, 6),
        "mean_memory_util_percent": round(mean_memory_util_percent, 6),
        "peak_power_draw_w": round(peak_power_draw_w, 6),
        "peak_temperature_c": round(peak_temperature_c, 6),
        "total_profile_seconds": round(total_profile_seconds, 6),
        "estimated_gpu_usage_status": estimated_gpu_usage_status,
        "recommended_batch_size_direction": recommended_batch_size_direction,
    }
    report_lines = [
        "# GPU Runtime Report",
        "",
        f"- run_root: {Path(run_root)}",
        f"- trace_available: {summary['trace_available']}",
        f"- sample_count: {summary['sample_count']}",
        f"- usable_sample_count: {summary['usable_sample_count']}",
        f"- profiling_status: {summary['profiling_status']}",
        f"- profiling_failure_reason: {summary['profiling_failure_reason']}",
        f"- gpu_name: {summary['gpu_name']}",
        f"- peak_memory_ratio: {summary['peak_memory_ratio']}",
        f"- mean_gpu_util_percent: {summary['mean_gpu_util_percent']}",
        f"- low_utilization_ratio: {summary['low_utilization_ratio']}",
        f"- estimated_gpu_usage_status: {summary['estimated_gpu_usage_status']}",
        f"- recommended_batch_size_direction: {summary['recommended_batch_size_direction']}",
    ]
    write_json_file(output_json, summary)
    write_markdown_file(output_md, "\n".join(report_lines))
    return summary


def main(argv: list[str] | None = None) -> int:
    """功能：执行 GPU 汇总 CLI。

    Execute the GPU summary CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Summarize GPU runtime profiling output.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--trace-csv", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args(argv)
    summarize_gpu_runtime_profile(
        run_root=args.run_root,
        trace_csv=args.trace_csv,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

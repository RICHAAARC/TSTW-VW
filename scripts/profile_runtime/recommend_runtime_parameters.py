"""
文件用途：读取 profiling 汇总并给出下一轮运行参数建议。
File purpose: Read profiling summaries and recommend runtime parameters for the next run.
Module type: General module
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.profile_runtime import read_json_file, write_json_file


def _load_optional_json(path: Path, warnings: list[str]) -> dict[str, Any]:
    """功能：读取可选 JSON 文件，缺失时记录 warning。

    Load an optional JSON file and record a warning when it is missing.

    Args:
        path: Input JSON path.
        warnings: Warning accumulator.

    Returns:
        The parsed JSON payload, or an empty dictionary.
    """
    if not path.exists():
        warnings.append(f"missing_input:{path.name}")
        return {}
    return read_json_file(path)


def recommend_runtime_parameters(
    *,
    run_root: str | Path,
    output_json: str | Path,
) -> dict[str, Any]:
    """功能：根据 profiling 汇总给出下一轮运行建议。

    Recommend the next-round runtime parameters from profiling summaries.

    Args:
        run_root: Run-root path.
        output_json: Output recommendation JSON path.

    Returns:
        The runtime-parameter recommendation payload.
    """
    run_root_path = Path(run_root)
    runtime_profile_dir = run_root_path / "runtime_profile"
    warnings: list[str] = []

    gpu_summary = _load_optional_json(runtime_profile_dir / "gpu_runtime_summary.json", warnings)
    timing_summary = _load_optional_json(runtime_profile_dir / "run_timing_summary.json", warnings)
    scale_estimate = _load_optional_json(runtime_profile_dir / "run_scale_estimate.json", warnings)
    failure_summary = _load_optional_json(runtime_profile_dir / "run_failure_summary.json", warnings)
    drive_io_profile = _load_optional_json(runtime_profile_dir / "drive_io_profile.json", warnings)

    peak_memory_ratio = float(gpu_summary.get("peak_memory_ratio", 0.0) or 0.0)
    mean_gpu_util_percent = float(gpu_summary.get("mean_gpu_util_percent", 0.0) or 0.0)
    timing_label = str(timing_summary.get("estimated_work_planning_label", "short_run") or "short_run")
    scale_label = str(scale_estimate.get("scale_label", "debug_small") or "debug_small")
    checker_status = failure_summary.get("checker_status", True)
    runtime_profile_failures = failure_summary.get("runtime_profile_failures", [])
    drive_io_status = str(drive_io_profile.get("drive_io_status", "unknown") or "unknown")
    events_by_name = timing_summary.get("events_by_name", {})
    if not isinstance(events_by_name, dict):
        events_by_name = {}
    runner_elapsed_seconds = float(
        events_by_name.get("real_video_vae_latent_runner", 0.0) or 0.0
    )
    runner_exceeds_shard_threshold = runner_elapsed_seconds >= 28800.0

    reasoning: list[str] = []
    if peak_memory_ratio > 0.90:
        batch_size_direction = "decrease"
        recommended_batch_size_frames = 2
        reasoning.append("peak_memory_ratio is above 0.90")
    elif peak_memory_ratio < 0.45 and mean_gpu_util_percent < 50.0:
        batch_size_direction = "increase_or_keep"
        recommended_batch_size_frames = 8
        reasoning.append("peak_memory_ratio is below 0.45")
        reasoning.append("mean_gpu_utilization is below 50")
    else:
        batch_size_direction = "keep"
        recommended_batch_size_frames = 4
        reasoning.append("current GPU memory and utilization are within a stable range")

    if drive_io_status == "slow":
        reasoning.append("drive_io_status is slow")

    if timing_label in {"multi_hour_run", "long_run"}:
        reasoning.append("run_timing indicates a multi-hour or long run")
    if scale_label in {"formal_medium", "formal_large"}:
        reasoning.append("run_scale_estimate indicates a larger formal workload")
    if runner_exceeds_shard_threshold:
        reasoning.append("real_video_vae_latent_runner exceeds 8 hours estimated runtime")

    if checker_status is False and runtime_profile_failures:
        recommended_runtime_profile_next = "debug_real_video_or_smoke"
        recommended_action = "fix_runtime_failures_before_rerun"
        reasoning.append("runtime failures were observed before a formal pass")
    elif drive_io_status == "slow":
        recommended_runtime_profile_next = "debug_real_video_or_smoke"
        recommended_action = "reduce_drive_io_then_rerun"
    elif runner_exceeds_shard_threshold:
        recommended_runtime_profile_next = "debug_real_video_or_smoke"
        recommended_action = "split_run_into_shards_or_reduce_attack_matrix_for_smoke"
    elif batch_size_direction == "decrease":
        recommended_runtime_profile_next = "formal"
        recommended_action = "rerun_with_smaller_batch_size_frames"
    elif batch_size_direction == "increase_or_keep":
        recommended_runtime_profile_next = "debug_real_video_or_smoke"
        recommended_action = "rerun_with_larger_batch_after_smoke_pass"
    else:
        recommended_runtime_profile_next = "formal"
        recommended_action = "rerun_with_current_parameters"

    if scale_label == "formal_large" or timing_label == "long_run":
        recommended_gpu_tier = "A100_or_better"
    else:
        recommended_gpu_tier = "L4_or_better"

    payload = {
        "status": True,
        "recommended_gpu_tier": recommended_gpu_tier,
        "recommended_batch_size_frames": recommended_batch_size_frames,
        "batch_size_direction": batch_size_direction,
        "recommended_runtime_profile_next": recommended_runtime_profile_next,
        "recommended_action": recommended_action,
        "reasoning": reasoning,
        "warnings": warnings,
    }
    write_json_file(output_json, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    """功能：执行参数建议 CLI。

    Execute the runtime-parameter recommendation CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Recommend runtime parameters from profiling summaries.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args(argv)
    recommend_runtime_parameters(
        run_root=args.run_root,
        output_json=args.output_json,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

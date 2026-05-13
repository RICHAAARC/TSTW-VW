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


def _contains_oom_signal(values: list[str]) -> bool:
    """功能：检测 failure 文本中是否出现 OOM 信号。

    Detect whether failure text contains an out-of-memory signal.

    Args:
        values: Candidate failure strings.

    Returns:
        True when an OOM-like signal is present.
    """
    normalized_text = " ".join(str(value).lower() for value in values if value)
    return "cuda out of memory" in normalized_text or "out of memory" in normalized_text or " oom" in normalized_text


def _profile_batch_cap(current_runtime_profile: str, current_gpu_target: str) -> int:
    """功能：返回当前 GPU / profile 家族的 batch 上限建议。

    Return the advised batch-size cap for the current GPU/profile family.

    Args:
        current_runtime_profile: Current runtime-profile name.
        current_gpu_target: Current GPU-target string.

    Returns:
        The advised upper bound for VAE frame-batch size.
    """
    normalized_profile = str(current_runtime_profile).lower()
    normalized_target = str(current_gpu_target).lower()
    if normalized_profile.startswith("a100_80g") or "a100" in normalized_target:
        return 32
    return 8


def _generic_recommended_runtime_profile_next(
    *,
    checker_status: Any,
    runtime_profile_failures: list[Any],
    drive_io_status: str,
    runner_exceeds_shard_threshold: bool,
    batch_size_direction: str,
) -> str:
    """功能：保持旧 recommendation 载荷兼容的 profile 建议。

    Keep the generic legacy-compatible runtime-profile recommendation.

    Args:
        checker_status: Checker status flag.
        runtime_profile_failures: Runtime-profile failure list.
        drive_io_status: Drive-IO classification.
        runner_exceeds_shard_threshold: Whether the runner exceeds the shard threshold.
        batch_size_direction: Recommended batch-size direction.

    Returns:
        The generic next-profile label.
    """
    if checker_status is False and runtime_profile_failures:
        return "debug_real_video_or_smoke"
    if drive_io_status == "slow":
        return "debug_real_video_or_smoke"
    if runner_exceeds_shard_threshold:
        return "debug_real_video_or_smoke"
    if batch_size_direction == "increase_or_keep":
        return "debug_real_video_or_smoke"
    return "formal"


def _specific_recommended_runtime_profile_next(
    *,
    current_runtime_profile: str,
    current_gpu_target: str,
    checker_status: Any,
    runtime_profile_failures: list[Any],
    drive_io_status: str,
    runner_exceeds_shard_threshold: bool,
    batch_size_direction: str,
    scale_label: str,
    video_attack_seconds: float,
    vae_reencode_seconds: float,
) -> str:
    """功能：在已有 profile plan 时给出具体 profile 建议。

    Recommend a concrete next runtime profile when a governed profile plan exists.

    Args:
        current_runtime_profile: Current runtime-profile name.
        current_gpu_target: Current GPU-target string.
        checker_status: Checker status flag.
        runtime_profile_failures: Runtime-profile failure list.
        drive_io_status: Drive-IO classification.
        runner_exceeds_shard_threshold: Whether the runner exceeds the shard threshold.
        batch_size_direction: Recommended batch-size direction.
        scale_label: Workload scale label.
        video_attack_seconds: Attack-dominant timing estimate.
        vae_reencode_seconds: VAE-dominant timing estimate.

    Returns:
        The concrete next runtime-profile label.
    """
    normalized_profile = str(current_runtime_profile).strip()
    normalized_profile_lower = normalized_profile.lower()
    normalized_gpu_target = str(current_gpu_target).lower()
    is_a100_profile = normalized_profile_lower.startswith("a100_80g") or "a100" in normalized_gpu_target

    if checker_status is False and runtime_profile_failures:
        return "l4_debug"
    if drive_io_status == "slow":
        return "l4_debug"
    if runner_exceeds_shard_threshold or (vae_reencode_seconds > 0.0 and vae_reencode_seconds >= video_attack_seconds):
        if is_a100_profile:
            if normalized_profile_lower == "a100_80g_formal" and scale_label == "formal_large":
                return "a100_80g_paper_main"
            return normalized_profile
        return "a100_80g_formal"
    if video_attack_seconds > vae_reencode_seconds and video_attack_seconds > 0.0:
        return normalized_profile or "l4_smoke"
    if batch_size_direction == "increase_or_keep" and normalized_profile_lower == "l4_debug":
        return "l4_smoke"
    return normalized_profile or "l4_formal"


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
    runtime_profile_plan = _load_optional_json(runtime_profile_dir / "runtime_profile_plan.json", warnings)
    environment_snapshot = _load_optional_json(runtime_profile_dir / "colab_environment_snapshot.json", warnings)

    peak_memory_ratio = float(gpu_summary.get("peak_memory_ratio", 0.0) or 0.0)
    mean_gpu_util_percent = float(gpu_summary.get("mean_gpu_util_percent", 0.0) or 0.0)
    timing_label = str(timing_summary.get("estimated_work_planning_label", "short_run") or "short_run")
    scale_label = str(scale_estimate.get("scale_label", "debug_small") or "debug_small")
    checker_status = failure_summary.get("checker_status", True)
    runtime_profile_failures = failure_summary.get("runtime_profile_failures", [])
    drive_io_status = str(drive_io_profile.get("drive_io_status", "unknown") or "unknown")
    current_runtime_profile = str(
        runtime_profile_plan.get("runtime_profile")
        or environment_snapshot.get("runtime_profile")
        or ""
    )
    current_gpu_target = str(
        runtime_profile_plan.get("gpu_target")
        or environment_snapshot.get("gpu_name")
        or ""
    )
    has_runtime_profile_plan = bool(runtime_profile_plan)
    current_batch_size_frames = int(
        runtime_profile_plan.get(
            "vae_batch_size_frames",
            runtime_profile_plan.get("batch_size_frames", 4),
        )
        or 4
    )
    events_by_name = timing_summary.get("events_by_name", {})
    if not isinstance(events_by_name, dict):
        events_by_name = {}
    runner_elapsed_seconds = float(
        events_by_name.get("real_video_vae_latent_runner", 0.0) or 0.0
    )
    video_attack_seconds = float(
        timing_summary.get("video_attack_seconds", events_by_name.get("video_attack_seconds", 0.0)) or 0.0
    )
    vae_reencode_seconds = float(
        timing_summary.get("vae_reencode_seconds", events_by_name.get("vae_reencode_seconds", 0.0)) or 0.0
    )
    runner_exceeds_shard_threshold = runner_elapsed_seconds >= 28800.0
    checker_blocking_reasons = failure_summary.get("checker_blocking_reasons", [])
    if not isinstance(checker_blocking_reasons, list):
        checker_blocking_reasons = []
    failure_reason_counts = failure_summary.get("failure_reason_counts", {})
    if not isinstance(failure_reason_counts, dict):
        failure_reason_counts = {}
    oom_detected = _contains_oom_signal(
        [
            *checker_blocking_reasons,
            *[str(item) for item in runtime_profile_failures],
            *[str(item) for item in failure_reason_counts.keys()],
        ]
    )

    reasoning: list[str] = []
    if peak_memory_ratio > 0.90 or oom_detected:
        batch_size_direction = "decrease"
        if has_runtime_profile_plan:
            recommended_batch_size_frames = max(1, current_batch_size_frames // 2)
        else:
            recommended_batch_size_frames = 2
        if peak_memory_ratio > 0.90:
            reasoning.append("peak_memory_ratio is above 0.90")
        if oom_detected:
            reasoning.append("oom-like failure signals were observed")
    elif peak_memory_ratio < 0.45 and mean_gpu_util_percent < 50.0:
        batch_size_direction = "increase_or_keep"
        if has_runtime_profile_plan:
            recommended_batch_size_frames = min(
                max(current_batch_size_frames, current_batch_size_frames * 2),
                _profile_batch_cap(current_runtime_profile, current_gpu_target),
            )
        else:
            recommended_batch_size_frames = 8
        reasoning.append("peak_memory_ratio is below 0.45")
        reasoning.append("mean_gpu_utilization is below 50")
    elif 0.45 <= peak_memory_ratio <= 0.85 and mean_gpu_util_percent >= 60.0:
        batch_size_direction = "keep"
        recommended_batch_size_frames = current_batch_size_frames if has_runtime_profile_plan else 4
        reasoning.append("peak_memory_ratio is between 0.45 and 0.85")
        reasoning.append("mean_gpu_utilization is at least 60")
    else:
        batch_size_direction = "keep"
        recommended_batch_size_frames = current_batch_size_frames if has_runtime_profile_plan else 4
        reasoning.append("current GPU memory and utilization are within a stable range")

    if drive_io_status == "slow":
        reasoning.append("drive_io_status is slow")

    if timing_label in {"multi_hour_run", "long_run"}:
        reasoning.append("run_timing indicates a multi-hour or long run")
    if scale_label in {"formal_medium", "formal_large"}:
        reasoning.append("run_scale_estimate indicates a larger formal workload")
    if runner_exceeds_shard_threshold:
        reasoning.append("real_video_vae_latent_runner exceeds 8 hours estimated runtime")
    if video_attack_seconds > vae_reencode_seconds and video_attack_seconds > 0.0:
        reasoning.append("video_attack_seconds dominates the profiled runtime")
    if vae_reencode_seconds >= video_attack_seconds and vae_reencode_seconds > 0.0:
        reasoning.append("vae_reencode_seconds dominates the profiled runtime")

    if checker_status is False and runtime_profile_failures:
        recommended_action = "fix_runtime_failures_before_rerun"
        reasoning.append("runtime failures were observed before a formal pass")
    elif drive_io_status == "slow":
        recommended_action = "reduce_drive_io_then_rerun"
    elif video_attack_seconds > vae_reencode_seconds and video_attack_seconds > 0.0:
        recommended_action = "tune_attack_workers_or_reduce_attack_subset_or_shard"
    elif vae_reencode_seconds >= video_attack_seconds and vae_reencode_seconds > 0.0:
        recommended_action = "increase_vae_batch_size_frames_or_use_a100_profile"
    elif runner_exceeds_shard_threshold:
        recommended_action = "split_run_into_shards_or_reduce_attack_matrix_for_smoke"
    elif batch_size_direction == "decrease":
        recommended_action = "rerun_with_smaller_batch_size_frames"
    elif batch_size_direction == "increase_or_keep":
        recommended_action = "rerun_with_larger_batch_after_smoke_pass"
    else:
        recommended_action = "rerun_with_current_parameters"

    if current_runtime_profile:
        recommended_runtime_profile_next = _specific_recommended_runtime_profile_next(
            current_runtime_profile=current_runtime_profile,
            current_gpu_target=current_gpu_target,
            checker_status=checker_status,
            runtime_profile_failures=runtime_profile_failures,
            drive_io_status=drive_io_status,
            runner_exceeds_shard_threshold=runner_exceeds_shard_threshold,
            batch_size_direction=batch_size_direction,
            scale_label=scale_label,
            video_attack_seconds=video_attack_seconds,
            vae_reencode_seconds=vae_reencode_seconds,
        )
    else:
        recommended_runtime_profile_next = _generic_recommended_runtime_profile_next(
            checker_status=checker_status,
            runtime_profile_failures=runtime_profile_failures,
            drive_io_status=drive_io_status,
            runner_exceeds_shard_threshold=runner_exceeds_shard_threshold,
            batch_size_direction=batch_size_direction,
        )

    if recommended_runtime_profile_next.startswith("a100_80g") or scale_label == "formal_large" or timing_label == "long_run":
        recommended_gpu_tier = "A100_or_better"
    else:
        recommended_gpu_tier = "L4_or_better"

    payload = {
        "status": True,
        "current_runtime_profile": current_runtime_profile or None,
        "current_gpu_target": current_gpu_target or None,
        "recommended_gpu_tier": recommended_gpu_tier,
        "recommended_batch_size_frames": recommended_batch_size_frames,
        "recommended_vae_batch_size_frames": recommended_batch_size_frames,
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

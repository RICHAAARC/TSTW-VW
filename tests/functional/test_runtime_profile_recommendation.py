"""
文件用途：验证受治理 runtime profile recommendation 的具体 profile 与 batch 建议。
File purpose: Validate concrete runtime-profile and batch recommendations for governed runtime profiles.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.profile_runtime.recommend_runtime_parameters import (
    recommend_runtime_parameters,
)


pytestmark = pytest.mark.quick


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.mark.unit
def test_runtime_profile_recommendation_keeps_current_l4_formal_when_utilization_is_healthy(
    tmp_path: Path,
) -> None:
    """Validate healthy L4 utilization keeps the current formal runtime profile.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"

    _write_json(
        runtime_profile_dir / "runtime_profile_plan.json",
        {
            "runtime_profile": "l4_formal",
            "gpu_target": "L4",
            "vae_batch_size_frames": 128,
            "batch_size_frames": 128,
        },
    )
    _write_json(
        runtime_profile_dir / "colab_environment_snapshot.json",
        {
            "runtime_profile": "l4_formal",
            "gpu_name": "NVIDIA L4",
        },
    )
    _write_json(
        runtime_profile_dir / "gpu_runtime_summary.json",
        {
            "peak_memory_ratio": 0.62,
            "mean_gpu_util_percent": 71.0,
        },
    )
    _write_json(
        runtime_profile_dir / "run_timing_summary.json",
        {
            "estimated_work_planning_label": "short_run",
            "events_by_name": {
                "real_video_vae_latent_runner": 1800.0,
            },
        },
    )
    _write_json(
        runtime_profile_dir / "run_scale_estimate.json",
        {
            "scale_label": "formal_small",
        },
    )
    _write_json(
        runtime_profile_dir / "run_failure_summary.json",
        {
            "checker_status": True,
            "runtime_profile_failures": [],
        },
    )
    _write_json(
        runtime_profile_dir / "drive_io_profile.json",
        {
            "drive_io_status": "moderate",
        },
    )

    payload = recommend_runtime_parameters(
        run_root=run_root,
        output_json=runtime_profile_dir / "runtime_parameter_recommendation.json",
    )

    assert payload["current_runtime_profile"] == "l4_formal"
    assert payload["recommended_runtime_profile_next"] == "l4_formal"
    assert payload["batch_size_direction"] == "keep"
    assert payload["recommended_batch_size_frames"] == 128


@pytest.mark.unit
def test_runtime_profile_recommendation_promotes_to_a100_for_vae_reencode_heavy_formal_run(
    tmp_path: Path,
) -> None:
    """Validate VAE-heavy formal runs recommend the A100 formal profile.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"

    _write_json(
        runtime_profile_dir / "runtime_profile_plan.json",
        {
            "runtime_profile": "l4_formal",
            "gpu_target": "L4",
            "vae_batch_size_frames": 8,
            "batch_size_frames": 8,
        },
    )
    _write_json(
        runtime_profile_dir / "gpu_runtime_summary.json",
        {
            "peak_memory_ratio": 0.38,
            "mean_gpu_util_percent": 34.0,
        },
    )
    _write_json(
        runtime_profile_dir / "run_timing_summary.json",
        {
            "estimated_work_planning_label": "multi_hour_run",
            "events_by_name": {
                "real_video_vae_latent_runner": 10800.0,
            },
            "vae_reencode_seconds": 7200.0,
            "video_attack_seconds": 1200.0,
        },
    )
    _write_json(
        runtime_profile_dir / "run_scale_estimate.json",
        {
            "scale_label": "formal_large",
        },
    )
    _write_json(
        runtime_profile_dir / "run_failure_summary.json",
        {
            "checker_status": True,
            "runtime_profile_failures": [],
        },
    )
    _write_json(
        runtime_profile_dir / "drive_io_profile.json",
        {
            "drive_io_status": "moderate",
        },
    )

    payload = recommend_runtime_parameters(
        run_root=run_root,
        output_json=runtime_profile_dir / "runtime_parameter_recommendation.json",
    )

    assert payload["recommended_runtime_profile_next"] == "a100_80g_formal"
    assert payload["recommended_action"] == "increase_vae_batch_size_frames_or_use_a100_profile"
    assert payload["recommended_gpu_tier"] == "A100_or_better"
    assert "vae_reencode_seconds dominates the profiled runtime" in payload["reasoning"]


@pytest.mark.unit
def test_runtime_profile_recommendation_reduces_batch_after_oom_signal(
    tmp_path: Path,
) -> None:
    """Validate OOM-like signals reduce the advised batch size for the next run.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"

    _write_json(
        runtime_profile_dir / "runtime_profile_plan.json",
        {
            "runtime_profile": "a100_80g_formal",
            "gpu_target": "A100-80G",
            "vae_batch_size_frames": 16,
            "batch_size_frames": 16,
        },
    )
    _write_json(
        runtime_profile_dir / "gpu_runtime_summary.json",
        {
            "peak_memory_ratio": 0.92,
            "mean_gpu_util_percent": 74.0,
        },
    )
    _write_json(
        runtime_profile_dir / "run_timing_summary.json",
        {
            "estimated_work_planning_label": "medium_run",
        },
    )
    _write_json(
        runtime_profile_dir / "run_scale_estimate.json",
        {
            "scale_label": "formal_medium",
        },
    )
    _write_json(
        runtime_profile_dir / "run_failure_summary.json",
        {
            "checker_status": True,
            "runtime_profile_failures": [],
            "failure_reason_counts": {
                "cuda out of memory": 1,
            },
        },
    )
    _write_json(
        runtime_profile_dir / "drive_io_profile.json",
        {
            "drive_io_status": "moderate",
        },
    )

    payload = recommend_runtime_parameters(
        run_root=run_root,
        output_json=runtime_profile_dir / "runtime_parameter_recommendation.json",
    )

    assert payload["recommended_runtime_profile_next"] == "a100_80g_formal"
    assert payload["batch_size_direction"] == "decrease"
    assert payload["recommended_batch_size_frames"] == 8
    assert payload["recommended_action"] == "rerun_with_smaller_batch_size_frames"


@pytest.mark.unit
def test_runtime_profile_recommendation_moves_to_debug_when_drive_io_is_slow(
    tmp_path: Path,
) -> None:
    """Validate slow Drive I/O recommends the governed debug profile.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"

    _write_json(
        runtime_profile_dir / "runtime_profile_plan.json",
        {
            "runtime_profile": "l4_formal",
            "gpu_target": "L4",
            "vae_batch_size_frames": 8,
            "batch_size_frames": 8,
        },
    )
    _write_json(
        runtime_profile_dir / "gpu_runtime_summary.json",
        {
            "peak_memory_ratio": 0.30,
            "mean_gpu_util_percent": 28.0,
        },
    )
    _write_json(
        runtime_profile_dir / "run_timing_summary.json",
        {
            "estimated_work_planning_label": "short_run",
        },
    )
    _write_json(
        runtime_profile_dir / "run_scale_estimate.json",
        {
            "scale_label": "formal_small",
        },
    )
    _write_json(
        runtime_profile_dir / "run_failure_summary.json",
        {
            "checker_status": True,
            "runtime_profile_failures": [],
        },
    )
    _write_json(
        runtime_profile_dir / "drive_io_profile.json",
        {
            "drive_io_status": "slow",
        },
    )

    payload = recommend_runtime_parameters(
        run_root=run_root,
        output_json=runtime_profile_dir / "runtime_parameter_recommendation.json",
    )

    assert payload["recommended_runtime_profile_next"] == "l4_debug"
    assert payload["recommended_action"] == "reduce_drive_io_then_rerun"
    assert "drive_io_status is slow" in payload["reasoning"]

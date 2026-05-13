"""
文件用途：验证 profiling 汇总到运行参数建议的映射合同。
File purpose: Validate mapping contracts from profiling summaries to runtime-parameter recommendations.
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


def test_runtime_parameter_recommendation_decreases_batch_under_memory_pressure(
    tmp_path: Path,
) -> None:
    """Validate high memory pressure leads to a smaller recommended batch size.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"
    output_json = runtime_profile_dir / "runtime_parameter_recommendation.json"

    _write_json(
        runtime_profile_dir / "gpu_runtime_summary.json",
        {
            "peak_memory_ratio": 0.95,
            "mean_gpu_util_percent": 82.0,
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
            "drive_io_status": "moderate",
        },
    )

    payload = recommend_runtime_parameters(
        run_root=run_root,
        output_json=output_json,
    )

    assert payload["recommended_batch_size_frames"] == 2
    assert payload["batch_size_direction"] == "decrease"
    assert payload["recommended_action"] == "rerun_with_smaller_batch_size_frames"
    assert output_json.exists()


def test_runtime_parameter_recommendation_flags_low_utilization_or_io(tmp_path: Path) -> None:
    """Validate low utilization recommends a larger batch or an IO investigation.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"
    output_json = runtime_profile_dir / "runtime_parameter_recommendation.json"

    _write_json(
        runtime_profile_dir / "gpu_runtime_summary.json",
        {
            "peak_memory_ratio": 0.30,
            "mean_gpu_util_percent": 25.0,
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
            "scale_label": "debug_small",
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
        output_json=output_json,
    )

    assert payload["recommended_batch_size_frames"] == 8
    assert payload["batch_size_direction"] == "increase_or_keep"
    assert payload["recommended_runtime_profile_next"] == "debug_real_video_or_smoke"
    assert payload["recommended_action"] == "reduce_drive_io_then_rerun"
    assert "drive_io_status is slow" in payload["reasoning"]


def test_runtime_parameter_recommendation_suggests_shards_for_very_long_runner(
    tmp_path: Path,
) -> None:
    """Validate very long runner timing recommends shard planning or a smaller smoke matrix.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"
    output_json = runtime_profile_dir / "runtime_parameter_recommendation.json"

    _write_json(
        runtime_profile_dir / "gpu_runtime_summary.json",
        {
            "peak_memory_ratio": 0.55,
            "mean_gpu_util_percent": 72.0,
        },
    )
    _write_json(
        runtime_profile_dir / "run_timing_summary.json",
        {
            "estimated_work_planning_label": "long_run",
            "events_by_name": {
                "real_video_vae_latent_runner": 28801.0,
            },
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
        output_json=output_json,
    )

    assert payload["recommended_gpu_tier"] == "A100_or_better"
    assert payload["recommended_runtime_profile_next"] == "debug_real_video_or_smoke"
    assert payload["recommended_action"] == "split_run_into_shards_or_reduce_attack_matrix_for_smoke"
    assert "real_video_vae_latent_runner exceeds 8 hours estimated runtime" in payload["reasoning"]

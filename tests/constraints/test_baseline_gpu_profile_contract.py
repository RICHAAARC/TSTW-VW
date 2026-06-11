"""验证 baseline GPU profiling 打包契约。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.baseline_gpu_profile import (
    BaselineGpuProfileSession,
    attach_gpu_profile_to_manifest,
    ensure_gpu_profile_trace_exists,
    required_gpu_profile_paths,
)

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_required_gpu_profile_paths_are_under_runtime_profile() -> None:
    """确认 GPU profiling 文件会进入 baseline 结果包的 runtime_profile 子目录。"""
    paths = required_gpu_profile_paths("external_videoseal")

    assert paths == [
        "runtime_profile/baseline_gpu_profiles/external_videoseal/gpu_runtime_trace.csv",
        "runtime_profile/baseline_gpu_profiles/external_videoseal/gpu_runtime_summary.json",
        "runtime_profile/baseline_gpu_profiles/external_videoseal/gpu_runtime_report.md",
        "runtime_profile/baseline_gpu_profiles/external_videoseal/gpu_runtime_profile_manifest.json",
    ]


def test_attach_gpu_profile_to_manifest_records_utilization_fields(tmp_path: Path) -> None:
    """确认 baseline manifest 会记录后续判断并行可行性所需的 GPU 利用率字段。"""
    run_root = tmp_path / "run_root"
    manifest_path = run_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"workflow_key": "baseline_comparison_gate", "baseline_name": "external_videoseal"}),
        encoding="utf-8",
    )
    session = BaselineGpuProfileSession(
        run_root=run_root,
        baseline_name="external_videoseal",
        enabled=False,
    )
    session.summary = {
        "profiling_status": "sampled",
        "gpu_name": "Fake GPU",
        "sample_count": 3,
        "usable_sample_count": 3,
        "peak_memory_used_mb": 4096.0,
        "peak_memory_ratio": 0.25,
        "mean_gpu_util_percent": 42.0,
        "median_gpu_util_percent": 40.0,
        "low_utilization_ratio": 0.67,
        "estimated_gpu_usage_status": "low_utilization",
        "recommended_batch_size_direction": "increase_or_check_io",
    }

    payload = attach_gpu_profile_to_manifest(manifest_path, session)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["estimated_gpu_usage_status"] == "low_utilization"
    assert manifest["gpu_profile"]["mean_gpu_util_percent"] == 42.0
    assert manifest["gpu_profile"]["peak_memory_ratio"] == 0.25
    assert manifest["gpu_profile"]["recommended_batch_size_direction"] == "increase_or_check_io"



def test_gpu_profile_trace_fallback_writes_unavailable_csv(tmp_path: Path) -> None:
    """确认 profiler 子进程失败时仍会留下可汇总的 unavailable trace。"""
    trace_csv = tmp_path / "runtime_profile" / "gpu_runtime_trace.csv"

    ensure_gpu_profile_trace_exists(
        trace_csv=trace_csv,
        baseline_name="external_videoseal",
    )

    text = trace_csv.read_text(encoding="utf-8")
    assert "event_tag" in text
    assert "external_videoseal" in text
    assert "unavailable" in text

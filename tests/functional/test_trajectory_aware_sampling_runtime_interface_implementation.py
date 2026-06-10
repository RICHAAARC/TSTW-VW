"""
文件用途: 验证 trajectory-aware sampling 的非后端连接版 runtime interface implementation。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.runtime_interface_implementation import (
    build_trajectory_aware_sampling_runtime_interface_implementation,
)

pytestmark = [pytest.mark.quick]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT
    / "configs"
    / "protocol"
    / "trajectory_aware_sampling_runtime_interface_implementation.json"
)


def _ready_scaffold() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingRuntimeInterfaceScaffoldDecision": "READY_FOR_REAL_GPU_RUNTIME_INTERFACE_IMPLEMENTATION",
        "NextAllowedConstructionAfterRuntimeInterfaceScaffold": "real_gpu_runtime_interface_implementation",
        "runtime_interface_scaffold_digest": "scaffold_digest",
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "request_prototypes": [
            {
                "request_id": "trajectory_replay_request_0000",
                "selected_record_digest": "record_digest",
                "event_id": "event_selected",
                "sample_id": "sample_selected",
                "method_variant": "tubelet_sync_trajectory_fusion",
                "attack_name": "local_clip",
                "selection_policy_kind": "trajectory_ranked_replay",
                "runtime_backend_connection_allowed": False,
                "real_generation_allowed": False,
                "real_watermark_integration_allowed": False,
            }
        ],
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_runtime_interface_implementation_builds_dry_run_manifests() -> None:
    """验证接口实现层只生成 dry-run 产物, 不打开真实后端。"""
    payload = build_trajectory_aware_sampling_runtime_interface_implementation(
        _ready_scaffold(),
        _config(),
        gpu_environment_override={
            "gpu_available": True,
            "cuda_available": True,
            "device_name": "test_gpu",
            "driver_version": "test_driver",
            "preflight_status": "available",
        },
    )

    assert (
        payload["TrajectoryAwareSamplingRuntimeInterfaceImplementationDecision"]
        == "READY_FOR_BACKEND_INTEGRATION_DECISION"
    )
    assert payload["TrajectoryAwareSamplingRuntimeInterfaceImplementationBlockingReasons"] == []
    assert payload["runtime_interface_implementation_allowed"] is True
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_generation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["dry_run_request_count"] == 1
    assert payload["dry_run_result_manifest_count"] == 1
    assert payload["gpu_preflight_summary"]["preflight_status"] == "available"
    assert payload["dry_run_requests"][0]["dry_run_only"] is True
    assert payload["dry_run_result_manifests"][0]["backend_status"] == "not_connected_by_governance"
    assert (
        payload["NextAllowedConstructionAfterRuntimeInterfaceImplementation"]
        == "backend_integration_decision"
    )


def test_runtime_interface_implementation_blocks_backend_enabled_scaffold() -> None:
    """验证如果上游 scaffold 误打开后端连接, implementation 会阻断。"""
    scaffold = _ready_scaffold()
    scaffold["runtime_backend_connection_allowed"] = True

    payload = build_trajectory_aware_sampling_runtime_interface_implementation(
        scaffold,
        _config(),
        gpu_environment_override={"gpu_available": False, "preflight_status": "unavailable"},
    )

    assert payload["TrajectoryAwareSamplingRuntimeInterfaceImplementationDecision"] == "INCONCLUSIVE"
    assert (
        "scaffold_enabled_runtime_backend_connection"
        in payload["TrajectoryAwareSamplingRuntimeInterfaceImplementationBlockingReasons"]
    )
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_generation_allowed"] is False


def test_runtime_interface_implementation_does_not_require_local_gpu_by_default() -> None:
    """验证本地 CPU 环境也能生成非后端连接版接口产物。"""
    payload = build_trajectory_aware_sampling_runtime_interface_implementation(
        _ready_scaffold(),
        _config(),
        gpu_environment_override={
            "gpu_available": False,
            "cuda_available": False,
            "device_name": "",
            "driver_version": "",
            "preflight_status": "unavailable",
        },
    )

    assert (
        payload["TrajectoryAwareSamplingRuntimeInterfaceImplementationDecision"]
        == "READY_FOR_BACKEND_INTEGRATION_DECISION"
    )
    assert payload["gpu_preflight_summary"]["preflight_status"] == "unavailable"
    assert payload["runtime_backend_connection_allowed"] is False

"""
文件用途: 验证 trajectory-aware sampling 的后端集成决策 gate。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.backend_integration_decision import (
    build_trajectory_aware_sampling_backend_integration_decision,
)

pytestmark = [pytest.mark.quick]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT
    / "configs"
    / "protocol"
    / "trajectory_aware_sampling_backend_integration_decision.json"
)


def _ready_implementation() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingRuntimeInterfaceImplementationDecision": "READY_FOR_BACKEND_INTEGRATION_DECISION",
        "NextAllowedConstructionAfterRuntimeInterfaceImplementation": "backend_integration_decision",
        "runtime_interface_implementation_digest": "implementation_digest",
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "dry_run_request_count": 1,
        "dry_run_result_manifest_count": 1,
        "gpu_preflight_summary": {
            "gpu_available": True,
            "cuda_available": True,
            "device_name": "test_gpu",
            "driver_version": "test_driver",
            "preflight_status": "available",
        },
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_backend_integration_decision_approves_adapter_scaffold_only() -> None:
    """验证 backend integration decision 只批准 adapter scaffold, 不打开真实后端。"""
    payload = build_trajectory_aware_sampling_backend_integration_decision(
        _ready_implementation(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingBackendIntegrationDecision"]
        == "READY_FOR_BACKEND_ADAPTER_SCAFFOLD"
    )
    assert payload["TrajectoryAwareSamplingBackendIntegrationDecisionBlockingReasons"] == []
    assert payload["backend_adapter_scaffold_allowed"] is True
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_generation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["dry_run_request_count"] == 1
    assert payload["dry_run_result_manifest_count"] == 1
    assert (
        payload["NextAllowedConstructionAfterBackendIntegrationDecision"]
        == "backend_adapter_scaffold"
    )


def test_backend_integration_decision_blocks_real_backend_enabled_input() -> None:
    """验证上游 implementation 如果误打开真实后端, 决策 gate 会阻断。"""
    implementation = _ready_implementation()
    implementation["runtime_backend_connection_allowed"] = True

    payload = build_trajectory_aware_sampling_backend_integration_decision(
        implementation,
        _config(),
    )

    assert payload["TrajectoryAwareSamplingBackendIntegrationDecision"] == "INCONCLUSIVE"
    assert (
        "implementation_enabled_runtime_backend_connection"
        in payload["TrajectoryAwareSamplingBackendIntegrationDecisionBlockingReasons"]
    )
    assert payload["backend_adapter_scaffold_allowed"] is False
    assert payload["runtime_backend_connection_allowed"] is False


def test_backend_integration_decision_requires_dry_run_manifests() -> None:
    """验证没有 dry-run 请求与结果 manifest 时不能推进后端 adapter scaffold。"""
    implementation = _ready_implementation()
    implementation["dry_run_request_count"] = 0
    implementation["dry_run_result_manifest_count"] = 0

    payload = build_trajectory_aware_sampling_backend_integration_decision(
        implementation,
        _config(),
    )

    assert payload["TrajectoryAwareSamplingBackendIntegrationDecision"] == "INCONCLUSIVE"
    assert "dry_run_request_count_below_minimum" in payload[
        "TrajectoryAwareSamplingBackendIntegrationDecisionBlockingReasons"
    ]
    assert "dry_run_result_manifest_count_below_minimum" in payload[
        "TrajectoryAwareSamplingBackendIntegrationDecisionBlockingReasons"
    ]

"""
文件用途: 验证外部真实 GPU backend connection smoke 结果 gate。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.real_gpu_backend_connection_smoke_result_gate import (
    build_trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate,
)

pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate.json"


def _ready_handoff() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffDecision": "READY_FOR_EXTERNAL_REAL_GPU_SMOKE_RUN",
        "NextRequiredExternalExecutionAfterSmokeHandoff": "real_gpu_backend_connection_smoke",
        "external_gpu_required": True,
        "runtime_backend_connection_allowed": False,
        "real_backend_connection_smoke_handoff_digest": "handoff_digest",
    }


def _passing_external_results() -> dict[str, object]:
    kinds = [
        "runtime_environment_snapshot",
        "model_identity_record",
        "backend_dependency_resolution_record",
        "single_request_execution_record",
        "runtime_failure_manifest",
    ]
    return {
        "external_smoke_result_status": "PASS",
        "external_gpu_runtime_detected": True,
        "external_model_identity_recorded": True,
        "external_backend_dependencies_resolved": True,
        "external_real_backend_connection_attempted": True,
        "external_real_backend_connection_succeeded": True,
        "external_real_generation_attempted": False,
        "external_real_watermark_integration_attempted": False,
        "runtime_failure_manifest": {
            "failure_manifest_recorded": True,
            "failure_count": 0,
        },
        "result_artifacts": [
            {
                "result_artifact_kind": kind,
                "result_artifact_status": "present",
                "formal_claim_support_allowed": False,
            }
            for kind in kinds
        ],
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_real_gpu_backend_connection_smoke_result_gate_passes_complete_external_results() -> None:
    """验证外部真实 GPU smoke 结果完整时, gate 允许进入下一构建层。"""
    payload = build_trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate(
        _ready_handoff(),
        _passing_external_results(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateDecision"]
        == "PASS"
    )
    assert payload["TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateBlockingReasons"] == []
    assert payload["external_gpu_runtime_detected"] is True
    assert payload["external_real_backend_connection_attempted"] is True
    assert payload["external_real_backend_connection_succeeded"] is True
    assert payload["external_real_generation_attempted"] is False
    assert payload["external_real_watermark_integration_attempted"] is False
    assert payload["observed_result_artifact_count"] == 5
    assert payload["missing_required_result_artifact_kinds"] == []
    assert (
        payload["NextAllowedConstructionAfterRealGpuBackendConnectionSmokeResultGate"]
        == "real_backend_runtime_validation_gate"
    )


def test_real_gpu_backend_connection_smoke_result_gate_blocks_missing_artifact() -> None:
    """验证缺少任一必需结果 artifact 时, gate 不允许继续推进。"""
    results = _passing_external_results()
    results["result_artifacts"] = results["result_artifacts"][:-1]

    payload = build_trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate(
        _ready_handoff(),
        results,
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateDecision"]
        == "INCONCLUSIVE"
    )
    assert "missing_required_external_smoke_result_artifacts" in payload[
        "TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateBlockingReasons"
    ]
    assert payload["missing_required_result_artifact_kinds"] == ["runtime_failure_manifest"]


def test_real_gpu_backend_connection_smoke_result_gate_blocks_real_generation_attempt() -> None:
    """验证 smoke 过程中如果尝试真实生成视频, gate 会阻断继续推进。"""
    results = _passing_external_results()
    results["external_real_generation_attempted"] = True

    payload = build_trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate(
        _ready_handoff(),
        results,
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateDecision"]
        == "INCONCLUSIVE"
    )
    assert "external_real_generation_attempted_unexpectedly" in payload[
        "TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateBlockingReasons"
    ]


def test_real_gpu_backend_connection_smoke_result_gate_blocks_unready_handoff() -> None:
    """验证 handoff 未准备完成时, 即使外部结果看似完整也不能继续推进。"""
    handoff = _ready_handoff()
    handoff["TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffDecision"] = "INCONCLUSIVE"

    payload = build_trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate(
        handoff,
        _passing_external_results(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateDecision"]
        == "INCONCLUSIVE"
    )
    assert "real_gpu_smoke_handoff_not_ready" in payload[
        "TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateBlockingReasons"
    ]

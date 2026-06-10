
"""
文件用途: 验证 trajectory-aware sampling 手动单请求结果 gate.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.manual_controlled_single_request_result_gate import (
    build_trajectory_aware_sampling_manual_controlled_single_request_result_gate,
)

pytestmark = [pytest.mark.quick]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_manual_controlled_single_request_result_gate.json"


def _ready_scaffold() -> dict[str, object]:
    request_descriptor = {
        "controlled_request_id": "controlled_real_generation_request_0000",
        "controlled_request_digest": "request_digest",
        "real_generation_execution_allowed": False,
        "real_watermark_integration_allowed": False,
    }
    return {
        "TrajectoryAwareSamplingControlledSingleRealGenerationRequestScaffoldDecision": "READY_FOR_MANUAL_CONTROLLED_REAL_GENERATION_REQUEST_RUN",
        "NextRequiredExternalExecutionAfterControlledSingleRequestScaffold": "manual_controlled_single_real_generation_request_run",
        "controlled_request_scaffold_ready": True,
        "manual_gpu_execution_required": True,
        "request_descriptor": request_descriptor,
        "controlled_single_real_generation_request_scaffold_digest": "scaffold_digest",
    }


def _passing_external_results() -> dict[str, object]:
    artifact_kinds = [
        "runtime_environment_snapshot",
        "model_identity_record",
        "controlled_single_request_result_record",
        "runtime_failure_manifest",
    ]
    return {
        "manual_controlled_single_request_result_status": "PASS",
        "controlled_request_digest": "request_digest",
        "external_gpu_runtime_detected": True,
        "external_model_identity_recorded": True,
        "controlled_single_request_result_recorded": True,
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
            for kind in artifact_kinds
        ],
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_manual_controlled_single_request_result_gate_passes_complete_non_claim_results() -> None:
    """验证外部结果完整且未执行真实生成时, gate 可以进入后续显式授权决策."""
    payload = build_trajectory_aware_sampling_manual_controlled_single_request_result_gate(
        _ready_scaffold(),
        _passing_external_results(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision"]
        == "PASS"
    )
    assert payload["TrajectoryAwareSamplingManualControlledSingleRequestResultGateBlockingReasons"] == []
    assert payload["external_real_generation_attempted"] is False
    assert payload["real_generation_execution_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["formal_claim_support_allowed"] is False
    assert payload["missing_required_result_artifact_kinds"] == []
    assert (
        payload["NextAllowedConstructionAfterManualControlledSingleRequestResultGate"]
        == "governed_real_generation_execution_authorization_decision"
    )


def test_manual_controlled_single_request_result_gate_blocks_digest_mismatch() -> None:
    """验证外部结果没有绑定同一条受控请求 digest 时会被阻断."""
    results = _passing_external_results()
    results["controlled_request_digest"] = "other_request_digest"

    payload = build_trajectory_aware_sampling_manual_controlled_single_request_result_gate(
        _ready_scaffold(),
        results,
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision"]
        == "INCONCLUSIVE"
    )
    assert "controlled_request_digest_mismatch" in payload[
        "TrajectoryAwareSamplingManualControlledSingleRequestResultGateBlockingReasons"
    ]


def test_manual_controlled_single_request_result_gate_blocks_unauthorized_real_generation() -> None:
    """验证当前阶段如果外部结果已经尝试真实生成, gate 会阻断继续推进."""
    results = _passing_external_results()
    results["external_real_generation_attempted"] = True

    payload = build_trajectory_aware_sampling_manual_controlled_single_request_result_gate(
        _ready_scaffold(),
        results,
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision"]
        == "INCONCLUSIVE"
    )
    assert "external_real_generation_attempted_without_authorization" in payload[
        "TrajectoryAwareSamplingManualControlledSingleRequestResultGateBlockingReasons"
    ]

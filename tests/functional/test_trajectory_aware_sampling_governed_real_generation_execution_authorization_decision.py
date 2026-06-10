
"""
文件用途: 验证 trajectory-aware sampling 的真实生成执行授权决策.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.governed_real_generation_execution_authorization_decision import (
    build_trajectory_aware_sampling_governed_real_generation_execution_authorization_decision,
)

pytestmark = [pytest.mark.quick]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_governed_real_generation_execution_authorization_decision.json"


def _passing_manual_result_gate() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision": "PASS",
        "NextAllowedConstructionAfterManualControlledSingleRequestResultGate": "governed_real_generation_execution_authorization_decision",
        "controlled_request_digest": "request_digest",
        "external_gpu_runtime_detected": True,
        "external_model_identity_recorded": True,
        "controlled_single_request_result_recorded": True,
        "external_real_watermark_integration_attempted": False,
        "formal_claim_support_allowed": False,
        "manual_controlled_single_request_result_gate_digest": "manual_gate_digest",
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_authorization_decision_blocks_real_generation_under_current_stage_contract() -> None:
    """验证当前阶段契约未允许真实生成时, 授权决策必须保持未授权状态."""
    payload = build_trajectory_aware_sampling_governed_real_generation_execution_authorization_decision(
        _passing_manual_result_gate(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationDecision"]
        == "REAL_GENERATION_EXECUTION_NOT_AUTHORIZED_CURRENT_STAGE_CONTRACT"
    )
    assert "current_stage_contract_disallows_real_generation_execution" in payload[
        "TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationBlockingReasons"
    ]
    assert payload["real_generation_execution_authorized"] is False
    assert payload["controlled_real_generation_execution_handoff_allowed"] is False
    assert payload["real_watermark_integration_authorized"] is False
    assert payload["formal_claim_support_authorized"] is False
    assert (
        payload["required_governance_action_before_real_generation_execution"]
        == "project_contract_update_for_controlled_real_generation_execution"
    )


def test_authorization_decision_blocks_unpassed_manual_result_gate() -> None:
    """验证手动单请求结果 gate 未通过时, 授权决策不能继续推进."""
    gate = _passing_manual_result_gate()
    gate["TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision"] = "INCONCLUSIVE"

    payload = build_trajectory_aware_sampling_governed_real_generation_execution_authorization_decision(
        gate,
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationDecision"]
        == "REAL_GENERATION_EXECUTION_NOT_AUTHORIZED_CURRENT_STAGE_CONTRACT"
    )
    assert "manual_controlled_single_request_result_gate_not_pass" in payload[
        "TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationBlockingReasons"
    ]


def test_authorization_decision_can_describe_future_handoff_only_when_config_explicitly_allows() -> None:
    """验证未来只有在配置显式允许时, 决策才会进入外部执行 handoff 状态."""
    config = _config()
    config["current_stage_contract_allows_real_generation_execution"] = True

    payload = build_trajectory_aware_sampling_governed_real_generation_execution_authorization_decision(
        _passing_manual_result_gate(),
        config,
    )

    assert (
        payload["TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationDecision"]
        == "READY_FOR_EXTERNAL_CONTROLLED_REAL_GENERATION_EXECUTION_HANDOFF"
    )
    assert payload["real_generation_execution_authorized"] is True
    assert payload["controlled_real_generation_execution_handoff_allowed"] is True
    assert payload["real_watermark_integration_authorized"] is False
    assert payload["formal_claim_support_authorized"] is False

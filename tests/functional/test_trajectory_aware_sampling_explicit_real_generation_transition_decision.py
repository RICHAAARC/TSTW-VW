"""
文件用途: 验证 trajectory-aware sampling 的显式真实生成切换决策.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.explicit_real_generation_transition_decision import (
    build_trajectory_aware_sampling_explicit_real_generation_transition_decision,
)


pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]


def _read_config() -> dict[str, object]:
    return json.loads(
        (
            ROOT
            / "configs"
            / "protocol"
            / "trajectory_aware_sampling_explicit_real_generation_transition_decision.json"
        ).read_text(encoding="utf-8")
    )


def _passing_runtime_validation_gate() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingRealBackendRuntimeValidationGateDecision": "PASS",
        "NextAllowedConstructionAfterRealBackendRuntimeValidationGate": "explicit_real_generation_transition_decision",
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "controlled_real_generation_request_allowed": False,
        "real_backend_runtime_validation_gate_digest": "runtime_validation_digest",
    }


def test_explicit_real_generation_transition_decision_allows_scaffold_only() -> None:
    """验证通过 runtime validation 后只允许进入单请求 scaffold, 不执行真实生成."""
    payload = build_trajectory_aware_sampling_explicit_real_generation_transition_decision(
        _passing_runtime_validation_gate(),
        _read_config(),
    )

    assert (
        payload["TrajectoryAwareSamplingExplicitRealGenerationTransitionDecision"]
        == "READY_FOR_CONTROLLED_SINGLE_REAL_GENERATION_REQUEST_SCAFFOLD"
    )
    assert payload["controlled_request_scaffold_allowed"] is True
    assert payload["controlled_real_generation_request_allowed"] is False
    assert payload["real_generation_execution_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["maximum_controlled_request_count"] == 1
    assert payload["formal_claim_support_allowed"] is False
    assert (
        payload["NextAllowedConstructionAfterExplicitRealGenerationTransitionDecision"]
        == "controlled_single_real_generation_request_scaffold"
    )


def test_explicit_real_generation_transition_decision_blocks_failed_runtime_gate() -> None:
    """验证 runtime validation 未通过时不会允许后续单请求 scaffold."""
    runtime_gate = _passing_runtime_validation_gate()
    runtime_gate[
        "TrajectoryAwareSamplingRealBackendRuntimeValidationGateDecision"
    ] = "INCONCLUSIVE"

    payload = build_trajectory_aware_sampling_explicit_real_generation_transition_decision(
        runtime_gate,
        _read_config(),
    )

    assert (
        payload["TrajectoryAwareSamplingExplicitRealGenerationTransitionDecision"]
        == "INCONCLUSIVE"
    )
    assert "real_backend_runtime_validation_gate_not_pass" in payload[
        "TrajectoryAwareSamplingExplicitRealGenerationTransitionBlockingReasons"
    ]
    assert payload["controlled_request_scaffold_allowed"] is False

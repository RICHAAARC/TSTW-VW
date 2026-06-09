"""
文件用途：验证 trajectory-aware sampling probe 的 readiness gate 语义。
File purpose: Validate readiness-gate semantics for the trajectory-aware sampling probe.
Module type: General module
"""

from __future__ import annotations

import pytest

from experiments.trajectory_aware_sampling_probe.readiness_audit import (
    build_trajectory_aware_sampling_readiness_decision,
)


pytestmark = [pytest.mark.quick]


def _passed_trajectory_decision() -> dict[str, object]:
    return {
        "Stage2DependencyStatus": "PASSED",
        "Stage3ImplementationDecision": "PASS",
        "Stage3MechanismDecision": "PASS",
        "NextAllowedStageByTrajectory": "trajectory_aware_sampling_probe",
    }


def _sampling_config() -> dict[str, object]:
    return {
        "construction_phase": "trajectory_aware_sampling_probe",
        "required_next_allowed_stage": "trajectory_aware_sampling_probe",
        "selected_sampling_policy_kind": "trajectory_ranked_replay",
        "allowed_sampling_policy_kinds": [
            "trajectory_ranked_replay",
            "control_balanced_replay",
        ],
        "enabled_runtime_capabilities": [
            "stage3_decision_readback",
            "record_digest_selection_plan",
        ],
    }


def test_sampling_readiness_passes_after_formal_trajectory_gate() -> None:
    """验证阶段 3 正式 PASS 后, 下一阶段 readiness gate 可以通过。"""
    decision = build_trajectory_aware_sampling_readiness_decision(
        _passed_trajectory_decision(),
        _sampling_config(),
    )

    assert decision["SamplingReadinessDecision"] == "PASS"
    assert decision["TrajectoryAwareSamplingBlockingReasons"] == []
    assert decision["UpstreamTrajectoryMechanismDecision"] == "PASS"
    assert decision["UpstreamStage2DependencyStatus"] == "PASSED"
    assert decision["selected_sampling_policy_kind"] == "trajectory_ranked_replay"
    assert decision["NextAllowedStageBySampling"] == "full_paper_protocol"


def test_sampling_readiness_blocks_unfinished_trajectory_gate() -> None:
    """验证阶段 3 未通过时不能进入 sampling 构建。"""
    upstream_decision = _passed_trajectory_decision()
    upstream_decision["Stage3MechanismDecision"] = "INCONCLUSIVE"

    decision = build_trajectory_aware_sampling_readiness_decision(
        upstream_decision,
        _sampling_config(),
    )

    assert decision["SamplingReadinessDecision"] == "INCONCLUSIVE"
    assert "stage3_mechanism_not_passed" in decision["TrajectoryAwareSamplingBlockingReasons"]
    assert decision["NextAllowedStageBySampling"] == "finish_trajectory_aware_sampling_probe"


def test_sampling_readiness_blocks_real_generation_capability() -> None:
    """验证当前 scaffold 显式阻断真实生成能力。"""
    sampling_config = _sampling_config()
    sampling_config["enabled_runtime_capabilities"] = [
        "stage3_decision_readback",
        "real_dit_generation",
    ]

    decision = build_trajectory_aware_sampling_readiness_decision(
        _passed_trajectory_decision(),
        sampling_config,
    )

    assert decision["SamplingReadinessDecision"] == "INCONCLUSIVE"
    assert "forbidden_runtime_capability_enabled" in decision["TrajectoryAwareSamplingBlockingReasons"]


def test_sampling_readiness_blocks_unknown_policy() -> None:
    """验证采样策略必须来自受治理 allowlist。"""
    sampling_config = _sampling_config()
    sampling_config["selected_sampling_policy_kind"] = "unregistered_policy"

    decision = build_trajectory_aware_sampling_readiness_decision(
        _passed_trajectory_decision(),
        sampling_config,
    )

    assert decision["SamplingReadinessDecision"] == "INCONCLUSIVE"
    assert "sampling_policy_kind_not_allowed" in decision["TrajectoryAwareSamplingBlockingReasons"]

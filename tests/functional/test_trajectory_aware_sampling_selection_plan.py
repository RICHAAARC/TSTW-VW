"""
文件用途: 验证 trajectory-aware sampling 的记录摘要选择计划。
Module type: General module
"""

from __future__ import annotations

import pytest

from experiments.trajectory_aware_sampling_probe.selection_plan_builder import (
    build_record_digest_selection_plan,
)

pytestmark = [pytest.mark.quick]


def _passed_trajectory_decision() -> dict[str, object]:
    return {
        "Stage2DependencyStatus": "PASSED",
        "Stage3ImplementationDecision": "PASS",
        "Stage3MechanismDecision": "PASS",
        "NextAllowedStageByTrajectory": "trajectory_aware_sampling_probe",
    }


def _sampling_config(policy_kind: str = "trajectory_ranked_replay") -> dict[str, object]:
    return {
        "construction_phase": "trajectory_aware_sampling_probe",
        "required_next_allowed_stage": "trajectory_aware_sampling_probe",
        "selected_sampling_policy_kind": policy_kind,
        "allowed_sampling_policy_kinds": [
            "trajectory_ranked_replay",
            "control_balanced_replay",
        ],
        "enabled_runtime_capabilities": [
            "stage3_decision_readback",
            "record_digest_selection_plan",
        ],
    }


def _record(
    *,
    event_id: str,
    sample_id: str,
    sample_role: str,
    method_variant: str,
    s_traj: float,
    s_final: float,
    control_score: float,
) -> dict[str, object]:
    return {
        "run_id": "run_formal",
        "event_id": event_id,
        "sample_id": sample_id,
        "split": "test",
        "sample_role": sample_role,
        "method_variant": method_variant,
        "attack_name": "temporal_crop",
        "evidence_scores": {
            "S_traj": s_traj,
            "S_final": s_final,
        },
        "mechanism_trace": {
            "trajectory_control_scores": {
                "permuted_time": control_score,
            },
            "trajectory_runtime_ms": 10.0,
        },
        "decision": True,
    }


def _records() -> list[dict[str, object]]:
    return [
        _record(
            event_id="event_low",
            sample_id="sample_low",
            sample_role="attacked_positive",
            method_variant="tubelet_traj",
            s_traj=0.2,
            s_final=0.1,
            control_score=0.01,
        ),
        _record(
            event_id="event_high",
            sample_id="sample_high",
            sample_role="attacked_positive",
            method_variant="tubelet_sync_trajectory_fusion",
            s_traj=0.8,
            s_final=0.3,
            control_score=0.02,
        ),
        _record(
            event_id="event_negative",
            sample_id="sample_negative",
            sample_role="attacked_negative",
            method_variant="tubelet_traj",
            s_traj=0.4,
            s_final=-0.2,
            control_score=0.5,
        ),
    ]


def test_selection_plan_builds_deterministic_trajectory_ranked_records() -> None:
    """验证 trajectory_ranked_replay 只生成 record digest 清单且排序稳定。"""
    first_plan = build_record_digest_selection_plan(
        _records(),
        _passed_trajectory_decision(),
        _sampling_config("trajectory_ranked_replay"),
        selected_record_limit=2,
    )
    second_plan = build_record_digest_selection_plan(
        _records(),
        _passed_trajectory_decision(),
        _sampling_config("trajectory_ranked_replay"),
        selected_record_limit=2,
    )

    assert first_plan == second_plan
    assert first_plan["SamplingSelectionPlanDecision"] == "PASS"
    assert first_plan["selection_output_kind"] == "record_digest_selection_plan"
    assert first_plan["selected_record_count"] == 2
    assert first_plan["selected_records"][0]["event_id"] == "event_high"
    assert first_plan["selected_records"][0]["record_digest"]
    assert first_plan["real_generation_allowed"] is False
    assert first_plan["real_watermark_integration_allowed"] is False
    assert first_plan["requires_real_gpu_validation"] is False


def test_selection_plan_supports_control_balanced_policy() -> None:
    """验证 control_balanced_replay 能优先暴露 control score 较强的对照记录。"""
    plan = build_record_digest_selection_plan(
        _records(),
        _passed_trajectory_decision(),
        _sampling_config("control_balanced_replay"),
        selected_record_limit=3,
    )

    assert plan["SamplingSelectionPlanDecision"] == "PASS"
    assert plan["selected_sampling_policy_kind"] == "control_balanced_replay"
    assert plan["selected_record_count"] == 3
    assert plan["policy_sections"]["control_balanced_replay"]["candidate_record_count"] == 3
    assert any(
        record["sample_role"] == "attacked_negative"
        for record in plan["selected_records"]
    )


def test_selection_plan_blocks_when_readiness_is_inconclusive() -> None:
    """验证上游机制未通过时不会产生 selected records。"""
    upstream_decision = _passed_trajectory_decision()
    upstream_decision["Stage3MechanismDecision"] = "INCONCLUSIVE"

    plan = build_record_digest_selection_plan(
        _records(),
        upstream_decision,
        _sampling_config(),
    )

    assert plan["SamplingSelectionPlanDecision"] == "INCONCLUSIVE"
    assert plan["SamplingReadinessDecision"] == "INCONCLUSIVE"
    assert plan["selected_record_count"] == 0
    assert plan["selected_records"] == []
    assert "stage3_mechanism_not_passed" in plan["SamplingSelectionBlockingReasons"]


def test_selection_plan_blocks_forbidden_generation_capability() -> None:
    """验证选择计划继续继承真实生成能力禁用规则。"""
    config = _sampling_config()
    config["enabled_runtime_capabilities"] = [
        "stage3_decision_readback",
        "real_video_generation",
    ]

    plan = build_record_digest_selection_plan(
        _records(),
        _passed_trajectory_decision(),
        config,
    )

    assert plan["SamplingSelectionPlanDecision"] == "INCONCLUSIVE"
    assert plan["selected_record_count"] == 0
    assert "forbidden_runtime_capability_enabled" in plan["SamplingSelectionBlockingReasons"]
    assert plan["real_generation_allowed"] is False

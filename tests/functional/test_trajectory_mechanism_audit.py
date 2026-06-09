"""
文件用途：验证阶段 3 trajectory mechanism audit 的基本决策语义。
File purpose: Validate the basic decision semantics of the stage-three trajectory mechanism audit.
Module type: General module
"""

from __future__ import annotations

import pytest

from experiments.trajectory_statistic_probe.mechanism_audit import (
    build_stage3_mechanism_decision,
)


pytestmark = [pytest.mark.quick]


def _build_record(
    method_variant: str,
    sample_role: str,
    attack_name: str,
    S_traj: float | None,
    trajectory_source_kind: str = "latent_interpolation_surrogate",
) -> dict[str, object]:
    source_kind = None if S_traj is None else trajectory_source_kind
    return {
        "run_id": "trajectory_probe_run",
        "split": "test",
        "method_variant": method_variant,
        "sample_role": sample_role,
        "attack_name": attack_name,
        "decision": bool(S_traj and S_traj > 0.0),
        "evidence_scores": {
            "S_tubelet": 0.1,
            "S_sync": 0.2,
            "S_traj": S_traj,
            "S_final": 0.2 if S_traj is None else 0.3,
        },
        "mechanism_trace": {
            "trajectory_source_kind": source_kind,
            "formal_trajectory_source_status": (
                None
                if S_traj is None
                else "candidate_ready"
                if source_kind == "stage2_frozen_endpoint_replay"
                else "not_formal_source"
            ),
            "trajectory_source_provenance_digest": (
                "stage2_manifest_digest"
                if source_kind == "stage2_frozen_endpoint_replay"
                else None
            ),
            "trajectory_statistic_kind": None if S_traj is None else "velocity_projection",
            "trajectory_time_grid": None if S_traj is None else [0.0, 0.5, 1.0],
            "trajectory_control_scores": {
                "traj_time_reversed": -0.1,
            },
            "trajectory_runtime_ms": 1.0,
        },
    }


def test_stage3_mechanism_audit_records_not_passed_dependency() -> None:
    """Validate that stage-three mechanism audit remains deferred by stage two.

    Args:
        None.

    Returns:
        None.
    """
    event_score_records = [
        _build_record("tubelet_only", "attacked_positive", "temporal_crop", None),
        _build_record("tubelet_sync", "attacked_positive", "temporal_crop", None),
        _build_record("traj_only", "attacked_positive", "temporal_crop", 0.4),
        _build_record("tubelet_traj", "attacked_positive", "temporal_crop", 0.5),
        _build_record(
            "tubelet_sync_trajectory_fusion",
            "attacked_positive",
            "temporal_crop",
            0.6,
        ),
    ]
    runtime_method_configs = [
        {"method_variant": "tubelet_only", "enable_trajectory": False},
        {"method_variant": "tubelet_sync", "enable_trajectory": False},
        {"method_variant": "traj_only", "enable_trajectory": True},
        {"method_variant": "tubelet_traj", "enable_trajectory": True},
        {"method_variant": "tubelet_sync_trajectory_fusion", "enable_trajectory": True},
    ]

    decision = build_stage3_mechanism_decision(
        event_score_records,
        threshold_records=[{"threshold_id": "threshold"}],
        runtime_method_configs=runtime_method_configs,
    )

    assert decision["Stage3ImplementationDecision"] == "PASS"
    assert decision["Stage3MechanismDecision"] == "INCONCLUSIVE"
    assert decision["Stage2DependencyStatus"] == "NOT_PASSED"
    assert "stage2_dependency_not_passed" in decision["Stage3MechanismBlockingReasons"]
    assert "surrogate_source_not_sufficient" in decision["Stage3MechanismBlockingReasons"]
    assert decision["NextAllowedStageByTrajectory"] == "finish_stage2_first"


def test_stage3_mechanism_audit_fails_when_enabled_variant_lacks_s_traj() -> None:
    """Validate that implementation fails when a trajectory-enabled variant misses `S_traj`.

    Args:
        None.

    Returns:
        None.
    """
    decision = build_stage3_mechanism_decision(
        event_score_records=[
            _build_record("traj_only", "attacked_positive", "temporal_crop", None),
        ],
        threshold_records=[{"threshold_id": "threshold"}],
        runtime_method_configs=[
            {"method_variant": "traj_only", "enable_trajectory": True},
        ],
    )

    assert decision["Stage3ImplementationDecision"] == "FAIL"
    assert "s_traj_missing_for_trajectory_enabled_variant" in decision["BlockingReasons"]
    assert decision["Stage3MechanismDecision"] == "INCONCLUSIVE"


def test_stage3_mechanism_audit_uses_passed_frozen_baseline_but_blocks_surrogate_pass() -> None:
    """验证冻结 baseline 通过时实现可 PASS, 但 surrogate trajectory 不允许机制 PASS。"""
    event_score_records = [
        _build_record("tubelet_only", "attacked_positive", "temporal_crop", None),
        _build_record("tubelet_sync", "attacked_positive", "temporal_crop", None),
        _build_record("traj_only", "attacked_positive", "temporal_crop", 0.4),
        _build_record("tubelet_traj", "attacked_positive", "temporal_crop", 0.5),
        _build_record(
            "tubelet_sync_trajectory_fusion",
            "attacked_positive",
            "temporal_crop",
            0.6,
        ),
    ]

    decision = build_stage3_mechanism_decision(
        event_score_records,
        threshold_records=[{"threshold_id": "threshold"}],
        runtime_method_configs=[
            {"method_variant": "tubelet_only", "enable_trajectory": False},
            {"method_variant": "tubelet_sync", "enable_trajectory": False},
            {"method_variant": "traj_only", "enable_trajectory": True},
            {"method_variant": "tubelet_traj", "enable_trajectory": True},
            {"method_variant": "tubelet_sync_trajectory_fusion", "enable_trajectory": True},
        ],
        frozen_baseline_manifest={"Stage2DependencyStatus": "PASSED"},
        trajectory_backend_config={
            "trajectory_source_kind": "latent_interpolation_surrogate",
        },
    )

    assert decision["Stage3ImplementationDecision"] == "PASS"
    assert decision["Stage2DependencyStatus"] == "PASSED"
    assert decision["Stage3MechanismDecision"] == "INCONCLUSIVE"
    assert "surrogate_source_not_sufficient" in decision["Stage3MechanismBlockingReasons"]


def test_stage3_mechanism_audit_accepts_formal_source_candidate_but_requires_validation() -> None:
    """验证 formal source candidate 可接入, 但仍不能跳过机制验证直接 PASS。"""
    event_score_records = [
        _build_record("tubelet_only", "attacked_positive", "temporal_crop", None),
        _build_record("tubelet_sync", "attacked_positive", "temporal_crop", None),
        _build_record(
            "traj_only",
            "attacked_positive",
            "temporal_crop",
            0.4,
            trajectory_source_kind="stage2_frozen_endpoint_replay",
        ),
        _build_record(
            "tubelet_traj",
            "attacked_positive",
            "temporal_crop",
            0.5,
            trajectory_source_kind="stage2_frozen_endpoint_replay",
        ),
        _build_record(
            "tubelet_sync_trajectory_fusion",
            "attacked_positive",
            "temporal_crop",
            0.6,
            trajectory_source_kind="stage2_frozen_endpoint_replay",
        ),
    ]
    for record in event_score_records:
        if record["mechanism_trace"]["trajectory_source_kind"] == "stage2_frozen_endpoint_replay":
            record["mechanism_trace"]["trajectory_control_scores"] = {
                "traj_time_reversed": 2.0,
            }

    decision = build_stage3_mechanism_decision(
        event_score_records,
        threshold_records=[{"threshold_id": "threshold"}],
        runtime_method_configs=[
            {"method_variant": "tubelet_only", "enable_trajectory": False},
            {"method_variant": "tubelet_sync", "enable_trajectory": False},
            {"method_variant": "traj_only", "enable_trajectory": True},
            {"method_variant": "tubelet_traj", "enable_trajectory": True},
            {"method_variant": "tubelet_sync_trajectory_fusion", "enable_trajectory": True},
        ],
        frozen_baseline_manifest={"Stage2DependencyStatus": "PASSED"},
        trajectory_backend_config={
            "trajectory_source_kind": "stage2_frozen_endpoint_replay",
        },
    )

    assert decision["Stage3ImplementationDecision"] == "PASS"
    assert decision["Stage2DependencyStatus"] == "PASSED"
    assert decision["trajectory_source_kind"] == "stage2_frozen_endpoint_replay"
    assert decision["formal_trajectory_source_status"] == "candidate_ready"
    assert decision["Stage3MechanismDecision"] == "INCONCLUSIVE"
    assert "surrogate_source_not_sufficient" not in decision["Stage3MechanismBlockingReasons"]
    assert decision["TrajectoryMechanismGateSummary"]["trajectory_control_gate"] == "FAIL"
    assert (
        "formal_source_candidate_requires_mechanism_validation"
        in decision["Stage3MechanismBlockingReasons"]
    )


def test_stage3_mechanism_audit_accepts_margin_gain_when_baseline_tpr_is_saturated() -> None:
    """验证 baseline TPR 饱和时, 正样本分数裕量增益可以支撑 gain gate。"""
    event_score_records = []
    runtime_method_configs = [
        {"method_variant": "tubelet_only", "enable_trajectory": False},
        {"method_variant": "tubelet_sync", "enable_trajectory": False},
        {"method_variant": "tubelet_traj", "enable_trajectory": True},
        {"method_variant": "tubelet_sync_trajectory_fusion", "enable_trajectory": True},
    ]
    threshold_records = [
        {
            "method_variant": "tubelet_only",
            "threshold_value": 0.5,
            "target_fpr": 0.001,
            "runtime_profile": "formal",
        },
        {
            "method_variant": "tubelet_sync",
            "threshold_value": 0.5,
            "target_fpr": 0.001,
            "runtime_profile": "formal",
        },
        {
            "method_variant": "tubelet_traj",
            "threshold_value": 0.5,
            "target_fpr": 0.001,
            "runtime_profile": "formal",
        },
        {
            "method_variant": "tubelet_sync_trajectory_fusion",
            "threshold_value": 0.5,
            "target_fpr": 0.001,
            "runtime_profile": "formal",
        },
    ]
    for index in range(2):
        sample_id = f"positive_{index}"
        for method_variant, score, s_traj in (
            ("tubelet_only", 0.7, None),
            ("tubelet_sync", 0.7, None),
            ("tubelet_traj", 0.9, 0.4),
            ("tubelet_sync_trajectory_fusion", 0.85, 0.3),
        ):
            event_score_records.append(
                _build_margin_record(
                    method_variant=method_variant,
                    sample_id=sample_id,
                    sample_role="attacked_positive",
                    s_final=score,
                    s_traj=s_traj,
                    decision=True,
                )
            )
    for index in range(2):
        sample_id = f"negative_{index}"
        for method_variant, s_traj in (
            ("tubelet_only", None),
            ("tubelet_sync", None),
            ("tubelet_traj", -0.1),
            ("tubelet_sync_trajectory_fusion", -0.1),
        ):
            event_score_records.append(
                _build_margin_record(
                    method_variant=method_variant,
                    sample_id=sample_id,
                    sample_role="attacked_negative",
                    s_final=0.1,
                    s_traj=s_traj,
                    decision=False,
                )
            )

    decision = build_stage3_mechanism_decision(
        event_score_records,
        threshold_records=threshold_records,
        runtime_method_configs=runtime_method_configs,
        frozen_baseline_manifest={"Stage2DependencyStatus": "PASSED"},
        trajectory_backend_config={
            "trajectory_source_kind": "stage2_frozen_endpoint_replay",
            "max_trajectory_runtime_ms": 10.0,
        },
    )

    assert decision["TrajectoryGainSummary"]["max_delta_traj"] == 0.0
    assert decision["TrajectoryGainSummary"]["max_positive_margin_delta_traj"] > 0.0
    assert decision["TrajectoryMechanismGateSummary"]["trajectory_gain_gate"] == "PASS"
    assert (
        decision["TrajectoryMechanismGateSummary"]["trajectory_negative_leakage_gate"]
        == "PASS"
    )
    assert decision["TrajectoryMechanismGateSummary"]["trajectory_control_gate"] == "PASS"
    assert decision["TrajectoryMechanismGateSummary"]["trajectory_runtime_gate"] == "PASS"
    assert (
        decision["TrajectoryMechanismGateSummary"][
            "trajectory_formal_runtime_profile_gate"
        ]
        == "PASS"
    )
    assert decision["Stage3MechanismDecision"] == "PASS"


def _build_margin_record(
    *,
    method_variant: str,
    sample_id: str,
    sample_role: str,
    s_final: float,
    s_traj: float | None,
    decision: bool,
) -> dict[str, object]:
    source_kind = None if s_traj is None else "stage2_frozen_endpoint_replay"
    return {
        "run_id": "trajectory_probe_run",
        "split": "test",
        "method_variant": method_variant,
        "sample_id": sample_id,
        "sample_role": sample_role,
        "attack_name": "temporal_crop",
        "decision": decision,
        "evidence_scores": {
            "S_tubelet": 0.7 if s_traj is None else 0.6,
            "S_sync": 0.7 if s_traj is None else 0.6,
            "S_traj": s_traj,
            "S_final": s_final,
        },
        "mechanism_trace": {
            "trajectory_source_kind": source_kind,
            "formal_trajectory_source_status": (
                None if s_traj is None else "candidate_ready"
            ),
            "trajectory_source_provenance_digest": (
                None if s_traj is None else "stage2_manifest_digest"
            ),
            "trajectory_statistic_kind": None if s_traj is None else "velocity_projection",
            "trajectory_time_grid": None if s_traj is None else [0.0, 0.5, 1.0],
            "trajectory_control_scores": (
                {} if s_traj is None else {"traj_time_reversed": 0.05}
            ),
            "trajectory_runtime_ms": None if s_traj is None else 1.0,
        },
    }

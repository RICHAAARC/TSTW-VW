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
) -> dict[str, object]:
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
            "trajectory_source_kind": None if S_traj is None else "latent_interpolation_surrogate",
            "trajectory_statistic_kind": None if S_traj is None else "velocity_projection",
            "trajectory_time_grid": None if S_traj is None else [0.0, 0.5, 1.0],
            "trajectory_control_scores": {
                "traj_time_reversed": -0.1,
            },
            "trajectory_runtime_ms": 1.0,
        },
    }


def test_stage3_mechanism_audit_defers_when_stage2_is_not_passed() -> None:
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
    assert decision["Stage3MechanismDecision"] == "DEFERRED_BY_STAGE2"
    assert decision["Stage2DependencyStatus"] == "NOT_PASSED"
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
"""
文件用途：验证 trajectory statistic probe 报告读取正式机制决策产物。
File purpose: Validate trajectory statistic probe report decision alignment.
Module type: General module
"""

from __future__ import annotations

import pytest

from experiments.trajectory_statistic_probe.artifact_builder import (
    build_trajectory_probe_report_text,
)


pytestmark = [pytest.mark.quick]


def test_trajectory_probe_report_uses_mechanism_decision_status() -> None:
    """验证报告状态来自机制决策, 而不是旧的硬编码阶段 2 defer 文本。"""
    report_text = build_trajectory_probe_report_text(
        event_score_records=[
            {
                "method_variant": "tubelet_traj",
                "attack_name": "temporal_crop",
            }
        ],
        gain_rows=[
            {
                "delta_traj": 0.0,
                "delta_positive_margin_traj": 0.342307,
            }
        ],
        correlation_rows=[],
        runtime_rows=[
            {
                "trajectory_runtime_ms": 275.211534,
            }
        ],
        mechanism_decision={
            "Stage2DependencyStatus": "PASSED",
            "Stage3ImplementationDecision": "PASS",
            "Stage3MechanismDecision": "PASS",
            "NextAllowedStageByTrajectory": "trajectory_aware_sampling_probe",
        },
    )

    assert "stage2_dependency_status: PASSED" in report_text
    assert "stage3_implementation_status: PASS" in report_text
    assert "stage3_mechanism_status: PASS" in report_text
    assert (
        "next_allowed_stage_by_trajectory: trajectory_aware_sampling_probe"
        in report_text
    )
    assert "stage3_mechanism_status: deferred_by_stage2" not in report_text


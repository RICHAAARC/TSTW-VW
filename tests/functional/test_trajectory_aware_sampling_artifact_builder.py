"""
文件用途: 验证 trajectory-aware sampling scaffold 产物写出路径。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.artifact_builder import (
    build_trajectory_aware_sampling_artifacts,
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
        "outputs": {
            "sampling_readiness_decision_path": "artifacts/sampling_readiness_decision.json",
            "sampling_selection_plan_path": "artifacts/sampling_selection_plan.json",
            "sampling_probe_report_path": "reports/trajectory_aware_sampling_probe_report.md",
        },
    }


def _records() -> list[dict[str, object]]:
    return [
        {
            "run_id": "run_formal",
            "event_id": "event_selected",
            "sample_id": "sample_selected",
            "split": "test",
            "sample_role": "attacked_positive",
            "method_variant": "tubelet_traj",
            "attack_name": "temporal_crop",
            "evidence_scores": {
                "S_traj": 0.7,
                "S_final": 0.3,
            },
            "mechanism_trace": {
                "trajectory_control_scores": {
                    "permuted_time": 0.02,
                },
                "trajectory_runtime_ms": 12.0,
            },
            "decision": True,
        }
    ]


def test_sampling_artifact_builder_writes_decision_plan_manifest_and_report(
    tmp_path: Path,
) -> None:
    """验证 sampling scaffold 产物可以在临时目录完成 CPU 闭环写出。"""
    paths = build_trajectory_aware_sampling_artifacts(
        _records(),
        _passed_trajectory_decision(),
        _sampling_config(),
        tmp_path,
    )

    for path in paths.values():
        assert path.exists()
        assert tmp_path in path.parents

    readiness = json.loads(
        paths["sampling_readiness_decision_path"].read_text(encoding="utf-8")
    )
    plan = json.loads(
        paths["sampling_selection_plan_path"].read_text(encoding="utf-8")
    )
    manifest = json.loads(
        paths["sampling_policy_manifest_path"].read_text(encoding="utf-8")
    )
    report_text = paths["sampling_probe_report_path"].read_text(encoding="utf-8")

    assert readiness["SamplingReadinessDecision"] == "PASS"
    assert plan["SamplingSelectionPlanDecision"] == "PASS"
    assert plan["selected_record_count"] == 1
    assert manifest["selection_plan_digest"] == plan["selection_plan_digest"]
    assert manifest["real_generation_allowed"] is False
    assert manifest["real_watermark_integration_allowed"] is False
    assert manifest["next_step_requires_real_gpu_validation"] is True
    assert manifest["NextRequiredValidationBySampling"] == "real_gpu_validation"
    assert "Trajectory-Aware Sampling Probe Report" in report_text
    assert "requires_real_gpu_validation: False" in report_text
    assert "next_step_requires_real_gpu_validation: True" in report_text

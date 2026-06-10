"""
文件用途: 验证 trajectory-aware sampling runner 和 CLI 的 CPU scaffold 闭环。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.runner import (
    TrajectoryAwareSamplingProbeRunner,
)
from experiments.trajectory_aware_sampling_probe.scaffold_cli import main as scaffold_main

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.quick]


def _write_upstream_trajectory_root(tmp_path: Path) -> Path:
    upstream_root = tmp_path / "trajectory_statistic_probe_formal"
    records_path = upstream_root / "records" / "event_scores.jsonl"
    decision_path = upstream_root / "artifacts" / "trajectory_mechanism_decision.json"
    records_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "run_id": "trajectory_run",
            "event_id": "event_selected",
            "sample_id": "sample_selected",
            "split": "test",
            "sample_role": "attacked_positive",
            "method_variant": "tubelet_sync_trajectory_fusion",
            "attack_name": "local_clip",
            "evidence_scores": {
                "S_traj": 0.9,
                "S_final": 0.4,
            },
            "mechanism_trace": {
                "trajectory_control_scores": {
                    "permuted_time": 0.01,
                },
                "trajectory_runtime_ms": 20.0,
            },
            "decision": True,
        }
    ]
    records_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    decision_path.write_text(
        json.dumps(
            {
                "Stage2DependencyStatus": "PASSED",
                "Stage3ImplementationDecision": "PASS",
                "Stage3MechanismDecision": "PASS",
                "NextAllowedStageByTrajectory": "trajectory_aware_sampling_probe",
                "Stage3MechanismBlockingReasons": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return upstream_root


def test_sampling_runner_reads_trajectory_root_and_writes_handoff_manifest(
    tmp_path: Path,
) -> None:
    """验证 runner 可以从阶段 3 输出根目录构建 sampling scaffold 产物。"""
    upstream_root = _write_upstream_trajectory_root(tmp_path)
    output_root = tmp_path / "trajectory_aware_sampling_probe_scaffold"

    result = TrajectoryAwareSamplingProbeRunner(ROOT).run(upstream_root, output_root)

    assert result.readiness_decision["SamplingReadinessDecision"] == "PASS"
    assert result.selection_plan["SamplingSelectionPlanDecision"] == "PASS"
    assert result.policy_manifest["selected_record_count"] == 1
    assert (
        result.gpu_validation_contract[
            "TrajectoryAwareSamplingGpuValidationContractDecision"
        ]
        == "READY_FOR_REAL_GPU_RUNTIME_VALIDATION"
    )
    assert (
        result.backend_transition_guard[
            "TrajectoryAwareSamplingBackendTransitionGuardDecision"
        ]
        == "BACKEND_TRANSITION_DECISION_REQUIRED"
    )
    handoff_manifest_path = output_root / "artifacts" / "sampling_handoff_manifest.json"
    gpu_validation_contract_path = (
        output_root
        / "artifacts"
        / "trajectory_aware_sampling_gpu_validation_contract.json"
    )
    backend_transition_guard_path = (
        output_root
        / "artifacts"
        / "trajectory_aware_sampling_backend_transition_guard.json"
    )
    assert handoff_manifest_path.exists()
    assert gpu_validation_contract_path.exists()
    assert backend_transition_guard_path.exists()
    handoff_manifest = json.loads(handoff_manifest_path.read_text(encoding="utf-8"))
    gpu_validation_contract = json.loads(
        gpu_validation_contract_path.read_text(encoding="utf-8")
    )
    backend_transition_guard = json.loads(
        backend_transition_guard_path.read_text(encoding="utf-8")
    )
    assert handoff_manifest["handoff_kind"] == "trajectory_aware_sampling_scaffold"
    assert handoff_manifest["requires_real_gpu_validation"] is False
    assert handoff_manifest["next_step_requires_real_gpu_validation"] is True
    assert handoff_manifest["NextRequiredValidationBySampling"] == "real_gpu_validation"
    assert handoff_manifest["real_generation_allowed"] is False
    assert (
        gpu_validation_contract[
            "TrajectoryAwareSamplingGpuValidationContractDecision"
        ]
        == "READY_FOR_REAL_GPU_RUNTIME_VALIDATION"
    )
    assert (
        gpu_validation_contract["NextAllowedConstructionAfterGpuValidationContract"]
        == "real_gpu_runtime_validation"
    )
    assert gpu_validation_contract["real_generation_allowed"] is False
    assert (
        backend_transition_guard[
            "TrajectoryAwareSamplingBackendTransitionGuardDecision"
        ]
        == "BACKEND_TRANSITION_DECISION_REQUIRED"
    )
    assert (
        backend_transition_guard[
            "NextAllowedConstructionAfterBackendTransitionGuard"
        ]
        == "explicit_backend_transition_decision"
    )
    assert backend_transition_guard["backend_transition_decision_required"] is True
    assert backend_transition_guard["real_generation_allowed"] is False


def test_sampling_scaffold_cli_prints_policy_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """验证 CLI 只调度 repository runner, 并输出 policy manifest 摘要。"""
    upstream_root = _write_upstream_trajectory_root(tmp_path)
    output_root = tmp_path / "trajectory_aware_sampling_probe_cli"

    exit_code = scaffold_main(
        [
            "--repository-root",
            str(ROOT),
            "--upstream-trajectory-root",
            str(upstream_root),
            "--output-root",
            str(output_root),
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads(captured.out)
    assert exit_code == 0
    assert manifest["SamplingSelectionPlanDecision"] == "PASS"
    assert manifest["selected_record_count"] == 1
    assert manifest["next_step_requires_real_gpu_validation"] is True
    assert manifest["NextRequiredValidationBySampling"] == "real_gpu_validation"
    assert (output_root / "artifacts" / "sampling_selection_plan.json").exists()
    assert (
        output_root
        / "artifacts"
        / "trajectory_aware_sampling_gpu_validation_contract.json"
    ).exists()
    assert (
        output_root
        / "artifacts"
        / "trajectory_aware_sampling_backend_transition_guard.json"
    ).exists()

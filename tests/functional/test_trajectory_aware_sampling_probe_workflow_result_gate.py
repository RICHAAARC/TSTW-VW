"""
文件用途: 验证 trajectory-aware sampling notebook helper 的 result gate 写出流程。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paper_workflow.notebook_utils.trajectory_aware_sampling_probe_workflow import (
    run_real_gpu_backend_connection_smoke_result_gate,
)

pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]


def _write_ready_handoff(run_root: Path) -> None:
    handoff_path = (
        run_root
        / "artifacts"
        / "trajectory_aware_sampling_real_backend_connection_smoke_handoff.json"
    )
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        json.dumps(
            {
                "TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffDecision": "READY_FOR_EXTERNAL_REAL_GPU_SMOKE_RUN",
                "NextRequiredExternalExecutionAfterSmokeHandoff": "real_gpu_backend_connection_smoke",
                "external_gpu_required": True,
                "runtime_backend_connection_allowed": False,
                "real_backend_connection_smoke_handoff_digest": "handoff_digest",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_passing_external_results(results_path: Path) -> None:
    kinds = [
        "runtime_environment_snapshot",
        "model_identity_record",
        "backend_dependency_resolution_record",
        "single_request_execution_record",
        "runtime_failure_manifest",
    ]
    results_path.write_text(
        json.dumps(
            {
                "external_smoke_result_status": "PASS",
                "external_gpu_runtime_detected": True,
                "external_model_identity_recorded": True,
                "external_backend_dependencies_resolved": True,
                "external_real_backend_connection_attempted": True,
                "external_real_backend_connection_succeeded": True,
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
                    for kind in kinds
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_notebook_workflow_writes_real_gpu_backend_connection_smoke_result_gate(
    tmp_path: Path,
) -> None:
    """验证 notebook helper 只调度仓库 gate, 并将结果 artifact 写入临时 run root。"""
    run_root = tmp_path / "trajectory_aware_sampling_probe_scaffold_gpu_validation"
    results_path = tmp_path / "external_real_gpu_smoke_results.json"
    _write_ready_handoff(run_root)
    _write_passing_external_results(results_path)

    payload = run_real_gpu_backend_connection_smoke_result_gate(
        repository_root=ROOT,
        run_root=run_root,
        external_smoke_results_path=results_path,
    )

    output_path = (
        run_root
        / "artifacts"
        / "trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate.json"
    )
    assert output_path.exists()
    written_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert (
        payload["TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateDecision"]
        == "PASS"
    )
    assert written_payload == payload
    assert (
        written_payload["NextAllowedConstructionAfterRealGpuBackendConnectionSmokeResultGate"]
        == "real_backend_runtime_validation_gate"
    )


def test_notebook_workflow_generates_environment_only_smoke_results(tmp_path: Path) -> None:
    """验证 Colab helper 可以生成可检查的环境级 smoke 结果 JSON。"""
    output_path = tmp_path / "external_real_gpu_smoke_results.json"

    payload = __import__(
        "paper_workflow.notebook_utils.trajectory_aware_sampling_probe_workflow",
        fromlist=["write_environment_only_real_gpu_backend_connection_smoke_results"],
    ).write_environment_only_real_gpu_backend_connection_smoke_results(
        repository_root=ROOT,
        output_path=output_path,
    )

    assert output_path.exists()
    written_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert written_payload == payload
    assert payload["external_smoke_result_status"] == "INCONCLUSIVE"
    assert payload["external_real_backend_connection_attempted"] is False
    assert payload["external_real_generation_attempted"] is False
    assert payload["external_real_watermark_integration_attempted"] is False
    assert len(payload["result_artifacts"]) == 5

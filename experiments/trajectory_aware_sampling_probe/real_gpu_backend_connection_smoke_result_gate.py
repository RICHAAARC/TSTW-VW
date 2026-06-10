"""
文件用途: 校验外部真实 GPU backend connection smoke 的结果包。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_HANDOFF_DECISION = "READY_FOR_EXTERNAL_REAL_GPU_SMOKE_RUN"
_PASS_DECISION = "PASS"


def build_trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate(
    real_backend_connection_smoke_handoff: dict[str, Any],
    external_smoke_results: dict[str, Any],
    result_gate_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 校验外部真实 GPU smoke 结果是否允许进入下一构建层。

    该函数属于项目特定写法。它只读取 Colab 或同等真实 GPU 环境已经带回的结果摘要,
    不导入真实模型库, 不连接真实生成后端, 不生成视频, 也不执行 watermark 算法。
    通用工程价值在于把“外部执行是否合格”的判定集中到仓库模块中, 避免 notebook 手写判断逻辑。
    """
    blocking_reasons: list[str] = []

    required_handoff_decision = result_gate_config.get(
        "required_handoff_decision",
        _READY_HANDOFF_DECISION,
    )
    if (
        real_backend_connection_smoke_handoff.get(
            "TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffDecision"
        )
        != required_handoff_decision
    ):
        blocking_reasons.append("real_gpu_smoke_handoff_not_ready")

    required_external_execution = result_gate_config.get(
        "required_next_external_execution_after_handoff",
        "real_gpu_backend_connection_smoke",
    )
    if (
        real_backend_connection_smoke_handoff.get(
            "NextRequiredExternalExecutionAfterSmokeHandoff"
        )
        != required_external_execution
    ):
        blocking_reasons.append("real_gpu_smoke_handoff_external_execution_mismatch")

    if real_backend_connection_smoke_handoff.get("external_gpu_required") is not True:
        blocking_reasons.append("external_gpu_requirement_missing")
    if real_backend_connection_smoke_handoff.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("handoff_enabled_local_runtime_backend_connection")
    if result_gate_config.get("runtime_backend_connection_allowed_in_local_runner") is not False:
        blocking_reasons.append("config_enabled_local_runtime_backend_connection")

    expected_kinds = list(result_gate_config.get("required_download_artifact_kinds", []))
    result_artifacts = _normalize_result_artifacts(external_smoke_results)
    observed_kinds = {
        str(artifact.get("result_artifact_kind"))
        for artifact in result_artifacts
        if isinstance(artifact, dict)
    }
    missing_kinds = [kind for kind in expected_kinds if kind not in observed_kinds]
    if missing_kinds:
        blocking_reasons.append("missing_required_external_smoke_result_artifacts")

    minimum_result_count = int(
        result_gate_config.get("minimum_required_result_artifact_count", len(expected_kinds))
    )
    if len(result_artifacts) < minimum_result_count:
        blocking_reasons.append("external_smoke_result_artifact_count_below_minimum")

    result_status = str(external_smoke_results.get("external_smoke_result_status", ""))
    required_status = str(result_gate_config.get("required_result_status_for_pass", _PASS_DECISION))
    if result_status != required_status:
        blocking_reasons.append("external_smoke_result_status_not_pass")

    if external_smoke_results.get("external_gpu_runtime_detected") is not True:
        blocking_reasons.append("external_gpu_runtime_not_detected")
    if external_smoke_results.get("external_model_identity_recorded") is not True:
        blocking_reasons.append("external_model_identity_not_recorded")
    if external_smoke_results.get("external_backend_dependencies_resolved") is not True:
        blocking_reasons.append("external_backend_dependencies_not_resolved")

    if result_gate_config.get("external_real_backend_connection_expected") is True:
        if external_smoke_results.get("external_real_backend_connection_attempted") is not True:
            blocking_reasons.append("external_real_backend_connection_not_attempted")
        if external_smoke_results.get("external_real_backend_connection_succeeded") is not True:
            blocking_reasons.append("external_real_backend_connection_not_succeeded")

    if external_smoke_results.get("external_real_generation_attempted") is not False:
        blocking_reasons.append("external_real_generation_attempted_unexpectedly")
    if external_smoke_results.get("external_real_watermark_integration_attempted") is not False:
        blocking_reasons.append("external_real_watermark_integration_attempted_unexpectedly")
    if result_gate_config.get("external_real_generation_allowed") is not False:
        blocking_reasons.append("config_enabled_external_real_generation")
    if result_gate_config.get("external_real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_external_real_watermark")

    failure_manifest = external_smoke_results.get("runtime_failure_manifest", {})
    if not isinstance(failure_manifest, dict):
        blocking_reasons.append("runtime_failure_manifest_not_object")
        failure_manifest = {}
    elif failure_manifest.get("failure_manifest_recorded") is not True:
        blocking_reasons.append("runtime_failure_manifest_not_recorded")

    decision = _PASS_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateDecision": decision,
        "TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateBlockingReasons": blocking_reasons,
        "project_stage": result_gate_config.get("project_stage"),
        "construction_phase": result_gate_config.get("construction_phase"),
        "target_construction_phase": result_gate_config.get("target_construction_phase"),
        "runtime_mode": result_gate_config.get("runtime_mode"),
        "external_smoke_result_status": result_status,
        "external_gpu_runtime_detected": external_smoke_results.get("external_gpu_runtime_detected") is True,
        "external_model_identity_recorded": external_smoke_results.get("external_model_identity_recorded") is True,
        "external_backend_dependencies_resolved": external_smoke_results.get("external_backend_dependencies_resolved") is True,
        "external_real_backend_connection_attempted": external_smoke_results.get("external_real_backend_connection_attempted") is True,
        "external_real_backend_connection_succeeded": external_smoke_results.get("external_real_backend_connection_succeeded") is True,
        "external_real_generation_attempted": external_smoke_results.get("external_real_generation_attempted") is True,
        "external_real_watermark_integration_attempted": external_smoke_results.get("external_real_watermark_integration_attempted") is True,
        "runtime_backend_connection_allowed_in_local_runner": False,
        "external_real_generation_allowed": False,
        "external_real_watermark_integration_allowed": False,
        "required_result_artifact_count": len(expected_kinds),
        "observed_result_artifact_count": len(result_artifacts),
        "missing_required_result_artifact_kinds": missing_kinds,
        "real_backend_connection_smoke_handoff_digest": real_backend_connection_smoke_handoff.get(
            "real_backend_connection_smoke_handoff_digest"
        ),
        "real_backend_connection_smoke_handoff_payload_digest": compute_object_digest(
            real_backend_connection_smoke_handoff
        ),
        "external_smoke_results_payload_digest": compute_object_digest(external_smoke_results),
        "NextAllowedConstructionAfterRealGpuBackendConnectionSmokeResultGate": (
            result_gate_config.get(
                "approved_next_construction_after_external_smoke_pass",
                "real_backend_runtime_validation_gate",
            )
            if decision == _PASS_DECISION
            else "finish_real_gpu_backend_connection_smoke"
        ),
    }
    payload["real_gpu_backend_connection_smoke_result_gate_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "real_gpu_backend_connection_smoke_result_gate_digest"
        }
    )
    return payload


def _normalize_result_artifacts(external_smoke_results: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = external_smoke_results.get("result_artifacts", [])
    if not isinstance(artifacts, list):
        return []
    return [artifact for artifact in artifacts if isinstance(artifact, dict)]

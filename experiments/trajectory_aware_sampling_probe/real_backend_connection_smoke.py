"""
文件用途: 构建 trajectory-aware sampling 的真实后端连接 smoke 执行请求 gate。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_CONNECTION_CONTRACT_DECISION = "READY_FOR_REAL_BACKEND_CONNECTION_SMOKE"
_READY_SMOKE_EXECUTION_REQUEST_DECISION = "READY_FOR_REAL_GPU_BACKEND_CONNECTION_SMOKE_EXECUTION"


def build_trajectory_aware_sampling_real_backend_connection_smoke(
    backend_connection_contract: dict[str, Any],
    real_backend_connection_smoke_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 生成真实 GPU 后端连接 smoke 的执行请求 gate。

    该函数属于项目特定写法。它只把 backend connection contract 转换为可在 Colab GPU 中执行的 smoke 请求,
    当前本地 runner 不导入真实模型库, 不连接真实 DiT / Flow Matching 后端, 不生成视频, 也不执行 watermark。
    这样可以把下一步真实 GPU smoke 所需的输入、输出、失败记录和禁止 claim 边界固定下来。
    """
    blocking_reasons: list[str] = []

    required_decision = real_backend_connection_smoke_config.get(
        "required_backend_connection_contract_decision",
        _READY_CONNECTION_CONTRACT_DECISION,
    )
    if (
        backend_connection_contract.get(
            "TrajectoryAwareSamplingBackendConnectionContractDecision"
        )
        != required_decision
    ):
        blocking_reasons.append("backend_connection_contract_not_ready")

    required_next = real_backend_connection_smoke_config.get(
        "required_next_allowed_construction_after_backend_connection_contract",
        "real_backend_connection_smoke",
    )
    if (
        backend_connection_contract.get(
            "NextAllowedConstructionAfterBackendConnectionContract"
        )
        != required_next
    ):
        blocking_reasons.append("backend_connection_contract_next_step_mismatch")

    if backend_connection_contract.get("backend_connection_contract_allowed") is not True:
        blocking_reasons.append("backend_connection_contract_permission_missing")
    if backend_connection_contract.get("real_backend_connection_smoke_allowed_after_contract") is not True:
        blocking_reasons.append("real_backend_smoke_permission_missing")
    if backend_connection_contract.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("contract_enabled_runtime_backend_connection")
    if backend_connection_contract.get("real_generation_allowed") is not False:
        blocking_reasons.append("contract_enabled_real_generation")
    if backend_connection_contract.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("contract_enabled_real_watermark")

    minimum_contract_section_count = int(
        real_backend_connection_smoke_config.get("minimum_contract_section_count", 1)
    )
    if int(backend_connection_contract.get("contract_section_count", 0)) < minimum_contract_section_count:
        blocking_reasons.append("contract_section_count_below_minimum")

    minimum_backend_family_count = int(
        real_backend_connection_smoke_config.get("minimum_smoke_backend_family_count", 1)
    )
    if int(backend_connection_contract.get("smoke_backend_family_count", 0)) < minimum_backend_family_count:
        blocking_reasons.append("smoke_backend_family_count_below_minimum")

    smoke_governance = backend_connection_contract.get("smoke_output_governance", {})
    if not isinstance(smoke_governance, dict):
        smoke_governance = {}
    if smoke_governance.get("formal_claim_support_allowed") is not False:
        blocking_reasons.append("smoke_formal_claim_support_must_remain_disabled")
    if smoke_governance.get("failure_manifest_required") is not True:
        blocking_reasons.append("failure_manifest_requirement_missing")

    if real_backend_connection_smoke_config.get("real_backend_connection_smoke_request_allowed") is not True:
        blocking_reasons.append("smoke_request_not_allowed")
    if real_backend_connection_smoke_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("config_enabled_runtime_backend_connection")
    if real_backend_connection_smoke_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("config_enabled_real_generation")
    if real_backend_connection_smoke_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")
    if real_backend_connection_smoke_config.get("real_backend_connection_attempted") is not False:
        blocking_reasons.append("config_attempted_real_backend_connection")

    request_count = int(real_backend_connection_smoke_config.get("smoke_execution_request_count", 1))
    smoke_execution_requests = [
        _build_smoke_execution_request(real_backend_connection_smoke_config, index)
        for index in range(max(request_count, 0))
    ]
    required_result_artifacts = [
        _build_required_result_artifact(artifact_kind, index)
        for index, artifact_kind in enumerate(
            real_backend_connection_smoke_config.get("required_smoke_result_artifacts", [])
        )
    ]

    decision = _READY_SMOKE_EXECUTION_REQUEST_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingRealBackendConnectionSmokeDecision": decision,
        "TrajectoryAwareSamplingRealBackendConnectionSmokeBlockingReasons": blocking_reasons,
        "project_stage": real_backend_connection_smoke_config.get("project_stage"),
        "construction_phase": real_backend_connection_smoke_config.get("construction_phase"),
        "target_construction_phase": real_backend_connection_smoke_config.get("target_construction_phase"),
        "runtime_mode": real_backend_connection_smoke_config.get("runtime_mode"),
        "real_backend_connection_smoke_request_allowed": decision == _READY_SMOKE_EXECUTION_REQUEST_DECISION,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "real_backend_connection_attempted": False,
        "gpu_execution_required_for_next_step": bool(
            real_backend_connection_smoke_config.get("gpu_execution_required_for_next_step", True)
        ),
        "smoke_execution_request_count": len(smoke_execution_requests),
        "smoke_execution_requests": smoke_execution_requests,
        "required_result_artifact_count": len(required_result_artifacts),
        "required_result_artifacts": required_result_artifacts,
        "backend_connection_contract_digest": backend_connection_contract.get("backend_connection_contract_digest"),
        "backend_connection_contract_payload_digest": compute_object_digest(backend_connection_contract),
        "forbidden_runtime_capabilities_until_real_gpu_backend_smoke_passes": list(
            real_backend_connection_smoke_config.get(
                "forbidden_runtime_capabilities_until_real_gpu_backend_smoke_passes", []
            )
        ),
        "NextRequiredValidationAfterRealBackendConnectionSmokeRequest": (
            real_backend_connection_smoke_config.get(
                "approved_next_validation", "real_gpu_backend_connection_smoke"
            )
            if decision == _READY_SMOKE_EXECUTION_REQUEST_DECISION
            else "finish_trajectory_aware_sampling_probe"
        ),
        "NextAllowedConstructionAfterRealBackendConnectionSmokePasses": (
            real_backend_connection_smoke_config.get(
                "approved_next_construction_after_gpu_smoke",
                "real_backend_runtime_validation_gate",
            )
            if decision == _READY_SMOKE_EXECUTION_REQUEST_DECISION
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    payload["real_backend_connection_smoke_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "real_backend_connection_smoke_digest"
        }
    )
    return payload


def _build_smoke_execution_request(
    real_backend_connection_smoke_config: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    request_payload = {
        "smoke_execution_request_id": f"real_backend_connection_smoke_request_{index:04d}",
        "smoke_execution_request_kind": str(
            real_backend_connection_smoke_config.get(
                "smoke_execution_request_kind",
                "single_selected_record_backend_connection_smoke",
            )
        ),
        "execution_location": "external_real_gpu_environment_required",
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "real_backend_connection_attempted": False,
    }
    request_payload["smoke_execution_request_digest"] = compute_object_digest(
        request_payload
    )
    return request_payload


def _build_required_result_artifact(artifact_kind: object, index: int) -> dict[str, Any]:
    artifact_payload = {
        "required_result_artifact_id": f"smoke_required_result_artifact_{index:04d}",
        "required_result_artifact_kind": str(artifact_kind),
        "required_result_artifact_status": "required_after_external_real_gpu_smoke",
        "formal_claim_support_allowed": False,
    }
    artifact_payload["required_result_artifact_digest"] = compute_object_digest(
        artifact_payload
    )
    return artifact_payload

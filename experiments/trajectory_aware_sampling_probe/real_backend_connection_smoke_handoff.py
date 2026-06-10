"""
文件用途: 构建 trajectory-aware sampling 的真实 GPU smoke handoff artifact。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_SMOKE_REQUEST_DECISION = "READY_FOR_REAL_GPU_BACKEND_CONNECTION_SMOKE_EXECUTION"
_READY_HANDOFF_DECISION = "READY_FOR_EXTERNAL_REAL_GPU_SMOKE_RUN"


def build_trajectory_aware_sampling_real_backend_connection_smoke_handoff(
    real_backend_connection_smoke: dict[str, Any],
    real_backend_connection_smoke_handoff_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 将真实后端 smoke 请求转换为外部 Colab / GPU 执行 handoff。

    该函数属于项目特定写法。它不连接真实生成后端, 不加载真实模型, 不生成视频, 也不执行 watermark 算法。
    它只把已经冻结的 smoke request gate 转换为可交给真实 GPU 环境执行的输入清单、下载清单和治理边界。
    这样可以在仓库仍禁止真实后端接入的阶段, 明确下一步需要由 Colab 产出哪些结果文件。
    """
    blocking_reasons: list[str] = []

    required_decision = real_backend_connection_smoke_handoff_config.get(
        "required_real_backend_connection_smoke_decision",
        _READY_SMOKE_REQUEST_DECISION,
    )
    if (
        real_backend_connection_smoke.get(
            "TrajectoryAwareSamplingRealBackendConnectionSmokeDecision"
        )
        != required_decision
    ):
        blocking_reasons.append("real_backend_connection_smoke_not_ready")

    required_next_validation = real_backend_connection_smoke_handoff_config.get(
        "required_next_validation_after_smoke_request",
        "real_gpu_backend_connection_smoke",
    )
    if (
        real_backend_connection_smoke.get(
            "NextRequiredValidationAfterRealBackendConnectionSmokeRequest"
        )
        != required_next_validation
    ):
        blocking_reasons.append("real_backend_connection_smoke_next_validation_mismatch")

    if real_backend_connection_smoke.get("real_backend_connection_smoke_request_allowed") is not True:
        blocking_reasons.append("real_backend_connection_smoke_request_not_allowed")
    if real_backend_connection_smoke.get("gpu_execution_required_for_next_step") is not True:
        blocking_reasons.append("gpu_execution_requirement_missing")
    if real_backend_connection_smoke.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("smoke_request_enabled_runtime_backend_connection")
    if real_backend_connection_smoke.get("real_generation_allowed") is not False:
        blocking_reasons.append("smoke_request_enabled_real_generation")
    if real_backend_connection_smoke.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("smoke_request_enabled_real_watermark")
    if real_backend_connection_smoke.get("real_backend_connection_attempted") is not False:
        blocking_reasons.append("smoke_request_attempted_real_backend_connection")

    if real_backend_connection_smoke_handoff_config.get("real_backend_connection_smoke_handoff_allowed") is not True:
        blocking_reasons.append("smoke_handoff_not_allowed")
    if real_backend_connection_smoke_handoff_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("config_enabled_runtime_backend_connection")
    if real_backend_connection_smoke_handoff_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("config_enabled_real_generation")
    if real_backend_connection_smoke_handoff_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")
    if real_backend_connection_smoke_handoff_config.get("real_backend_connection_attempted") is not False:
        blocking_reasons.append("config_attempted_real_backend_connection")

    minimum_request_count = int(
        real_backend_connection_smoke_handoff_config.get(
            "minimum_smoke_execution_request_count",
            1,
        )
    )
    if int(real_backend_connection_smoke.get("smoke_execution_request_count", 0)) < minimum_request_count:
        blocking_reasons.append("smoke_execution_request_count_below_minimum")

    minimum_result_artifact_count = int(
        real_backend_connection_smoke_handoff_config.get(
            "minimum_required_result_artifact_count",
            1,
        )
    )
    if int(real_backend_connection_smoke.get("required_result_artifact_count", 0)) < minimum_result_artifact_count:
        blocking_reasons.append("required_result_artifact_count_below_minimum")

    upload_artifacts = [
        _build_handoff_artifact("upload", artifact_kind, index)
        for index, artifact_kind in enumerate(
            real_backend_connection_smoke_handoff_config.get(
                "required_upload_artifact_kinds",
                [],
            )
        )
    ]
    download_artifacts = [
        _build_handoff_artifact("download", artifact_kind, index)
        for index, artifact_kind in enumerate(
            real_backend_connection_smoke_handoff_config.get(
                "required_download_artifact_kinds",
                [],
            )
        )
    ]
    handoff_sections = list(
        real_backend_connection_smoke_handoff_config.get("required_handoff_sections", [])
    )

    decision = _READY_HANDOFF_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffDecision": decision,
        "TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffBlockingReasons": blocking_reasons,
        "project_stage": real_backend_connection_smoke_handoff_config.get("project_stage"),
        "construction_phase": real_backend_connection_smoke_handoff_config.get("construction_phase"),
        "target_construction_phase": real_backend_connection_smoke_handoff_config.get("target_construction_phase"),
        "runtime_mode": real_backend_connection_smoke_handoff_config.get("runtime_mode"),
        "real_backend_connection_smoke_handoff_allowed": decision == _READY_HANDOFF_DECISION,
        "external_gpu_required": bool(
            real_backend_connection_smoke_handoff_config.get("external_gpu_required", True)
        ),
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "real_backend_connection_attempted": False,
        "required_handoff_section_count": len(handoff_sections),
        "required_handoff_sections": handoff_sections,
        "required_upload_artifact_count": len(upload_artifacts),
        "required_upload_artifacts": upload_artifacts,
        "required_download_artifact_count": len(download_artifacts),
        "required_download_artifacts": download_artifacts,
        "external_execution_requirements": {
            "execution_location": "external_colab_or_equivalent_real_gpu_environment",
            "required_external_execution": real_backend_connection_smoke_handoff_config.get(
                "approved_next_external_execution",
                "real_gpu_backend_connection_smoke",
            ),
            "must_return_download_artifacts": True,
            "formal_claim_support_allowed": False,
        },
        "governance_boundaries": {
            "runtime_backend_connection_allowed_in_local_runner": False,
            "real_generation_allowed_in_local_runner": False,
            "real_watermark_integration_allowed_in_local_runner": False,
            "real_backend_connection_attempted_in_local_runner": False,
        },
        "forbidden_runtime_capabilities_until_external_smoke_passes": list(
            real_backend_connection_smoke_handoff_config.get(
                "forbidden_runtime_capabilities_until_external_smoke_passes",
                [],
            )
        ),
        "real_backend_connection_smoke_digest": real_backend_connection_smoke.get(
            "real_backend_connection_smoke_digest"
        ),
        "real_backend_connection_smoke_payload_digest": compute_object_digest(
            real_backend_connection_smoke
        ),
        "NextRequiredExternalExecutionAfterSmokeHandoff": (
            real_backend_connection_smoke_handoff_config.get(
                "approved_next_external_execution",
                "real_gpu_backend_connection_smoke",
            )
            if decision == _READY_HANDOFF_DECISION
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    payload["real_backend_connection_smoke_handoff_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "real_backend_connection_smoke_handoff_digest"
        }
    )
    return payload


def _build_handoff_artifact(direction: str, artifact_kind: object, index: int) -> dict[str, Any]:
    artifact_payload = {
        "handoff_artifact_id": f"{direction}_handoff_artifact_{index:04d}",
        "handoff_artifact_direction": direction,
        "handoff_artifact_kind": str(artifact_kind),
        "handoff_artifact_status": "required_for_external_real_gpu_smoke",
        "formal_claim_support_allowed": False,
    }
    artifact_payload["handoff_artifact_digest"] = compute_object_digest(artifact_payload)
    return artifact_payload

"""
文件用途: 构建 trajectory-aware sampling 后端切换前的受治理阻断产物。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


def build_trajectory_aware_sampling_backend_transition_guard(
    gpu_validation_contract: dict[str, Any],
    backend_transition_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 从 GPU validation contract 生成后端切换前的显式治理守卫。

    该函数属于项目特定写法。它不连接真实 runtime backend, 不执行真实视频生成,
    也不执行真实 watermark 嵌入或检测。它只把“已经可以进入真实 GPU runtime
    验证”这一事实转换为一个更严格的切换前守卫: 后续若要接入真实 DiT /
    Flow Matching / watermark 后端, 必须先有单独的 backend-transition 决策。
    """
    blocking_reasons: list[str] = []

    required_contract_decision = backend_transition_config.get(
        "required_gpu_validation_contract_decision",
        "READY_FOR_REAL_GPU_RUNTIME_VALIDATION",
    )
    if (
        gpu_validation_contract.get(
            "TrajectoryAwareSamplingGpuValidationContractDecision"
        )
        != required_contract_decision
    ):
        blocking_reasons.append("gpu_validation_contract_not_ready")

    required_next_allowed_construction = backend_transition_config.get(
        "required_next_allowed_construction",
        "real_gpu_runtime_validation",
    )
    if (
        gpu_validation_contract.get(
            "NextAllowedConstructionAfterGpuValidationContract"
        )
        != required_next_allowed_construction
    ):
        blocking_reasons.append("next_allowed_construction_not_real_gpu_validation")

    if gpu_validation_contract.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("runtime_backend_connection_already_enabled")
    if gpu_validation_contract.get("real_generation_allowed") is not False:
        blocking_reasons.append("real_generation_already_enabled")
    if gpu_validation_contract.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("real_watermark_integration_already_enabled")

    if backend_transition_config.get("backend_transition_decision_required") is not True:
        blocking_reasons.append("backend_transition_decision_requirement_missing")
    if backend_transition_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("runtime_backend_connection_must_remain_disabled")
    if backend_transition_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("real_generation_must_remain_disabled")
    if backend_transition_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("real_watermark_must_remain_disabled")

    decision = (
        "BACKEND_TRANSITION_DECISION_REQUIRED"
        if not blocking_reasons
        else "INCONCLUSIVE"
    )
    guard_payload: dict[str, Any] = {
        "TrajectoryAwareSamplingBackendTransitionGuardDecision": decision,
        "TrajectoryAwareSamplingBackendTransitionGuardBlockingReasons": blocking_reasons,
        "project_stage": backend_transition_config.get("project_stage"),
        "construction_phase": backend_transition_config.get("construction_phase"),
        "target_construction_phase": backend_transition_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": backend_transition_config.get("runtime_mode"),
        "backend_transition_decision_required": True,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "forbidden_runtime_capabilities_until_backend_transition": list(
            backend_transition_config.get(
                "forbidden_runtime_capabilities_until_backend_transition",
                [],
            )
        ),
        "gpu_validation_contract_digest": gpu_validation_contract.get(
            "gpu_validation_contract_digest"
        ),
        "gpu_validation_contract_payload_digest": compute_object_digest(
            gpu_validation_contract
        ),
        "NextAllowedConstructionAfterBackendTransitionGuard": (
            "explicit_backend_transition_decision"
            if decision == "BACKEND_TRANSITION_DECISION_REQUIRED"
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    guard_payload["backend_transition_guard_digest"] = compute_object_digest(
        {
            key: value
            for key, value in guard_payload.items()
            if key != "backend_transition_guard_digest"
        }
    )
    return guard_payload

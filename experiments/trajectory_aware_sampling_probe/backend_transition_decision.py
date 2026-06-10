"""
文件用途: 构建 trajectory-aware sampling 的显式后端切换决策产物。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


def build_trajectory_aware_sampling_backend_transition_decision(
    backend_transition_guard: dict[str, Any],
    backend_transition_decision_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 将后端切换守卫推进为显式的接口脚手架决策。

    该函数属于项目特定写法。它只批准下一步构建真实 GPU runtime 的接口脚手架,
    不批准真实 backend 连接, 不批准真实视频生成, 也不批准真实 watermark 集成。
    这样可以在进入高风险真实后端实现前, 先冻结请求 schema、结果 manifest
    和 GPU preflight 边界。
    """
    blocking_reasons: list[str] = []

    required_guard_decision = backend_transition_decision_config.get(
        "required_backend_transition_guard_decision",
        "BACKEND_TRANSITION_DECISION_REQUIRED",
    )
    if (
        backend_transition_guard.get(
            "TrajectoryAwareSamplingBackendTransitionGuardDecision"
        )
        != required_guard_decision
    ):
        blocking_reasons.append("backend_transition_guard_not_ready")

    required_next_construction = backend_transition_decision_config.get(
        "required_next_allowed_construction_after_guard",
        "explicit_backend_transition_decision",
    )
    if (
        backend_transition_guard.get(
            "NextAllowedConstructionAfterBackendTransitionGuard"
        )
        != required_next_construction
    ):
        blocking_reasons.append("backend_transition_guard_next_step_mismatch")

    if backend_transition_guard.get("backend_transition_decision_required") is not True:
        blocking_reasons.append("backend_transition_decision_requirement_missing")
    if backend_transition_guard.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("guard_runtime_backend_connection_enabled")
    if backend_transition_guard.get("real_generation_allowed") is not False:
        blocking_reasons.append("guard_real_generation_enabled")
    if backend_transition_guard.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("guard_real_watermark_enabled")

    if backend_transition_decision_config.get("runtime_interface_scaffold_allowed") is not True:
        blocking_reasons.append("runtime_interface_scaffold_not_allowed")
    if backend_transition_decision_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("runtime_backend_connection_must_remain_disabled")
    if backend_transition_decision_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("real_generation_must_remain_disabled")
    if backend_transition_decision_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("real_watermark_must_remain_disabled")

    decision = (
        "APPROVED_FOR_RUNTIME_INTERFACE_SCAFFOLD_ONLY"
        if not blocking_reasons
        else "INCONCLUSIVE"
    )
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingBackendTransitionDecision": decision,
        "TrajectoryAwareSamplingBackendTransitionDecisionBlockingReasons": (
            blocking_reasons
        ),
        "project_stage": backend_transition_decision_config.get("project_stage"),
        "construction_phase": backend_transition_decision_config.get(
            "construction_phase"
        ),
        "target_construction_phase": backend_transition_decision_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": backend_transition_decision_config.get("runtime_mode"),
        "runtime_interface_scaffold_allowed": (
            decision == "APPROVED_FOR_RUNTIME_INTERFACE_SCAFFOLD_ONLY"
        ),
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "approved_interface_scaffold_capabilities": list(
            backend_transition_decision_config.get(
                "approved_interface_scaffold_capabilities",
                [],
            )
        ),
        "forbidden_runtime_capabilities_until_backend_implementation": list(
            backend_transition_decision_config.get(
                "forbidden_runtime_capabilities_until_backend_implementation",
                [],
            )
        ),
        "backend_transition_guard_digest": backend_transition_guard.get(
            "backend_transition_guard_digest"
        ),
        "backend_transition_guard_payload_digest": compute_object_digest(
            backend_transition_guard
        ),
        "NextAllowedConstructionAfterBackendTransitionDecision": (
            backend_transition_decision_config.get(
                "approved_next_construction",
                "real_gpu_runtime_interface_scaffold",
            )
            if decision == "APPROVED_FOR_RUNTIME_INTERFACE_SCAFFOLD_ONLY"
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    payload["backend_transition_decision_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "backend_transition_decision_digest"
        }
    )
    return payload

"""
文件用途: 构建 trajectory-aware sampling 的后端集成决策 gate 产物。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_IMPLEMENTATION_DECISION = "READY_FOR_BACKEND_INTEGRATION_DECISION"
_READY_BACKEND_DECISION = "READY_FOR_BACKEND_ADAPTER_SCAFFOLD"


def build_trajectory_aware_sampling_backend_integration_decision(
    runtime_interface_implementation: dict[str, Any],
    backend_integration_decision_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 根据非后端连接版 runtime interface implementation 生成后端集成决策。

    该函数属于项目特定写法。它只判断当前接口实现层是否已经具备进入后端 adapter scaffold 的条件,
    不连接真实 DiT / Flow Matching 后端, 不生成真实视频, 也不执行真实 watermark 嵌入或检测。
    这一设计的主要考虑在于: 在高风险真实后端接入之前, 先把 adapter 配置 schema、请求转换 schema、
    结果归一化 schema 和失败 manifest schema 的构建许可固定为可审计 artifact。
    """
    blocking_reasons: list[str] = []

    required_decision = backend_integration_decision_config.get(
        "required_runtime_interface_implementation_decision",
        _READY_IMPLEMENTATION_DECISION,
    )
    if (
        runtime_interface_implementation.get(
            "TrajectoryAwareSamplingRuntimeInterfaceImplementationDecision"
        )
        != required_decision
    ):
        blocking_reasons.append("runtime_interface_implementation_not_ready")

    required_next_construction = backend_integration_decision_config.get(
        "required_next_allowed_construction_after_implementation",
        "backend_integration_decision",
    )
    if (
        runtime_interface_implementation.get(
            "NextAllowedConstructionAfterRuntimeInterfaceImplementation"
        )
        != required_next_construction
    ):
        blocking_reasons.append(
            "runtime_interface_implementation_next_construction_mismatch"
        )

    if runtime_interface_implementation.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("implementation_enabled_runtime_backend_connection")
    if runtime_interface_implementation.get("real_generation_allowed") is not False:
        blocking_reasons.append("implementation_enabled_real_generation")
    if runtime_interface_implementation.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("implementation_enabled_real_watermark")

    minimum_request_count = int(
        backend_integration_decision_config.get("minimum_dry_run_request_count", 1)
    )
    if int(runtime_interface_implementation.get("dry_run_request_count", 0)) < minimum_request_count:
        blocking_reasons.append("dry_run_request_count_below_minimum")

    minimum_manifest_count = int(
        backend_integration_decision_config.get(
            "minimum_dry_run_result_manifest_count",
            1,
        )
    )
    if (
        int(runtime_interface_implementation.get("dry_run_result_manifest_count", 0))
        < minimum_manifest_count
    ):
        blocking_reasons.append("dry_run_result_manifest_count_below_minimum")

    gpu_preflight_summary = runtime_interface_implementation.get(
        "gpu_preflight_summary",
        {},
    )
    if not isinstance(gpu_preflight_summary, dict):
        gpu_preflight_summary = {}
    if (
        backend_integration_decision_config.get("require_gpu_preflight_observation")
        is True
        and "preflight_status" not in gpu_preflight_summary
    ):
        blocking_reasons.append("gpu_preflight_observation_missing")

    if backend_integration_decision_config.get("backend_adapter_scaffold_allowed") is not True:
        blocking_reasons.append("backend_adapter_scaffold_not_allowed")
    if backend_integration_decision_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("config_enabled_runtime_backend_connection")
    if backend_integration_decision_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("config_enabled_real_generation")
    if backend_integration_decision_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")

    decision = _READY_BACKEND_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingBackendIntegrationDecision": decision,
        "TrajectoryAwareSamplingBackendIntegrationDecisionBlockingReasons": (
            blocking_reasons
        ),
        "project_stage": backend_integration_decision_config.get("project_stage"),
        "construction_phase": backend_integration_decision_config.get(
            "construction_phase"
        ),
        "target_construction_phase": backend_integration_decision_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": backend_integration_decision_config.get("runtime_mode"),
        "backend_adapter_scaffold_allowed": decision == _READY_BACKEND_DECISION,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "approved_backend_adapter_scaffold_capabilities": list(
            backend_integration_decision_config.get(
                "approved_backend_adapter_scaffold_capabilities",
                [],
            )
        ),
        "forbidden_runtime_capabilities_until_backend_adapter_scaffold": list(
            backend_integration_decision_config.get(
                "forbidden_runtime_capabilities_until_backend_adapter_scaffold",
                [],
            )
        ),
        "runtime_interface_implementation_digest": (
            runtime_interface_implementation.get(
                "runtime_interface_implementation_digest"
            )
        ),
        "runtime_interface_implementation_payload_digest": compute_object_digest(
            runtime_interface_implementation
        ),
        "dry_run_request_count": runtime_interface_implementation.get(
            "dry_run_request_count",
            0,
        ),
        "dry_run_result_manifest_count": runtime_interface_implementation.get(
            "dry_run_result_manifest_count",
            0,
        ),
        "gpu_preflight_summary": gpu_preflight_summary,
        "NextAllowedConstructionAfterBackendIntegrationDecision": (
            backend_integration_decision_config.get(
                "approved_next_construction",
                "backend_adapter_scaffold",
            )
            if decision == _READY_BACKEND_DECISION
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    payload["backend_integration_decision_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "backend_integration_decision_digest"
        }
    )
    return payload

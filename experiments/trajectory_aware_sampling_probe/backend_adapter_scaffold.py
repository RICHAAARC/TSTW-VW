"""
文件用途: 构建 trajectory-aware sampling 的后端 adapter scaffold 产物。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_BACKEND_INTEGRATION_DECISION = "READY_FOR_BACKEND_ADAPTER_SCAFFOLD"
_READY_ADAPTER_SCAFFOLD_DECISION = "READY_FOR_BACKEND_CONNECTION_CONTRACT"


def build_trajectory_aware_sampling_backend_adapter_scaffold(
    backend_integration_decision: dict[str, Any],
    backend_adapter_scaffold_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 生成只描述 schema 的 backend adapter scaffold。

    该函数属于项目特定写法。它把 backend integration decision 转换为后续真实后端连接前需要的
    adapter schema 清单, 包括 adapter 配置 schema、请求转换 schema、结果归一化 schema 和失败 manifest schema。
    此处不导入真实模型库, 不连接真实 DiT / Flow Matching 后端, 不生成视频, 也不执行真实 watermark 算法。
    这一实现的通用工程价值在于: 在高成本或高风险后端接入前, 先冻结输入输出边界和失败路径。
    """
    blocking_reasons: list[str] = []

    required_decision = backend_adapter_scaffold_config.get(
        "required_backend_integration_decision",
        _READY_BACKEND_INTEGRATION_DECISION,
    )
    if (
        backend_integration_decision.get(
            "TrajectoryAwareSamplingBackendIntegrationDecision"
        )
        != required_decision
    ):
        blocking_reasons.append("backend_integration_decision_not_ready")

    required_next_construction = backend_adapter_scaffold_config.get(
        "required_next_allowed_construction_after_backend_integration_decision",
        "backend_adapter_scaffold",
    )
    if (
        backend_integration_decision.get(
            "NextAllowedConstructionAfterBackendIntegrationDecision"
        )
        != required_next_construction
    ):
        blocking_reasons.append("backend_integration_decision_next_step_mismatch")

    if backend_integration_decision.get("backend_adapter_scaffold_allowed") is not True:
        blocking_reasons.append("backend_adapter_scaffold_permission_missing")
    if backend_integration_decision.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("integration_decision_enabled_runtime_backend_connection")
    if backend_integration_decision.get("real_generation_allowed") is not False:
        blocking_reasons.append("integration_decision_enabled_real_generation")
    if backend_integration_decision.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("integration_decision_enabled_real_watermark")

    if backend_adapter_scaffold_config.get("backend_adapter_scaffold_allowed") is not True:
        blocking_reasons.append("config_backend_adapter_scaffold_not_allowed")
    if backend_adapter_scaffold_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("config_enabled_runtime_backend_connection")
    if backend_adapter_scaffold_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("config_enabled_real_generation")
    if backend_adapter_scaffold_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")

    required_schema_kinds = list(
        backend_adapter_scaffold_config.get("required_adapter_schema_kinds", [])
    )
    if not required_schema_kinds:
        blocking_reasons.append("adapter_schema_kinds_missing")

    adapter_schema_descriptors = [
        _build_adapter_schema_descriptor(schema_kind, index)
        for index, schema_kind in enumerate(required_schema_kinds)
    ]
    backend_adapter_kinds = list(
        backend_adapter_scaffold_config.get("backend_adapter_kinds", [])
    )
    adapter_stubs = [
        _build_adapter_stub(adapter_kind, index)
        for index, adapter_kind in enumerate(backend_adapter_kinds)
    ]

    decision = _READY_ADAPTER_SCAFFOLD_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingBackendAdapterScaffoldDecision": decision,
        "TrajectoryAwareSamplingBackendAdapterScaffoldBlockingReasons": blocking_reasons,
        "project_stage": backend_adapter_scaffold_config.get("project_stage"),
        "construction_phase": backend_adapter_scaffold_config.get("construction_phase"),
        "target_construction_phase": backend_adapter_scaffold_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": backend_adapter_scaffold_config.get("runtime_mode"),
        "backend_adapter_scaffold_allowed": decision == _READY_ADAPTER_SCAFFOLD_DECISION,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "adapter_schema_count": len(adapter_schema_descriptors),
        "adapter_stub_count": len(adapter_stubs),
        "adapter_schema_descriptors": adapter_schema_descriptors,
        "adapter_stubs": adapter_stubs,
        "backend_integration_decision_digest": backend_integration_decision.get(
            "backend_integration_decision_digest"
        ),
        "backend_integration_decision_payload_digest": compute_object_digest(
            backend_integration_decision
        ),
        "forbidden_runtime_capabilities_until_backend_connection_contract": list(
            backend_adapter_scaffold_config.get(
                "forbidden_runtime_capabilities_until_backend_connection_contract",
                [],
            )
        ),
        "NextAllowedConstructionAfterBackendAdapterScaffold": (
            backend_adapter_scaffold_config.get(
                "approved_next_construction",
                "backend_connection_contract",
            )
            if decision == _READY_ADAPTER_SCAFFOLD_DECISION
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    payload["backend_adapter_scaffold_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "backend_adapter_scaffold_digest"
        }
    )
    return payload


def _build_adapter_schema_descriptor(schema_kind: object, index: int) -> dict[str, Any]:
    schema_payload = {
        "schema_id": f"adapter_schema_{index:04d}",
        "schema_kind": str(schema_kind),
        "schema_status": "reserved_schema_only",
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
    }
    schema_payload["adapter_schema_digest"] = compute_object_digest(schema_payload)
    return schema_payload


def _build_adapter_stub(adapter_kind: object, index: int) -> dict[str, Any]:
    stub_payload = {
        "adapter_stub_id": f"backend_adapter_stub_{index:04d}",
        "adapter_kind": str(adapter_kind),
        "adapter_status": "not_connected_by_governance",
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
    }
    stub_payload["adapter_stub_digest"] = compute_object_digest(
        stub_payload
    )
    return stub_payload

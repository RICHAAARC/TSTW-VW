"""
文件用途: 构建 trajectory-aware sampling 的真实后端 runtime validation gate.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_PASS_DECISION = "PASS"
_READY_ADAPTER_SCAFFOLD_DECISION = "READY_FOR_BACKEND_CONNECTION_CONTRACT"
_READY_CONNECTION_CONTRACT_DECISION = "READY_FOR_REAL_BACKEND_CONNECTION_SMOKE"


def build_trajectory_aware_sampling_real_backend_runtime_validation_gate(
    real_gpu_backend_connection_smoke_result_gate: dict[str, Any],
    backend_adapter_scaffold: dict[str, Any],
    backend_connection_contract: dict[str, Any],
    runtime_validation_gate_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 验证真实后端 runtime 接入前的 schema、失败路径和治理边界.

    该函数属于项目特定写法. 它只消费已经落盘的 gate 和 scaffold artifact,
    不连接真实后端, 不发起真实视频生成请求, 不执行真实 watermark. 其作用是把
    “是否已经具备进入受控单请求真实生成前的接口治理条件”集中到 repository
    module 中判断, 避免 notebook 直接承载正式协议判断逻辑.
    """
    blocking_reasons: list[str] = []

    required_connection_gate_decision = runtime_validation_gate_config.get(
        "required_real_gpu_backend_connection_smoke_result_gate_decision",
        _PASS_DECISION,
    )
    if (
        real_gpu_backend_connection_smoke_result_gate.get(
            "TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateDecision"
        )
        != required_connection_gate_decision
    ):
        blocking_reasons.append("real_gpu_backend_connection_smoke_result_gate_not_pass")

    required_previous_next_step = runtime_validation_gate_config.get(
        "required_next_allowed_construction_after_connection_smoke_result_gate",
        "real_backend_runtime_validation_gate",
    )
    if (
        real_gpu_backend_connection_smoke_result_gate.get(
            "NextAllowedConstructionAfterRealGpuBackendConnectionSmokeResultGate"
        )
        != required_previous_next_step
    ):
        blocking_reasons.append("connection_smoke_result_gate_next_step_mismatch")

    if (
        backend_adapter_scaffold.get(
            "TrajectoryAwareSamplingBackendAdapterScaffoldDecision"
        )
        != runtime_validation_gate_config.get(
            "required_backend_adapter_scaffold_decision",
            _READY_ADAPTER_SCAFFOLD_DECISION,
        )
    ):
        blocking_reasons.append("backend_adapter_scaffold_not_ready")

    if (
        backend_connection_contract.get(
            "TrajectoryAwareSamplingBackendConnectionContractDecision"
        )
        != runtime_validation_gate_config.get(
            "required_backend_connection_contract_decision",
            _READY_CONNECTION_CONTRACT_DECISION,
        )
    ):
        blocking_reasons.append("backend_connection_contract_not_ready")

    adapter_schema_descriptors = _as_dict_list(
        backend_adapter_scaffold.get("adapter_schema_descriptors", [])
    )
    required_schema_kinds = [
        str(item)
        for item in runtime_validation_gate_config.get(
            "required_adapter_schema_kinds",
            [],
        )
    ]
    observed_schema_kinds = {
        str(item.get("schema_kind"))
        for item in adapter_schema_descriptors
        if isinstance(item, dict)
    }
    missing_schema_kinds = [
        schema_kind
        for schema_kind in required_schema_kinds
        if schema_kind not in observed_schema_kinds
    ]
    if missing_schema_kinds:
        blocking_reasons.append("adapter_schema_kinds_missing_for_runtime_validation")

    minimum_schema_count = int(
        runtime_validation_gate_config.get(
            "minimum_adapter_schema_count",
            len(required_schema_kinds),
        )
    )
    if len(adapter_schema_descriptors) < minimum_schema_count:
        blocking_reasons.append("adapter_schema_count_below_runtime_validation_minimum")

    if _any_runtime_capability_enabled(adapter_schema_descriptors):
        blocking_reasons.append("adapter_schema_enabled_runtime_capability")

    failure_path_descriptors = [
        _build_failure_path_descriptor(failure_path_kind, index)
        for index, failure_path_kind in enumerate(
            runtime_validation_gate_config.get("required_failure_path_kinds", [])
        )
    ]
    if not failure_path_descriptors:
        blocking_reasons.append("runtime_failure_path_descriptors_missing")

    if (
        runtime_validation_gate_config.get(
            "real_generation_allowed_after_runtime_validation",
        )
        is not False
    ):
        blocking_reasons.append("config_enabled_real_generation_after_validation")
    if (
        runtime_validation_gate_config.get(
            "real_watermark_integration_allowed_after_runtime_validation",
        )
        is not False
    ):
        blocking_reasons.append("config_enabled_real_watermark_after_validation")

    if (
        real_gpu_backend_connection_smoke_result_gate.get(
            "external_real_generation_attempted"
        )
        is not False
    ):
        blocking_reasons.append("external_real_generation_attempted_before_validation")
    if (
        real_gpu_backend_connection_smoke_result_gate.get(
            "external_real_watermark_integration_attempted"
        )
        is not False
    ):
        blocking_reasons.append(
            "external_real_watermark_integration_attempted_before_validation"
        )

    decision = _PASS_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingRealBackendRuntimeValidationGateDecision": decision,
        "TrajectoryAwareSamplingRealBackendRuntimeValidationGateBlockingReasons": (
            blocking_reasons
        ),
        "project_stage": runtime_validation_gate_config.get("project_stage"),
        "construction_phase": runtime_validation_gate_config.get("construction_phase"),
        "target_construction_phase": runtime_validation_gate_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": runtime_validation_gate_config.get("runtime_mode"),
        "adapter_schema_validation_status": (
            "PASS" if not missing_schema_kinds else "INCONCLUSIVE"
        ),
        "required_adapter_schema_count": minimum_schema_count,
        "observed_adapter_schema_count": len(adapter_schema_descriptors),
        "missing_adapter_schema_kinds": missing_schema_kinds,
        "failure_path_validation_status": (
            "PASS" if failure_path_descriptors else "INCONCLUSIVE"
        ),
        "failure_path_count": len(failure_path_descriptors),
        "failure_path_descriptors": failure_path_descriptors,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "controlled_real_generation_request_allowed": False,
        "controlled_real_watermark_request_allowed": False,
        "real_gpu_backend_connection_smoke_result_gate_digest": (
            real_gpu_backend_connection_smoke_result_gate.get(
                "real_gpu_backend_connection_smoke_result_gate_digest"
            )
        ),
        "real_gpu_backend_connection_smoke_result_gate_payload_digest": (
            compute_object_digest(real_gpu_backend_connection_smoke_result_gate)
        ),
        "backend_adapter_scaffold_digest": backend_adapter_scaffold.get(
            "backend_adapter_scaffold_digest"
        ),
        "backend_adapter_scaffold_payload_digest": compute_object_digest(
            backend_adapter_scaffold
        ),
        "backend_connection_contract_digest": backend_connection_contract.get(
            "backend_connection_contract_digest"
        ),
        "backend_connection_contract_payload_digest": compute_object_digest(
            backend_connection_contract
        ),
        "NextAllowedConstructionAfterRealBackendRuntimeValidationGate": (
            runtime_validation_gate_config.get(
                "approved_next_construction_after_runtime_validation",
                "explicit_real_generation_transition_decision",
            )
            if decision == _PASS_DECISION
            else "finish_real_backend_runtime_validation_gate"
        ),
    }
    payload["real_backend_runtime_validation_gate_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "real_backend_runtime_validation_gate_digest"
        }
    )
    return payload


def build_real_backend_runtime_validation_report_section(
    runtime_validation_gate: dict[str, Any],
) -> str:
    """功能: 生成 runtime validation gate 的报告补充段落.

    该段落只汇总受治理 artifact 中的判断结果, 便于打包后的报告与新增 gate
    对齐. 它不支持正式论文 claim, 也不表示真实生成或 watermark 已经启用.
    """
    return "\n".join(
        [
            "",
            "## Real Backend Runtime Validation Gate",
            "",
            "该段落由 repository helper 根据受治理 gate artifact 生成.",
            "",
            (
                "real_backend_runtime_validation_gate_decision: "
                f"{runtime_validation_gate.get('TrajectoryAwareSamplingRealBackendRuntimeValidationGateDecision')}"
            ),
            (
                "adapter_schema_validation_status: "
                f"{runtime_validation_gate.get('adapter_schema_validation_status')}"
            ),
            (
                "observed_adapter_schema_count: "
                f"{runtime_validation_gate.get('observed_adapter_schema_count')}"
            ),
            (
                "failure_path_validation_status: "
                f"{runtime_validation_gate.get('failure_path_validation_status')}"
            ),
            (
                "failure_path_count: "
                f"{runtime_validation_gate.get('failure_path_count')}"
            ),
            (
                "next_allowed_construction_after_real_backend_runtime_validation_gate: "
                f"{runtime_validation_gate.get('NextAllowedConstructionAfterRealBackendRuntimeValidationGate')}"
            ),
            (
                "real_generation_allowed: "
                f"{runtime_validation_gate.get('real_generation_allowed')}"
            ),
            (
                "real_watermark_integration_allowed: "
                f"{runtime_validation_gate.get('real_watermark_integration_allowed')}"
            ),
            "",
        ]
    )


def _build_failure_path_descriptor(
    failure_path_kind: object,
    index: int,
) -> dict[str, Any]:
    descriptor = {
        "failure_path_id": f"runtime_failure_path_{index:04d}",
        "failure_path_kind": str(failure_path_kind),
        "failure_path_status": "schema_validated_not_executed",
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
    }
    descriptor["failure_path_digest"] = compute_object_digest(descriptor)
    return descriptor


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _any_runtime_capability_enabled(items: list[dict[str, Any]]) -> bool:
    return any(
        item.get("runtime_backend_connection_allowed") is not False
        or item.get("real_generation_allowed") is not False
        or item.get("real_watermark_integration_allowed") is not False
        for item in items
    )

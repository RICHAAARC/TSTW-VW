"""
文件用途: 构建 trajectory-aware sampling 真实 GPU runtime 的接口脚手架产物。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


def build_trajectory_aware_sampling_runtime_interface_scaffold(
    selection_plan: dict[str, Any],
    backend_transition_decision: dict[str, Any],
    runtime_interface_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 冻结真实 GPU runtime 的最小接口 schema, 不连接真实后端。

    该函数属于项目特定写法。它把已经通过的 record-digest selection plan 转换为
    后续真实 GPU runtime 可以消费的 request schema 和 manifest schema。它不加载
    DiT / Flow Matching, 不生成视频, 不执行 watermark 嵌入或检测。其通用价值在于:
    在高风险后端实现前, 先把输入、输出、preflight 和禁止能力写成可审计 artifact。
    """
    blocking_reasons: list[str] = []

    required_decision = runtime_interface_config.get(
        "required_backend_transition_decision",
        "APPROVED_FOR_RUNTIME_INTERFACE_SCAFFOLD_ONLY",
    )
    if (
        backend_transition_decision.get(
            "TrajectoryAwareSamplingBackendTransitionDecision"
        )
        != required_decision
    ):
        blocking_reasons.append("backend_transition_decision_not_approved")

    required_next_construction = runtime_interface_config.get(
        "required_next_allowed_construction_after_decision",
        "real_gpu_runtime_interface_scaffold",
    )
    if (
        backend_transition_decision.get(
            "NextAllowedConstructionAfterBackendTransitionDecision"
        )
        != required_next_construction
    ):
        blocking_reasons.append("backend_transition_next_construction_mismatch")

    if backend_transition_decision.get("runtime_interface_scaffold_allowed") is not True:
        blocking_reasons.append("runtime_interface_scaffold_not_allowed")
    if backend_transition_decision.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("backend_transition_enabled_runtime_backend")
    if backend_transition_decision.get("real_generation_allowed") is not False:
        blocking_reasons.append("backend_transition_enabled_real_generation")
    if backend_transition_decision.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("backend_transition_enabled_real_watermark")

    if (
        selection_plan.get("SamplingSelectionPlanDecision")
        != runtime_interface_config.get("required_selection_plan_decision", "PASS")
    ):
        blocking_reasons.append("selection_plan_not_passed")
    if (
        selection_plan.get("selection_output_kind")
        != runtime_interface_config.get(
            "required_selection_output_kind",
            "record_digest_selection_plan",
        )
    ):
        blocking_reasons.append("selection_output_kind_mismatch")

    selected_records = selection_plan.get("selected_records", [])
    if not isinstance(selected_records, list):
        selected_records = []
    minimum_selected_count = int(
        runtime_interface_config.get("minimum_selected_record_count", 1)
    )
    if len(selected_records) < minimum_selected_count:
        blocking_reasons.append("selected_record_count_below_minimum")

    if runtime_interface_config.get("runtime_interface_scaffold_allowed") is not True:
        blocking_reasons.append("config_runtime_interface_scaffold_not_allowed")
    if runtime_interface_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("config_runtime_backend_connection_enabled")
    if runtime_interface_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("config_real_generation_enabled")
    if runtime_interface_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_real_watermark_enabled")

    decision = (
        "READY_FOR_REAL_GPU_RUNTIME_INTERFACE_IMPLEMENTATION"
        if not blocking_reasons
        else "INCONCLUSIVE"
    )
    request_prototypes = [
        _build_request_prototype(record, index)
        for index, record in enumerate(selected_records)
        if isinstance(record, dict)
    ]
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingRuntimeInterfaceScaffoldDecision": decision,
        "TrajectoryAwareSamplingRuntimeInterfaceScaffoldBlockingReasons": (
            blocking_reasons
        ),
        "project_stage": runtime_interface_config.get("project_stage"),
        "construction_phase": runtime_interface_config.get("construction_phase"),
        "target_construction_phase": runtime_interface_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": runtime_interface_config.get("runtime_mode"),
        "backend_protocol_shape_kind": runtime_interface_config.get(
            "backend_protocol_shape_kind"
        ),
        "request_schema_kind": runtime_interface_config.get("request_schema_kind"),
        "result_manifest_schema_kind": runtime_interface_config.get(
            "result_manifest_schema_kind"
        ),
        "gpu_preflight_schema_kind": runtime_interface_config.get(
            "gpu_preflight_schema_kind"
        ),
        "request_required_fields": list(
            runtime_interface_config.get("request_required_fields", [])
        ),
        "result_manifest_required_fields": list(
            runtime_interface_config.get("result_manifest_required_fields", [])
        ),
        "gpu_preflight_required_fields": list(
            runtime_interface_config.get("gpu_preflight_required_fields", [])
        ),
        "request_prototypes": request_prototypes,
        "request_prototype_count": len(request_prototypes),
        "selected_record_count": len(selected_records),
        "selection_plan_digest": selection_plan.get("selection_plan_digest"),
        "backend_transition_decision_digest": backend_transition_decision.get(
            "backend_transition_decision_digest"
        ),
        "backend_transition_decision_payload_digest": compute_object_digest(
            backend_transition_decision
        ),
        "runtime_interface_scaffold_allowed": (
            decision == "READY_FOR_REAL_GPU_RUNTIME_INTERFACE_IMPLEMENTATION"
        ),
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "forbidden_runtime_capabilities_until_backend_implementation": list(
            runtime_interface_config.get(
                "forbidden_runtime_capabilities_until_backend_implementation",
                [],
            )
        ),
        "NextAllowedConstructionAfterRuntimeInterfaceScaffold": (
            "real_gpu_runtime_interface_implementation"
            if decision == "READY_FOR_REAL_GPU_RUNTIME_INTERFACE_IMPLEMENTATION"
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    payload["runtime_interface_scaffold_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "runtime_interface_scaffold_digest"
        }
    )
    return payload


def _build_request_prototype(record: dict[str, Any], index: int) -> dict[str, Any]:
    record_digest = str(record.get("record_digest", ""))
    return {
        "request_id": f"trajectory_replay_request_{index:04d}",
        "selected_record_digest": record_digest,
        "event_id": str(record.get("event_id", "")),
        "sample_id": str(record.get("sample_id", "")),
        "method_variant": str(record.get("method_variant", "")),
        "attack_name": str(record.get("attack_name", "")),
        "selection_policy_kind": str(record.get("selection_policy_kind", "")),
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "request_digest": compute_object_digest(
            {
                "request_index": index,
                "selected_record_digest": record_digest,
                "event_id": record.get("event_id"),
                "sample_id": record.get("sample_id"),
                "method_variant": record.get("method_variant"),
                "attack_name": record.get("attack_name"),
                "selection_policy_kind": record.get("selection_policy_kind"),
            }
        ),
    }

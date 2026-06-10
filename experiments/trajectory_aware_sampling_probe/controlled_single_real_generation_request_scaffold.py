"""
文件用途: 构建 trajectory-aware sampling 的单条受控真实生成请求 scaffold.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_TRANSITION_DECISION = (
    "READY_FOR_CONTROLLED_SINGLE_REAL_GENERATION_REQUEST_SCAFFOLD"
)
_READY_SCAFFOLD_DECISION = "READY_FOR_MANUAL_CONTROLLED_REAL_GENERATION_REQUEST_RUN"


def build_trajectory_aware_sampling_controlled_single_real_generation_request_scaffold(
    explicit_transition_decision: dict[str, Any],
    selection_plan: dict[str, Any],
    request_scaffold_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 生成单条受控真实生成请求的 schema-only scaffold.

    该函数属于项目特定的治理实现. 它只从已经冻结的 selection plan 中选择一条
    record digest, 并为后续手动 GPU 执行准备请求边界、失败 manifest 边界和
    non-claim 输出边界. 该函数不导入真实生成后端, 不发起真实视频生成请求,
    不执行真实 watermark.
    """
    blocking_reasons: list[str] = []

    if (
        explicit_transition_decision.get(
            "TrajectoryAwareSamplingExplicitRealGenerationTransitionDecision"
        )
        != request_scaffold_config.get(
            "required_explicit_real_generation_transition_decision",
            _READY_TRANSITION_DECISION,
        )
    ):
        blocking_reasons.append("explicit_real_generation_transition_decision_not_ready")

    if (
        explicit_transition_decision.get(
            "NextAllowedConstructionAfterExplicitRealGenerationTransitionDecision"
        )
        != request_scaffold_config.get(
            "required_next_allowed_construction_after_transition_decision",
            "controlled_single_real_generation_request_scaffold",
        )
    ):
        blocking_reasons.append("explicit_transition_next_step_mismatch")

    if explicit_transition_decision.get("controlled_request_scaffold_allowed") is not True:
        blocking_reasons.append("controlled_request_scaffold_not_allowed")
    if explicit_transition_decision.get("real_generation_execution_allowed") is not False:
        blocking_reasons.append("transition_decision_enabled_real_generation_execution")
    if explicit_transition_decision.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("transition_decision_enabled_real_watermark")

    maximum_request_count = int(
        request_scaffold_config.get("maximum_controlled_request_count", 1)
    )
    if maximum_request_count != 1:
        blocking_reasons.append("controlled_request_count_must_be_one")

    selected_records = _selected_records(selection_plan)
    if not selected_records:
        blocking_reasons.append("selection_plan_has_no_selected_records")

    selected_record = selected_records[0] if selected_records else {}
    request_descriptor = _build_request_descriptor(
        selected_record,
        request_scaffold_config,
    )
    handoff_descriptor = _build_manual_handoff_descriptor(
        request_descriptor,
        request_scaffold_config,
    )
    failure_manifest_schema = _build_failure_manifest_schema(
        request_descriptor,
        request_scaffold_config,
    )
    output_boundary = _build_output_boundary(request_scaffold_config)

    decision = _READY_SCAFFOLD_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingControlledSingleRealGenerationRequestScaffoldDecision": (
            decision
        ),
        "TrajectoryAwareSamplingControlledSingleRealGenerationRequestScaffoldBlockingReasons": (
            blocking_reasons
        ),
        "project_stage": request_scaffold_config.get("project_stage"),
        "construction_phase": request_scaffold_config.get("construction_phase"),
        "target_construction_phase": request_scaffold_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": request_scaffold_config.get("runtime_mode"),
        "controlled_request_scaffold_ready": decision == _READY_SCAFFOLD_DECISION,
        "manual_gpu_execution_required": True,
        "controlled_real_generation_request_allowed": False,
        "real_generation_execution_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
        "maximum_controlled_request_count": maximum_request_count,
        "selected_request_count": 1 if selected_records else 0,
        "request_descriptor": request_descriptor,
        "manual_execution_handoff_descriptor": handoff_descriptor,
        "runtime_failure_manifest_schema": failure_manifest_schema,
        "non_claim_output_boundary": output_boundary,
        "explicit_real_generation_transition_decision_digest": (
            explicit_transition_decision.get(
                "explicit_real_generation_transition_decision_digest"
            )
        ),
        "explicit_real_generation_transition_decision_payload_digest": (
            compute_object_digest(explicit_transition_decision)
        ),
        "selection_plan_digest": selection_plan.get("selection_plan_digest"),
        "selection_plan_payload_digest": compute_object_digest(selection_plan),
        "NextRequiredExternalExecutionAfterControlledSingleRequestScaffold": (
            request_scaffold_config.get(
                "next_required_external_execution_after_scaffold",
                "manual_controlled_single_real_generation_request_run",
            )
            if decision == _READY_SCAFFOLD_DECISION
            else "finish_controlled_single_real_generation_request_scaffold"
        ),
    }
    payload["controlled_single_real_generation_request_scaffold_digest"] = (
        compute_object_digest(
            {
                key: value
                for key, value in payload.items()
                if key != "controlled_single_real_generation_request_scaffold_digest"
            }
        )
    )
    return payload


def build_controlled_single_real_generation_request_scaffold_report_section(
    scaffold: dict[str, Any],
) -> str:
    """功能: 生成单条受控真实生成请求 scaffold 的报告补充段落."""
    return "\n".join(
        [
            "",
            "## Controlled Single Real Generation Request Scaffold",
            "",
            "该段落只汇总单条受控请求 scaffold, 不表示真实生成已经执行.",
            "",
            (
                "controlled_single_real_generation_request_scaffold_decision: "
                f"{scaffold.get('TrajectoryAwareSamplingControlledSingleRealGenerationRequestScaffoldDecision')}"
            ),
            (
                "selected_request_count: "
                f"{scaffold.get('selected_request_count')}"
            ),
            (
                "manual_gpu_execution_required: "
                f"{scaffold.get('manual_gpu_execution_required')}"
            ),
            (
                "real_generation_execution_allowed: "
                f"{scaffold.get('real_generation_execution_allowed')}"
            ),
            (
                "real_watermark_integration_allowed: "
                f"{scaffold.get('real_watermark_integration_allowed')}"
            ),
            (
                "next_required_external_execution_after_controlled_single_request_scaffold: "
                f"{scaffold.get('NextRequiredExternalExecutionAfterControlledSingleRequestScaffold')}"
            ),
            "",
        ]
    )


def _selected_records(selection_plan: dict[str, Any]) -> list[dict[str, Any]]:
    records = selection_plan.get("selected_records", [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _build_request_descriptor(
    selected_record: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    descriptor = {
        "controlled_request_id": "controlled_real_generation_request_0000",
        "selected_record_digest": str(selected_record.get("record_digest", "")),
        "event_id": str(selected_record.get("event_id", "")),
        "sample_id": str(selected_record.get("sample_id", "")),
        "method_variant": str(selected_record.get("method_variant", "")),
        "attack_name": str(selected_record.get("attack_name", "")),
        "request_schema_kind": "controlled_single_real_generation_request_schema",
        "backend_invocation_boundary_kind": str(
            config.get(
                "backend_invocation_boundary_kind",
                "manual_gpu_backend_invocation_boundary",
            )
        ),
        "controlled_real_generation_request_allowed": False,
        "real_generation_execution_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
    }
    descriptor["controlled_request_digest"] = compute_object_digest(descriptor)
    return descriptor


def _build_manual_handoff_descriptor(
    request_descriptor: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    descriptor = {
        "handoff_kind": "manual_controlled_single_real_generation_request_handoff",
        "controlled_request_digest": request_descriptor.get(
            "controlled_request_digest"
        ),
        "required_runtime": config.get("required_runtime", "external_gpu"),
        "manual_gpu_execution_required": True,
        "automatic_backend_invocation_allowed": False,
        "real_generation_execution_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
    }
    descriptor["manual_handoff_digest"] = compute_object_digest(descriptor)
    return descriptor


def _build_failure_manifest_schema(
    request_descriptor: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    schema = {
        "failure_manifest_schema_kind": "controlled_single_request_failure_manifest_schema",
        "controlled_request_digest": request_descriptor.get(
            "controlled_request_digest"
        ),
        "failure_manifest_required": True,
        "required_failure_fields": list(config.get("required_failure_fields", [])),
        "formal_claim_support_allowed": False,
    }
    schema["failure_manifest_schema_digest"] = compute_object_digest(schema)
    return schema


def _build_output_boundary(config: dict[str, Any]) -> dict[str, Any]:
    boundary = {
        "output_boundary_kind": "controlled_single_request_non_claim_output_boundary",
        "allowed_output_artifact_kinds": list(
            config.get("allowed_output_artifact_kinds", [])
        ),
        "formal_claim_support_allowed": False,
        "records_required_before_claim_support": True,
        "real_watermark_integration_allowed": False,
    }
    boundary["output_boundary_digest"] = compute_object_digest(boundary)
    return boundary


"""
文件用途: 构建 trajectory-aware sampling 的外部受控真实生成执行 handoff.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_AUTHORIZATION_DECISION = "READY_FOR_EXTERNAL_CONTROLLED_REAL_GENERATION_EXECUTION_HANDOFF"
_READY_HANDOFF_DECISION = "READY_FOR_EXTERNAL_CONTROLLED_REAL_GENERATION_EXECUTION_RUN"


def build_trajectory_aware_sampling_external_controlled_real_generation_execution_handoff(
    authorization_decision: dict[str, Any],
    controlled_single_request_scaffold: dict[str, Any],
    handoff_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 生成外部 GPU 手动执行单条真实视频生成请求所需的 handoff.

    该函数属于项目特定的治理实现. 它只生成外部执行描述、请求 digest 绑定、允许输出边界和
    失败 manifest schema, 不导入真实生成模型, 不调用 DiT / Flow Matching / VAE 后端, 不执行
    watermark. 该 handoff 的用途是让用户在 Colab 或其他外部 GPU 环境中手动执行 1 条受控请求,
    并把结果作为 non-claim artifact 带回后续 gate 校验.
    """
    blocking_reasons: list[str] = []

    required_authorization_decision = handoff_config.get(
        "required_authorization_decision",
        _READY_AUTHORIZATION_DECISION,
    )
    if (
        authorization_decision.get(
            "TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationDecision"
        )
        != required_authorization_decision
    ):
        blocking_reasons.append("governed_real_generation_execution_not_authorized")

    if authorization_decision.get("real_generation_execution_authorized") is not True:
        blocking_reasons.append("real_generation_execution_authorized_flag_missing")
    if authorization_decision.get("controlled_real_generation_execution_handoff_allowed") is not True:
        blocking_reasons.append("controlled_real_generation_execution_handoff_not_allowed")
    if authorization_decision.get("real_watermark_integration_authorized") is not False:
        blocking_reasons.append("authorization_enabled_real_watermark")
    if authorization_decision.get("formal_claim_support_authorized") is not False:
        blocking_reasons.append("authorization_enabled_formal_claim")

    request_descriptor = _as_dict(controlled_single_request_scaffold.get("request_descriptor"))
    controlled_request_digest = str(request_descriptor.get("controlled_request_digest", ""))
    if not controlled_request_digest:
        blocking_reasons.append("controlled_request_digest_missing")
    if authorization_decision.get("controlled_request_digest") != controlled_request_digest:
        blocking_reasons.append("authorization_request_digest_mismatch")

    maximum_request_count = int(handoff_config.get("maximum_external_controlled_request_count", 1))
    if maximum_request_count != 1:
        blocking_reasons.append("external_controlled_request_count_must_be_one")

    if handoff_config.get("repository_internal_backend_invocation_allowed") is not False:
        blocking_reasons.append("config_enabled_repository_internal_backend_invocation")
    if handoff_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")
    if handoff_config.get("formal_claim_support_allowed") is not False:
        blocking_reasons.append("config_enabled_formal_claim")

    execution_descriptor = _build_execution_descriptor(
        request_descriptor,
        authorization_decision,
        handoff_config,
    )
    result_schema = _build_external_result_schema(execution_descriptor, handoff_config)
    failure_manifest_schema = _build_external_failure_manifest_schema(
        execution_descriptor,
        handoff_config,
    )
    output_boundary = _build_external_output_boundary(handoff_config)

    decision = _READY_HANDOFF_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffDecision": decision,
        "TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffBlockingReasons": blocking_reasons,
        "project_stage": handoff_config.get("project_stage"),
        "construction_phase": handoff_config.get("construction_phase"),
        "target_construction_phase": handoff_config.get("target_construction_phase"),
        "runtime_mode": handoff_config.get("runtime_mode"),
        "external_controlled_real_generation_execution_ready": decision == _READY_HANDOFF_DECISION,
        "external_gpu_execution_required": True,
        "manual_external_execution_required": True,
        "maximum_external_controlled_request_count": maximum_request_count,
        "repository_internal_backend_invocation_allowed": False,
        "external_real_generation_execution_allowed": decision == _READY_HANDOFF_DECISION,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
        "controlled_request_digest": controlled_request_digest,
        "execution_descriptor": execution_descriptor,
        "external_result_schema": result_schema,
        "external_failure_manifest_schema": failure_manifest_schema,
        "non_claim_output_boundary": output_boundary,
        "governed_real_generation_execution_authorization_decision_digest": authorization_decision.get(
            "governed_real_generation_execution_authorization_decision_digest"
        ),
        "governed_real_generation_execution_authorization_decision_payload_digest": compute_object_digest(
            authorization_decision
        ),
        "controlled_single_request_scaffold_digest": controlled_single_request_scaffold.get(
            "controlled_single_real_generation_request_scaffold_digest"
        ),
        "controlled_single_request_scaffold_payload_digest": compute_object_digest(
            controlled_single_request_scaffold
        ),
        "NextRequiredExternalExecutionAfterExternalControlledRealGenerationExecutionHandoff": (
            handoff_config.get(
                "next_required_external_execution_after_handoff",
                "external_controlled_single_real_generation_execution_run",
            )
            if decision == _READY_HANDOFF_DECISION
            else "finish_external_controlled_real_generation_execution_handoff"
        ),
    }
    payload["external_controlled_real_generation_execution_handoff_digest"] = (
        compute_object_digest(
            {
                key: value
                for key, value in payload.items()
                if key != "external_controlled_real_generation_execution_handoff_digest"
            }
        )
    )
    return payload


def build_external_controlled_real_generation_execution_handoff_report_section(
    handoff: dict[str, Any],
) -> str:
    """功能: 生成外部受控真实生成执行 handoff 的报告补充段落."""
    return "\n".join(
        [
            "",
            "## External Controlled Real Generation Execution Handoff",
            "",
            "该段落只汇总外部单条真实生成执行 handoff, 不表示仓库已经内置真实生成后端或 watermark.",
            "",
            (
                "external_controlled_real_generation_execution_handoff_decision: "
                f"{handoff.get('TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffDecision')}"
            ),
            (
                "external_controlled_real_generation_execution_ready: "
                f"{handoff.get('external_controlled_real_generation_execution_ready')}"
            ),
            (
                "external_real_generation_execution_allowed: "
                f"{handoff.get('external_real_generation_execution_allowed')}"
            ),
            (
                "repository_internal_backend_invocation_allowed: "
                f"{handoff.get('repository_internal_backend_invocation_allowed')}"
            ),
            (
                "real_watermark_integration_allowed: "
                f"{handoff.get('real_watermark_integration_allowed')}"
            ),
            (
                "formal_claim_support_allowed: "
                f"{handoff.get('formal_claim_support_allowed')}"
            ),
            (
                "next_required_external_execution_after_external_controlled_real_generation_execution_handoff: "
                f"{handoff.get('NextRequiredExternalExecutionAfterExternalControlledRealGenerationExecutionHandoff')}"
            ),
            "",
        ]
    )


def _build_execution_descriptor(
    request_descriptor: dict[str, Any],
    authorization_decision: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    descriptor = {
        "execution_descriptor_kind": "external_controlled_single_real_generation_execution_descriptor",
        "controlled_request_id": request_descriptor.get("controlled_request_id"),
        "controlled_request_digest": request_descriptor.get("controlled_request_digest"),
        "selected_record_digest": request_descriptor.get("selected_record_digest"),
        "event_id": request_descriptor.get("event_id"),
        "sample_id": request_descriptor.get("sample_id"),
        "method_variant": request_descriptor.get("method_variant"),
        "attack_name": request_descriptor.get("attack_name"),
        "required_runtime": config.get("required_runtime", "external_gpu"),
        "execution_boundary_kind": config.get(
            "execution_boundary_kind",
            "manual_external_gpu_single_request_boundary",
        ),
        "repository_internal_backend_invocation_allowed": False,
        "external_real_generation_execution_allowed": True,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
        "authorization_decision_digest": authorization_decision.get(
            "governed_real_generation_execution_authorization_decision_digest"
        ),
    }
    descriptor["execution_descriptor_digest"] = compute_object_digest(descriptor)
    return descriptor


def _build_external_result_schema(
    execution_descriptor: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    schema = {
        "external_result_schema_kind": "external_controlled_single_real_generation_result_schema",
        "controlled_request_digest": execution_descriptor.get("controlled_request_digest"),
        "required_result_fields": list(config.get("required_external_result_fields", [])),
        "required_result_artifact_kinds": list(config.get("required_result_artifact_kinds", [])),
        "formal_claim_support_allowed": False,
    }
    schema["external_result_schema_digest"] = compute_object_digest(schema)
    return schema


def _build_external_failure_manifest_schema(
    execution_descriptor: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    schema = {
        "external_failure_manifest_schema_kind": "external_controlled_single_real_generation_failure_manifest_schema",
        "controlled_request_digest": execution_descriptor.get("controlled_request_digest"),
        "failure_manifest_required": True,
        "required_failure_fields": list(config.get("required_failure_fields", [])),
        "formal_claim_support_allowed": False,
    }
    schema["external_failure_manifest_schema_digest"] = compute_object_digest(schema)
    return schema


def _build_external_output_boundary(config: dict[str, Any]) -> dict[str, Any]:
    boundary = {
        "output_boundary_kind": "external_controlled_single_real_generation_non_claim_output_boundary",
        "allowed_output_artifact_kinds": list(config.get("allowed_output_artifact_kinds", [])),
        "maximum_external_controlled_request_count": int(
            config.get("maximum_external_controlled_request_count", 1)
        ),
        "repository_internal_backend_invocation_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
    }
    boundary["output_boundary_digest"] = compute_object_digest(boundary)
    return boundary


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

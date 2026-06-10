
"""
文件用途: 构建外部受控单条真实生成执行 run package.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_HANDOFF_DECISION = "READY_FOR_EXTERNAL_CONTROLLED_REAL_GENERATION_EXECUTION_RUN"
_READY_RUN_PACKAGE_DECISION = "READY_FOR_MANUAL_EXTERNAL_MODEL_EXECUTION"


def build_trajectory_aware_sampling_external_controlled_single_real_generation_execution_run(
    external_execution_handoff: dict[str, Any],
    run_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 生成外部 GPU 手动执行真实生成所需的 run package.

    该函数只把 handoff 转换为可执行说明、模型选择边界和结果模板. 它不会在仓库内加载真实
    生成模型, 不调用 DiT / Flow Matching / VAE 后端, 不执行 watermark. 真实生成必须由用户在
    Colab 或同等外部 GPU 环境手动完成, 并把结果摘要按模板带回后续 intake gate.
    """
    blocking_reasons: list[str] = []

    if (
        external_execution_handoff.get(
            "TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffDecision"
        )
        != run_config.get("required_external_execution_handoff_decision", _READY_HANDOFF_DECISION)
    ):
        blocking_reasons.append("external_controlled_real_generation_execution_handoff_not_ready")

    if external_execution_handoff.get("external_controlled_real_generation_execution_ready") is not True:
        blocking_reasons.append("external_controlled_real_generation_execution_ready_flag_missing")
    if external_execution_handoff.get("external_real_generation_execution_allowed") is not True:
        blocking_reasons.append("external_real_generation_execution_not_allowed")
    if external_execution_handoff.get("repository_internal_backend_invocation_allowed") is not False:
        blocking_reasons.append("handoff_enabled_repository_internal_backend_invocation")
    if external_execution_handoff.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("handoff_enabled_real_watermark")
    if external_execution_handoff.get("formal_claim_support_allowed") is not False:
        blocking_reasons.append("handoff_enabled_formal_claim")

    maximum_request_count = int(run_config.get("maximum_external_controlled_request_count", 1))
    if maximum_request_count != 1:
        blocking_reasons.append("external_controlled_request_count_must_be_one")

    if run_config.get("repository_internal_backend_invocation_allowed") is not False:
        blocking_reasons.append("config_enabled_repository_internal_backend_invocation")
    if run_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")
    if run_config.get("formal_claim_support_allowed") is not False:
        blocking_reasons.append("config_enabled_formal_claim")

    execution_descriptor = _as_dict(external_execution_handoff.get("execution_descriptor"))
    controlled_request_digest = str(execution_descriptor.get("controlled_request_digest", ""))
    if not controlled_request_digest:
        blocking_reasons.append("controlled_request_digest_missing")

    model_execution_boundary = _build_model_execution_boundary(run_config)
    manual_execution_steps = _build_manual_execution_steps(run_config)
    result_submission_template = _build_result_submission_template(
        controlled_request_digest,
        execution_descriptor,
        external_execution_handoff,
        run_config,
    )

    decision = _READY_RUN_PACKAGE_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunDecision": decision,
        "TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunBlockingReasons": blocking_reasons,
        "project_stage": run_config.get("project_stage"),
        "construction_phase": run_config.get("construction_phase"),
        "target_construction_phase": run_config.get("target_construction_phase"),
        "runtime_mode": run_config.get("runtime_mode"),
        "external_controlled_single_real_generation_execution_run_ready": decision == _READY_RUN_PACKAGE_DECISION,
        "external_gpu_execution_required": True,
        "manual_external_model_execution_required": True,
        "external_model_loading_required": True,
        "maximum_external_controlled_request_count": maximum_request_count,
        "repository_internal_backend_invocation_allowed": False,
        "external_real_generation_execution_allowed": decision == _READY_RUN_PACKAGE_DECISION,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
        "controlled_request_digest": controlled_request_digest,
        "execution_descriptor": execution_descriptor,
        "model_execution_boundary": model_execution_boundary,
        "manual_execution_steps": manual_execution_steps,
        "result_submission_template": result_submission_template,
        "external_execution_handoff_digest": external_execution_handoff.get(
            "external_controlled_real_generation_execution_handoff_digest"
        ),
        "external_execution_handoff_payload_digest": compute_object_digest(
            external_execution_handoff
        ),
        "NextRequiredExternalActionAfterExternalControlledSingleRealGenerationExecutionRun": (
            run_config.get(
                "next_required_external_action_after_run_package",
                "manual_external_model_execution_and_result_upload",
            )
            if decision == _READY_RUN_PACKAGE_DECISION
            else "finish_external_controlled_single_real_generation_execution_run"
        ),
    }
    payload["external_controlled_single_real_generation_execution_run_digest"] = (
        compute_object_digest(
            {
                key: value
                for key, value in payload.items()
                if key != "external_controlled_single_real_generation_execution_run_digest"
            }
        )
    )
    return payload


def build_external_controlled_single_real_generation_execution_run_report_section(
    run_package: dict[str, Any],
) -> str:
    """功能: 生成外部受控单条真实生成执行 run package 的报告段落."""
    return "\n".join(
        [
            "",
            "## External Controlled Single Real Generation Execution Run",
            "",
            "该段落只汇总外部手动执行 run package, 不表示仓库已经自动加载或调用真实生成模型.",
            "",
            (
                "external_controlled_single_real_generation_execution_run_decision: "
                f"{run_package.get('TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunDecision')}"
            ),
            (
                "external_controlled_single_real_generation_execution_run_ready: "
                f"{run_package.get('external_controlled_single_real_generation_execution_run_ready')}"
            ),
            (
                "external_model_loading_required: "
                f"{run_package.get('external_model_loading_required')}"
            ),
            (
                "external_real_generation_execution_allowed: "
                f"{run_package.get('external_real_generation_execution_allowed')}"
            ),
            (
                "repository_internal_backend_invocation_allowed: "
                f"{run_package.get('repository_internal_backend_invocation_allowed')}"
            ),
            (
                "real_watermark_integration_allowed: "
                f"{run_package.get('real_watermark_integration_allowed')}"
            ),
            (
                "formal_claim_support_allowed: "
                f"{run_package.get('formal_claim_support_allowed')}"
            ),
            (
                "next_required_external_action_after_external_controlled_single_real_generation_execution_run: "
                f"{run_package.get('NextRequiredExternalActionAfterExternalControlledSingleRealGenerationExecutionRun')}"
            ),
            "",
        ]
    )


def _build_model_execution_boundary(config: dict[str, Any]) -> dict[str, Any]:
    boundary = {
        "model_execution_boundary_kind": "manual_external_model_execution_boundary",
        "allowed_external_model_interface_kinds": list(
            config.get("allowed_external_model_interface_kinds", [])
        ),
        "model_identity_record_required": True,
        "runtime_environment_snapshot_required": True,
        "generated_video_artifact_metadata_required": True,
        "repository_internal_backend_invocation_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
    }
    boundary["model_execution_boundary_digest"] = compute_object_digest(boundary)
    return boundary


def _build_manual_execution_steps(config: dict[str, Any]) -> list[dict[str, Any]]:
    steps = []
    for index, step in enumerate(config.get("manual_execution_step_kinds", [])):
        descriptor = {
            "manual_execution_step_id": f"manual_external_execution_step_{index:04d}",
            "manual_execution_step_kind": str(step),
            "repository_internal_backend_invocation_allowed": False,
            "real_watermark_integration_allowed": False,
            "formal_claim_support_allowed": False,
        }
        descriptor["manual_execution_step_digest"] = compute_object_digest(descriptor)
        steps.append(descriptor)
    return steps


def _build_result_submission_template(
    controlled_request_digest: str,
    execution_descriptor: dict[str, Any],
    external_execution_handoff: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    template = {
        "result_template_kind": "external_controlled_single_real_generation_result_submission_template",
        "controlled_request_digest": controlled_request_digest,
        "controlled_request_id": execution_descriptor.get("controlled_request_id"),
        "external_real_generation_execution_status": "pending_manual_external_execution",
        "required_result_fields": list(config.get("required_result_fields", [])),
        "required_result_artifact_kinds": list(config.get("required_result_artifact_kinds", [])),
        "runtime_failure_manifest_required": True,
        "generated_video_artifact_metadata_required": True,
        "external_result_schema_digest": _as_dict(
            external_execution_handoff.get("external_result_schema")
        ).get("external_result_schema_digest"),
        "external_failure_manifest_schema_digest": _as_dict(
            external_execution_handoff.get("external_failure_manifest_schema")
        ).get("external_failure_manifest_schema_digest"),
        "formal_claim_support_allowed": False,
    }
    template["result_template_digest"] = compute_object_digest(template)
    return template


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

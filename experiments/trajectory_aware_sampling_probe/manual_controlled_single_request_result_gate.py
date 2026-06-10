
"""
文件用途: 校验外部手动单请求运行结果是否满足 trajectory-aware sampling 的治理边界.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_SCAFFOLD_DECISION = "READY_FOR_MANUAL_CONTROLLED_REAL_GENERATION_REQUEST_RUN"
_PASS_DECISION = "PASS"


def build_trajectory_aware_sampling_manual_controlled_single_request_result_gate(
    controlled_single_request_scaffold: dict[str, Any],
    external_manual_request_results: dict[str, Any],
    result_gate_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 校验手动单请求运行结果, 并保持当前阶段不自动启用真实生成.

    该函数属于项目特定的治理 gate. 它只消费 Colab 或同等外部 GPU 环境已经写出的
    结果摘要, 不导入真实生成后端, 不发起视频生成请求, 不执行真实 watermark. 当前阶段的
    主要价值在于确认单条请求的 digest 绑定、运行环境记录、模型身份记录、失败路径记录和
    non-claim 输出边界是否完整, 为后续显式授权真实生成执行提供可审计输入.
    """
    blocking_reasons: list[str] = []

    required_scaffold_decision = result_gate_config.get(
        "required_controlled_single_request_scaffold_decision",
        _READY_SCAFFOLD_DECISION,
    )
    if (
        controlled_single_request_scaffold.get(
            "TrajectoryAwareSamplingControlledSingleRealGenerationRequestScaffoldDecision"
        )
        != required_scaffold_decision
    ):
        blocking_reasons.append("controlled_single_request_scaffold_not_ready")

    required_external_execution = result_gate_config.get(
        "required_next_external_execution_after_scaffold",
        "manual_controlled_single_real_generation_request_run",
    )
    if (
        controlled_single_request_scaffold.get(
            "NextRequiredExternalExecutionAfterControlledSingleRequestScaffold"
        )
        != required_external_execution
    ):
        blocking_reasons.append("controlled_single_request_scaffold_next_step_mismatch")

    if controlled_single_request_scaffold.get("controlled_request_scaffold_ready") is not True:
        blocking_reasons.append("controlled_single_request_scaffold_ready_flag_missing")
    if controlled_single_request_scaffold.get("manual_gpu_execution_required") is not True:
        blocking_reasons.append("manual_gpu_execution_requirement_missing")

    request_descriptor = _as_dict(
        controlled_single_request_scaffold.get("request_descriptor")
    )
    scaffold_request_digest = str(request_descriptor.get("controlled_request_digest", ""))
    external_request_digest = str(
        external_manual_request_results.get("controlled_request_digest", "")
    )
    if not scaffold_request_digest:
        blocking_reasons.append("controlled_request_digest_missing_from_scaffold")
    if external_request_digest != scaffold_request_digest:
        blocking_reasons.append("controlled_request_digest_mismatch")

    required_status = str(
        result_gate_config.get("required_manual_request_result_status_for_pass", _PASS_DECISION)
    )
    result_status = str(
        external_manual_request_results.get("manual_controlled_single_request_result_status", "")
    )
    if result_status != required_status:
        blocking_reasons.append("manual_controlled_single_request_result_status_not_pass")

    if external_manual_request_results.get("external_gpu_runtime_detected") is not True:
        blocking_reasons.append("external_gpu_runtime_not_detected")
    if external_manual_request_results.get("external_model_identity_recorded") is not True:
        blocking_reasons.append("external_model_identity_not_recorded")
    if external_manual_request_results.get("controlled_single_request_result_recorded") is not True:
        blocking_reasons.append("controlled_single_request_result_not_recorded")

    allow_real_generation_attempt = (
        result_gate_config.get("external_real_generation_attempt_allowed") is True
    )
    if (
        external_manual_request_results.get("external_real_generation_attempted") is True
        and not allow_real_generation_attempt
    ):
        blocking_reasons.append("external_real_generation_attempted_without_authorization")
    if external_manual_request_results.get("external_real_watermark_integration_attempted") is not False:
        blocking_reasons.append("external_real_watermark_integration_attempted_unexpectedly")

    if result_gate_config.get("real_generation_execution_allowed_after_result_gate") is not False:
        blocking_reasons.append("config_enabled_real_generation_after_result_gate")
    if result_gate_config.get("real_watermark_integration_allowed_after_result_gate") is not False:
        blocking_reasons.append("config_enabled_real_watermark_after_result_gate")
    if result_gate_config.get("formal_claim_support_allowed_after_result_gate") is not False:
        blocking_reasons.append("config_enabled_formal_claim_after_result_gate")

    result_artifacts = _normalize_result_artifacts(external_manual_request_results)
    required_artifact_kinds = [
        str(kind) for kind in result_gate_config.get("required_result_artifact_kinds", [])
    ]
    observed_artifact_kinds = {
        str(artifact.get("result_artifact_kind"))
        for artifact in result_artifacts
        if isinstance(artifact, dict)
    }
    missing_artifact_kinds = [
        kind for kind in required_artifact_kinds if kind not in observed_artifact_kinds
    ]
    if missing_artifact_kinds:
        blocking_reasons.append("missing_required_manual_request_result_artifacts")

    failure_manifest = _as_dict(
        external_manual_request_results.get("runtime_failure_manifest")
    )
    if failure_manifest.get("failure_manifest_recorded") is not True:
        blocking_reasons.append("runtime_failure_manifest_not_recorded")

    decision = _PASS_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision": decision,
        "TrajectoryAwareSamplingManualControlledSingleRequestResultGateBlockingReasons": blocking_reasons,
        "project_stage": result_gate_config.get("project_stage"),
        "construction_phase": result_gate_config.get("construction_phase"),
        "target_construction_phase": result_gate_config.get("target_construction_phase"),
        "runtime_mode": result_gate_config.get("runtime_mode"),
        "manual_controlled_single_request_result_status": result_status,
        "controlled_request_digest": scaffold_request_digest,
        "external_controlled_request_digest": external_request_digest,
        "external_gpu_runtime_detected": external_manual_request_results.get("external_gpu_runtime_detected") is True,
        "external_model_identity_recorded": external_manual_request_results.get("external_model_identity_recorded") is True,
        "controlled_single_request_result_recorded": external_manual_request_results.get("controlled_single_request_result_recorded") is True,
        "external_real_generation_attempted": external_manual_request_results.get("external_real_generation_attempted") is True,
        "external_real_generation_attempt_allowed": allow_real_generation_attempt,
        "external_real_watermark_integration_attempted": external_manual_request_results.get("external_real_watermark_integration_attempted") is True,
        "real_generation_execution_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
        "required_result_artifact_count": len(required_artifact_kinds),
        "observed_result_artifact_count": len(result_artifacts),
        "missing_required_result_artifact_kinds": missing_artifact_kinds,
        "runtime_failure_manifest_recorded": failure_manifest.get("failure_manifest_recorded") is True,
        "controlled_single_request_scaffold_digest": controlled_single_request_scaffold.get(
            "controlled_single_real_generation_request_scaffold_digest"
        ),
        "controlled_single_request_scaffold_payload_digest": compute_object_digest(
            controlled_single_request_scaffold
        ),
        "external_manual_request_results_payload_digest": compute_object_digest(
            external_manual_request_results
        ),
        "NextAllowedConstructionAfterManualControlledSingleRequestResultGate": (
            result_gate_config.get(
                "approved_next_construction_after_manual_result_gate_pass",
                "governed_real_generation_execution_authorization_decision",
            )
            if decision == _PASS_DECISION
            else "finish_manual_controlled_single_request_result_gate"
        ),
    }
    payload["manual_controlled_single_request_result_gate_digest"] = (
        compute_object_digest(
            {
                key: value
                for key, value in payload.items()
                if key != "manual_controlled_single_request_result_gate_digest"
            }
        )
    )
    return payload


def build_manual_controlled_single_request_result_gate_report_section(
    result_gate: dict[str, Any],
) -> str:
    """功能: 生成手动单请求结果 gate 的报告补充段落."""
    return "\n".join(
        [
            "",
            "## Manual Controlled Single Request Result Gate",
            "",
            "该段落只汇总外部手动单请求结果的受治理校验状态, 不表示真实生成或 watermark 已启用.",
            "",
            (
                "manual_controlled_single_request_result_gate_decision: "
                f"{result_gate.get('TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision')}"
            ),
            (
                "manual_controlled_single_request_result_status: "
                f"{result_gate.get('manual_controlled_single_request_result_status')}"
            ),
            (
                "external_real_generation_attempted: "
                f"{result_gate.get('external_real_generation_attempted')}"
            ),
            (
                "real_generation_execution_allowed: "
                f"{result_gate.get('real_generation_execution_allowed')}"
            ),
            (
                "real_watermark_integration_allowed: "
                f"{result_gate.get('real_watermark_integration_allowed')}"
            ),
            (
                "formal_claim_support_allowed: "
                f"{result_gate.get('formal_claim_support_allowed')}"
            ),
            (
                "next_allowed_construction_after_manual_controlled_single_request_result_gate: "
                f"{result_gate.get('NextAllowedConstructionAfterManualControlledSingleRequestResultGate')}"
            ),
            "",
        ]
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_result_artifacts(
    external_manual_request_results: dict[str, Any],
) -> list[dict[str, Any]]:
    artifacts = external_manual_request_results.get("result_artifacts", [])
    if not isinstance(artifacts, list):
        return []
    return [artifact for artifact in artifacts if isinstance(artifact, dict)]


"""
文件用途: 构建 trajectory-aware sampling 的真实生成执行授权决策.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_PASS_RESULT_GATE_DECISION = "PASS"
_NOT_AUTHORIZED_DECISION = "REAL_GENERATION_EXECUTION_NOT_AUTHORIZED_CURRENT_STAGE_CONTRACT"
_READY_HANDOFF_DECISION = "READY_FOR_EXTERNAL_CONTROLLED_REAL_GENERATION_EXECUTION_HANDOFF"


def build_trajectory_aware_sampling_governed_real_generation_execution_authorization_decision(
    manual_controlled_single_request_result_gate: dict[str, Any],
    authorization_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 给出是否允许进入受控真实视频生成执行的显式治理决策.

    该函数属于项目特定的阶段治理实现. 它只读取已经落盘的手动单请求结果 gate, 不连接真实
    生成后端, 不发起视频生成请求, 不执行真实 watermark. 当前项目契约仍禁止真实视频生成,
    因此默认配置会产出未授权决策, 并把下一步明确为项目契约和阶段治理更新。
    """
    blocking_reasons: list[str] = []

    required_gate_decision = authorization_config.get(
        "required_manual_controlled_single_request_result_gate_decision",
        _PASS_RESULT_GATE_DECISION,
    )
    if (
        manual_controlled_single_request_result_gate.get(
            "TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision"
        )
        != required_gate_decision
    ):
        blocking_reasons.append("manual_controlled_single_request_result_gate_not_pass")

    required_next_step = authorization_config.get(
        "required_next_allowed_construction_after_manual_result_gate",
        "governed_real_generation_execution_authorization_decision",
    )
    if (
        manual_controlled_single_request_result_gate.get(
            "NextAllowedConstructionAfterManualControlledSingleRequestResultGate"
        )
        != required_next_step
    ):
        blocking_reasons.append("manual_result_gate_next_step_mismatch")

    if manual_controlled_single_request_result_gate.get("external_gpu_runtime_detected") is not True:
        blocking_reasons.append("external_gpu_runtime_not_detected")
    if manual_controlled_single_request_result_gate.get("external_model_identity_recorded") is not True:
        blocking_reasons.append("external_model_identity_not_recorded")
    if manual_controlled_single_request_result_gate.get("controlled_single_request_result_recorded") is not True:
        blocking_reasons.append("controlled_single_request_result_not_recorded")
    if manual_controlled_single_request_result_gate.get("external_real_watermark_integration_attempted") is not False:
        blocking_reasons.append("external_real_watermark_attempted_before_authorization")
    if manual_controlled_single_request_result_gate.get("formal_claim_support_allowed") is not False:
        blocking_reasons.append("manual_result_gate_enabled_formal_claim")

    contract_allows_real_generation = (
        authorization_config.get("current_stage_contract_allows_real_generation_execution")
        is True
    )
    if not contract_allows_real_generation:
        blocking_reasons.append("current_stage_contract_disallows_real_generation_execution")

    if authorization_config.get("real_watermark_integration_authorized_after_decision") is not False:
        blocking_reasons.append("config_enabled_real_watermark_authorization")
    if authorization_config.get("formal_claim_support_authorized_after_decision") is not False:
        blocking_reasons.append("config_enabled_formal_claim_authorization")

    decision = (
        _READY_HANDOFF_DECISION
        if not blocking_reasons and contract_allows_real_generation
        else _NOT_AUTHORIZED_DECISION
    )
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationDecision": decision,
        "TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationBlockingReasons": blocking_reasons,
        "project_stage": authorization_config.get("project_stage"),
        "construction_phase": authorization_config.get("construction_phase"),
        "target_construction_phase": authorization_config.get("target_construction_phase"),
        "runtime_mode": authorization_config.get("runtime_mode"),
        "current_stage_contract_allows_real_generation_execution": contract_allows_real_generation,
        "controlled_request_digest": manual_controlled_single_request_result_gate.get(
            "controlled_request_digest"
        ),
        "manual_controlled_single_request_result_gate_decision": manual_controlled_single_request_result_gate.get(
            "TrajectoryAwareSamplingManualControlledSingleRequestResultGateDecision"
        ),
        "manual_controlled_single_request_result_gate_digest": manual_controlled_single_request_result_gate.get(
            "manual_controlled_single_request_result_gate_digest"
        ),
        "manual_controlled_single_request_result_gate_payload_digest": compute_object_digest(
            manual_controlled_single_request_result_gate
        ),
        "real_generation_execution_authorized": decision == _READY_HANDOFF_DECISION,
        "controlled_real_generation_execution_handoff_allowed": decision == _READY_HANDOFF_DECISION,
        "real_watermark_integration_authorized": False,
        "formal_claim_support_authorized": False,
        "maximum_authorized_controlled_request_count": int(
            authorization_config.get("maximum_authorized_controlled_request_count", 1)
        ),
        "required_governance_action_before_real_generation_execution": (
            authorization_config.get(
                "required_governance_action_before_real_generation_execution",
                "project_contract_update_for_controlled_real_generation_execution",
            )
            if decision != _READY_HANDOFF_DECISION
            else "none"
        ),
        "NextAllowedConstructionAfterGovernedRealGenerationExecutionAuthorizationDecision": (
            authorization_config.get(
                "approved_next_construction_after_authorization",
                "external_controlled_real_generation_execution_handoff",
            )
            if decision == _READY_HANDOFF_DECISION
            else "finish_governed_real_generation_execution_authorization_decision"
        ),
    }
    payload["governed_real_generation_execution_authorization_decision_digest"] = (
        compute_object_digest(
            {
                key: value
                for key, value in payload.items()
                if key != "governed_real_generation_execution_authorization_decision_digest"
            }
        )
    )
    return payload


def build_governed_real_generation_execution_authorization_report_section(
    authorization_decision: dict[str, Any],
) -> str:
    """功能: 生成真实生成执行授权决策的报告补充段落."""
    return "\n".join(
        [
            "",
            "## Governed Real Generation Execution Authorization Decision",
            "",
            "该段落只汇总真实生成执行授权的治理决策, 不表示真实视频生成已经执行.",
            "",
            (
                "governed_real_generation_execution_authorization_decision: "
                f"{authorization_decision.get('TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationDecision')}"
            ),
            (
                "current_stage_contract_allows_real_generation_execution: "
                f"{authorization_decision.get('current_stage_contract_allows_real_generation_execution')}"
            ),
            (
                "real_generation_execution_authorized: "
                f"{authorization_decision.get('real_generation_execution_authorized')}"
            ),
            (
                "real_watermark_integration_authorized: "
                f"{authorization_decision.get('real_watermark_integration_authorized')}"
            ),
            (
                "formal_claim_support_authorized: "
                f"{authorization_decision.get('formal_claim_support_authorized')}"
            ),
            (
                "required_governance_action_before_real_generation_execution: "
                f"{authorization_decision.get('required_governance_action_before_real_generation_execution')}"
            ),
            (
                "next_allowed_construction_after_governed_real_generation_execution_authorization_decision: "
                f"{authorization_decision.get('NextAllowedConstructionAfterGovernedRealGenerationExecutionAuthorizationDecision')}"
            ),
            "",
        ]
    )

"""
文件用途: 构建 trajectory-aware sampling 的显式真实生成切换决策.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_PASS_DECISION = "PASS"
_READY_DECISION = "READY_FOR_CONTROLLED_SINGLE_REAL_GENERATION_REQUEST_SCAFFOLD"


def build_trajectory_aware_sampling_explicit_real_generation_transition_decision(
    real_backend_runtime_validation_gate: dict[str, Any],
    transition_decision_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 判断是否可以进入单条受控真实生成请求 scaffold.

    该函数属于项目特定的治理 gate. 它不连接真实生成后端, 不发起真实视频生成,
    不执行真实 watermark. 它只在 runtime validation gate 已经通过后, 冻结下一步
    “单条受控真实生成请求 scaffold”所需的数量限制、失败记录要求和正式 claim 禁用
    边界. 这样可以在真正执行高成本后端请求前, 先把治理条件显式落盘.
    """
    blocking_reasons: list[str] = []

    required_runtime_validation_decision = transition_decision_config.get(
        "required_real_backend_runtime_validation_gate_decision",
        _PASS_DECISION,
    )
    if (
        real_backend_runtime_validation_gate.get(
            "TrajectoryAwareSamplingRealBackendRuntimeValidationGateDecision"
        )
        != required_runtime_validation_decision
    ):
        blocking_reasons.append("real_backend_runtime_validation_gate_not_pass")

    required_next_step = transition_decision_config.get(
        "required_next_allowed_construction_after_runtime_validation_gate",
        "explicit_real_generation_transition_decision",
    )
    if (
        real_backend_runtime_validation_gate.get(
            "NextAllowedConstructionAfterRealBackendRuntimeValidationGate"
        )
        != required_next_step
    ):
        blocking_reasons.append("runtime_validation_gate_next_step_mismatch")

    if real_backend_runtime_validation_gate.get("real_generation_allowed") is not False:
        blocking_reasons.append("runtime_validation_gate_enabled_real_generation")
    if (
        real_backend_runtime_validation_gate.get("real_watermark_integration_allowed")
        is not False
    ):
        blocking_reasons.append("runtime_validation_gate_enabled_real_watermark")
    if (
        real_backend_runtime_validation_gate.get(
            "controlled_real_generation_request_allowed"
        )
        is not False
    ):
        blocking_reasons.append(
            "runtime_validation_gate_enabled_controlled_generation_request"
        )

    maximum_request_count = int(
        transition_decision_config.get("maximum_controlled_request_count", 1)
    )
    if maximum_request_count != 1:
        blocking_reasons.append("controlled_request_count_must_be_one")

    if transition_decision_config.get("failure_manifest_required") is not True:
        blocking_reasons.append("failure_manifest_requirement_missing")
    if transition_decision_config.get("formal_claim_support_allowed") is not False:
        blocking_reasons.append("formal_claim_support_must_remain_disabled")
    if transition_decision_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")
    if transition_decision_config.get("real_generation_execution_allowed") is not False:
        blocking_reasons.append("config_enabled_real_generation_execution")

    request_scaffold_sections = [
        _build_request_scaffold_section(section_kind, index)
        for index, section_kind in enumerate(
            transition_decision_config.get("required_request_scaffold_sections", [])
        )
    ]
    if not request_scaffold_sections:
        blocking_reasons.append("controlled_request_scaffold_sections_missing")

    decision = _READY_DECISION if not blocking_reasons else "INCONCLUSIVE"
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingExplicitRealGenerationTransitionDecision": decision,
        "TrajectoryAwareSamplingExplicitRealGenerationTransitionBlockingReasons": (
            blocking_reasons
        ),
        "project_stage": transition_decision_config.get("project_stage"),
        "construction_phase": transition_decision_config.get("construction_phase"),
        "target_construction_phase": transition_decision_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": transition_decision_config.get("runtime_mode"),
        "controlled_request_scaffold_allowed": decision == _READY_DECISION,
        "controlled_real_generation_request_allowed": False,
        "real_generation_execution_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
        "maximum_controlled_request_count": maximum_request_count,
        "failure_manifest_required": True,
        "request_scaffold_section_count": len(request_scaffold_sections),
        "request_scaffold_sections": request_scaffold_sections,
        "real_backend_runtime_validation_gate_digest": (
            real_backend_runtime_validation_gate.get(
                "real_backend_runtime_validation_gate_digest"
            )
        ),
        "real_backend_runtime_validation_gate_payload_digest": compute_object_digest(
            real_backend_runtime_validation_gate
        ),
        "NextAllowedConstructionAfterExplicitRealGenerationTransitionDecision": (
            transition_decision_config.get(
                "approved_next_construction_after_transition_decision",
                "controlled_single_real_generation_request_scaffold",
            )
            if decision == _READY_DECISION
            else "finish_explicit_real_generation_transition_decision"
        ),
    }
    payload["explicit_real_generation_transition_decision_digest"] = (
        compute_object_digest(
            {
                key: value
                for key, value in payload.items()
                if key != "explicit_real_generation_transition_decision_digest"
            }
        )
    )
    return payload


def build_explicit_real_generation_transition_report_section(
    transition_decision: dict[str, Any],
) -> str:
    """功能: 生成显式真实生成切换决策的报告补充段落."""
    return "\n".join(
        [
            "",
            "## Explicit Real Generation Transition Decision",
            "",
            "该段落只汇总受治理切换决策, 不表示真实生成已经执行.",
            "",
            (
                "explicit_real_generation_transition_decision: "
                f"{transition_decision.get('TrajectoryAwareSamplingExplicitRealGenerationTransitionDecision')}"
            ),
            (
                "controlled_request_scaffold_allowed: "
                f"{transition_decision.get('controlled_request_scaffold_allowed')}"
            ),
            (
                "maximum_controlled_request_count: "
                f"{transition_decision.get('maximum_controlled_request_count')}"
            ),
            (
                "real_generation_execution_allowed: "
                f"{transition_decision.get('real_generation_execution_allowed')}"
            ),
            (
                "real_watermark_integration_allowed: "
                f"{transition_decision.get('real_watermark_integration_allowed')}"
            ),
            (
                "next_allowed_construction_after_explicit_real_generation_transition_decision: "
                f"{transition_decision.get('NextAllowedConstructionAfterExplicitRealGenerationTransitionDecision')}"
            ),
            "",
        ]
    )


def _build_request_scaffold_section(section_kind: object, index: int) -> dict[str, Any]:
    section = {
        "request_scaffold_section_id": f"controlled_request_scaffold_section_{index:04d}",
        "request_scaffold_section_kind": str(section_kind),
        "request_scaffold_section_status": "required_before_controlled_execution",
        "controlled_real_generation_request_allowed": False,
        "real_generation_execution_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
    }
    section["request_scaffold_section_digest"] = compute_object_digest(section)
    return section

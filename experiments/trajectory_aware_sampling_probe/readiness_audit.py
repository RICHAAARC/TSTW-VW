"""
文件用途：构建 trajectory-aware sampling probe 的最小 readiness gate。
File purpose: Build the minimal readiness gate for the trajectory-aware sampling probe.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


FORBIDDEN_RUNTIME_CAPABILITIES = frozenset(
    {
        "real_dit_generation",
        "flow_matching_generation",
        "real_video_generation",
        "real_watermark_embedding",
        "real_watermark_detection",
    }
)


def build_trajectory_aware_sampling_readiness_decision(
    trajectory_mechanism_decision: dict[str, Any],
    sampling_probe_config: dict[str, Any],
) -> dict[str, Any]:
    """功能：判断是否允许进入 trajectory-aware sampling 的下一步构建准备。

    该函数属于项目特定 gate。它并不执行采样、不调用生成模型、不写出实验记录；
    它只把阶段 3 的正式机制决策和下一阶段配置合并检查, 形成一个可审计的 readiness 决策。
    在其他项目中可复用的部分是: 使用上游正式决策文件作为只读依赖, 并把 forbidden capability
    显式列入 gate, 防止 scaffold 被误扩展成真实运行逻辑。
    """
    blocking_reasons: list[str] = []

    if trajectory_mechanism_decision.get("Stage2DependencyStatus") != "PASSED":
        blocking_reasons.append("stage2_dependency_not_passed")
    if trajectory_mechanism_decision.get("Stage3ImplementationDecision") != "PASS":
        blocking_reasons.append("stage3_implementation_not_passed")
    if trajectory_mechanism_decision.get("Stage3MechanismDecision") != "PASS":
        blocking_reasons.append("stage3_mechanism_not_passed")

    construction_phase = str(
        sampling_probe_config.get("construction_phase", "")
    ).strip()
    expected_next_stage = str(
        sampling_probe_config.get(
            "required_next_allowed_stage",
            "trajectory_aware_sampling_probe",
        )
    ).strip()
    if construction_phase != "trajectory_aware_sampling_probe":
        blocking_reasons.append("sampling_construction_phase_mismatch")
    if trajectory_mechanism_decision.get("NextAllowedStageByTrajectory") != expected_next_stage:
        blocking_reasons.append("trajectory_next_stage_not_sampling_probe")

    enabled_capabilities = {
        str(capability)
        for capability in sampling_probe_config.get("enabled_runtime_capabilities", [])
    }
    forbidden_enabled = sorted(enabled_capabilities & FORBIDDEN_RUNTIME_CAPABILITIES)
    if forbidden_enabled:
        blocking_reasons.append("forbidden_runtime_capability_enabled")

    allowed_policy_kinds = _as_string_list(
        sampling_probe_config.get("allowed_sampling_policy_kinds", [])
    )
    selected_policy_kind = str(
        sampling_probe_config.get("selected_sampling_policy_kind", "")
    ).strip()
    if not selected_policy_kind:
        blocking_reasons.append("sampling_policy_kind_missing")
    elif selected_policy_kind not in allowed_policy_kinds:
        blocking_reasons.append("sampling_policy_kind_not_allowed")

    decision = "PASS" if not blocking_reasons else "INCONCLUSIVE"
    return {
        "SamplingReadinessDecision": decision,
        "TrajectoryAwareSamplingBlockingReasons": blocking_reasons,
        "UpstreamTrajectoryMechanismDecision": trajectory_mechanism_decision.get(
            "Stage3MechanismDecision"
        ),
        "UpstreamTrajectoryImplementationDecision": trajectory_mechanism_decision.get(
            "Stage3ImplementationDecision"
        ),
        "UpstreamStage2DependencyStatus": trajectory_mechanism_decision.get(
            "Stage2DependencyStatus"
        ),
        "upstream_trajectory_decision_digest": compute_object_digest(
            trajectory_mechanism_decision
        ),
        "construction_phase": construction_phase,
        "selected_sampling_policy_kind": selected_policy_kind,
        "allowed_sampling_policy_kinds": allowed_policy_kinds,
        "forbidden_runtime_capabilities": sorted(FORBIDDEN_RUNTIME_CAPABILITIES),
        "enabled_runtime_capabilities": sorted(enabled_capabilities),
        "NextAllowedStageBySampling": (
            "full_paper_protocol" if decision == "PASS" else "finish_trajectory_aware_sampling_probe"
        ),
    }


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

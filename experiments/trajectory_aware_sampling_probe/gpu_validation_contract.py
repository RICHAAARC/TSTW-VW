"""
文件用途: 构建 trajectory-aware sampling 后续真实 GPU runtime 的验证合同。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


def build_trajectory_aware_sampling_gpu_validation_contract(
    sampling_policy_manifest: dict[str, Any],
    sampling_handoff_manifest: dict[str, Any],
    gpu_validation_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 从 sampling scaffold 产物生成下一步真实 GPU runtime 的准入合同。

    该函数属于项目特定的治理层。它不执行真实生成, 不连接 DiT / Flow Matching, 不执行 watermark 嵌入或检测。
    它只检查 sampling scaffold 是否已经 PASS, 并把下一步需要真实 GPU 验证的能力显式列入合同。
    这种写法的通用价值在于: 在真正接入昂贵或高风险后端前, 先冻结输入选择、阻断原因和能力边界。
    """
    blocking_reasons: list[str] = []

    if sampling_policy_manifest.get("SamplingReadinessDecision") != gpu_validation_config.get(
        "required_upstream_sampling_readiness_decision",
        "PASS",
    ):
        blocking_reasons.append("sampling_readiness_not_passed")
    if sampling_policy_manifest.get("SamplingSelectionPlanDecision") != gpu_validation_config.get(
        "required_upstream_sampling_selection_plan_decision",
        "PASS",
    ):
        blocking_reasons.append("sampling_selection_plan_not_passed")
    if sampling_policy_manifest.get("NextRequiredValidationBySampling") != gpu_validation_config.get(
        "required_next_required_validation_by_sampling",
        "real_gpu_validation",
    ):
        blocking_reasons.append("next_required_validation_not_real_gpu")
    if sampling_policy_manifest.get("next_step_requires_real_gpu_validation") is not True:
        blocking_reasons.append("next_step_real_gpu_flag_missing")

    selected_record_count = _as_int(sampling_policy_manifest.get("selected_record_count"))
    minimum_selected_record_count = _as_int(
        gpu_validation_config.get("minimum_selected_record_count", 1)
    )
    if selected_record_count < minimum_selected_record_count:
        blocking_reasons.append("selected_record_count_below_minimum")

    if sampling_policy_manifest.get("selection_plan_digest") != sampling_handoff_manifest.get(
        "selection_plan_digest"
    ):
        blocking_reasons.append("selection_plan_digest_mismatch")

    if gpu_validation_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("runtime_backend_connection_must_remain_disabled")
    if gpu_validation_config.get("real_generation_allowed_in_contract_builder") is not False:
        blocking_reasons.append("real_generation_must_remain_disabled_in_contract_builder")
    if gpu_validation_config.get("real_watermark_integration_allowed_in_contract_builder") is not False:
        blocking_reasons.append("real_watermark_must_remain_disabled_in_contract_builder")

    decision = "READY_FOR_REAL_GPU_RUNTIME_VALIDATION" if not blocking_reasons else "INCONCLUSIVE"
    contract_payload: dict[str, Any] = {
        "TrajectoryAwareSamplingGpuValidationContractDecision": decision,
        "TrajectoryAwareSamplingGpuValidationBlockingReasons": blocking_reasons,
        "project_stage": gpu_validation_config.get("project_stage"),
        "construction_phase": gpu_validation_config.get("construction_phase"),
        "target_construction_phase": gpu_validation_config.get("target_construction_phase"),
        "runtime_mode": gpu_validation_config.get("runtime_mode"),
        "selected_record_count": selected_record_count,
        "selection_plan_digest": sampling_policy_manifest.get("selection_plan_digest"),
        "sampling_policy_manifest_digest": compute_object_digest(sampling_policy_manifest),
        "sampling_handoff_manifest_digest": compute_object_digest(sampling_handoff_manifest),
        "next_runtime_capabilities_requiring_real_gpu_validation": list(
            gpu_validation_config.get(
                "next_runtime_capabilities_requiring_real_gpu_validation",
                [],
            )
        ),
        "forbidden_runtime_capabilities_until_backend_transition": list(
            gpu_validation_config.get(
                "forbidden_runtime_capabilities_until_backend_transition",
                [],
            )
        ),
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "NextRequiredValidationBySampling": sampling_policy_manifest.get(
            "NextRequiredValidationBySampling"
        ),
        "NextAllowedConstructionAfterGpuValidationContract": (
            "real_gpu_runtime_validation"
            if decision == "READY_FOR_REAL_GPU_RUNTIME_VALIDATION"
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    contract_payload["gpu_validation_contract_digest"] = compute_object_digest(
        {
            key: value
            for key, value in contract_payload.items()
            if key != "gpu_validation_contract_digest"
        }
    )
    return contract_payload


def _as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0

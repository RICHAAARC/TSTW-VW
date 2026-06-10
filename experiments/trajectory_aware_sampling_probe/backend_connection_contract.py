"""
文件用途: 构建 trajectory-aware sampling 的 backend connection contract 产物。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.core.digest import compute_object_digest


_READY_ADAPTER_SCAFFOLD_DECISION = "READY_FOR_BACKEND_CONNECTION_CONTRACT"
_READY_CONNECTION_CONTRACT_DECISION = "READY_FOR_REAL_BACKEND_CONNECTION_SMOKE"


def build_trajectory_aware_sampling_backend_connection_contract(
    backend_adapter_scaffold: dict[str, Any],
    backend_connection_contract_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 生成真实后端连接 smoke 之前的显式合同。

    该函数属于项目特定写法。它只定义进入真实后端 smoke 前必须满足的环境、模型、请求、失败记录和
    smoke 输出边界, 不导入真实模型库, 不连接真实 DiT / Flow Matching 后端, 不生成视频, 也不执行真实 watermark。
    这一实现的主要考虑在于: 在允许下一步真实后端 smoke 前, 先明确 smoke 不能支持 formal claim,
    并要求记录 GPU 环境、模型身份、失败 manifest 和输出治理边界。
    """
    blocking_reasons: list[str] = []

    required_decision = backend_connection_contract_config.get(
        "required_backend_adapter_scaffold_decision",
        _READY_ADAPTER_SCAFFOLD_DECISION,
    )
    if (
        backend_adapter_scaffold.get(
            "TrajectoryAwareSamplingBackendAdapterScaffoldDecision"
        )
        != required_decision
    ):
        blocking_reasons.append("backend_adapter_scaffold_not_ready")

    required_next_construction = backend_connection_contract_config.get(
        "required_next_allowed_construction_after_backend_adapter_scaffold",
        "backend_connection_contract",
    )
    if (
        backend_adapter_scaffold.get(
            "NextAllowedConstructionAfterBackendAdapterScaffold"
        )
        != required_next_construction
    ):
        blocking_reasons.append("backend_adapter_scaffold_next_step_mismatch")

    if backend_adapter_scaffold.get("backend_adapter_scaffold_allowed") is not True:
        blocking_reasons.append("backend_adapter_scaffold_permission_missing")
    if backend_adapter_scaffold.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("adapter_scaffold_enabled_runtime_backend_connection")
    if backend_adapter_scaffold.get("real_generation_allowed") is not False:
        blocking_reasons.append("adapter_scaffold_enabled_real_generation")
    if backend_adapter_scaffold.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("adapter_scaffold_enabled_real_watermark")

    minimum_schema_count = int(
        backend_connection_contract_config.get("minimum_adapter_schema_count", 4)
    )
    if int(backend_adapter_scaffold.get("adapter_schema_count", 0)) < minimum_schema_count:
        blocking_reasons.append("adapter_schema_count_below_minimum")

    minimum_stub_count = int(
        backend_connection_contract_config.get("minimum_adapter_entry_count", 1)
    )
    if int(backend_adapter_scaffold.get("adapter_stub_count", 0)) < minimum_stub_count:
        blocking_reasons.append("adapter_stub_count_below_minimum")

    required_sections = list(
        backend_connection_contract_config.get("required_smoke_contract_sections", [])
    )
    if not required_sections:
        blocking_reasons.append("smoke_contract_sections_missing")

    smoke_output_governance = backend_connection_contract_config.get(
        "smoke_output_governance",
        {},
    )
    if not isinstance(smoke_output_governance, dict):
        smoke_output_governance = {}
    if smoke_output_governance.get("formal_claim_support_allowed") is not False:
        blocking_reasons.append("smoke_formal_claim_support_must_remain_disabled")
    if smoke_output_governance.get("failure_manifest_required") is not True:
        blocking_reasons.append("failure_manifest_requirement_missing")
    if smoke_output_governance.get("runtime_environment_snapshot_required") is not True:
        blocking_reasons.append("runtime_environment_snapshot_requirement_missing")
    if smoke_output_governance.get("model_identity_record_required") is not True:
        blocking_reasons.append("model_identity_record_requirement_missing")

    if backend_connection_contract_config.get("backend_connection_contract_allowed") is not True:
        blocking_reasons.append("backend_connection_contract_not_allowed")
    if backend_connection_contract_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("config_enabled_runtime_backend_connection")
    if backend_connection_contract_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("config_enabled_real_generation")
    if backend_connection_contract_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")

    contract_sections = [
        _build_contract_section(section_kind, index)
        for index, section_kind in enumerate(required_sections)
    ]
    smoke_backend_families = [
        _build_smoke_backend_family_entry(backend_family, index)
        for index, backend_family in enumerate(
            backend_connection_contract_config.get("allowed_smoke_backend_families", [])
        )
    ]

    decision = (
        _READY_CONNECTION_CONTRACT_DECISION if not blocking_reasons else "INCONCLUSIVE"
    )
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingBackendConnectionContractDecision": decision,
        "TrajectoryAwareSamplingBackendConnectionContractBlockingReasons": (
            blocking_reasons
        ),
        "project_stage": backend_connection_contract_config.get("project_stage"),
        "construction_phase": backend_connection_contract_config.get(
            "construction_phase"
        ),
        "target_construction_phase": backend_connection_contract_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": backend_connection_contract_config.get("runtime_mode"),
        "backend_connection_contract_allowed": (
            decision == _READY_CONNECTION_CONTRACT_DECISION
        ),
        "real_backend_connection_smoke_allowed_after_contract": (
            decision == _READY_CONNECTION_CONTRACT_DECISION
            and backend_connection_contract_config.get(
                "real_backend_connection_smoke_allowed_after_contract"
            )
            is True
        ),
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "contract_section_count": len(contract_sections),
        "contract_sections": contract_sections,
        "smoke_backend_family_count": len(smoke_backend_families),
        "smoke_backend_families": smoke_backend_families,
        "minimum_gpu_requirements": dict(
            backend_connection_contract_config.get("minimum_gpu_requirements", {})
        ),
        "smoke_output_governance": smoke_output_governance,
        "backend_adapter_scaffold_digest": backend_adapter_scaffold.get(
            "backend_adapter_scaffold_digest"
        ),
        "backend_adapter_scaffold_payload_digest": compute_object_digest(
            backend_adapter_scaffold
        ),
        "forbidden_runtime_capabilities_until_real_backend_connection_smoke": list(
            backend_connection_contract_config.get(
                "forbidden_runtime_capabilities_until_real_backend_connection_smoke",
                [],
            )
        ),
        "NextAllowedConstructionAfterBackendConnectionContract": (
            backend_connection_contract_config.get(
                "approved_next_construction",
                "real_backend_connection_smoke",
            )
            if decision == _READY_CONNECTION_CONTRACT_DECISION
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    payload["backend_connection_contract_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "backend_connection_contract_digest"
        }
    )
    return payload


def _build_contract_section(section_kind: object, index: int) -> dict[str, Any]:
    section_payload = {
        "contract_section_id": f"backend_connection_contract_section_{index:04d}",
        "contract_section_kind": str(section_kind),
        "contract_section_status": "required_before_real_backend_smoke",
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
    }
    section_payload["contract_section_digest"] = compute_object_digest(
        section_payload
    )
    return section_payload


def _build_smoke_backend_family_entry(
    backend_family: object,
    index: int,
) -> dict[str, Any]:
    family_payload = {
        "smoke_backend_family_id": f"smoke_backend_family_{index:04d}",
        "smoke_backend_family": str(backend_family),
        "smoke_backend_family_status": "contract_only_not_connected",
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
    }
    family_payload["smoke_backend_family_digest"] = compute_object_digest(
        family_payload
    )
    return family_payload

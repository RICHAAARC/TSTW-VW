"""
文件用途：验证 trajectory-aware sampling probe 的配置与边界契约。
File purpose: Validate configuration and boundary contracts for the trajectory-aware sampling probe.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_probe.json"
ABLATION_CONFIG_PATH = ROOT / "configs" / "ablation" / "trajectory_aware_sampling_ablation.json"


def test_trajectory_aware_sampling_protocol_config_is_decision_only() -> None:
    """验证下一阶段配置只允许 decision-only scaffold。"""
    config = json.loads(PROTOCOL_CONFIG_PATH.read_text(encoding="utf-8"))

    assert config["project_stage"] == "trajectory_aware_sampling_probe"
    assert config["construction_phase"] == "trajectory_aware_sampling_probe"
    assert config["target_construction_phase"] == "full_paper_protocol"
    assert config["upstream_required_construction_phase"] == "trajectory_statistic_probe"
    assert config["required_upstream_mechanism_decision"] == "PASS"
    assert config["required_next_allowed_stage"] == "trajectory_aware_sampling_probe"
    assert config["runtime_mode"] == "decision_only_scaffold"
    assert config["real_generation_allowed"] is False
    assert config["real_watermark_integration_allowed"] is False
    assert config["notebook_entrypoint_allowed"] is False
    assert "real_dit_generation" in config["forbidden_runtime_capabilities"]
    assert "flow_matching_generation" in config["forbidden_runtime_capabilities"]
    assert "real_watermark_embedding" in config["forbidden_runtime_capabilities"]
    assert config["outputs"]["sampling_selection_plan_path"] == "artifacts/sampling_selection_plan.json"
    assert config["outputs"]["sampling_handoff_manifest_path"] == "artifacts/sampling_handoff_manifest.json"
    assert "record_digest_selection_plan" in config["enabled_runtime_capabilities"]


def test_trajectory_aware_sampling_ablation_config_uses_record_selection_only() -> None:
    """验证下一阶段 ablation 仅描述记录选择计划, 不打开真实后端。"""
    config = json.loads(ABLATION_CONFIG_PATH.read_text(encoding="utf-8"))

    assert config["project_stage"] == "trajectory_aware_sampling_probe"
    assert config["construction_phase"] == "trajectory_aware_sampling_probe"
    assert config["selection_output_kind"] == "record_digest_selection_plan"
    assert config["allow_real_generation"] is False
    assert config["allow_flow_matching_backend"] is False
    assert config["allow_real_watermark_algorithm"] is False
    assert config["candidate_sampling_policy_kinds"] == [
        "trajectory_ranked_replay",
        "control_balanced_replay",
    ]


def test_trajectory_aware_sampling_gpu_validation_contract_keeps_backends_disabled() -> None:
    """验证真实 GPU runtime 验证合同只冻结准入条件, 不提前接入真实后端。"""
    config = json.loads((ROOT / "configs" / "protocol" / "trajectory_aware_sampling_gpu_validation_contract.json").read_text(encoding="utf-8"))

    assert config["project_stage"] == "trajectory_aware_sampling_probe"
    assert config["construction_phase"] == "trajectory_aware_sampling_probe"
    assert config["target_construction_phase"] == "full_paper_protocol"
    assert config["runtime_mode"] == "real_gpu_validation_contract_only"
    assert config["required_next_required_validation_by_sampling"] == "real_gpu_validation"
    assert config["runtime_backend_connection_allowed"] is False
    assert config["real_generation_allowed_in_contract_builder"] is False
    assert config["real_watermark_integration_allowed_in_contract_builder"] is False
    assert "trajectory_aware_sampling_runtime" in config["next_runtime_capabilities_requiring_real_gpu_validation"]
    assert "real_dit_generation" in config["forbidden_runtime_capabilities_until_backend_transition"]


def test_trajectory_aware_sampling_backend_transition_guard_requires_decision() -> None:
    """验证后端切换前守卫只能要求显式决策, 不能提前打开真实后端。"""
    config = json.loads((ROOT / "configs" / "protocol" / "trajectory_aware_sampling_backend_transition_guard.json").read_text(encoding="utf-8"))

    assert config["project_stage"] == "trajectory_aware_sampling_probe"
    assert config["construction_phase"] == "trajectory_aware_sampling_probe"
    assert config["target_construction_phase"] == "full_paper_protocol"
    assert config["runtime_mode"] == "backend_transition_guard_only"
    assert (
        config["required_gpu_validation_contract_decision"]
        == "READY_FOR_REAL_GPU_RUNTIME_VALIDATION"
    )
    assert config["required_next_allowed_construction"] == "real_gpu_runtime_validation"
    assert config["backend_transition_decision_required"] is True
    assert config["runtime_backend_connection_allowed"] is False
    assert config["real_generation_allowed"] is False
    assert config["real_watermark_integration_allowed"] is False
    assert (
        config["outputs"]["backend_transition_guard_path"]
        == "artifacts/trajectory_aware_sampling_backend_transition_guard.json"
    )


def test_trajectory_aware_sampling_backend_transition_decision_allows_interface_only() -> None:
    """验证显式后端切换决策只允许接口脚手架, 仍不允许真实后端。"""
    config = json.loads((ROOT / "configs" / "protocol" / "trajectory_aware_sampling_backend_transition_decision.json").read_text(encoding="utf-8"))

    assert config["project_stage"] == "trajectory_aware_sampling_probe"
    assert config["construction_phase"] == "trajectory_aware_sampling_probe"
    assert config["target_construction_phase"] == "full_paper_protocol"
    assert config["runtime_mode"] == "backend_transition_decision_interface_scaffold_only"
    assert (
        config["required_backend_transition_guard_decision"]
        == "BACKEND_TRANSITION_DECISION_REQUIRED"
    )
    assert (
        config["required_next_allowed_construction_after_guard"]
        == "explicit_backend_transition_decision"
    )
    assert config["approved_next_construction"] == "real_gpu_runtime_interface_scaffold"
    assert config["runtime_interface_scaffold_allowed"] is True
    assert config["runtime_backend_connection_allowed"] is False
    assert config["real_generation_allowed"] is False
    assert config["real_watermark_integration_allowed"] is False
    assert "backend_protocol_shape" in config["approved_interface_scaffold_capabilities"]
    assert "real_dit_generation" in config[
        "forbidden_runtime_capabilities_until_backend_implementation"
    ]
    assert (
        config["outputs"]["backend_transition_decision_path"]
        == "artifacts/trajectory_aware_sampling_backend_transition_decision.json"
    )


def test_trajectory_aware_sampling_runtime_interface_scaffold_defines_schema_only() -> None:
    """验证 runtime interface scaffold 只定义接口 schema, 不打开真实 backend。"""
    config = json.loads((ROOT / "configs" / "protocol" / "trajectory_aware_sampling_runtime_interface_scaffold.json").read_text(encoding="utf-8"))

    assert config["project_stage"] == "trajectory_aware_sampling_probe"
    assert config["construction_phase"] == "trajectory_aware_sampling_probe"
    assert config["target_construction_phase"] == "full_paper_protocol"
    assert config["runtime_mode"] == "real_gpu_runtime_interface_scaffold_only"
    assert (
        config["required_backend_transition_decision"]
        == "APPROVED_FOR_RUNTIME_INTERFACE_SCAFFOLD_ONLY"
    )
    assert (
        config["required_next_allowed_construction_after_decision"]
        == "real_gpu_runtime_interface_scaffold"
    )
    assert config["required_selection_plan_decision"] == "PASS"
    assert config["runtime_interface_scaffold_allowed"] is True
    assert config["runtime_backend_connection_allowed"] is False
    assert config["real_generation_allowed"] is False
    assert config["real_watermark_integration_allowed"] is False
    assert config["request_schema_kind"] == "selected_record_replay_request_schema"
    assert config["result_manifest_schema_kind"] == "runtime_result_manifest_schema"
    assert config["gpu_preflight_schema_kind"] == "gpu_environment_preflight_schema"
    assert "real_video_generation" in config[
        "forbidden_runtime_capabilities_until_backend_implementation"
    ]
    assert (
        config["outputs"]["runtime_interface_scaffold_path"]
        == "artifacts/trajectory_aware_sampling_runtime_interface_scaffold.json"
    )


def test_trajectory_aware_sampling_runtime_interface_implementation_is_no_backend() -> None:
    """验证 runtime interface implementation 只允许非后端连接版 dry-run。"""
    config = json.loads((ROOT / "configs" / "protocol" / "trajectory_aware_sampling_runtime_interface_implementation.json").read_text(encoding="utf-8"))

    assert config["project_stage"] == "trajectory_aware_sampling_probe"
    assert config["construction_phase"] == "trajectory_aware_sampling_probe"
    assert config["target_construction_phase"] == "full_paper_protocol"
    assert config["runtime_mode"] == "real_gpu_runtime_interface_implementation_no_backend"
    assert (
        config["required_runtime_interface_scaffold_decision"]
        == "READY_FOR_REAL_GPU_RUNTIME_INTERFACE_IMPLEMENTATION"
    )
    assert (
        config["required_next_allowed_construction_after_scaffold"]
        == "real_gpu_runtime_interface_implementation"
    )
    assert config["runtime_interface_implementation_allowed"] is True
    assert config["runtime_backend_connection_allowed"] is False
    assert config["real_generation_allowed"] is False
    assert config["real_watermark_integration_allowed"] is False
    assert config["approved_next_construction"] == "backend_integration_decision"
    assert config["dry_run_backend_status"] == "not_connected_by_governance"
    assert "real_dit_generation" in config[
        "forbidden_runtime_capabilities_until_backend_integration_decision"
    ]
    assert (
        config["outputs"]["runtime_interface_implementation_path"]
        == "artifacts/trajectory_aware_sampling_runtime_interface_implementation.json"
    )


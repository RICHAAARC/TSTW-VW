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

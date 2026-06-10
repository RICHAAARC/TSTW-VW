"""
文件用途: 验证 trajectory-aware sampling 后续真实 GPU runtime 合同。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.gpu_validation_contract import (
    build_trajectory_aware_sampling_gpu_validation_contract,
)

pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_gpu_validation_contract.json"


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _policy_manifest() -> dict[str, object]:
    return {
        "SamplingReadinessDecision": "PASS",
        "SamplingSelectionPlanDecision": "PASS",
        "selected_record_count": 8,
        "selection_plan_digest": "digest_a",
        "next_step_requires_real_gpu_validation": True,
        "NextRequiredValidationBySampling": "real_gpu_validation",
    }


def _handoff_manifest() -> dict[str, object]:
    return {
        "handoff_kind": "trajectory_aware_sampling_scaffold",
        "selected_record_count": 8,
        "selection_plan_digest": "digest_a",
        "next_step_requires_real_gpu_validation": True,
        "NextRequiredValidationBySampling": "real_gpu_validation",
    }


def test_gpu_validation_contract_accepts_passed_sampling_scaffold() -> None:
    """验证通过的 sampling scaffold 可以生成真实 GPU runtime 验证准入合同。"""
    contract = build_trajectory_aware_sampling_gpu_validation_contract(
        _policy_manifest(),
        _handoff_manifest(),
        _config(),
    )

    assert (
        contract["TrajectoryAwareSamplingGpuValidationContractDecision"]
        == "READY_FOR_REAL_GPU_RUNTIME_VALIDATION"
    )
    assert contract["TrajectoryAwareSamplingGpuValidationBlockingReasons"] == []
    assert contract["project_stage"] == "trajectory_aware_sampling_probe"
    assert contract["target_construction_phase"] == "full_paper_protocol"
    assert contract["runtime_backend_connection_allowed"] is False
    assert contract["real_generation_allowed"] is False
    assert contract["real_watermark_integration_allowed"] is False
    assert contract["NextAllowedConstructionAfterGpuValidationContract"] == "real_gpu_runtime_validation"
    assert "trajectory_aware_sampling_runtime" in contract[
        "next_runtime_capabilities_requiring_real_gpu_validation"
    ]


def test_gpu_validation_contract_blocks_digest_mismatch() -> None:
    """验证 handoff digest 不一致时不能进入真实 GPU runtime 验证。"""
    handoff = _handoff_manifest()
    handoff["selection_plan_digest"] = "other_digest"

    contract = build_trajectory_aware_sampling_gpu_validation_contract(
        _policy_manifest(),
        handoff,
        _config(),
    )

    assert contract["TrajectoryAwareSamplingGpuValidationContractDecision"] == "INCONCLUSIVE"
    assert "selection_plan_digest_mismatch" in contract[
        "TrajectoryAwareSamplingGpuValidationBlockingReasons"
    ]


def test_gpu_validation_contract_blocks_if_backend_is_enabled_too_early() -> None:
    """验证合同构建阶段不能提前打开真实后端连接。"""
    config = _config()
    config["runtime_backend_connection_allowed"] = True

    contract = build_trajectory_aware_sampling_gpu_validation_contract(
        _policy_manifest(),
        _handoff_manifest(),
        config,
    )

    assert contract["TrajectoryAwareSamplingGpuValidationContractDecision"] == "INCONCLUSIVE"
    assert "runtime_backend_connection_must_remain_disabled" in contract[
        "TrajectoryAwareSamplingGpuValidationBlockingReasons"
    ]

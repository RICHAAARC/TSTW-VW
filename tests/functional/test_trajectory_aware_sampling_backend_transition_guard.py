"""
文件用途: 验证 trajectory-aware sampling 后端切换前治理守卫。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.backend_transition_guard import (
    build_trajectory_aware_sampling_backend_transition_guard,
)

pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT
    / "configs"
    / "protocol"
    / "trajectory_aware_sampling_backend_transition_guard.json"
)


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _gpu_validation_contract() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingGpuValidationContractDecision": (
            "READY_FOR_REAL_GPU_RUNTIME_VALIDATION"
        ),
        "TrajectoryAwareSamplingGpuValidationBlockingReasons": [],
        "NextAllowedConstructionAfterGpuValidationContract": (
            "real_gpu_runtime_validation"
        ),
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "gpu_validation_contract_digest": "digest_a",
    }


def test_backend_transition_guard_requires_explicit_backend_transition_decision() -> None:
    """验证已通过的 GPU validation contract 仍只能推进到显式后端切换决策。"""
    guard = build_trajectory_aware_sampling_backend_transition_guard(
        _gpu_validation_contract(),
        _config(),
    )

    assert (
        guard["TrajectoryAwareSamplingBackendTransitionGuardDecision"]
        == "BACKEND_TRANSITION_DECISION_REQUIRED"
    )
    assert guard["TrajectoryAwareSamplingBackendTransitionGuardBlockingReasons"] == []
    assert guard["backend_transition_decision_required"] is True
    assert guard["runtime_backend_connection_allowed"] is False
    assert guard["real_generation_allowed"] is False
    assert guard["real_watermark_integration_allowed"] is False
    assert (
        guard["NextAllowedConstructionAfterBackendTransitionGuard"]
        == "explicit_backend_transition_decision"
    )


def test_backend_transition_guard_blocks_unready_gpu_validation_contract() -> None:
    """验证 GPU validation contract 未 ready 时不能进入后端切换决策。"""
    contract = _gpu_validation_contract()
    contract["TrajectoryAwareSamplingGpuValidationContractDecision"] = "INCONCLUSIVE"

    guard = build_trajectory_aware_sampling_backend_transition_guard(
        contract,
        _config(),
    )

    assert (
        guard["TrajectoryAwareSamplingBackendTransitionGuardDecision"]
        == "INCONCLUSIVE"
    )
    assert "gpu_validation_contract_not_ready" in guard[
        "TrajectoryAwareSamplingBackendTransitionGuardBlockingReasons"
    ]


def test_backend_transition_guard_blocks_if_real_generation_is_already_enabled() -> None:
    """验证守卫阶段不能提前打开真实生成能力。"""
    contract = _gpu_validation_contract()
    contract["real_generation_allowed"] = True

    guard = build_trajectory_aware_sampling_backend_transition_guard(
        contract,
        _config(),
    )

    assert (
        guard["TrajectoryAwareSamplingBackendTransitionGuardDecision"]
        == "INCONCLUSIVE"
    )
    assert "real_generation_already_enabled" in guard[
        "TrajectoryAwareSamplingBackendTransitionGuardBlockingReasons"
    ]

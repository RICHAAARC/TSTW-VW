"""
文件用途: 验证 trajectory-aware sampling 显式后端切换决策。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.backend_transition_decision import (
    build_trajectory_aware_sampling_backend_transition_decision,
)

pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT
    / "configs"
    / "protocol"
    / "trajectory_aware_sampling_backend_transition_decision.json"
)


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _guard() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingBackendTransitionGuardDecision": (
            "BACKEND_TRANSITION_DECISION_REQUIRED"
        ),
        "TrajectoryAwareSamplingBackendTransitionGuardBlockingReasons": [],
        "NextAllowedConstructionAfterBackendTransitionGuard": (
            "explicit_backend_transition_decision"
        ),
        "backend_transition_decision_required": True,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "backend_transition_guard_digest": "digest_guard",
    }


def test_backend_transition_decision_approves_interface_scaffold_only() -> None:
    """验证显式后端切换决策只批准接口脚手架, 不批准真实后端。"""
    decision = build_trajectory_aware_sampling_backend_transition_decision(
        _guard(),
        _config(),
    )

    assert (
        decision["TrajectoryAwareSamplingBackendTransitionDecision"]
        == "APPROVED_FOR_RUNTIME_INTERFACE_SCAFFOLD_ONLY"
    )
    assert decision["TrajectoryAwareSamplingBackendTransitionDecisionBlockingReasons"] == []
    assert decision["runtime_interface_scaffold_allowed"] is True
    assert decision["runtime_backend_connection_allowed"] is False
    assert decision["real_generation_allowed"] is False
    assert decision["real_watermark_integration_allowed"] is False
    assert (
        decision["NextAllowedConstructionAfterBackendTransitionDecision"]
        == "real_gpu_runtime_interface_scaffold"
    )


def test_backend_transition_decision_blocks_unready_guard() -> None:
    """验证 guard 未 ready 时不能批准接口脚手架。"""
    guard = _guard()
    guard["TrajectoryAwareSamplingBackendTransitionGuardDecision"] = "INCONCLUSIVE"

    decision = build_trajectory_aware_sampling_backend_transition_decision(
        guard,
        _config(),
    )

    assert decision["TrajectoryAwareSamplingBackendTransitionDecision"] == "INCONCLUSIVE"
    assert "backend_transition_guard_not_ready" in decision[
        "TrajectoryAwareSamplingBackendTransitionDecisionBlockingReasons"
    ]


def test_backend_transition_decision_blocks_if_backend_connection_enabled() -> None:
    """验证显式决策配置不能提前打开真实 backend 连接。"""
    config = _config()
    config["runtime_backend_connection_allowed"] = True

    decision = build_trajectory_aware_sampling_backend_transition_decision(
        _guard(),
        config,
    )

    assert decision["TrajectoryAwareSamplingBackendTransitionDecision"] == "INCONCLUSIVE"
    assert "runtime_backend_connection_must_remain_disabled" in decision[
        "TrajectoryAwareSamplingBackendTransitionDecisionBlockingReasons"
    ]

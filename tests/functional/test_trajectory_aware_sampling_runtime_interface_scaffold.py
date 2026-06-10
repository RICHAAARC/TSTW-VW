"""
文件用途: 验证 trajectory-aware sampling 真实 GPU runtime 接口脚手架。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.runtime_interface_scaffold import (
    build_trajectory_aware_sampling_runtime_interface_scaffold,
)

pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT
    / "configs"
    / "protocol"
    / "trajectory_aware_sampling_runtime_interface_scaffold.json"
)


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _selection_plan() -> dict[str, object]:
    return {
        "SamplingSelectionPlanDecision": "PASS",
        "selection_output_kind": "record_digest_selection_plan",
        "selection_plan_digest": "digest_selection",
        "selected_records": [
            {
                "record_digest": "record_digest_a",
                "event_id": "event_a",
                "sample_id": "sample_a",
                "method_variant": "tubelet_sync_trajectory_fusion",
                "attack_name": "local_clip",
                "selection_policy_kind": "trajectory_ranked_replay",
            }
        ],
    }


def _backend_transition_decision() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingBackendTransitionDecision": (
            "APPROVED_FOR_RUNTIME_INTERFACE_SCAFFOLD_ONLY"
        ),
        "NextAllowedConstructionAfterBackendTransitionDecision": (
            "real_gpu_runtime_interface_scaffold"
        ),
        "runtime_interface_scaffold_allowed": True,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "backend_transition_decision_digest": "digest_decision",
    }


def test_runtime_interface_scaffold_builds_request_and_manifest_schemas() -> None:
    """验证接口脚手架只冻结请求和结果 schema, 不打开真实后端。"""
    scaffold = build_trajectory_aware_sampling_runtime_interface_scaffold(
        _selection_plan(),
        _backend_transition_decision(),
        _config(),
    )

    assert (
        scaffold["TrajectoryAwareSamplingRuntimeInterfaceScaffoldDecision"]
        == "READY_FOR_REAL_GPU_RUNTIME_INTERFACE_IMPLEMENTATION"
    )
    assert scaffold["TrajectoryAwareSamplingRuntimeInterfaceScaffoldBlockingReasons"] == []
    assert scaffold["request_schema_kind"] == "selected_record_replay_request_schema"
    assert scaffold["result_manifest_schema_kind"] == "runtime_result_manifest_schema"
    assert scaffold["gpu_preflight_schema_kind"] == "gpu_environment_preflight_schema"
    assert scaffold["request_prototype_count"] == 1
    assert scaffold["runtime_interface_scaffold_allowed"] is True
    assert scaffold["runtime_backend_connection_allowed"] is False
    assert scaffold["real_generation_allowed"] is False
    assert scaffold["real_watermark_integration_allowed"] is False
    assert (
        scaffold["NextAllowedConstructionAfterRuntimeInterfaceScaffold"]
        == "real_gpu_runtime_interface_implementation"
    )


def test_runtime_interface_scaffold_blocks_unapproved_backend_transition() -> None:
    """验证后端切换决策未批准时不能构建 runtime 接口脚手架。"""
    decision = _backend_transition_decision()
    decision["TrajectoryAwareSamplingBackendTransitionDecision"] = "INCONCLUSIVE"

    scaffold = build_trajectory_aware_sampling_runtime_interface_scaffold(
        _selection_plan(),
        decision,
        _config(),
    )

    assert (
        scaffold["TrajectoryAwareSamplingRuntimeInterfaceScaffoldDecision"]
        == "INCONCLUSIVE"
    )
    assert "backend_transition_decision_not_approved" in scaffold[
        "TrajectoryAwareSamplingRuntimeInterfaceScaffoldBlockingReasons"
    ]


def test_runtime_interface_scaffold_blocks_empty_selection_plan() -> None:
    """验证没有 selected records 时不能形成可执行请求原型。"""
    plan = _selection_plan()
    plan["selected_records"] = []

    scaffold = build_trajectory_aware_sampling_runtime_interface_scaffold(
        plan,
        _backend_transition_decision(),
        _config(),
    )

    assert (
        scaffold["TrajectoryAwareSamplingRuntimeInterfaceScaffoldDecision"]
        == "INCONCLUSIVE"
    )
    assert "selected_record_count_below_minimum" in scaffold[
        "TrajectoryAwareSamplingRuntimeInterfaceScaffoldBlockingReasons"
    ]

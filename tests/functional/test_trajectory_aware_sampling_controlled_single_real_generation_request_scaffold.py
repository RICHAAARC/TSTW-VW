"""
文件用途: 验证 trajectory-aware sampling 的单条受控真实生成请求 scaffold.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.controlled_single_real_generation_request_scaffold import (
    build_trajectory_aware_sampling_controlled_single_real_generation_request_scaffold,
)


pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]


def _read_config() -> dict[str, object]:
    return json.loads(
        (
            ROOT
            / "configs"
            / "protocol"
            / "trajectory_aware_sampling_controlled_single_real_generation_request_scaffold.json"
        ).read_text(encoding="utf-8")
    )


def _ready_transition_decision() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingExplicitRealGenerationTransitionDecision": "READY_FOR_CONTROLLED_SINGLE_REAL_GENERATION_REQUEST_SCAFFOLD",
        "NextAllowedConstructionAfterExplicitRealGenerationTransitionDecision": "controlled_single_real_generation_request_scaffold",
        "controlled_request_scaffold_allowed": True,
        "real_generation_execution_allowed": False,
        "real_watermark_integration_allowed": False,
        "explicit_real_generation_transition_decision_digest": "transition_digest",
    }


def _selection_plan() -> dict[str, object]:
    return {
        "selection_plan_digest": "selection_digest",
        "selected_records": [
            {
                "record_digest": "record_digest_0000",
                "event_id": "event_0000",
                "sample_id": "sample_0000",
                "method_variant": "tubelet_sync_trajectory_fusion",
                "attack_name": "temporal_crop",
            }
        ],
    }


def test_controlled_single_real_generation_request_scaffold_is_ready() -> None:
    """验证 scaffold 可以冻结单条请求边界, 但不执行真实生成."""
    payload = build_trajectory_aware_sampling_controlled_single_real_generation_request_scaffold(
        _ready_transition_decision(),
        _selection_plan(),
        _read_config(),
    )

    assert (
        payload[
            "TrajectoryAwareSamplingControlledSingleRealGenerationRequestScaffoldDecision"
        ]
        == "READY_FOR_MANUAL_CONTROLLED_REAL_GENERATION_REQUEST_RUN"
    )
    assert payload["selected_request_count"] == 1
    assert payload["manual_gpu_execution_required"] is True
    assert payload["real_generation_execution_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["formal_claim_support_allowed"] is False
    assert (
        payload["NextRequiredExternalExecutionAfterControlledSingleRequestScaffold"]
        == "manual_controlled_single_real_generation_request_run"
    )
    assert (
        payload["request_descriptor"]["selected_record_digest"]
        == "record_digest_0000"
    )


def test_controlled_single_real_generation_request_scaffold_blocks_empty_selection() -> None:
    """验证没有 selected record 时 scaffold 明确阻断."""
    selection_plan = _selection_plan()
    selection_plan["selected_records"] = []

    payload = build_trajectory_aware_sampling_controlled_single_real_generation_request_scaffold(
        _ready_transition_decision(),
        selection_plan,
        _read_config(),
    )

    assert (
        payload[
            "TrajectoryAwareSamplingControlledSingleRealGenerationRequestScaffoldDecision"
        ]
        == "INCONCLUSIVE"
    )
    assert "selection_plan_has_no_selected_records" in payload[
        "TrajectoryAwareSamplingControlledSingleRealGenerationRequestScaffoldBlockingReasons"
    ]
    assert payload["selected_request_count"] == 0

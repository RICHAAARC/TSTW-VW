
"""
文件用途: 验证外部受控单条真实生成执行 run package 的治理语义.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.external_controlled_single_real_generation_execution_run import (
    build_trajectory_aware_sampling_external_controlled_single_real_generation_execution_run,
)

pytestmark = [pytest.mark.quick]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_external_controlled_single_real_generation_execution_run.json"


def _ready_handoff() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffDecision": "READY_FOR_EXTERNAL_CONTROLLED_REAL_GENERATION_EXECUTION_RUN",
        "external_controlled_real_generation_execution_ready": True,
        "external_real_generation_execution_allowed": True,
        "repository_internal_backend_invocation_allowed": False,
        "real_watermark_integration_allowed": False,
        "formal_claim_support_allowed": False,
        "external_controlled_real_generation_execution_handoff_digest": "handoff_digest",
        "execution_descriptor": {
            "controlled_request_id": "controlled_real_generation_request_0000",
            "controlled_request_digest": "request_digest",
            "sample_id": "sample_id",
            "method_variant": "tubelet_traj",
            "attack_name": "latent_gaussian_noise",
        },
        "external_result_schema": {
            "external_result_schema_digest": "result_schema_digest",
        },
        "external_failure_manifest_schema": {
            "external_failure_manifest_schema_digest": "failure_schema_digest",
        },
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_external_controlled_single_real_generation_execution_run_is_ready() -> None:
    """验证 handoff ready 后可以生成外部手动模型执行 run package."""
    payload = build_trajectory_aware_sampling_external_controlled_single_real_generation_execution_run(
        _ready_handoff(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunDecision"]
        == "READY_FOR_MANUAL_EXTERNAL_MODEL_EXECUTION"
    )
    assert payload["TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunBlockingReasons"] == []
    assert payload["external_controlled_single_real_generation_execution_run_ready"] is True
    assert payload["external_model_loading_required"] is True
    assert payload["manual_external_model_execution_required"] is True
    assert payload["external_real_generation_execution_allowed"] is True
    assert payload["repository_internal_backend_invocation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["formal_claim_support_allowed"] is False
    assert payload["result_submission_template"]["controlled_request_digest"] == "request_digest"
    assert (
        payload["NextRequiredExternalActionAfterExternalControlledSingleRealGenerationExecutionRun"]
        == "manual_external_model_execution_and_result_upload"
    )


def test_external_controlled_single_real_generation_execution_run_blocks_unready_handoff() -> None:
    """验证 handoff 未 ready 时不能进入外部模型执行 run package."""
    handoff = _ready_handoff()
    handoff[
        "TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffDecision"
    ] = "INCONCLUSIVE"

    payload = build_trajectory_aware_sampling_external_controlled_single_real_generation_execution_run(
        handoff,
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunDecision"]
        == "INCONCLUSIVE"
    )
    assert "external_controlled_real_generation_execution_handoff_not_ready" in payload[
        "TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunBlockingReasons"
    ]


def test_external_controlled_single_real_generation_execution_run_blocks_internal_backend_config() -> None:
    """验证配置如果尝试允许仓库内部后端调用, run package 会被阻断."""
    config = _config()
    config["repository_internal_backend_invocation_allowed"] = True

    payload = build_trajectory_aware_sampling_external_controlled_single_real_generation_execution_run(
        _ready_handoff(),
        config,
    )

    assert (
        payload["TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunDecision"]
        == "INCONCLUSIVE"
    )
    assert "config_enabled_repository_internal_backend_invocation" in payload[
        "TrajectoryAwareSamplingExternalControlledSingleRealGenerationExecutionRunBlockingReasons"
    ]

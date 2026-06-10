
"""
文件用途: 验证外部受控真实生成执行 handoff 的治理语义.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.external_controlled_real_generation_execution_handoff import (
    build_trajectory_aware_sampling_external_controlled_real_generation_execution_handoff,
)

pytestmark = [pytest.mark.quick]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_external_controlled_real_generation_execution_handoff.json"


def _authorization_decision() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationDecision": "READY_FOR_EXTERNAL_CONTROLLED_REAL_GENERATION_EXECUTION_HANDOFF",
        "controlled_request_digest": "request_digest",
        "real_generation_execution_authorized": True,
        "controlled_real_generation_execution_handoff_allowed": True,
        "real_watermark_integration_authorized": False,
        "formal_claim_support_authorized": False,
        "governed_real_generation_execution_authorization_decision_digest": "authorization_digest",
    }


def _controlled_scaffold() -> dict[str, object]:
    return {
        "controlled_single_real_generation_request_scaffold_digest": "scaffold_digest",
        "request_descriptor": {
            "controlled_request_id": "controlled_real_generation_request_0000",
            "controlled_request_digest": "request_digest",
            "selected_record_digest": "record_digest",
            "event_id": "event_id",
            "sample_id": "sample_id",
            "method_variant": "tubelet_traj",
            "attack_name": "latent_gaussian_noise",
        },
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_external_controlled_real_generation_execution_handoff_is_ready() -> None:
    """验证授权通过后可以生成外部单请求真实生成执行 handoff."""
    payload = build_trajectory_aware_sampling_external_controlled_real_generation_execution_handoff(
        _authorization_decision(),
        _controlled_scaffold(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffDecision"]
        == "READY_FOR_EXTERNAL_CONTROLLED_REAL_GENERATION_EXECUTION_RUN"
    )
    assert payload["TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffBlockingReasons"] == []
    assert payload["external_controlled_real_generation_execution_ready"] is True
    assert payload["external_real_generation_execution_allowed"] is True
    assert payload["repository_internal_backend_invocation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["formal_claim_support_allowed"] is False
    assert payload["maximum_external_controlled_request_count"] == 1
    assert (
        payload["NextRequiredExternalExecutionAfterExternalControlledRealGenerationExecutionHandoff"]
        == "external_controlled_single_real_generation_execution_run"
    )
    assert payload["execution_descriptor"]["controlled_request_digest"] == "request_digest"


def test_external_controlled_real_generation_execution_handoff_blocks_unready_authorization() -> None:
    """验证授权未通过时不能生成外部执行 handoff."""
    authorization = _authorization_decision()
    authorization[
        "TrajectoryAwareSamplingGovernedRealGenerationExecutionAuthorizationDecision"
    ] = "REAL_GENERATION_EXECUTION_NOT_AUTHORIZED_CURRENT_STAGE_CONTRACT"
    authorization["real_generation_execution_authorized"] = False

    payload = build_trajectory_aware_sampling_external_controlled_real_generation_execution_handoff(
        authorization,
        _controlled_scaffold(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffDecision"]
        == "INCONCLUSIVE"
    )
    assert "governed_real_generation_execution_not_authorized" in payload[
        "TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffBlockingReasons"
    ]


def test_external_controlled_real_generation_execution_handoff_blocks_digest_mismatch() -> None:
    """验证授权决策和请求 scaffold 不绑定同一 digest 时会被阻断."""
    authorization = _authorization_decision()
    authorization["controlled_request_digest"] = "other_request_digest"

    payload = build_trajectory_aware_sampling_external_controlled_real_generation_execution_handoff(
        authorization,
        _controlled_scaffold(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffDecision"]
        == "INCONCLUSIVE"
    )
    assert "authorization_request_digest_mismatch" in payload[
        "TrajectoryAwareSamplingExternalControlledRealGenerationExecutionHandoffBlockingReasons"
    ]

"""
文件用途: 验证 trajectory-aware sampling 的真实后端连接 smoke 请求 gate。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.real_backend_connection_smoke import (
    build_trajectory_aware_sampling_real_backend_connection_smoke,
)

pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_real_backend_connection_smoke.json"


def _ready_contract() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingBackendConnectionContractDecision": "READY_FOR_REAL_BACKEND_CONNECTION_SMOKE",
        "NextAllowedConstructionAfterBackendConnectionContract": "real_backend_connection_smoke",
        "backend_connection_contract_digest": "contract_digest",
        "backend_connection_contract_allowed": True,
        "real_backend_connection_smoke_allowed_after_contract": True,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "contract_section_count": 6,
        "smoke_backend_family_count": 3,
        "smoke_output_governance": {
            "formal_claim_support_allowed": False,
            "failure_manifest_required": True,
        },
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_real_backend_connection_smoke_builds_gpu_execution_request_only() -> None:
    """验证该 gate 只生成真实 GPU smoke 请求, 当前不连接真实后端。"""
    payload = build_trajectory_aware_sampling_real_backend_connection_smoke(
        _ready_contract(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingRealBackendConnectionSmokeDecision"]
        == "READY_FOR_REAL_GPU_BACKEND_CONNECTION_SMOKE_EXECUTION"
    )
    assert payload["TrajectoryAwareSamplingRealBackendConnectionSmokeBlockingReasons"] == []
    assert payload["real_backend_connection_smoke_request_allowed"] is True
    assert payload["gpu_execution_required_for_next_step"] is True
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_generation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["real_backend_connection_attempted"] is False
    assert payload["smoke_execution_request_count"] == 1
    assert payload["required_result_artifact_count"] == 5
    assert (
        payload["NextRequiredValidationAfterRealBackendConnectionSmokeRequest"]
        == "real_gpu_backend_connection_smoke"
    )


def test_real_backend_connection_smoke_blocks_backend_enabled_contract() -> None:
    """验证上游 contract 如果误打开真实后端, smoke 请求 gate 会阻断。"""
    contract = _ready_contract()
    contract["runtime_backend_connection_allowed"] = True

    payload = build_trajectory_aware_sampling_real_backend_connection_smoke(
        contract,
        _config(),
    )

    assert payload["TrajectoryAwareSamplingRealBackendConnectionSmokeDecision"] == "INCONCLUSIVE"
    assert "contract_enabled_runtime_backend_connection" in payload[
        "TrajectoryAwareSamplingRealBackendConnectionSmokeBlockingReasons"
    ]
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_backend_connection_attempted"] is False


def test_real_backend_connection_smoke_requires_failure_manifest_governance() -> None:
    """验证缺少 failure manifest 要求时不能进入真实 GPU smoke 执行。"""
    contract = _ready_contract()
    contract["smoke_output_governance"] = {
        "formal_claim_support_allowed": False,
        "failure_manifest_required": False,
    }

    payload = build_trajectory_aware_sampling_real_backend_connection_smoke(
        contract,
        _config(),
    )

    assert payload["TrajectoryAwareSamplingRealBackendConnectionSmokeDecision"] == "INCONCLUSIVE"
    assert "failure_manifest_requirement_missing" in payload[
        "TrajectoryAwareSamplingRealBackendConnectionSmokeBlockingReasons"
    ]

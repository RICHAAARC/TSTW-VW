"""
文件用途: 验证真实 GPU smoke handoff gate。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.real_backend_connection_smoke_handoff import (
    build_trajectory_aware_sampling_real_backend_connection_smoke_handoff,
)

pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "protocol" / "trajectory_aware_sampling_real_backend_connection_smoke_handoff.json"


def _ready_smoke_request() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingRealBackendConnectionSmokeDecision": "READY_FOR_REAL_GPU_BACKEND_CONNECTION_SMOKE_EXECUTION",
        "NextRequiredValidationAfterRealBackendConnectionSmokeRequest": "real_gpu_backend_connection_smoke",
        "real_backend_connection_smoke_request_allowed": True,
        "gpu_execution_required_for_next_step": True,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "real_backend_connection_attempted": False,
        "smoke_execution_request_count": 1,
        "required_result_artifact_count": 5,
        "real_backend_connection_smoke_digest": "smoke_digest",
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_real_backend_connection_smoke_handoff_builds_external_gpu_package_request() -> None:
    """验证 handoff 只声明外部真实 GPU 执行要求, 当前不连接真实后端。"""
    payload = build_trajectory_aware_sampling_real_backend_connection_smoke_handoff(
        _ready_smoke_request(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffDecision"]
        == "READY_FOR_EXTERNAL_REAL_GPU_SMOKE_RUN"
    )
    assert payload["TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffBlockingReasons"] == []
    assert payload["real_backend_connection_smoke_handoff_allowed"] is True
    assert payload["external_gpu_required"] is True
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_generation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["real_backend_connection_attempted"] is False
    assert payload["required_upload_artifact_count"] == 5
    assert payload["required_download_artifact_count"] == 5
    assert (
        payload["NextRequiredExternalExecutionAfterSmokeHandoff"]
        == "real_gpu_backend_connection_smoke"
    )
    assert (
        payload["external_execution_requirements"]["execution_location"]
        == "external_colab_or_equivalent_real_gpu_environment"
    )


def test_real_backend_connection_smoke_handoff_blocks_unready_smoke_request() -> None:
    """验证上游 smoke request 未通过时, handoff 不会误导用户进入真实 GPU 执行。"""
    smoke_request = _ready_smoke_request()
    smoke_request["TrajectoryAwareSamplingRealBackendConnectionSmokeDecision"] = "INCONCLUSIVE"

    payload = build_trajectory_aware_sampling_real_backend_connection_smoke_handoff(
        smoke_request,
        _config(),
    )

    assert payload["TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffDecision"] == "INCONCLUSIVE"
    assert "real_backend_connection_smoke_not_ready" in payload[
        "TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffBlockingReasons"
    ]
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_backend_connection_attempted"] is False


def test_real_backend_connection_smoke_handoff_blocks_local_backend_connection_attempt() -> None:
    """验证本地 smoke request 如果已尝试真实后端连接, handoff 会阻断。"""
    smoke_request = _ready_smoke_request()
    smoke_request["real_backend_connection_attempted"] = True

    payload = build_trajectory_aware_sampling_real_backend_connection_smoke_handoff(
        smoke_request,
        _config(),
    )

    assert payload["TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffDecision"] == "INCONCLUSIVE"
    assert "smoke_request_attempted_real_backend_connection" in payload[
        "TrajectoryAwareSamplingRealBackendConnectionSmokeHandoffBlockingReasons"
    ]

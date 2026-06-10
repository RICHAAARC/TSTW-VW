"""
文件用途: 验证 trajectory-aware sampling 的 backend adapter scaffold。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.backend_adapter_scaffold import (
    build_trajectory_aware_sampling_backend_adapter_scaffold,
)

pytestmark = [pytest.mark.quick]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT
    / "configs"
    / "protocol"
    / "trajectory_aware_sampling_backend_adapter_scaffold.json"
)


def _ready_backend_integration_decision() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingBackendIntegrationDecision": "READY_FOR_BACKEND_ADAPTER_SCAFFOLD",
        "NextAllowedConstructionAfterBackendIntegrationDecision": "backend_adapter_scaffold",
        "backend_integration_decision_digest": "backend_integration_digest",
        "backend_adapter_scaffold_allowed": True,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_backend_adapter_scaffold_freezes_adapter_schemas_only() -> None:
    """验证 adapter scaffold 只冻结 schema 与 stub, 不打开真实后端。"""
    payload = build_trajectory_aware_sampling_backend_adapter_scaffold(
        _ready_backend_integration_decision(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingBackendAdapterScaffoldDecision"]
        == "READY_FOR_BACKEND_CONNECTION_CONTRACT"
    )
    assert payload["TrajectoryAwareSamplingBackendAdapterScaffoldBlockingReasons"] == []
    assert payload["backend_adapter_scaffold_allowed"] is True
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_generation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["adapter_schema_count"] == 4
    assert payload["adapter_stub_count"] == 2
    assert payload["adapter_schema_descriptors"][0]["schema_status"] == "reserved_schema_only"
    assert payload["adapter_stubs"][0]["adapter_status"] == "not_connected_by_governance"
    assert (
        payload["NextAllowedConstructionAfterBackendAdapterScaffold"]
        == "backend_connection_contract"
    )


def test_backend_adapter_scaffold_blocks_backend_enabled_decision() -> None:
    """验证上游决策如果误打开真实后端, adapter scaffold 会阻断。"""
    decision = _ready_backend_integration_decision()
    decision["runtime_backend_connection_allowed"] = True

    payload = build_trajectory_aware_sampling_backend_adapter_scaffold(
        decision,
        _config(),
    )

    assert payload["TrajectoryAwareSamplingBackendAdapterScaffoldDecision"] == "INCONCLUSIVE"
    assert "integration_decision_enabled_runtime_backend_connection" in payload[
        "TrajectoryAwareSamplingBackendAdapterScaffoldBlockingReasons"
    ]
    assert payload["runtime_backend_connection_allowed"] is False


def test_backend_adapter_scaffold_requires_schema_kinds() -> None:
    """验证没有 adapter schema 清单时不能推进到 backend connection contract。"""
    config = _config()
    config["required_adapter_schema_kinds"] = []

    payload = build_trajectory_aware_sampling_backend_adapter_scaffold(
        _ready_backend_integration_decision(),
        config,
    )

    assert payload["TrajectoryAwareSamplingBackendAdapterScaffoldDecision"] == "INCONCLUSIVE"
    assert "adapter_schema_kinds_missing" in payload[
        "TrajectoryAwareSamplingBackendAdapterScaffoldBlockingReasons"
    ]

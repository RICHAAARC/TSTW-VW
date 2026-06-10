"""
文件用途: 验证 trajectory-aware sampling 的 backend connection contract。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.backend_connection_contract import (
    build_trajectory_aware_sampling_backend_connection_contract,
)

pytestmark = [pytest.mark.quick]

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT
    / "configs"
    / "protocol"
    / "trajectory_aware_sampling_backend_connection_contract.json"
)


def _ready_adapter_scaffold() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingBackendAdapterScaffoldDecision": "READY_FOR_BACKEND_CONNECTION_CONTRACT",
        "NextAllowedConstructionAfterBackendAdapterScaffold": "backend_connection_contract",
        "backend_adapter_scaffold_digest": "adapter_scaffold_digest",
        "backend_adapter_scaffold_allowed": True,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "adapter_schema_count": 4,
        "adapter_stub_count": 2,
    }


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_backend_connection_contract_allows_next_real_backend_smoke_only() -> None:
    """验证 connection contract 只批准下一步 smoke, 当前仍不连接真实后端。"""
    payload = build_trajectory_aware_sampling_backend_connection_contract(
        _ready_adapter_scaffold(),
        _config(),
    )

    assert (
        payload["TrajectoryAwareSamplingBackendConnectionContractDecision"]
        == "READY_FOR_REAL_BACKEND_CONNECTION_SMOKE"
    )
    assert payload["TrajectoryAwareSamplingBackendConnectionContractBlockingReasons"] == []
    assert payload["backend_connection_contract_allowed"] is True
    assert payload["real_backend_connection_smoke_allowed_after_contract"] is True
    assert payload["runtime_backend_connection_allowed"] is False
    assert payload["real_generation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert payload["contract_section_count"] == 6
    assert payload["smoke_backend_family_count"] == 3
    assert payload["smoke_output_governance"]["formal_claim_support_allowed"] is False
    assert (
        payload["NextAllowedConstructionAfterBackendConnectionContract"]
        == "real_backend_connection_smoke"
    )


def test_backend_connection_contract_blocks_backend_enabled_adapter_scaffold() -> None:
    """验证上游 adapter scaffold 如果误打开真实后端, connection contract 会阻断。"""
    scaffold = _ready_adapter_scaffold()
    scaffold["runtime_backend_connection_allowed"] = True

    payload = build_trajectory_aware_sampling_backend_connection_contract(
        scaffold,
        _config(),
    )

    assert payload["TrajectoryAwareSamplingBackendConnectionContractDecision"] == "INCONCLUSIVE"
    assert "adapter_scaffold_enabled_runtime_backend_connection" in payload[
        "TrajectoryAwareSamplingBackendConnectionContractBlockingReasons"
    ]
    assert payload["runtime_backend_connection_allowed"] is False


def test_backend_connection_contract_requires_smoke_governance() -> None:
    """验证 smoke 输出治理缺失时不能推进到真实后端 smoke。"""
    config = _config()
    config["smoke_output_governance"] = {
        "formal_claim_support_allowed": True,
        "failure_manifest_required": False,
        "runtime_environment_snapshot_required": False,
        "model_identity_record_required": False,
    }

    payload = build_trajectory_aware_sampling_backend_connection_contract(
        _ready_adapter_scaffold(),
        config,
    )

    assert payload["TrajectoryAwareSamplingBackendConnectionContractDecision"] == "INCONCLUSIVE"
    reasons = payload["TrajectoryAwareSamplingBackendConnectionContractBlockingReasons"]
    assert "smoke_formal_claim_support_must_remain_disabled" in reasons
    assert "failure_manifest_requirement_missing" in reasons
    assert "runtime_environment_snapshot_requirement_missing" in reasons
    assert "model_identity_record_requirement_missing" in reasons

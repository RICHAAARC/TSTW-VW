"""
文件用途: 验证 trajectory-aware sampling 的真实后端 runtime validation gate.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_aware_sampling_probe.real_backend_runtime_validation_gate import (
    build_trajectory_aware_sampling_real_backend_runtime_validation_gate,
)


pytestmark = [pytest.mark.quick]
ROOT = Path(__file__).resolve().parents[2]


def _read_config() -> dict[str, object]:
    return json.loads(
        (
            ROOT
            / "configs"
            / "protocol"
            / "trajectory_aware_sampling_real_backend_runtime_validation_gate.json"
        ).read_text(encoding="utf-8")
    )


def _passing_connection_gate() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingRealGpuBackendConnectionSmokeResultGateDecision": "PASS",
        "NextAllowedConstructionAfterRealGpuBackendConnectionSmokeResultGate": "real_backend_runtime_validation_gate",
        "external_real_generation_attempted": False,
        "external_real_watermark_integration_attempted": False,
        "real_gpu_backend_connection_smoke_result_gate_digest": "connection_gate_digest",
    }


def _adapter_scaffold() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingBackendAdapterScaffoldDecision": "READY_FOR_BACKEND_CONNECTION_CONTRACT",
        "adapter_schema_count": 4,
        "adapter_schema_descriptors": [
            {
                "schema_kind": "adapter_config_schema",
                "runtime_backend_connection_allowed": False,
                "real_generation_allowed": False,
                "real_watermark_integration_allowed": False,
            },
            {
                "schema_kind": "request_mapping_schema",
                "runtime_backend_connection_allowed": False,
                "real_generation_allowed": False,
                "real_watermark_integration_allowed": False,
            },
            {
                "schema_kind": "result_normalization_schema",
                "runtime_backend_connection_allowed": False,
                "real_generation_allowed": False,
                "real_watermark_integration_allowed": False,
            },
            {
                "schema_kind": "runtime_failure_manifest_schema",
                "runtime_backend_connection_allowed": False,
                "real_generation_allowed": False,
                "real_watermark_integration_allowed": False,
            },
        ],
        "backend_adapter_scaffold_digest": "adapter_scaffold_digest",
    }


def _connection_contract() -> dict[str, object]:
    return {
        "TrajectoryAwareSamplingBackendConnectionContractDecision": "READY_FOR_REAL_BACKEND_CONNECTION_SMOKE",
        "backend_connection_contract_digest": "connection_contract_digest",
    }


def test_real_backend_runtime_validation_gate_passes_with_schema_and_failure_paths() -> None:
    """验证 runtime validation gate 可以在 schema 与失败路径齐备时通过."""
    payload = build_trajectory_aware_sampling_real_backend_runtime_validation_gate(
        _passing_connection_gate(),
        _adapter_scaffold(),
        _connection_contract(),
        _read_config(),
    )

    assert (
        payload["TrajectoryAwareSamplingRealBackendRuntimeValidationGateDecision"]
        == "PASS"
    )
    assert payload["adapter_schema_validation_status"] == "PASS"
    assert payload["failure_path_validation_status"] == "PASS"
    assert payload["failure_path_count"] == 5
    assert payload["real_generation_allowed"] is False
    assert payload["real_watermark_integration_allowed"] is False
    assert (
        payload["NextAllowedConstructionAfterRealBackendRuntimeValidationGate"]
        == "explicit_real_generation_transition_decision"
    )


def test_real_backend_runtime_validation_gate_blocks_missing_schema() -> None:
    """验证缺失 adapter schema 时 gate 明确阻断, 且不打开真实生成能力."""
    adapter_scaffold = _adapter_scaffold()
    adapter_scaffold["adapter_schema_descriptors"] = adapter_scaffold[
        "adapter_schema_descriptors"
    ][:-1]
    adapter_scaffold["adapter_schema_count"] = 3

    payload = build_trajectory_aware_sampling_real_backend_runtime_validation_gate(
        _passing_connection_gate(),
        adapter_scaffold,
        _connection_contract(),
        _read_config(),
    )

    assert (
        payload["TrajectoryAwareSamplingRealBackendRuntimeValidationGateDecision"]
        == "INCONCLUSIVE"
    )
    assert "adapter_schema_kinds_missing_for_runtime_validation" in payload[
        "TrajectoryAwareSamplingRealBackendRuntimeValidationGateBlockingReasons"
    ]
    assert payload["controlled_real_generation_request_allowed"] is False

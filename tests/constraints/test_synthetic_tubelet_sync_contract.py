"""
文件用途：验证阶段 1 synthetic tubelet sync 入口 method config 契约。
File purpose: Validate the reserved method-config contract for the synthetic_tubelet_sync_probe synthetic tubelet sync entry.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

from copy import deepcopy
from pathlib import Path

from experiments.synthetic_tubelet_sync_probe.synthetic_tubelet_sync_contract import (
    SUPPORTED_METHOD_VARIANTS,
    build_reserved_method_support_matrix,
)
from tools.harness.validate_project_contract import (
    load_json_config,
    validate_synthetic_tubelet_sync_method_config_data,
)


ROOT = Path(__file__).resolve().parents[2]


def test_reserved_method_support_matrix_keeps_three_stage_one_variants() -> None:
    """Validate that the reserved method support matrix exposes the governed variants.

    Args:
        None.

    Returns:
        None.
    """
    support_matrix = build_reserved_method_support_matrix()
    assert tuple(support_matrix.keys()) == SUPPORTED_METHOD_VARIANTS


def test_stage_one_method_support_configs_pass() -> None:
    """Validate that all reserved synthetic_tubelet_sync_probe method configs pass the contract.

    Args:
        None.

    Returns:
        None.
    """
    for method_variant in SUPPORTED_METHOD_VARIANTS:
        data = load_json_config(ROOT / "configs" / "method" / f"{method_variant}.json")
        assert validate_synthetic_tubelet_sync_method_config_data(data) == []


def test_frame_prc_requires_unit_tubelet_length() -> None:
    """Validate that `frame_prc` keeps the frame-level tubelet length.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "method" / "frame_prc.json")
    broken = deepcopy(data)
    broken["tubelet_length"] = 4
    violations = validate_synthetic_tubelet_sync_method_config_data(broken)
    assert any(
        violation["reason"] == "unexpected_tubelet_length_for_frame_prc"
        for violation in violations
    )


def test_tubelet_sync_requires_sync_enabled() -> None:
    """Validate that `tubelet_sync` keeps synchronization enabled.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "method" / "tubelet_sync.json")
    broken = deepcopy(data)
    broken["enable_sync"] = False
    violations = validate_synthetic_tubelet_sync_method_config_data(broken)
    assert any(
        violation["reason"] == "unexpected_enable_sync_for_tubelet_sync"
        for violation in violations
    )


def test_tubelet_sync_formal_config_keeps_stage_two_candidate_gate_values() -> None:
    """验证 synthetic 正式配置复用阶段 2 frozen candidate 的同步安全 gate 口径。

    Args:
        None.

    Returns:
        None.
    """
    synthetic_config = load_json_config(ROOT / "configs" / "method" / "tubelet_sync.json")
    stage_two_grid = load_json_config(
        ROOT / "configs" / "ablation" / "stage2_vae_mechanism_calibration_grid.json"
    )
    stage_two_candidate = load_json_config(
        ROOT / "configs" / "method" / "real_video_tubelet_sync_candidate_runtime.json"
    )

    synthetic_sync = synthetic_config["sync_search"]
    stage_two_grid_sync = stage_two_grid["grid"]
    stage_two_candidate_sync = stage_two_candidate["sync_search"]

    assert synthetic_sync["min_sync_alignment_coverage_ratio"] == (
        stage_two_grid_sync["min_sync_alignment_coverage_ratio"][0]
    )
    assert synthetic_sync["min_sync_alignment_coverage_ratio"] == (
        stage_two_candidate_sync["min_sync_alignment_coverage_ratio"]
    )
    assert synthetic_sync["sync_confidence_gate_rule"] == (
        stage_two_candidate_sync["sync_confidence_gate_rule"]
    )
    assert synthetic_sync["min_payload_rescue_gain"] == (
        stage_two_candidate_sync["min_payload_rescue_gain"]
    )
    assert synthetic_sync["min_aligned_payload_score"] == (
        stage_two_candidate_sync["min_aligned_payload_score"]
    )

"""
文件用途：验证阶段 0 support config 骨架配置。
File purpose: Validate the governed protocol skeleton runtime support config skeletons.
Module type: General module
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tools.harness.validate_project_contract import (
    load_json_config,
    validate_ablation_placeholder_data,
    validate_attack_placeholder_data,
    validate_synthetic_tubelet_sync_ablation_support_data,
    validate_synthetic_tubelet_sync_protocol_support_data,
    validate_temporal_attack_matrix_support_data,
)


ROOT = Path(__file__).resolve().parents[1]


def test_ablation_placeholder_config_passes() -> None:
    """Validate that the checked-in ablation placeholder config passes.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "ablation" / "ablation_placeholder.json")
    assert validate_ablation_placeholder_data(data) == []


def test_ablation_placeholder_requires_shared_attack_matrix() -> None:
    """Validate that ablation configs cannot diverge on attack matrices.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "ablation" / "ablation_placeholder.json")
    broken = deepcopy(data)
    broken["shared_attack_matrix_required"] = False
    violations = validate_ablation_placeholder_data(broken)
    assert any(
        violation["reason"] == "shared_attack_matrix_must_be_required"
        for violation in violations
    )


def test_attack_placeholder_config_passes() -> None:
    """Validate that the checked-in identity attack placeholder config passes.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "attacks" / "identity_attack_placeholder.json"
    )
    assert validate_attack_placeholder_data(data) == []


def test_attack_placeholder_requires_identity_attack_name() -> None:
    """Validate that the protocol skeleton runtime attack matrix remains identity-only.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "attacks" / "identity_attack_placeholder.json"
    )
    broken = deepcopy(data)
    broken["attack_matrix_placeholder"][0]["attack_name_placeholder"] = (
        "temporal_crop_placeholder"
    )
    violations = validate_attack_placeholder_data(broken)
    assert any(
        violation["reason"] == "attack_name_placeholder_must_equal_identity_attack_placeholder"
        for violation in violations
    )


def test_synthetic_tubelet_sync_protocol_support_config_passes() -> None:
    """Validate that the reserved synthetic_tubelet_sync_probe protocol support config passes.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "protocol" / "synthetic_tubelet_sync_probe.json"
    )
    assert validate_synthetic_tubelet_sync_protocol_support_data(data) == []


def test_synthetic_tubelet_sync_protocol_support_requires_mechanism_trace() -> None:
    """Validate that the reserved protocol support config requires mechanism trace.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "protocol" / "synthetic_tubelet_sync_probe.json"
    )
    broken = deepcopy(data)
    broken["mechanism_trace_required"] = False
    violations = validate_synthetic_tubelet_sync_protocol_support_data(broken)
    assert any(
        violation["reason"] == "mechanism_trace_must_be_required"
        for violation in violations
    )


def test_temporal_attack_matrix_support_config_passes() -> None:
    """Validate that the reserved temporal attack matrix support config passes.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "attacks" / "temporal_attack_matrix.json"
    )
    assert validate_temporal_attack_matrix_support_data(data) == []


def test_temporal_attack_matrix_requires_governed_attack_order() -> None:
    """Validate that the reserved temporal attack matrix keeps the governed attack order.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "attacks" / "temporal_attack_matrix.json"
    )
    broken = deepcopy(data)
    broken["attacks"] = broken["attacks"][:-1]
    violations = validate_temporal_attack_matrix_support_data(broken)
    assert any(
        violation["reason"] == "stage_one_attack_names_must_match_governed_order"
        for violation in violations
    )


def test_synthetic_tubelet_sync_ablation_support_config_passes() -> None:
    """Validate that the reserved synthetic_tubelet_sync_probe ablation support config passes.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "ablation" / "synthetic_tubelet_sync_ablation.json"
    )
    assert validate_synthetic_tubelet_sync_ablation_support_data(data) == []


def test_synthetic_tubelet_sync_ablation_requires_shared_attack_matrix_name() -> None:
    """Validate that the reserved ablation support config keeps the governed attack matrix.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "ablation" / "synthetic_tubelet_sync_ablation.json"
    )
    broken = deepcopy(data)
    broken["shared_attack_matrix_name"] = "identity_attack_placeholder"
    violations = validate_synthetic_tubelet_sync_ablation_support_data(broken)
    assert any(
        violation["reason"] == "shared_attack_matrix_name_must_equal_temporal_attack_matrix"
        for violation in violations
    )
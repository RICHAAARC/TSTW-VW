"""
鏂囦欢鐢ㄩ€旓細楠岃瘉 fixed low-FPR 闃堝€煎崗璁瓧娈点€?File purpose: Validate threshold protocol governance for the protocol_skeleton stage.
Module type: General module
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tools.harness.validate_project_contract import (
    load_json_config,
    validate_protocol_config_data,
)


ROOT = Path(__file__).resolve().parents[1]


def test_calibration_split_and_negative_roles_pass() -> None:
    """Validate that the checked-in threshold protocol passes governance checks.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "protocol" / "protocol_skeleton.json")
    assert validate_protocol_config_data(data) == []


def test_required_calibration_negative_roles_present() -> None:
    """Validate that clean and attacked negatives are both included.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "protocol" / "protocol_skeleton.json")
    roles = set(data["threshold_protocol"]["calibration_negative_roles"])
    assert {"clean_negative", "attacked_negative"}.issubset(roles)


def test_test_threshold_update_allowed_true_fails() -> None:
    """Validate that enabling threshold updates on test is rejected.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "protocol" / "protocol_skeleton.json")
    broken = deepcopy(data)
    broken["threshold_protocol"]["test_threshold_update_allowed"] = True
    violations = validate_protocol_config_data(broken)
    assert any(
        violation["reason"] == "test_threshold_updates_must_be_disabled"
        for violation in violations
    )


def test_attack_specific_thresholds_are_disabled() -> None:
    """Validate that protocol skeleton runtime protocol config blocks attack-specific thresholds.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "protocol" / "protocol_skeleton.json")
    broken = deepcopy(data)
    broken["threshold_protocol"]["allow_attack_specific_threshold"] = True
    violations = validate_protocol_config_data(broken)
    assert any(
        violation["reason"] == "attack_specific_thresholds_must_be_disabled"
        for violation in violations
    )

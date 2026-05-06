"""
文件用途：验证 protocol_skeleton 项目契约配置。
File purpose: Validate the governed project contract for the protocol_skeleton stage.
Module type: General module
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tools.harness.validate_project_contract import (
    load_json_config,
    validate_project_contract_data,
)


ROOT = Path(__file__).resolve().parents[1]


def test_project_contract_matches_current_stage() -> None:
    """Validate that the checked-in project contract satisfies the stage contract.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "project" / "project_contract.json")
    assert validate_project_contract_data(data) == []


def test_missing_attacked_negative_fails() -> None:
    """Validate that removing `attacked_negative` breaks the contract.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "project" / "project_contract.json")
    broken = deepcopy(data)
    broken["sample_roles"] = [
        role for role in broken["sample_roles"] if role != "attacked_negative"
    ]
    violations = validate_project_contract_data(broken)
    assert any(
        violation["reason"] == "missing_required_sample_roles"
        for violation in violations
    )


def test_missing_trajectory_evidence_fails() -> None:
    """Validate that removing `trajectory_evidence` breaks the contract.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "project" / "project_contract.json")
    broken = deepcopy(data)
    broken["evidence_names"] = [
        name for name in broken["evidence_names"] if name != "trajectory_evidence"
    ]
    violations = validate_project_contract_data(broken)
    assert any(
        violation["reason"] == "missing_required_evidence_names"
        for violation in violations
    )

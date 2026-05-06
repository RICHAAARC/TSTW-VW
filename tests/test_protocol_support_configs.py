"""
文件用途：验证阶段 0 support config 骨架配置。
File purpose: Validate the governed stage-0 support config skeletons.
Module type: General module
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tools.harness.validate_project_contract import (
    load_json_config,
    validate_ablation_placeholder_data,
    validate_attack_placeholder_data,
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
    """Validate that the stage-0 attack matrix remains identity-only.

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
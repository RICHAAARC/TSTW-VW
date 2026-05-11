"""
文件用途：验证命名治理规则与命名审计行为。File purpose: Validate naming governance helper functions and the naming audit behavior.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from tools.harness.audits.audit_naming_conventions import run_audit
from tools.harness.lib.naming_rules import (
    find_forbidden_method_variant,
    find_forbidden_version_like_names,
    is_snake_case_name,
)


def test_valid_naming_examples_pass() -> None:
    """Validate that legitimate naming examples pass helper checks.

    Args:
        None.

    Returns:
        None.
    """
    assert is_snake_case_name("tubelet_sync")
    assert find_forbidden_method_variant('method_variant: "tubelet_sync"') == []


def test_forbidden_method_variant_full_fails() -> None:
    """Validate that `full` is rejected as a formal method variant.

    Args:
        None.

    Returns:
        None.
    """
    assert find_forbidden_method_variant('method_variant: "full"') == ["full"]


def test_version_like_name_protocol_skeleton_v1_fails() -> None:
    """Validate that version-like names are rejected.

    Args:
        None.

    Returns:
        None.
    """
    assert "protocol_skeleton_v1" in find_forbidden_version_like_names(
        "protocol_skeleton_v1"
    )


def test_protocol_skeleton_as_project_stage_fails(tmp_path: Path) -> None:
    """Validate that `protocol_skeleton` is blocked as a formal project stage.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    config_root = tmp_path / "configs" / "project"
    config_root.mkdir(parents=True)
    (config_root / "bad_config.json").write_text(
        '{"project_stage": "protocol_skeleton", "method_variant": "tubelet_sync"}\n',
        encoding="utf-8",
    )

    report = run_audit(tmp_path)
    assert report["decision"] == "fail"
    assert any(
        violation["reason"] == "forbidden_project_stage_name"
        for violation in report["violations"]
    )


def test_docs_builds_are_excluded_from_naming_audit(tmp_path: Path) -> None:
    """Validate that reference files under `docs/builds` are excluded.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    builds_root = tmp_path / "docs" / "builds"
    builds_root.mkdir(parents=True)
    (builds_root / "protocol_skeleton_v1.md").write_text(
        "configs/project/project_" + "contract" + ".yaml\n",
        encoding="utf-8",
    )

    report = run_audit(tmp_path)
    assert report["decision"] == "pass"


def test_yaml_config_suffix_is_rejected(tmp_path: Path) -> None:
    """Validate that governed config files must use the `.json` suffix.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    config_root = tmp_path / "configs" / "project"
    config_root.mkdir(parents=True)
    (config_root / "legacy_contract.yaml").write_text("{}\n", encoding="utf-8")

    report = run_audit(tmp_path)
    assert report["decision"] == "fail"
    assert any(
        violation["reason"] == "formal_config_must_use_json_suffix"
        for violation in report["violations"]
    )


def test_stale_yaml_reference_is_rejected(tmp_path: Path) -> None:
    """Validate that governed files cannot reference old formal `.yaml` paths.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    stale_reference = "configs/project/" + "project_contract" + ".yaml"
    (tmp_path / "README.md").write_text(stale_reference + "\n", encoding="utf-8")

    report = run_audit(tmp_path)
    assert report["decision"] == "fail"
    assert any(
        violation["reason"] == "stale_yaml_config_reference"
        for violation in report["violations"]
    )

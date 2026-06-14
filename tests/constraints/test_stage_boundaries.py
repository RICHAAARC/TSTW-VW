"""
文件用途：验证阶段顺序与 release boundary 未越界。
File purpose: Validate stage ordering and release-boundary constraints.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

from pathlib import Path

from tools.harness.validate_project_contract import load_json_config


ROOT = Path(__file__).resolve().parents[2]


def test_release_directories_are_absent_in_bootstrap_repository() -> None:
    """Validate that the bootstrap stage has not created release directories.

    Args:
        None.

    Returns:
        None.
    """
    assert not (ROOT / "minimal_release").exists()
    assert not (ROOT / "release").exists()


def test_release_boundary_doc_places_release_stage_last() -> None:
    """Validate that the release boundary document keeps release extraction last.

    Args:
        None.

    Returns:
        None.
    """
    text = (ROOT / "docs" / "release_boundary.md").read_text(encoding="utf-8")
    assert "release/" in text
    assert "minimal_release_extraction" in text
    assert text.rfind("minimal_release_extraction") > text.rfind("full_paper_protocol")


def test_project_contract_stage_matches_active_formal_phase() -> None:
    """Validate that the checked-in project stage matches the active formal phase.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(ROOT / "configs" / "project" / "project_contract.json")
    assert data["project_stage"] == "paper_artifact_gate"
    assert data["target_construction_phase"] == "submission_readiness_gate"

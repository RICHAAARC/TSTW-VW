"""
File purpose: Validate governed documentation constraints.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_naming_governance_blocks_weak_stage_and_version_tokens() -> None:
    text = _read("docs/naming_governance.md").lower()
    assert "stage1" in text
    assert "stage2" in text
    assert "stage_1" in text
    assert "stage-1" in text
    assert "_v1" in text
    assert "_p1" in text


def test_placeholder_random_governance_mentions_required_roots() -> None:
    text = _read("docs/placeholder_random_governance.md").lower()
    assert "main" in text
    assert "tests" in text
    assert "tools" in text
    assert ".codex" in text


def test_field_registry_declares_single_registration_table() -> None:
    text = _read("docs/field_registry.md")
    assert "Registry constraint" in text
    assert "docs/field_registry.md" in text

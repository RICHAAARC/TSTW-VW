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


def test_file_organization_contract_mentions_release_boundaries() -> None:
    text = _read("docs/file_organization.md")
    assert "experiments/" in text
    assert "scripts/" in text
    assert "paper_workflow/" in text
    assert "main/colab/" in text


def test_harness_engineering_mentions_file_organization_gate() -> None:
    text = _read("docs/harness_engineering.md")
    assert "docs/file_organization.md" in text
    assert "experiments/" in text
    assert "scripts/" in text
    assert "paper_workflow/colab_utils/" in text
    assert "audit_reports/" in text
    assert "release/" in text


def test_repository_intake_skill_mentions_file_organization_directories() -> None:
    text = _read(".codex/skills/repository_intake.skill.md")
    assert "docs/file_organization.md" in text
    assert "`scripts`" in text
    assert "`experiments`" in text
    assert "`audit_reports`" in text
    assert "`.codex`" in text
    assert "`release`" in text
    assert "`outputs/` is an ephemeral runtime root" in text


def test_release_boundary_mentions_file_organization_contract() -> None:
    text = _read("docs/release_boundary.md")
    assert "docs/file_organization.md" in text
    assert "`release/`" in text
    assert "`minimal_release_extraction`" in text


def test_stage_progression_guard_skill_uses_semantic_stage_names() -> None:
    text = _read(".codex/skills/stage_progression_guard.skill.md")
    assert "allowed semantic stage names" in text.lower()
    assert "synthetic_tubelet_sync_probe" in text
    assert "real_video_vae_latent_probe" in text
    assert (
        "`protocol_skeleton`, `synthetic_tubelet_sync_probe`, `*_v1`, and `*_p0` style "
        "stage identifiers are blocked as formal stage names."
        not in text
    )


def test_minimal_release_skill_mentions_release_directory_prohibition() -> None:
    text = _read(".codex/skills/minimal_release.skill.md")
    assert "`minimal_release/`" in text
    assert "`release/`" in text

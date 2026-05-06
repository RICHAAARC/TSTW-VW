"""
文件用途：验证阶段 0 治理文档已冻结关键边界。
File purpose: Validate that stage-0 governance documents freeze the required boundaries.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    """Read a UTF-8 text file from the repository root.

    Args:
        relative_path: Repository-relative file path.

    Returns:
        File content as UTF-8 text.
    """
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_artifact_rebuild_governance_mentions_records_and_manifest() -> None:
    """Validate that artifact rebuild rules bind outputs to governed provenance.

    Args:
        None.

    Returns:
        None.
    """
    text = _read("docs/artifact_rebuild_governance.md")
    lowered = text.lower()
    assert "records" in lowered
    assert "manifest" in lowered
    assert "manual" in lowered


def test_claim_governance_blocks_placeholder_backed_supported_claims() -> None:
    """Validate that claim governance ties supported claims to governed artifacts.

    Args:
        None.

    Returns:
        None.
    """
    text = _read("docs/claim_governance.md")
    lowered = text.lower()
    assert "supported claim" in lowered
    assert "placeholder" in lowered
    assert any(keyword in lowered for keyword in ("table", "curve", "report"))


def test_ablation_governance_requires_shared_protocol_constraints() -> None:
    """Validate that ablation governance documents shared split and attack rules.

    Args:
        None.

    Returns:
        None.
    """
    text = _read("docs/ablation_governance.md")
    lowered = text.lower()
    assert "split" in lowered
    assert "attack matrix" in lowered
    assert "target fpr" in lowered
    assert "table builder" in lowered
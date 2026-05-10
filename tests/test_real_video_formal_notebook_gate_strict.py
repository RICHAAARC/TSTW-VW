"""
文件用途：验证阶段 2 Colab notebook formal gate 的严格约束。
File purpose: Validate strict formal-gate constraints for the stage-two Colab notebook.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "paper_workflow" / "Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb"


def _load_notebook_text() -> str:
    notebook_payload = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    cells = notebook_payload.get("cells", [])
    text_parts: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            text_parts.append("".join(str(line) for line in source))
        else:
            text_parts.append(str(source))
    return "\n".join(text_parts)


def test_stage2_formal_notebook_gate_is_strict() -> None:
    """Validate the notebook enforces strict formal checks.

    Args:
        None.

    Returns:
        None.
    """
    notebook_text = _load_notebook_text()
    assert "REQUIRE_FORMAL_PASS = True" in notebook_text
    assert "require_formal_pass_criteria=REQUIRE_FORMAL_PASS" in notebook_text
    assert "if not formal_checks['status']:" in notebook_text
    assert "raise RuntimeError(formal_checks)" in notebook_text


def test_stage2_formal_notebook_avoids_direct_tables_threshold_writes() -> None:
    """Validate notebook does not directly write formal tables or thresholds files.

    Args:
        None.

    Returns:
        None.
    """
    notebook_text = _load_notebook_text().lower()
    forbidden_patterns = [
        "tables/main_tpr_fpr_table.csv",
        "tables/quality_table.csv",
        "thresholds/thresholds.json",
        "to_csv('tables/",
        "to_csv(\"tables/",
        "json.dump(",
    ]
    assert all(pattern not in notebook_text for pattern in forbidden_patterns)

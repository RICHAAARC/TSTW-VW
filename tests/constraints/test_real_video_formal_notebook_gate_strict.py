"""
鏂囦欢鐢ㄩ€旓細楠岃瘉闃舵 2 Colab notebook formal gate 鐨勪弗鏍肩害鏉熴€?
File purpose: Validate strict formal-gate constraints for the stage-two Colab notebook.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = ROOT / "paper_workflow" / "aggregate_real_video_vae_latent_probe_shards.ipynb"


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


def test_real_video_formal_notebook_gate_is_strict() -> None:
    """Validate the run notebook enforces strict formal checks.

    Args:
        None.

    Returns:
        None.
    """
    notebook_text = _load_notebook_text()
    assert "merge_real_video_vae_latent_shards.py" in notebook_text
    assert "ready_for_baseline_comparison_gate" in notebook_text
    assert 'if not completion_summary["status"]:' in notebook_text
    assert "raise RuntimeError(completion_summary)" in notebook_text


def test_real_video_formal_notebook_avoids_raw_dataset_handling_and_direct_writes() -> None:
    """Validate notebook B avoids raw-dataset handling and direct formal output writes.

    Args:
        None.

    Returns:
        None.
    """
    notebook_text = _load_notebook_text().lower()
    forbidden_patterns = [
        "scripts.prepare_datasets.build_processed_real_video_dataset",
        "raw_dataset_download_manifest.json",
        "extract_raw_dataset_archive",
        "to_csv('tables/",
        "to_csv(\"tables/",
        "json.dump(",
    ]
    assert all(pattern not in notebook_text for pattern in forbidden_patterns)


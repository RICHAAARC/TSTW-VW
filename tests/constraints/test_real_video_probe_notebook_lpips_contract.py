"""
文件用途：验证阶段 2 notebook 的 LPIPS gate 与最终摘要写盘契约。
File purpose: Validate the stage-two notebook LPIPS gate and final-summary persistence contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = [pytest.mark.constraint]


NOTEBOOK_PATH = Path("paper_workflow/run_real_video_vae_latent_probe.ipynb")


def _read_notebook_source() -> str:
    """功能：读取 notebook 全部代码文本，用于轻量静态契约测试。"""
    notebook_payload = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook_payload.get("cells", [])
    )


def test_real_video_probe_notebook_rejects_bool_lpips_evidence() -> None:
    """功能：确保 notebook 的 LPIPS 证据计数与正式 gate 一样拒绝 bool。"""
    notebook_source = _read_notebook_source()

    assert "def _is_non_bool_number(value):" in notebook_source
    assert "not isinstance(value, bool)" in notebook_source
    assert "lpips_score = quality_metrics.get('watermarked_video_lpips')" in notebook_source
    assert "if _is_non_bool_number(lpips_score):" in notebook_source


def test_real_video_probe_notebook_persists_final_summary_paths() -> None:
    """功能：确保 Colab 单次运行后可以直接定位 notebook 最终摘要。"""
    notebook_source = _read_notebook_source()

    assert "NOTEBOOK_FINAL_SUMMARY_PATH = RUNTIME_PROFILE_ROOT / 'notebook_final_summary.json'" in notebook_source
    assert "FAMILY_FINAL_SUMMARY_PATH = FAMILY_ROOT / 'notebook_final_summary.json'" in notebook_source
    assert "NOTEBOOK_FINAL_SUMMARY_PATH.write_text" in notebook_source
    assert "FAMILY_FINAL_SUMMARY_PATH.write_text" in notebook_source
    assert "'notebook_final_summary_path'" in notebook_source
    assert "'family_final_summary_path'" in notebook_source

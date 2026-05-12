"""
文件用途：验证 real video tar.zst packager notebook handoff contract。
File purpose: Validate the real-video tar.zst packager notebook handoff contract.
Module type: Constraint test module
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_real_video_tar_zst_packager_notebook_contract() -> None:
    """Validate that the governed notebook delegates tar.zst packaging to scripts."""
    notebook_path = ROOT / "paper_workflow" / "run_real_video_vae_latent_probe.ipynb"
    assert notebook_path.exists()
    notebook_text = notebook_path.read_text(encoding="utf-8")

    assert "from scripts.package_results.package_real_video_vae_latent_tar_zst import package_real_video_vae_latent_tar_zst" in notebook_text
    assert "package_real_video_vae_latent_tar_zst(" in notebook_text
    assert "drive_archive_path = tar_pack['archive_path']" in notebook_text
    assert "compat_pack_root = RUN_ROOT" in notebook_text
    assert '"archive_path": str(drive_archive_path)' in notebook_text or "'archive_path': str(drive_archive_path)" in notebook_text

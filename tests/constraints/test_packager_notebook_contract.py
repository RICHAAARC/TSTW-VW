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
    workflow_path = (
        ROOT
        / "paper_workflow"
        / "notebook_utils"
        / "real_video_vae_latent_probe_workflow.py"
    )
    zip_packager_path = (
        ROOT
        / "scripts"
        / "package_results"
        / "package_real_video_vae_latent_outputs.py"
    )
    tar_packager_path = (
        ROOT
        / "scripts"
        / "package_results"
        / "package_real_video_vae_latent_tar_zst.py"
    )
    assert notebook_path.exists()
    assert workflow_path.exists()
    assert zip_packager_path.exists()
    assert tar_packager_path.exists()
    notebook_text = notebook_path.read_text(encoding="utf-8")
    workflow_text = workflow_path.read_text(encoding="utf-8")
    zip_packager_text = zip_packager_path.read_text(encoding="utf-8")
    tar_packager_text = tar_packager_path.read_text(encoding="utf-8")

    assert "probe_workflow.package_probe_non_formal_audit_bundle(" in notebook_text
    assert "probe_workflow.package_probe_family_results(" in notebook_text
    assert "TSTW_PACKAGE_NON_FORMAL_AUDIT_BUNDLE" in notebook_text
    assert (
        "from scripts.package_results.package_real_video_vae_latent_tar_zst import"
        in workflow_text
    )
    assert "package_real_video_vae_latent_tar_zst(" in workflow_text
    assert "local_archive_path = package_payload['drive_archive_path']" in notebook_text
    assert "probe_workflow.materialize_probe_family_results_to_drive(" in notebook_text
    assert "drive_archive_path = drive_family_materialization_summary.get('drive_archive_path')" in notebook_text
    assert "compat_pack_root = package_payload['compat_pack_root']" in notebook_text
    assert "drive_root=None" in notebook_text
    assert "drive_family_root=DRIVE_FAMILY_ROOT" in notebook_text
    assert '"drive_archive_path": str(tar_pack["archive_path"])' in workflow_text or "'drive_archive_path': str(tar_pack[\"archive_path\"])" in workflow_text
    assert "runtime_profile" in zip_packager_text
    assert "runtime_profile_included" in zip_packager_text
    assert "runtime_profile" in tar_packager_text
    assert "runtime_profile_included" in tar_packager_text

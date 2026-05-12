"""
文件用途：验证阶段 2 scaffold 打包器生成 zip 与摘要文件。
File purpose: Validate that the stage-two scaffold packager creates a zip archive and summaries.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

pytestmark = pytest.mark.integration

from scripts.package_results.drive_packager import pack_real_video_vae_latent_run
from tests.helpers.real_video_probe_run import run_real_video_vae_latent_debug


@pytest.mark.smoke
def test_real_video_vae_latent_drive_packager_emits_archive_and_summaries(tmp_path: Path) -> None:
    """Validate that the stage-two scaffold packager emits archive and summaries.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = run_real_video_vae_latent_debug(tmp_path)
    packaged_paths = pack_real_video_vae_latent_run(
        run_root=output_root,
        drive_output_dir=tmp_path / "packed_runs",
    )
    assert packaged_paths["zip_path"].exists()
    assert packaged_paths["summary_path"].exists()
    assert packaged_paths["checks_path"].exists()
    summary_payload = json.loads(packaged_paths["summary_path"].read_text(encoding="utf-8"))
    assert summary_payload["construction_phase"] == "real_video_vae_latent_probe"
    assert "RealVideoVaeLatentDecision" in summary_payload
    with zipfile.ZipFile(packaged_paths["zip_path"]) as archive:
        archive_names = set(archive.namelist())
    assert any(name.endswith("records/event_scores.jsonl") for name in archive_names)
    assert any(name.endswith("thresholds/thresholds.json") for name in archive_names)
    assert any(name.endswith("tables/quality_table.csv") for name in archive_names)
    assert any(name.endswith("tables/real_video_vae_latent_governance_summary.csv") for name in archive_names)
    assert any(name.endswith("reports/vae_latent_probe_report.md") for name in archive_names)

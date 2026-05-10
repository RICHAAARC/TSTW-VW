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

from main.colab.drive_packager import pack_stage2_run
from tests.stage2_test_support import run_stage2_tiny


@pytest.mark.smoke
def test_stage2_drive_packager_emits_archive_and_summaries(tmp_path: Path) -> None:
    """Validate that the stage-two scaffold packager emits archive and summaries.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = run_stage2_tiny(tmp_path)
    packaged_paths = pack_stage2_run(
        run_root=output_root,
        drive_output_dir=tmp_path / "packed_runs",
    )
    assert packaged_paths["zip_path"].exists()
    assert packaged_paths["summary_path"].exists()
    assert packaged_paths["checks_path"].exists()
    summary_payload = json.loads(packaged_paths["summary_path"].read_text(encoding="utf-8"))
    assert summary_payload["construction_phase"] == "real_video_vae_latent_probe"
    assert "Stage2Decision" in summary_payload
    with zipfile.ZipFile(packaged_paths["zip_path"]) as archive:
        archive_names = set(archive.namelist())
    assert any(name.endswith("records/event_scores.jsonl") for name in archive_names)
    assert any(name.endswith("thresholds/thresholds.json") for name in archive_names)
    assert any(name.endswith("tables/quality_table.csv") for name in archive_names)
    assert any(name.endswith("tables/stage2_governance_summary.csv") for name in archive_names)
    assert any(name.endswith("reports/vae_latent_probe_report.md") for name in archive_names)

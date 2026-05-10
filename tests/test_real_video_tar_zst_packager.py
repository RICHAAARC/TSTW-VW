"""
文件用途：验证 tar.zst 打包器可生成归档与摘要文件。
File purpose: Validate the tar.zst packager outputs archive and summary files.
Module type: General module
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from main.colab.notebook_result_checker import check_real_video_vae_latent_outputs
from main.colab.tar_zst_packager import pack_run_to_tar_zst
from tests.real_video_vae_latent_test_support import run_real_video_vae_latent_tiny


@pytest.mark.smoke
def test_stage2_tar_zst_packager_outputs_archive_and_checks(tmp_path: Path) -> None:
    """Validate tar.zst packager outputs archive, summary, and checks files.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    if shutil.which("tar") is None:
        pytest.skip("tar is unavailable")
    help_text = subprocess.check_output(["tar", "--help"], text=True)
    if "--zstd" not in help_text:
        pytest.skip("tar --zstd is unavailable")

    output_root = run_real_video_vae_latent_tiny(tmp_path)
    checks_payload = check_real_video_vae_latent_outputs(output_root, run_mode="smoke")
    packaged_paths = pack_run_to_tar_zst(
        run_root=output_root,
        drive_result_dir=tmp_path / "packed_tar_zst",
        checks_payload=checks_payload,
    )

    assert packaged_paths["archive_path"].exists()
    assert packaged_paths["summary_path"].exists()
    assert packaged_paths["checks_path"].exists()
    tar_listing = subprocess.check_output(["tar", "--list", "--file", str(packaged_paths["archive_path"])], text=True)
    assert "records/event_scores.jsonl" in tar_listing
    assert "thresholds/thresholds.json" in tar_listing
    assert "tables/quality_table.csv" in tar_listing

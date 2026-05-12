"""
文件用途：验证 real video tar.zst 打包器的 smoke 归档路径。
File purpose: Validate the real-video tar.zst packager smoke archive path.
Module type: Integration test module
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.check_results.real_video_vae_latent_output_checker import (
    check_real_video_vae_latent_outputs,
)
from scripts.package_results.tar_zst_packager import pack_run_to_tar_zst
from tests.helpers.real_video_probe_run import run_real_video_vae_latent_debug


pytestmark = [pytest.mark.integration, pytest.mark.smoke]


def test_real_video_tar_zst_packager_outputs_archive_and_checks(tmp_path: Path) -> None:
    """Validate tar.zst packager outputs archive, summary, and checks files."""
    if shutil.which("tar") is None:
        pytest.skip("tar is unavailable")
    help_text = subprocess.check_output(["tar", "--help"], text=True)
    if "--zstd" not in help_text:
        pytest.skip("tar --zstd is unavailable")

    output_root = run_real_video_vae_latent_debug(tmp_path)
    checks_payload = check_real_video_vae_latent_outputs(output_root, run_mode="smoke")
    packaged_paths = pack_run_to_tar_zst(
        run_root=output_root,
        drive_result_dir=tmp_path / "packed_tar_zst",
        checks_payload=checks_payload,
        exclude_large_intermediate_latents=True,
    )

    assert packaged_paths["archive_path"].exists()
    assert packaged_paths["summary_path"].exists()
    assert packaged_paths["checks_path"].exists()
    summary_payload = json.loads(packaged_paths["summary_path"].read_text(encoding="utf-8"))
    assert summary_payload["archive_format"] == "tar.zst"
    assert summary_payload["decision"] == checks_payload["RealVideoVaeLatentDecision"]
    assert summary_payload["checks_path"] == str(packaged_paths["checks_path"])
    assert summary_payload["summary_path"] == str(packaged_paths["summary_path"])
    assert summary_payload["excluded_patterns"]

    tar_listing = subprocess.check_output(
        ["tar", "--list", "--file", str(packaged_paths["archive_path"])],
        text=True,
    )
    assert "records/event_scores.jsonl" in tar_listing
    assert "thresholds/thresholds.json" in tar_listing
    assert "tables/quality_table.csv" in tar_listing
    assert "reports/vae_latent_probe_report.md" in tar_listing
    assert "artifacts/run_manifest.json" in tar_listing
    assert "artifacts/artifact_manifest.json" in tar_listing
    assert "artifacts/runtime_manifest.json" in tar_listing

"""
文件用途：验证 tar.zst 打包器可生成归档与摘要文件。
File purpose: Validate the tar.zst packager outputs archive and summary files.
Module type: General module
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.check_results.real_video_vae_latent_output_checker import (
    check_real_video_vae_latent_outputs,
)
from scripts.package_results.tar_zst_packager import pack_run_to_tar_zst
from tests.real_video_vae_latent_test_support import run_real_video_vae_latent_tiny


@pytest.mark.smoke
def test_real_video_tar_zst_packager_outputs_archive_and_checks(tmp_path: Path) -> None:
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

    tar_listing = subprocess.check_output(["tar", "--list", "--file", str(packaged_paths["archive_path"])], text=True)
    assert "records/event_scores.jsonl" in tar_listing
    assert "thresholds/thresholds.json" in tar_listing
    assert "tables/quality_table.csv" in tar_listing
    assert "reports/vae_latent_probe_report.md" in tar_listing
    assert "artifacts/run_manifest.json" in tar_listing
    assert "artifacts/artifact_manifest.json" in tar_listing
    assert "artifacts/runtime_manifest.json" in tar_listing


def _make_run_root(tmp_path: Path) -> Path:
    """Build a minimal real_video_vae_latent_probe run root for tar.zst contract tests."""
    return run_real_video_vae_latent_tiny(tmp_path)


def test_real_video_tar_zst_packager_summary_fields(tmp_path: Path) -> None:
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_results"
    checks_payload = {
        "RealVideoVaeLatentDecision": "INCONCLUSIVE",
        "status": False,
        "BlockingReasons": ["video_vae_backend_placeholder"],
    }

    with (
        patch("scripts.package_results.tar_zst_packager._supports_tar_zstd", return_value=True),
        patch("scripts.package_results.tar_zst_packager.subprocess.run"),
    ):
        result = pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
            exclude_large_intermediate_latents=True,
        )

    assert result["archive_path"].suffix == ".zst"
    assert result["archive_path"].stem.endswith(".tar")
    assert result["summary_path"].exists()
    assert result["checks_path"].exists()

    summary = json.loads(result["summary_path"].read_text(encoding="utf-8"))
    assert summary["archive_format"] == "tar.zst"
    assert summary["decision"] == "INCONCLUSIVE"
    assert summary["status"] is False
    assert "archive_path" in summary
    assert "summary_path" in summary
    assert "checks_path" in summary
    assert "run_id" in summary
    assert isinstance(summary["excluded_patterns"], list)
    assert len(summary["excluded_patterns"]) > 0


def test_real_video_tar_zst_packager_decision_matches_checks(tmp_path: Path) -> None:
    run_root = _make_run_root(tmp_path)
    for decision_value in ("PASS", "FAIL", "INCONCLUSIVE"):
        drive_result_dir = tmp_path / f"drive_{decision_value}"
        checks_payload = {
            "RealVideoVaeLatentDecision": decision_value,
            "status": decision_value == "PASS",
        }

        with (
            patch("scripts.package_results.tar_zst_packager._supports_tar_zstd", return_value=True),
            patch("scripts.package_results.tar_zst_packager.subprocess.run"),
        ):
            result = pack_run_to_tar_zst(
                run_root=run_root,
                drive_result_dir=drive_result_dir,
                checks_payload=checks_payload,
            )

        summary = json.loads(result["summary_path"].read_text(encoding="utf-8"))
        checks_out = json.loads(result["checks_path"].read_text(encoding="utf-8"))
        assert summary["decision"] == decision_value
        assert checks_out["RealVideoVaeLatentDecision"] == decision_value


def test_real_video_tar_zst_packager_archive_extension(tmp_path: Path) -> None:
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_ext_check"
    checks_payload: dict[str, Any] = {
        "RealVideoVaeLatentDecision": "INCONCLUSIVE",
        "status": False,
    }

    with (
        patch("scripts.package_results.tar_zst_packager._supports_tar_zstd", return_value=True),
        patch("scripts.package_results.tar_zst_packager.subprocess.run"),
    ):
        result = pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
        )

    archive_name = result["archive_path"].name
    assert archive_name.endswith(".tar.zst")
    assert result["summary_path"].name.endswith("_summary.json")
    assert result["checks_path"].name.endswith("_checks.json")


def test_real_video_tar_zst_packager_raises_without_tar_zstd(tmp_path: Path) -> None:
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_guard"
    checks_payload: dict[str, Any] = {
        "RealVideoVaeLatentDecision": "INCONCLUSIVE",
        "status": False,
    }

    with (
        patch("scripts.package_results.tar_zst_packager._supports_tar_zstd", return_value=False),
        pytest.raises(RuntimeError, match="tar --zstd is unavailable"),
    ):
        pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
        )


def test_real_video_tar_zst_packager_notebook_contract() -> None:
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "paper_workflow"
        / "Stage2_Real_Video_VAE_Latent_Probe.ipynb"
    )
    assert notebook_path.exists()
    notebook_text = notebook_path.read_text(encoding="utf-8")

    assert "from scripts.package_results.tar_zst_packager import pack_run_to_tar_zst" in notebook_text
    assert "pack_run_to_tar_zst(" in notebook_text
    assert "drive_archive_path = tar_pack[" in notebook_text
    assert "compat_pack_root = run_root" in notebook_text
    assert '"archive_path": str(drive_archive_path)' in notebook_text or "'archive_path': str(drive_archive_path)" in notebook_text

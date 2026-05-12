"""
文件用途：验证 tar.zst 打包器的轻量功能契约。
File purpose: Validate quick functional contracts for the tar.zst packager.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from scripts.package_results.tar_zst_packager import pack_run_to_tar_zst


pytestmark = pytest.mark.quick


def _make_run_root(tmp_path: Path) -> Path:
    """Build a minimal run root for tar.zst contract tests without invoking a runner."""
    run_root = tmp_path / "run_root"
    for relative_path in (
        "records",
        "thresholds",
        "tables",
        "figures",
        "reports",
        "failure_case_gallery",
        "logs",
        "artifacts",
    ):
        (run_root / relative_path).mkdir(parents=True, exist_ok=True)
    (run_root / "artifacts" / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": "quick_packager_contract",
                "construction_phase": "real_video_vae_latent_probe",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return run_root


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

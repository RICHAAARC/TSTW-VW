"""
文件用途：验证 tar.zst 打包器的轻量功能契约。
File purpose: Validate quick functional contracts for the tar.zst packager.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any
from unittest.mock import patch

import pytest

from scripts.package_results.tar_zst_packager import pack_run_to_tar_zst


pytestmark = pytest.mark.quick


class _PassthroughCompressedWriter:
    def __init__(self, handle: Any) -> None:
        self._handle = handle

    def __enter__(self) -> "_PassthroughCompressedWriter":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        del exc_type, exc_value, traceback
        return False

    def write(self, data: bytes) -> int:
        return self._handle.write(data)


class _FakeZstdCompressor:
    def stream_writer(self, handle: Any) -> _PassthroughCompressedWriter:
        return _PassthroughCompressedWriter(handle)


class _FakeZstandardModule:
    def ZstdCompressor(self) -> _FakeZstdCompressor:
        return _FakeZstdCompressor()


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
        patch("scripts.package_results.tar_zst_packager._load_zstandard_module", return_value=None),
        pytest.raises(RuntimeError, match="python fallback requires the zstandard package"),
    ):
        pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
        )


def test_real_video_tar_zst_packager_falls_back_when_external_tar_fails(
    tmp_path: Path,
) -> None:
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_fallback"
    checks_payload: dict[str, Any] = {
        "RealVideoVaeLatentDecision": "INCONCLUSIVE",
        "status": False,
    }

    failing_error = subprocess.CalledProcessError(
        2,
        ["tar", "--zstd", "-cf", "archive.tar.zst"],
        stderr="tar (child): zstd: Cannot exec: No such file or directory",
    )

    with (
        patch("scripts.package_results.tar_zst_packager._supports_tar_zstd", return_value=True),
        patch(
            "scripts.package_results.tar_zst_packager._load_zstandard_module",
            return_value=_FakeZstandardModule(),
        ),
        patch(
            "scripts.package_results.tar_zst_packager.subprocess.run",
            side_effect=failing_error,
        ),
    ):
        result = pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
        )

    assert result["archive_path"].exists()
    assert result["archive_path"].name.endswith(".tar.zst")
    assert not any(path.suffix == ".tar" for path in drive_result_dir.iterdir())


def test_real_video_tar_zst_packager_replaces_zero_byte_archive_on_fallback(
    tmp_path: Path,
) -> None:
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_zero_byte"
    checks_payload: dict[str, Any] = {
        "RealVideoVaeLatentDecision": "INCONCLUSIVE",
        "status": False,
    }

    def _create_zero_byte_archive_then_fail(*args: Any, **kwargs: Any) -> None:
        del kwargs
        command = args[0]
        archive_path = Path(command[3])
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(b"")
        raise subprocess.CalledProcessError(
            2,
            command,
            stderr="tar (child): zstd: Cannot exec: No such file or directory",
        )

    with (
        patch("scripts.package_results.tar_zst_packager._supports_tar_zstd", return_value=True),
        patch(
            "scripts.package_results.tar_zst_packager._load_zstandard_module",
            return_value=_FakeZstandardModule(),
        ),
        patch(
            "scripts.package_results.tar_zst_packager.subprocess.run",
            side_effect=_create_zero_byte_archive_then_fail,
        ),
    ):
        result = pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
        )

    assert result["archive_path"].exists()
    assert result["archive_path"].stat().st_size > 0

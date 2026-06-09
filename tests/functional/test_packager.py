"""
文件用途：验证 real-video zip / tar.zst 打包器的轻量功能契约。
File purpose: Validate quick functional contracts for the real-video zip and tar.zst packagers.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any
from unittest.mock import patch
import zipfile

import pytest

import scripts.package_results.drive_packager as drive_packager_module
import scripts.package_results.package_real_video_vae_latent_tar_zst as family_tar_packager_module
from paper_workflow.notebook_utils.real_video_vae_latent_probe_workflow import (
    _write_stage2_frozen_baseline_handoff,
)

from scripts.package_results.drive_packager import pack_real_video_vae_latent_run
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
    (run_root / "artifacts" / "artifact_manifest.json").write_text(
        json.dumps({"artifacts": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_root / "artifacts" / "runtime_manifest.json").write_text(
        json.dumps({"git_commit": "test-commit"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_root / "artifacts" / "runtime_config.json").write_text(
        json.dumps({"runtime_profile": "debug_real_video"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_root / "artifacts" / "stage2_mechanism_decision.json").write_text(
        json.dumps(
            {
                "Stage2ImplementationDecision": "PASS",
                "Stage2MechanismDecision": "INCONCLUSIVE",
                "Stage2MechanismBlockingReasons": ["sample_count_insufficient"],
                "NextAllowedStageByImplementation": "trajectory_statistic_probe",
                "NextAllowedStageByMechanism": "remain_in_real_video_vae_latent_probe",
                "RecommendedNextAction": "stage2_mechanism_calibration_run",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return run_root


def test_real_video_drive_packager_includes_stage2_mechanism_decision(tmp_path: Path) -> None:
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_zip"

    with patch.object(
        drive_packager_module,
        "check_real_video_vae_latent_outputs",
        return_value={
            "RealVideoVaeLatentDecision": "INCONCLUSIVE",
            "BlockingReasons": [],
        },
    ):
        result = pack_real_video_vae_latent_run(
            run_root=run_root,
            drive_output_dir=drive_result_dir,
            exclude_large_intermediate_latents=True,
        )

    with zipfile.ZipFile(result["zip_path"]) as archive:
        archive_names = set(archive.namelist())

    assert (
        f"{run_root.name}/artifacts/stage2_mechanism_decision.json" in archive_names
    )


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


def test_real_video_family_tar_packager_keeps_stage2_mechanism_decision(
    tmp_path: Path,
) -> None:
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "family_tar"
    captured_inputs: dict[str, list[str]] = {}

    def _capture_tar_inputs(
        *,
        archive_path: Path,
        run_root_path: Path,
        tar_inputs: list[str],
    ) -> None:
        del run_root_path
        captured_inputs["tar_inputs"] = list(tar_inputs)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(b"tar")

    with (
        patch.object(family_tar_packager_module, "_supports_tar_zstd", return_value=True),
        patch.object(
            family_tar_packager_module,
            "_pack_with_external_tar_zstd",
            side_effect=_capture_tar_inputs,
        ),
    ):
        result = family_tar_packager_module._package_run_with_runtime_profile(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload={
                "RealVideoVaeLatentDecision": "INCONCLUSIVE",
                "status": False,
            },
            exclude_large_intermediate_latents=True,
        )

    assert result["archive_path"].exists()
    assert (
        f"{run_root.name}/artifacts/stage2_mechanism_decision.json"
        in captured_inputs["tar_inputs"]
    )


def test_real_video_tar_zst_packager_keeps_stage2_mechanism_decision(
    tmp_path: Path,
) -> None:
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "public_tar"
    captured_inputs: dict[str, list[str]] = {}

    def _capture_tar_inputs(
        *,
        archive_path: Path,
        run_root_path: Path,
        tar_inputs: list[str],
    ) -> None:
        del run_root_path
        captured_inputs["tar_inputs"] = list(tar_inputs)
        archive_path.write_bytes(b"tar")

    with (
        patch("scripts.package_results.tar_zst_packager._supports_tar_zstd", return_value=True),
        patch(
            "scripts.package_results.tar_zst_packager._pack_with_external_tar_zstd",
            side_effect=_capture_tar_inputs,
        ),
    ):
        result = pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload={
                "RealVideoVaeLatentDecision": "INCONCLUSIVE",
                "status": False,
            },
            exclude_large_intermediate_latents=True,
        )

    assert result["archive_path"].exists()
    assert (
        f"{run_root.name}/artifacts/stage2_mechanism_decision.json"
        in captured_inputs["tar_inputs"]
    )


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


def test_notebook_family_packaging_writes_stage2_frozen_baseline_handoff(
    tmp_path: Path,
) -> None:
    """验证 notebook handoff 摘要包含阶段 3 replay 需要的最小文件合同。"""
    run_root = _make_run_root(tmp_path)
    family_root = tmp_path / "family_root"
    package_payload = {
        "drive_archive_path": str(family_root / "packages" / "run.tar.zst"),
        "zip_pack": {"zip_path": str(family_root / "packages" / "run.zip")},
        "archive_format": "tar.zst",
        "package_format": "tar.zst",
    }

    handoff_path = _write_stage2_frozen_baseline_handoff(
        run_root=run_root,
        family_root=family_root,
        package_payload=package_payload,
        mechanism_summary={
            "Stage2ImplementationDecision": "PASS",
            "Stage2MechanismDecision": "PASS",
            "stage2_mechanism_protocol": "aligned_payload_safety",
            "NextAllowedStageByMechanism": "trajectory_statistic_probe",
        },
    )

    handoff_payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert handoff_payload["handoff_kind"] == (
        "stage2_frozen_baseline_for_trajectory_statistic_probe"
    )
    for required_relpath in (
        "records/event_scores.jsonl",
        "thresholds/thresholds.json",
        "artifacts/run_manifest.json",
        "artifacts/stage2_mechanism_decision.json",
    ):
        assert required_relpath in handoff_payload["required_relpaths"]
    assert handoff_payload["Stage2MechanismDecision"] == "PASS"


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

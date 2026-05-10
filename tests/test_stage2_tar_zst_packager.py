"""
文件用途：验证 P9 阶段 tar.zst packager 合约，不依赖 tar --zstd 二进制。
File purpose: Validate the P9-stage tar.zst packager contract without requiring tar --zstd binary.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from main.colab.tar_zst_packager import pack_run_to_tar_zst
from tests.real_video_vae_latent_test_support import run_real_video_vae_latent_tiny


def _make_run_root(tmp_path: Path) -> Path:
    """功能：构造最小化 run root 用于 packager 测试。

    Build a minimal stage-two run root for packager contract testing.

    Args:
        tmp_path: Temporary directory root.

    Returns:
        The run root path with required subdirectories and run_manifest.json.
    """
    return run_real_video_vae_latent_tiny(tmp_path)


def test_stage2_tar_zst_packager_summary_fields(tmp_path: Path) -> None:
    """Validate that pack_run_to_tar_zst writes summary with required P9 fields.

    Uses subprocess.run mock so tar --zstd binary is not required.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_results"
    checks_payload = {
        "RealVideoVaeLatentDecision": "INCONCLUSIVE",
        "status": False,
        "BlockingReasons": ["video_vae_backend_placeholder"],
    }

    # tar --zstd 二进制不可用时通过 mock 跳过实际打包，只测 summary/checks 写出逻辑
    with (
        patch("main.colab.tar_zst_packager._supports_tar_zstd", return_value=True),
        patch("main.colab.tar_zst_packager.subprocess.run"),
    ):
        result = pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
            exclude_large_intermediate_latents=True,
        )

    # 三个输出路径必须存在（summary 和 checks 是真实写出的）
    assert result["archive_path"].suffix == ".zst"
    assert result["archive_path"].stem.endswith(".tar")
    assert result["summary_path"].exists()
    assert result["checks_path"].exists()

    summary = json.loads(result["summary_path"].read_text(encoding="utf-8"))

    # P9 必须字段
    assert summary["archive_format"] == "tar.zst"
    assert summary["decision"] == "INCONCLUSIVE"
    assert summary["status"] is False
    assert "archive_path" in summary
    assert "summary_path" in summary
    assert "checks_path" in summary
    assert "run_id" in summary
    assert isinstance(summary["excluded_patterns"], list)
    assert len(summary["excluded_patterns"]) > 0  # exclude_large_intermediate_latents=True


def test_stage2_tar_zst_packager_decision_matches_checks(tmp_path: Path) -> None:
    """Validate that decision in summary payload matches checks_payload.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = _make_run_root(tmp_path)
    for decision_value in ("PASS", "FAIL", "INCONCLUSIVE"):
        drive_result_dir = tmp_path / f"drive_{decision_value}"
        checks_payload = {
            "RealVideoVaeLatentDecision": decision_value,
            "status": decision_value == "PASS",
        }

        with (
            patch("main.colab.tar_zst_packager._supports_tar_zstd", return_value=True),
            patch("main.colab.tar_zst_packager.subprocess.run"),
        ):
            result = pack_run_to_tar_zst(
                run_root=run_root,
                drive_result_dir=drive_result_dir,
                checks_payload=checks_payload,
            )

        summary = json.loads(result["summary_path"].read_text(encoding="utf-8"))
        checks_out = json.loads(result["checks_path"].read_text(encoding="utf-8"))
        # decision 必须与 checks_payload 一致
        assert summary["decision"] == decision_value
        assert checks_out["RealVideoVaeLatentDecision"] == decision_value


def test_stage2_tar_zst_packager_archive_extension(tmp_path: Path) -> None:
    """Validate that the archive output path ends with .tar.zst.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_ext_check"
    checks_payload: dict = {"RealVideoVaeLatentDecision": "INCONCLUSIVE", "status": False}

    with (
        patch("main.colab.tar_zst_packager._supports_tar_zstd", return_value=True),
        patch("main.colab.tar_zst_packager.subprocess.run"),
    ):
        result = pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
        )

    archive_name = result["archive_path"].name
    assert archive_name.endswith(".tar.zst"), f"archive name {archive_name!r} does not end with .tar.zst"
    assert result["summary_path"].name.endswith("_summary.json")
    assert result["checks_path"].name.endswith("_checks.json")


def test_stage2_tar_zst_packager_raises_without_tar_zstd(tmp_path: Path) -> None:
    """Validate that pack_run_to_tar_zst raises RuntimeError when tar --zstd is unavailable.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = _make_run_root(tmp_path)
    drive_result_dir = tmp_path / "drive_guard"
    checks_payload: dict = {"RealVideoVaeLatentDecision": "INCONCLUSIVE", "status": False}

    with (
        patch("main.colab.tar_zst_packager._supports_tar_zstd", return_value=False),
        pytest.raises(RuntimeError, match="tar --zstd is unavailable"),
    ):
        pack_run_to_tar_zst(
            run_root=run_root,
            drive_result_dir=drive_result_dir,
            checks_payload=checks_payload,
        )


def test_stage2_tar_zst_packager_notebook_cell14_contract() -> None:
    """Validate that notebook Cell 14 calls pack_run_to_tar_zst as the primary Drive packager.

    P9 contract: tar.zst must be the primary Drive output; zip is only a local compat byproduct.

    Args:
        None.

    Returns:
        None.
    """
    notebook_path = Path(__file__).resolve().parents[1] / "paper_workflow" / "Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb"
    assert notebook_path.exists()
    notebook_text = notebook_path.read_text(encoding="utf-8")

    # tar.zst packager 必须被 import 并调用
    assert "from main.colab.tar_zst_packager import pack_run_to_tar_zst" in notebook_text
    assert "pack_run_to_tar_zst(" in notebook_text

    # drive_archive_path 必须来自 tar_pack（tar.zst packager 输出），而非 compat_pack（zip）
    assert "drive_archive_path = tar_pack[" in notebook_text

    # zip 只作本地副产物，compat_pack_root 必须是本地 run_root 子路径
    assert "compat_pack_root = run_root" in notebook_text

    # result_registry 中 archive_path 必须来自 tar_pack 输出的 drive_archive_path
    assert '"archive_path": str(drive_archive_path)' in notebook_text or "'archive_path': str(drive_archive_path)" in notebook_text

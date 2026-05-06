"""
文件用途：验证仓库 intake 检查与阶段 0 目录边界。
File purpose: Validate repository intake inspection and protocol_skeleton directory boundaries.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from tools.harness.inspect_repository import EXPECTED_DIRECTORIES, inspect_repository


ROOT = Path(__file__).resolve().parents[1]


def test_empty_repository_bootstrap_is_detected(tmp_path: Path) -> None:
    """Validate that a directory without governed roots is bootstrap-empty.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    report = inspect_repository(tmp_path)
    assert report["repository_mode"] == "empty_repository_bootstrap"
    assert all(
        report["directory_status"][directory_name]["exists"] is False
        for directory_name in EXPECTED_DIRECTORIES
    )


def test_governed_repository_reports_protocol_skeleton_status() -> None:
    """Validate that the current repository exposes stage and directory status.

    Args:
        None.

    Returns:
        None.
    """
    report = inspect_repository(ROOT)
    assert report["repository_mode"] == "governed_repository"
    assert report["project_stage"] == "protocol_skeleton"
    assert report["directory_status"]["configs"]["exists"] is True
    assert report["directory_status"]["docs"]["exists"] is True
    assert report["directory_status"]["tools"]["exists"] is True
    assert report["directory_status"]["tests"]["exists"] is True
    assert report["directory_status"]["main"]["exists"] is False
    assert report["directory_status"]["paper_workflow"]["exists"] is False
    assert report["directory_status"]["outputs"]["exists"] is False
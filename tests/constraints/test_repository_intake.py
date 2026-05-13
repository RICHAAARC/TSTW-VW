"""
文件用途：验证仓库 intake 检查与当前 formal stage 的目录边界。
File purpose: Validate repository intake inspection and active formal-stage directory boundaries.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

from pathlib import Path

from tools.harness.inspect_repository import (
    EXPECTED_DIRECTORIES,
    REAL_VIDEO_VAE_LATENT_REQUIRED_PATHS,
    inspect_repository,
)


ROOT = Path(__file__).resolve().parents[2]


def test_empty_repository_bootstrap_is_detected(tmp_path: Path) -> None:
    """Validate that a directory without governed roots is bootstrap-empty.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    report = inspect_repository(tmp_path)
    assert report["repository_mode"] == "empty_repository_bootstrap"
    assert report["directory_boundary_contract"]["exists"] is False
    assert report["directory_boundary_contract"]["source_of_truth"] == "docs/file_organization.md"
    assert report["directory_boundary_source_of_truth_confirmed"] is False
    assert all(
        report["directory_status"][directory_name]["exists"] is False
        for directory_name in EXPECTED_DIRECTORIES
    )


def test_governed_repository_reports_active_stage_status() -> None:
    """Validate that the current repository exposes active-stage and directory status.

    Args:
        None.

    Returns:
        None.
    """
    report = inspect_repository(ROOT)
    assert report["repository_mode"] == "governed_repository"
    assert report["project_stage"] == "synthetic_tubelet_sync_probe"
    assert "outputs" not in EXPECTED_DIRECTORIES
    assert report["directory_boundary_contract"]["exists"] is True
    assert report["directory_boundary_contract"]["source_of_truth"] == "docs/file_organization.md"
    assert report["directory_boundary_source_of_truth_confirmed"] is True
    assert report["directory_status"]["configs"]["exists"] is True
    assert report["directory_status"]["docs"]["exists"] is True
    assert report["directory_status"]["tools"]["exists"] is True
    assert report["directory_status"]["tests"]["exists"] is True
    assert report["directory_status"]["main"]["exists"] is True
    assert report["directory_status"]["paper_workflow"]["exists"] is True
    assert report["directory_status"]["scripts"]["exists"] is True
    assert report["directory_status"]["experiments"]["exists"] is True
    assert report["directory_status"]["audit_reports"]["exists"] is True
    assert report["directory_status"][".codex"]["exists"] is True
    assert report["directory_status"]["examples"]["exists"] is False
    assert report["directory_status"]["release"]["exists"] is False
    assert "outputs/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    next_stage_readiness = report["next_stage_readiness"]
    assert next_stage_readiness["target_construction_phase"] == "real_video_vae_latent_probe"
    assert next_stage_readiness["all_required_paths_present"] is True
    assert next_stage_readiness["present_required_path_count"] == len(
        REAL_VIDEO_VAE_LATENT_REQUIRED_PATHS
    )
    assert next_stage_readiness["required_path_count"] == len(REAL_VIDEO_VAE_LATENT_REQUIRED_PATHS)
    assert next_stage_readiness["required_paths"]["real_video_vae_latent_processed_dataset_notebook"]["exists"] is True
    assert next_stage_readiness["required_paths"]["real_video_vae_latent_probe_notebook"]["exists"] is True
    assert next_stage_readiness["required_paths"]["real_video_vae_latent_notebook_utils_root"]["exists"] is True
    assert (
        next_stage_readiness["required_paths"]["real_video_vae_latent_runtime_profile_root"]["exists"] is True
    )
    assert (
        next_stage_readiness["required_paths"][
            "real_video_vae_latent_runtime_profile_workflow_helper"
        ]["exists"]
        is True
    )
    assert (
        next_stage_readiness["required_paths"][
            "real_video_vae_latent_run_timing_workflow_helper"
        ]["exists"]
        is True
    )
    assert (
        next_stage_readiness["required_paths"][
            "real_video_vae_latent_runtime_parameter_recommendation_module"
        ]["exists"]
        is True
    )
    assert (
        next_stage_readiness["required_paths"][
            "real_video_vae_latent_run_failure_summary_module"
        ]["exists"]
        is True
    )
    assert (
        next_stage_readiness["required_paths"]["real_video_vae_latent_runner_module"]["exists"] is True
    )
    assert (
        next_stage_readiness["required_paths"]["real_video_vae_latent_named_tar_packager_module"]["exists"] is True
    )

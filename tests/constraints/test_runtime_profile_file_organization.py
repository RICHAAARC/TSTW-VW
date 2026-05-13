"""
文件用途：验证 runtime profiling 脚本与 notebook helper 的文件组织合同。
File purpose: Validate the file-organization contract for runtime profiling scripts and notebook helpers.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]
RUN_NOTEBOOK_PATH = ROOT / "paper_workflow" / "run_real_video_vae_latent_probe.ipynb"
PROFILE_RUNTIME_ROOT = ROOT / "scripts" / "profile_runtime"
FILE_ORGANIZATION_PATH = ROOT / "docs" / "file_organization.md"
AUDIT_FILE_ORGANIZATION_PATH = (
    ROOT / "tools" / "harness" / "audits" / "audit_file_organization_contract.py"
)
REPOSITORY_INTAKE_PATH = ROOT / "tools" / "harness" / "inspect_repository.py"
RUNTIME_PROFILE_WORKFLOW_PATH = (
    ROOT / "paper_workflow" / "notebook_utils" / "runtime_profile_workflow.py"
)
RUN_TIMING_WORKFLOW_PATH = (
    ROOT / "paper_workflow" / "notebook_utils" / "run_timing_workflow.py"
)
TRACKED_PROFILE_PATHS = [
    PROFILE_RUNTIME_ROOT / "__init__.py",
    PROFILE_RUNTIME_ROOT / "capture_colab_environment.py",
    PROFILE_RUNTIME_ROOT / "profile_run_timing.py",
    PROFILE_RUNTIME_ROOT / "summarize_run_timing.py",
    PROFILE_RUNTIME_ROOT / "profile_gpu_runtime.py",
    PROFILE_RUNTIME_ROOT / "summarize_gpu_profile.py",
    PROFILE_RUNTIME_ROOT / "estimate_real_video_vae_latent_run_scale.py",
    PROFILE_RUNTIME_ROOT / "watch_real_video_vae_latent_progress.py",
    PROFILE_RUNTIME_ROOT / "profile_drive_io.py",
    PROFILE_RUNTIME_ROOT / "recommend_runtime_parameters.py",
    ROOT / "scripts" / "check_results" / "summarize_run_failures.py",
    RUNTIME_PROFILE_WORKFLOW_PATH,
    RUN_TIMING_WORKFLOW_PATH,
]
WEAK_NAMING_TOKENS = ("stage2", "stage_2", "v1", "p2", "latest", "final")


def test_runtime_profile_paths_exist() -> None:
    """Validate governed runtime profiling paths exist in approved locations.

    Args:
        None.

    Returns:
        None.
    """
    assert PROFILE_RUNTIME_ROOT.exists()
    assert RUNTIME_PROFILE_WORKFLOW_PATH.exists()
    assert RUN_TIMING_WORKFLOW_PATH.exists()
    assert all(path.exists() for path in TRACKED_PROFILE_PATHS)


def test_main_has_no_runtime_profile_modules() -> None:
    """Validate main/ does not host notebook-only profiling modules.

    Args:
        None.

    Returns:
        None.
    """
    main_root = ROOT / "main"
    assert not (main_root / "profile_runtime").exists()
    forbidden_matches = []
    for path in main_root.rglob("*"):
        normalized_name = path.name.lower()
        if "profile_runtime" in normalized_name:
            forbidden_matches.append(path)
        if "gpu_profile" in normalized_name:
            forbidden_matches.append(path)
        if "colab" in normalized_name and "profile" in normalized_name:
            forbidden_matches.append(path)
    assert forbidden_matches == []


def test_runtime_profile_paths_avoid_weak_naming() -> None:
    """Validate newly added profiling paths avoid weak stage-like naming.

    Args:
        None.

    Returns:
        None.
    """
    for path in TRACKED_PROFILE_PATHS:
        normalized_name = path.stem.lower()
        assert all(token not in normalized_name for token in WEAK_NAMING_TOKENS)


def test_notebook_imports_notebook_utils_profilers_only() -> None:
    """Validate the notebook imports profiler helpers only from notebook_utils.

    Args:
        None.

    Returns:
        None.
    """
    notebook_text = RUN_NOTEBOOK_PATH.read_text(encoding="utf-8")
    assert "from paper_workflow.notebook_utils import runtime_profile_workflow" in notebook_text
    assert "from paper_workflow.notebook_utils import run_timing_workflow" in notebook_text
    assert "from main" not in notebook_text
    assert "nvidia-smi" not in notebook_text


def test_runtime_profile_paths_registered_in_docs_and_governance_contracts() -> None:
    """Validate runtime profiling additions are registered in docs and governance contracts.

    Args:
        None.

    Returns:
        None.
    """
    file_organization_text = FILE_ORGANIZATION_PATH.read_text(encoding="utf-8")
    audit_text = AUDIT_FILE_ORGANIZATION_PATH.read_text(encoding="utf-8")
    intake_text = REPOSITORY_INTAKE_PATH.read_text(encoding="utf-8")

    assert "profile_runtime/" in file_organization_text
    assert "summarize_run_failures.py" in file_organization_text
    assert "scripts/profile_runtime" in audit_text
    assert "paper_workflow/notebook_utils/runtime_profile_workflow.py" in audit_text
    assert "paper_workflow/notebook_utils/run_timing_workflow.py" in audit_text
    assert "scripts/profile_runtime/recommend_runtime_parameters.py" in intake_text
    assert "scripts/check_results/summarize_run_failures.py" in intake_text

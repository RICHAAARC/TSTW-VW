"""
文件用途：验证真实视频 workflow notebook 入口遵循受治理合同。
File purpose: Validate that the governed real-video workflow notebooks follow the governed contract.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD_NOTEBOOK_PATH = ROOT / "paper_workflow" / "build_processed_real_video_dataset.ipynb"
RUN_NOTEBOOK_PATH = ROOT / "paper_workflow" / "run_real_video_vae_latent_probe.ipynb"
BUILD_WORKFLOW_PATH = (
    ROOT
    / "paper_workflow"
    / "notebook_utils"
    / "processed_real_video_dataset_workflow.py"
)
RUN_WORKFLOW_PATH = (
    ROOT
    / "paper_workflow"
    / "notebook_utils"
    / "real_video_vae_latent_probe_workflow.py"
)
BUILD_REQUIRED_CELL_TITLES = [
    "00_runtime_identity_and_user_config",
    "01_mount_google_drive",
    "02_validate_raw_dataset_registry",
    "03_select_raw_dataset_source",
    "04_prepare_local_dataset_workspace",
    "05_extract_raw_dataset_archive",
    "06_build_processed_video_clips",
    "07_write_processed_dataset_manifest",
    "08_validate_processed_dataset",
    "09_register_processed_dataset",
    "10_print_processed_dataset_handoff",
]
RUN_REQUIRED_CELL_TITLES = [
    "00_runtime_identity_and_user_config",
    "01_mount_google_drive",
    "02_read_processed_dataset_registry",
    "03_prepare_local_runtime_workspace",
    "04_clone_or_update_repository",
    "05_install_runtime_dependencies",
    "06_prepare_session_model",
    "07_write_runtime_config",
    "08_check_gpu_and_runtime",
    "09_verify_repository_contract",
    "10_run_smoke_tests",
    "11_run_real_video_vae_latent_formal",
    "12_rebuild_tables_and_reports",
    "13_check_real_video_vae_latent_outputs",
    "14_package_family_results",
    "15_print_final_family_summary",
]


def _load_notebook(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cell_text(cell: dict[str, object]) -> str:
    source = cell.get("source", [])
    if isinstance(source, list):
        return "".join(str(line) for line in source)
    return str(source)


def _assert_title_order(cells: list[object], required_titles: list[str]) -> None:
    title_positions: list[int] = []
    for required_title in required_titles:
        matching_index = next(
            index
            for index, cell in enumerate(cells)
            if isinstance(cell, dict) and required_title in _cell_text(cell)
        )
        title_positions.append(matching_index)
    assert title_positions == sorted(title_positions)


def test_processed_dataset_notebook_exists_and_uses_governed_entrypoints() -> None:
    """Validate that notebook A exists and only delegates to the dataset builder path.

    Args:
        None.

    Returns:
        None.
    """
    assert BUILD_NOTEBOOK_PATH.exists()
    notebook = _load_notebook(BUILD_NOTEBOOK_PATH)
    cells = notebook.get("cells", [])
    assert isinstance(cells, list) and cells
    notebook_text = "\n".join(_cell_text(cell) for cell in cells if isinstance(cell, dict))
    assert BUILD_WORKFLOW_PATH.exists()
    workflow_text = BUILD_WORKFLOW_PATH.read_text(encoding="utf-8")

    _assert_title_order(cells, BUILD_REQUIRED_CELL_TITLES)

    assert "# Build Processed Real Video Dataset" in notebook_text
    assert (
        "00 Runtime Identity And User Config "
        "(`00_runtime_identity_and_user_config`)"
    ) in notebook_text
    assert "### 00_runtime_identity_and_user_config" not in notebook_text
    assert (
        "paper_workflow.notebook_utils import "
        "processed_real_video_dataset_workflow"
    ) in notebook_text
    assert "dataset_workflow.build_processed_dataset_handoff" in notebook_text
    assert "scripts.prepare_datasets.build_processed_real_video_dataset" not in notebook_text
    assert "scripts.prepare_datasets.build_processed_real_video_dataset" in workflow_text
    assert "raw_dataset_download_manifest.json" in notebook_text
    assert "PROCESSED_DATASET_KEY" in notebook_text
    assert "processed_dataset_checks.json" in notebook_text
    assert "/content/drive/MyDrive" in notebook_text
    assert "experiments.real_video_vae_latent_probe.runner" not in notebook_text
    assert "scripts.check_results.check_real_video_vae_latent_outputs" not in notebook_text
    assert "scripts.package_results.package_real_video_vae_latent_outputs" not in notebook_text


def test_real_video_run_notebook_exists_and_uses_governed_entrypoints() -> None:
    """Validate that notebook B exists and delegates to the governed run modules.

    Args:
        None.

    Returns:
        None.
    """
    assert RUN_NOTEBOOK_PATH.exists()
    notebook = _load_notebook(RUN_NOTEBOOK_PATH)
    cells = notebook.get("cells", [])
    assert isinstance(cells, list) and cells
    notebook_text = "\n".join(_cell_text(cell) for cell in cells if isinstance(cell, dict))
    assert RUN_WORKFLOW_PATH.exists()
    workflow_text = RUN_WORKFLOW_PATH.read_text(encoding="utf-8")

    _assert_title_order(cells, RUN_REQUIRED_CELL_TITLES)

    assert "# Run Real Video VAE Latent Probe" in notebook_text
    assert (
        "00 Runtime Identity And User Config "
        "(`00_runtime_identity_and_user_config`)"
    ) in notebook_text
    assert "### 00_runtime_identity_and_user_config" not in notebook_text
    assert (
        "paper_workflow.notebook_utils import "
        "real_video_vae_latent_probe_workflow"
    ) in notebook_text
    assert "probe_workflow.prepare_probe_runtime_workspace" in notebook_text
    assert "probe_workflow.prepare_probe_session_model" in notebook_text
    assert "probe_workflow.write_probe_runtime_config" in notebook_text
    assert "probe_workflow.run_probe_runner" in notebook_text
    assert "probe_workflow.rebuild_probe_tables_and_reports" in notebook_text
    assert "probe_workflow.check_probe_outputs" in notebook_text
    assert "probe_workflow.package_probe_family_results" in notebook_text
    assert "repo_env['PYTHONPATH']" in notebook_text
    assert "env=repo_env" in notebook_text
    assert "cwd=REPO_ROOT" in notebook_text
    assert "huggingface_hub" in notebook_text
    assert "diffusers" in notebook_text
    assert "experiments.real_video_vae_latent_probe.runner" not in notebook_text
    assert "scripts.prepare_models.prepare_session_autoencoder_kl" not in notebook_text
    assert "scripts.check_results.check_real_video_vae_latent_outputs" not in notebook_text
    assert "scripts.package_results.package_real_video_vae_latent_outputs" not in notebook_text
    assert "scripts.package_results.package_real_video_vae_latent_tar_zst" not in notebook_text
    assert "from paper_workflow.colab_utils.runtime_check import run_runtime_preflight_check" not in notebook_text
    assert "experiments.real_video_vae_latent_probe.runner" in workflow_text
    assert "scripts.prepare_models.prepare_session_autoencoder_kl" in workflow_text
    assert "scripts.check_results.check_real_video_vae_latent_outputs" in workflow_text
    assert "scripts.package_results.package_real_video_vae_latent_outputs" in workflow_text
    assert "scripts.package_results.package_real_video_vae_latent_tar_zst" in workflow_text
    assert "from paper_workflow.colab_utils.runtime_check import run_runtime_preflight_check" in workflow_text
    assert "session_only_no_drive_model_storage" in workflow_text
    assert "REQUIRE_FORMAL_PASS = True" in notebook_text
    assert "require_formal_pass_criteria=REQUIRE_FORMAL_PASS" in notebook_text
    assert "drive_archive_path = package_payload['drive_archive_path']" in notebook_text
    assert "compat_pack_root = package_payload['compat_pack_root']" in notebook_text
    assert "formal_validation_summary" in notebook_text
    assert "result_registry.jsonl" in notebook_text
    assert "family_registry.jsonl" in notebook_text
    assert "/content/TSTW_runtime" in notebook_text
    assert "/content/drive/MyDrive" in notebook_text
    assert "raw_dataset_download_manifest.json" not in notebook_text


def test_real_video_vae_latent_notebook_cells_use_python_metadata() -> None:
    """Validate that every code cell declares Python language metadata.

    Args:
        None.

    Returns:
        None.
    """
    for notebook_path in (BUILD_NOTEBOOK_PATH, RUN_NOTEBOOK_PATH):
        notebook = _load_notebook(notebook_path)
        cells = notebook.get("cells", [])
        code_cells = [cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"]
        assert code_cells
        notebook_language = (
            notebook.get("metadata", {})
            .get("language_info", {})
            .get("name")
        )
        assert notebook_language == "python"
        assert all(
            cell.get("metadata", {}).get("language") in {None, "python"}
            for cell in code_cells
        )

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
BUILD_REQUIRED_STEP_KEYS = [
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
RUN_REQUIRED_STEP_KEYS = [
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


def _cell_metadata(cell: dict[str, object]) -> dict[str, object]:
    metadata = cell.get("metadata", {})
    if isinstance(metadata, dict):
        return metadata
    return {}


def _cell_step_key(cell: dict[str, object]) -> str | None:
    step_key = _cell_metadata(cell).get("step_key")
    if isinstance(step_key, str):
        return step_key
    return None


def _assert_step_key_order(cells: list[object], required_step_keys: list[str]) -> None:
    observed_step_keys = [
        _cell_step_key(cell)
        for cell in cells
        if isinstance(cell, dict) and _cell_step_key(cell) is not None
    ]
    assert observed_step_keys == required_step_keys
    assert all(
        isinstance(cell, dict) and cell.get("cell_type") == "markdown"
        for cell in cells
        if isinstance(cell, dict) and _cell_step_key(cell) is not None
    )


def _all_indices(text: str, substring: str) -> list[int]:
    indices: list[int] = []
    start = 0
    while True:
        index = text.find(substring, start)
        if index < 0:
            return indices
        indices.append(index)
        start = index + len(substring)


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

    _assert_step_key_order(cells, BUILD_REQUIRED_STEP_KEYS)

    assert "# Build Processed Real Video Dataset" in notebook_text
    assert "## 00 Runtime Identity And User Config" in notebook_text
    assert "(`00_runtime_identity_and_user_config`)" not in notebook_text
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

    _assert_step_key_order(cells, RUN_REQUIRED_STEP_KEYS)

    assert "# Run Real Video VAE Latent Probe" in notebook_text
    assert "## 00 Runtime Identity And User Config" in notebook_text
    assert "(`00_runtime_identity_and_user_config`)" not in notebook_text
    assert "### 00_runtime_identity_and_user_config" not in notebook_text
    assert (
        "paper_workflow.notebook_utils import "
        "real_video_vae_latent_probe_workflow"
    ) in notebook_text
    assert "from paper_workflow.notebook_utils import runtime_profile_workflow" in notebook_text
    assert "from paper_workflow.notebook_utils import run_timing_workflow" in notebook_text
    assert "probe_workflow.prepare_probe_runtime_workspace" in notebook_text
    assert "probe_workflow.prepare_probe_session_model" in notebook_text
    assert "probe_workflow.materialize_family_id(" in notebook_text
    assert "probe_workflow.write_probe_runtime_config" in notebook_text
    assert "probe_workflow.run_probe_runner" in notebook_text
    assert "probe_workflow.rebuild_probe_tables_and_reports" in notebook_text
    assert "probe_workflow.check_probe_outputs" in notebook_text
    assert "probe_workflow.run_probe_stage2_mechanism_audit" in notebook_text
    assert "probe_workflow.package_probe_family_results" in notebook_text
    assert "FAMILY_ID_TEMPLATE" in notebook_text
    assert "PROCESSED_DATASET_MANIFEST" in notebook_text
    assert "dataset_manifest_path=PROCESSED_DATASET_MANIFEST" in notebook_text
    assert "dataset_manifest=PROCESSED_DATASET_MANIFEST" in notebook_text
    assert "attack_matrix=ATTACK_MATRIX_PATH" in notebook_text
    assert "ablation_config=ABLATION_CONFIG_PATH" in notebook_text
    assert "repo_env['PYTHONPATH']" in notebook_text
    assert "env=repo_env" in notebook_text
    assert "cwd=REPO_ROOT" in notebook_text
    assert "huggingface_hub" in notebook_text
    assert "diffusers" in notebook_text
    assert "PROFILE_RUNTIME = RUN_MODE == 'formal'" in notebook_text
    assert "PROFILE_GPU_RUNTIME = PROFILE_RUNTIME" in notebook_text
    assert "GPU_PROFILE_INTERVAL_SECONDS = 2" in notebook_text
    assert "BATCH_SIZE_FRAMES = 8" in notebook_text
    assert "TSTW_BATCH_SIZE_FRAMES" in notebook_text
    assert "TSTW_REQUIRE_LPIPS_EVIDENCE" in notebook_text
    assert "TSTW_SAMPLES_PER_ROLE_OVERRIDE" in notebook_text
    assert "run_timer = run_timing_workflow.start_run_timing(" in notebook_text
    assert "runtime_profile_workflow.capture_colab_environment(" in notebook_text
    assert "runtime_profile_workflow.profile_drive_io(" in notebook_text
    assert "runtime_profile_workflow.estimate_real_video_vae_latent_run_scale(" in notebook_text
    assert "runtime_profile_workflow.start_gpu_runtime_profile(" in notebook_text
    assert "runtime_profile_workflow.stop_gpu_runtime_profile(" in notebook_text
    assert "runtime_profile_workflow.summarize_gpu_runtime_profile(" in notebook_text
    assert "run_timing_workflow.summarize_run_timing(" in notebook_text
    assert "runtime_profile_workflow.summarize_run_failures(" in notebook_text
    assert "runtime_profile_workflow.recommend_runtime_parameters(" in notebook_text
    assert "with run_timer.event('runtime_preflight'" in notebook_text
    assert "with run_timer.event('model_preparation'" in notebook_text
    assert "with run_timer.event('real_video_vae_latent_runner'" in notebook_text
    assert "with run_timer.event('table_and_report_rebuild'" in notebook_text
    assert "with run_timer.event('formal_checker'" in notebook_text
    assert "with run_timer.event('stage2_mechanism_audit'" in notebook_text
    assert "with run_timer.event('result_packaging'" in notebook_text
    assert "experiments.real_video_vae_latent_probe.runner" not in notebook_text
    assert "scripts.prepare_models.prepare_session_autoencoder_kl" not in notebook_text
    assert "scripts.check_results.check_real_video_vae_latent_outputs" not in notebook_text
    assert "scripts.package_results.package_real_video_vae_latent_outputs" not in notebook_text
    assert "scripts.package_results.package_real_video_vae_latent_tar_zst" not in notebook_text
    assert "from paper_workflow.colab_utils.runtime_check import run_runtime_preflight_check" not in notebook_text
    assert "nvidia-smi" not in notebook_text
    assert "experiments.real_video_vae_latent_probe.runner" in workflow_text
    assert "scripts.prepare_models.prepare_session_autoencoder_kl" in workflow_text
    assert "scripts.check_results.check_real_video_vae_latent_outputs" in workflow_text
    assert "scripts.package_results.package_real_video_vae_latent_outputs" in workflow_text
    assert "scripts.package_results.package_real_video_vae_latent_tar_zst" in workflow_text
    assert "from paper_workflow.colab_utils.runtime_check import run_runtime_preflight_check" in workflow_text
    assert "session_only_no_drive_model_storage" in workflow_text
    assert "dataset_manifest_path" in workflow_text
    assert "REQUIRE_FORMAL_PASS = True" in notebook_text
    assert "require_formal_pass_criteria=REQUIRE_FORMAL_PASS" in notebook_text
    assert "mechanism_summary=stage2_mechanism_summary" in notebook_text
    assert "samples_per_role=RUNNER_SAMPLES_PER_ROLE_OVERRIDE" in notebook_text
    assert "batch_size_frames=BATCH_SIZE_FRAMES" in notebook_text
    assert "lpips_evidence_summary" in notebook_text
    assert "drive_archive_path = package_payload['drive_archive_path']" in notebook_text
    assert "compat_pack_root = package_payload['compat_pack_root']" in notebook_text
    summarize_run_timing_call = "run_timing_summary = run_timing_workflow.summarize_run_timing("
    summarize_run_timing_indices = _all_indices(notebook_text, summarize_run_timing_call)
    formal_checker_index = notebook_text.index(
        "formal_validation_summary = probe_workflow.check_probe_outputs("
    )
    mechanism_audit_index = notebook_text.index(
        "stage2_mechanism_summary = probe_workflow.run_probe_stage2_mechanism_audit("
    )
    package_call_index = notebook_text.index("probe_workflow.package_probe_family_results(")
    assert len(summarize_run_timing_indices) == 3
    assert formal_checker_index < mechanism_audit_index < package_call_index
    assert formal_checker_index < summarize_run_timing_indices[1] < package_call_index
    assert package_call_index < summarize_run_timing_indices[2]
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

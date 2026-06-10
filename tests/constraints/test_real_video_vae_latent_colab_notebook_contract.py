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
STAGE2_CALIBRATION_GRID_PATH = (
    ROOT / "configs" / "ablation" / "stage2_vae_mechanism_calibration_grid.json"
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




def _legacy_dataset_key() -> str:
    return "__".join(
        [
            "real_video_vae_latent_probe",
            "davis2017_trainval480p",
            "256x256",
            "32f",
            "8fps",
            "freeze001",
        ]
    )


def _legacy_family_template() -> str:
    return "__".join(
        [
            "real_video_vae_latent_probe",
            "formal",
            "davis2017_trainval480p",
            "utc_time",
            "short_commit",
        ]
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
    assert (
        "real_video_vae_latent_probe_davis2017_trainval480p_256x256_32f_8fps_freeze001"
        in notebook_text
    )
    assert _legacy_dataset_key() not in notebook_text
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
    assert "probe_workflow.run_probe_stage2_mechanism_calibration" in notebook_text
    assert "probe_workflow.write_probe_tubelet_anchor_forensics" in notebook_text
    assert "probe_workflow.package_probe_non_formal_audit_bundle" in notebook_text
    assert "probe_workflow.package_probe_family_results" in notebook_text
    assert "FAMILY_ID_TEMPLATE" in notebook_text
    assert (
        "real_video_vae_latent_probe_formal_davis2017_trainval480p_utc_time_short_commit"
        in notebook_text
    )
    assert _legacy_family_template() not in notebook_text
    assert "DRIVE_FAMILY_ROOT = DRIVE_ROOT / 'TSTW' / 'results' / WORKFLOW_KEY / RUN_ID" in notebook_text
    assert "LOCAL_FAMILY_ROOT = LOCAL_RUNTIME_ROOT / 'families' / WORKFLOW_KEY / RUN_ID" in notebook_text
    assert "FAMILY_ROOT = LOCAL_FAMILY_ROOT" in notebook_text
    assert "FAMILY_ROOT = DRIVE_ROOT / 'TSTW' / 'results' / 'real_video_vae_latent_probe' / FAMILY_ID" not in notebook_text
    assert "FAMILY_ROOT = DRIVE_ROOT / 'TSTW' / 'results' / 'families' / FAMILY_ID" not in notebook_text
    assert "PROCESSED_DATASET_MANIFEST" in notebook_text
    assert (
        "real_video_vae_latent_probe_davis2017_trainval480p_256x256_32f_8fps_freeze001"
        in notebook_text
    )
    assert _legacy_dataset_key() not in notebook_text
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
    assert "NOTEBOOK_MANUAL_CONFIG" in notebook_text
    assert "NOTEBOOK_MANUAL_ENV_MAP" in notebook_text
    assert "仓库 bootstrap 相关变量在该配置单元内解析为唯一来源" in notebook_text
    assert "REPO_URL = os.environ.get('TSTW_REPO_URL', 'https://github.com/RICHAAARC/TSTW-VW.git')" not in notebook_text
    assert "REPO_BRANCH = os.environ.get('TSTW_REPO_BRANCH', 'main')" not in notebook_text
    assert "REPO_ROOT = Path(os.environ.get('TSTW_REPO_ROOT', '/content/TSTW-VW'))" not in notebook_text
    assert "_resolve_required_environment_text('TSTW_REPO_URL')" in notebook_text
    assert "_resolve_required_environment_text('TSTW_REPO_BRANCH')" in notebook_text
    assert "_resolve_required_environment_text('TSTW_REPO_ROOT')" in notebook_text
    assert "repository bootstrap failed during git clone." in notebook_text
    assert "git_clone_stdout=" in notebook_text
    assert "git_clone_stderr=" in notebook_text
    assert "'fetch', '--depth', '1', 'origin', repo_branch" in notebook_text
    assert "'pull', '--ff-only', 'origin', repo_branch" in notebook_text
    assert "TSTW_WORKFLOW_KEY" in notebook_text
    assert "TSTW_STEP_KEY" in notebook_text
    assert "TSTW_FAMILY_ID_TEMPLATE" in notebook_text
    assert "TSTW_PROCESSED_DATASET_KEY" in notebook_text
    assert "TSTW_DRIVE_ROOT" in notebook_text
    assert "TSTW_LOCAL_RUNTIME_ROOT" in notebook_text
    assert "TSTW_MODEL_ID" in notebook_text
    assert "TSTW_BATCH_SIZE_FRAMES" in notebook_text
    assert "cross_event_vae_batching_enabled" in notebook_text
    assert "cross_event_vae_decode_batch_size" in notebook_text
    assert "cross_event_vae_encode_batch_size" in notebook_text
    assert "TSTW_CROSS_EVENT_VAE_BATCHING_ENABLED" in notebook_text
    assert "TSTW_CROSS_EVENT_VAE_DECODE_BATCH_SIZE" in notebook_text
    assert "TSTW_CROSS_EVENT_VAE_ENCODE_BATCH_SIZE" in notebook_text
    assert "'cross_event_vae_batching_enabled': False" in notebook_text
    assert "cross_event_vae_batching_enabled=CROSS_EVENT_VAE_BATCHING_ENABLED" in notebook_text
    assert "cross_event_vae_batching_summary.json" in notebook_text
    assert "TSTW_SHARD_COUNT" in notebook_text
    assert "TSTW_SHARD_INDEX" in notebook_text
    assert "TSTW_WORKER_COUNT" in notebook_text
    assert "TSTW_REQUIRE_LPIPS_EVIDENCE" in notebook_text
    assert "TSTW_SAMPLES_PER_ROLE_OVERRIDE" in notebook_text
    assert "TSTW_RUN_MAIN_FORMAL" in notebook_text
    assert "TSTW_PACKAGE_NON_FORMAL_AUDIT_BUNDLE" in notebook_text
    assert "TSTW_RUN_TUBELET_ANCHOR_FORENSICS" in notebook_text
    assert "'effective_manual_env'" in notebook_text
    assert "TSTW_STAGE2_MECHANISM_CALIBRATION_GRID_PATH" in notebook_text
    assert "TSTW_RESET_STAGE2_MECHANISM_CALIBRATION_RUN_ROOT" in notebook_text
    assert "probe_workflow.reset_probe_runtime_run_root(" in notebook_text
    assert "reset_run_root=False" in notebook_text
    assert "'samples_per_role_override': 20" in notebook_text
    assert "'run_main_formal': True" in notebook_text
    assert "'run_stage2_mechanism_calibration': False" in notebook_text
    assert "'run_tubelet_anchor_forensics': False" in notebook_text
    assert "'reset_stage2_mechanism_calibration_run_root': False" in notebook_text
    assert "'run_stage2_local_clip_sync_forensics': False" in notebook_text
    assert "'package_non_formal_audit_bundle': False" in notebook_text
    assert "'require_stage2_mechanism_pass': True" in notebook_text
    assert "selected_tubelet_anchor_forensics.csv" in notebook_text
    assert "selected_tubelet_anchor_forensics_summary.json" in notebook_text
    assert "stage2_controlled_search_stage_summary" in notebook_text
    assert "stage2_grid_config_preview" in notebook_text
    assert "stage2_search_stage_preview" in notebook_text
    assert "stage2_vae_mechanism_calibration_grid__" not in notebook_text
    assert "TL02_CONTROLLED_SYNC_WIDE_GRID" not in notebook_text
    assert "TUBELET_RESCUE_EXPANDED_SYNC_GRID" not in notebook_text
    assert "TUBELET_UNSATURATED_ANCHOR_PROBE_SYNC_WIDE_GRID" not in notebook_text
    assert "STAGE2_CALIBRATION_TARGET" not in notebook_text
    assert "stage2_calibration_target" not in notebook_text
    assert "run_timer = run_timing_workflow.start_run_timing(" in notebook_text
    assert "runtime_profile_workflow.capture_colab_environment(" in notebook_text
    assert "runtime_profile_workflow.profile_drive_io(" in notebook_text
    assert "runtime_profile_workflow.estimate_real_video_vae_latent_run_scale(" in notebook_text
    assert "runtime_profile_workflow.start_gpu_runtime_profile(" in notebook_text
    assert "runtime_profile_workflow.stop_gpu_runtime_profile(" in notebook_text
    assert "runtime_profile_workflow.summarize_gpu_runtime_profile(" in notebook_text
    assert "runtime_profile_workflow.write_gpu_runtime_audit_record(" in notebook_text
    assert "run_timing_workflow.summarize_run_timing(" in notebook_text
    assert "runtime_profile_workflow.summarize_run_failures(" in notebook_text
    assert "runtime_profile_workflow.recommend_runtime_parameters(" in notebook_text
    assert "with run_timer.event('runtime_preflight'" in notebook_text
    assert "with run_timer.event('model_preparation'" in notebook_text
    assert "with run_timer.event('real_video_vae_latent_runner'" in notebook_text
    assert "with run_timer.event('table_and_report_rebuild'" in notebook_text
    assert "with run_timer.event('formal_checker'" in notebook_text
    assert "stage2_calibration_gpu_profile_process = runtime_profile_workflow.start_gpu_runtime_profile(" in notebook_text
    assert "run_root=STAGE2_MECHANISM_CALIBRATION_RUN_ROOT" in notebook_text
    assert "with run_timer.event('stage2_mechanism_audit'" in notebook_text
    assert "with run_timer.event('stage2_mechanism_calibration'" in notebook_text
    assert "with run_timer.event('tubelet_anchor_forensics'" in notebook_text
    assert "with run_timer.event('audit_bundle_packaging'" in notebook_text
    assert "with run_timer.event('result_packaging'" in notebook_text
    assert "run_main_formal_disabled" in notebook_text
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
    assert "shard_count=SHARD_COUNT" in notebook_text
    assert "shard_index=SHARD_INDEX" in notebook_text
    assert "worker_count=WORKER_COUNT" in notebook_text
    assert "lpips_evidence_summary" in notebook_text
    assert "def _is_non_bool_number(value):" in notebook_text
    assert "lpips_score = quality_metrics.get('watermarked_video_lpips')" in notebook_text
    assert "if _is_non_bool_number(lpips_score):" in notebook_text
    assert "quality_metrics.get('watermarked_video_lpips') is not None" not in notebook_text
    assert "tubelet_anchor_forensics_summary" in notebook_text
    assert "non_formal_audit_bundle_summary" in notebook_text
    assert "local_archive_path = package_payload['drive_archive_path']" in notebook_text
    assert "probe_workflow.materialize_probe_family_results_to_drive(" in notebook_text
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


def test_stage2_calibration_grid_owns_search_space_after_notebook_deparameterization() -> None:
    """验证阶段 2 搜索空间由配置文件拥有, notebook 不内联候选窗口。

    Args:
        None.

    Returns:
        None.
    """
    grid_config = json.loads(STAGE2_CALIBRATION_GRID_PATH.read_text(encoding="utf-8"))
    search_stage_names = [
        str(stage_payload["stage_name"])
        for stage_payload in grid_config["search_stages"]
    ]

    assert grid_config["campaign_mode"] == "staged_search"
    assert "sync_refine_scan" not in search_stage_names
    assert grid_config["anchor_selection_policy"] == "fixed_unsaturated_anchor"
    assert "sync_rescuable_anchor_selection" not in grid_config
    assert grid_config["fixed_tubelet_only_anchor"] == {
        "tubelet_length": 4,
        "spatial_patch_size": [4, 4],
        "embedding_projection_support_weight": 0.09,
        "embedding_margin": 1.0,
    }
    assert grid_config["strict_anchor_required_before_sync"] is True
    threshold_overrides = grid_config["threshold_protocol_overrides"]
    assert threshold_overrides[
        "tubelet_length_threshold_guard_band_multiplier_by_profile"
    ]["formal"]["default"] == 0.75
    assert threshold_overrides[
        "tubelet_length_threshold_guard_band_multiplier_by_profile"
    ]["formal"]["length_ge_16"] == 1.0
    assert threshold_overrides[
        "sync_threshold_guard_band_multiplier_by_profile"
    ]["formal"] == 0.75
    assert search_stage_names == [
        "formal_anchor_diag",
        "formal_sync_diag",
    ]
    assert grid_config["calibration_purpose"] == (
        "stage2_fixed_aligned_payload_candidate_confirmation"
    )
    assert grid_config["grid"]["tubelet_length"] == [4]
    assert grid_config["grid"]["spatial_patch_size"] == [[4, 4]]
    assert grid_config["grid"]["embedding_projection_support_weight"] == [0.09]
    assert grid_config["grid"]["embedding_margin"] == [1.0]
    assert grid_config["grid"]["lambda_sync"] == [0.01]
    assert grid_config["grid"]["sync_search_radius"] == [8]
    assert grid_config["grid"]["min_sync_positive_margin"] == [0.0]
    assert grid_config["grid"]["min_sync_alignment_coverage_ratio"] == [0.125]
    assert grid_config["grid"]["min_sync_alignment_matched_count"] == [64]
    assert grid_config["grid"]["sync_confidence_gate_rule"] == [
        "aligned_payload_safety_gate"
    ]
    assert grid_config["grid"]["min_payload_rescue_gain"] == [0.01]
    assert grid_config["grid"]["min_aligned_payload_score"] == [0.095]
    assert grid_config["top_candidate_limit"] == 1
    assert grid_config["confirmation_expected_candidate"] == {
        "method_variant": "tubelet_sync_cal_tl04_sp04x04_w009_em1000_sr08_ls010_mg000_cv125_mc64_grapsafe_rg010_as095_frsync_rescue",
        "candidate_selection_status": "eligible",
        "sync_confidence_gate_rule": "aligned_payload_safety_gate",
        "min_payload_rescue_gain": 0.01,
        "min_aligned_payload_score": 0.095,
        "min_temporal_crop_sync_gain": 0.1,
        "min_local_clip_sync_gain": 0.1,
        "max_attacked_negative_fpr": 0.0,
        "negative_rescue_over_threshold_count": 0,
    }
    assert "min_aligned_rescue_gain" not in grid_config["grid"]
    assert "min_aligned_score_gate" not in grid_config["grid"]
    assert "min_sync_candidate_score" not in grid_config["grid"]


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

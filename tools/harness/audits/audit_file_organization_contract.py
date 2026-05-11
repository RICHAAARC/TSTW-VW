"""
文件用途：执行文件组织契约审计。
File purpose: Audit repository structure against the governed file organization contract.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.json_report import build_report, exit_with_report


REQUIRED_PATHS = {
    "docs_file_organization_contract": "docs/file_organization.md",
    "scripts_root": "scripts",
    "experiments_root": "experiments",
    "protocol_skeleton_root": "experiments/protocol_skeleton",
    "paper_workflow_colab_utils": "paper_workflow/colab_utils",
    "paper_workflow_notebook_utils": "paper_workflow/notebook_utils",
    "processed_dataset_notebook_entrypoint": "paper_workflow/build_processed_real_video_dataset.ipynb",
    "real_video_probe_notebook_entrypoint": "paper_workflow/run_real_video_vae_latent_probe.ipynb",
    "main_cli_root": "main/cli",
    "main_identity_attack": "main/attacks/identity_attack.py",
    "main_video_vae_tensor_runtime": "main/vae/video_vae_tensor_runtime.py",
    "main_method_runtime": "main/methods/temporal_tubelet_watermark/method.py",
    "stage_two_runner": "experiments/real_video_vae_latent_probe/runner.py",
    "stage_two_artifact_builder": "experiments/real_video_vae_latent_probe/artifact_builder.py",
    "stage_two_output_layout": "experiments/real_video_vae_latent_probe/output_layout.py",
    "processed_dataset_builder_script": "scripts/prepare_datasets/build_processed_real_video_dataset.py",
    "session_model_prepare_script": "scripts/prepare_models/prepare_session_autoencoder_kl.py",
    "stage_two_named_output_checker": "scripts/check_results/check_real_video_vae_latent_outputs.py",
    "stage_two_named_packager": "scripts/package_results/package_real_video_vae_latent_outputs.py",
    "stage_two_named_tar_packager": "scripts/package_results/package_real_video_vae_latent_tar_zst.py",
    "protocol_skeleton_identity_attack_config": "experiments/protocol_skeleton/configs/attacks/identity_attack_placeholder.json",
    "protocol_skeleton_ablation_config": "experiments/protocol_skeleton/configs/ablation/ablation_placeholder.json",
    "protocol_skeleton_protocol_config": "experiments/protocol_skeleton/configs/protocol/protocol_skeleton.json",
    "stage_one_synthetic_backend": "experiments/synthetic_tubelet_sync_probe/synthetic_video_latent.py",
    "stage_one_synthetic_contract": "experiments/synthetic_tubelet_sync_probe/synthetic_tubelet_sync_contract.py",
    "stage_one_ablation_runner": "experiments/synthetic_tubelet_sync_probe/ablation_runner.py",
    "stage_two_output_checker": "scripts/check_results/real_video_vae_latent_output_checker.py",
    "stage_two_tar_packager": "scripts/package_results/tar_zst_packager.py",
    "colab_runtime_check": "paper_workflow/colab_utils/runtime_check.py",
}

FORBIDDEN_PATHS = {
    "main_colab_root": "main/colab",
    "minimal_release_root": "minimal_release",
    "release_root": "release",
    "stage_two_runner_in_main": "main/protocol/real_video_vae_latent_runner.py",
    "stage_two_artifact_builder_in_main": "main/analysis/real_video_vae_latent_artifacts.py",
    "stage_two_paths_in_main": "main/protocol/real_video_vae_latent_paths.py",
    "legacy_stage_two_notebook_entrypoint": "paper_workflow/Stage2_Real_Video_VAE_Latent_Probe.ipynb",
    "legacy_stage_two_colab_notebook_entrypoint": "paper_workflow/Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb",
    "legacy_stage_two_drive_packager_wrapper": "paper_workflow/notebook_utils/stage2_real_video_vae_latent_probe_drive_packager.py",
    "legacy_stage_two_notebook_result_checker_wrapper": "paper_workflow/notebook_utils/stage2_real_video_vae_latent_probe_result_checker.py",
    "stage_one_ablation_runner_in_main": "main/protocol/ablation_runner.py",
    "synthetic_backend_in_main": "main/backends/synthetic_video_latent.py",
    "random_backend_in_main": "main/backends/synthetic_latent_backend_random.py",
    "synthetic_contract_in_main": "main/methods/temporal_tubelet_watermark/synthetic_tubelet_sync_contract.py",
    "placeholder_attack_in_main": "main/attacks/identity_attack_placeholder.py",
    "placeholder_vae_backend_in_main": "main/vae/video_vae_backend_placeholder.py",
    "placeholder_method_in_main": "main/methods/temporal_tubelet_watermark/method_placeholder.py",
    "placeholder_attack_in_top_level_configs": "configs/attacks/identity_attack_placeholder.json",
    "placeholder_ablation_in_top_level_configs": "configs/ablation/ablation_placeholder.json",
    "placeholder_method_in_top_level_configs": "configs/method/method_placeholder.json",
    "empty_placeholder_method_in_top_level_configs": "configs/method/empty_watermark_method_placeholder.json",
    "random_method_in_top_level_configs": "configs/method/random_score_detector_random.json",
    "protocol_skeleton_protocol_in_top_level_configs": "configs/protocol/protocol_skeleton.json",
    "protocol_skeleton_ablation_in_top_level_configs": "configs/ablation/protocol_skeleton_methods.json",
    "stage_one_protocol_in_top_level_configs": "configs/protocol/synthetic_tubelet_sync_probe.json",
    "stage_one_attack_matrix_in_top_level_configs": "configs/attacks/temporal_attack_matrix.json",
    "stage_one_ablation_in_top_level_configs": "configs/ablation/synthetic_tubelet_sync_ablation.json",
}


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the file organization contract audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized file organization audit report.
    """
    root_path = Path(root)
    checked_paths = [
        str(root_path / relative_path)
        for relative_path in (*REQUIRED_PATHS.values(), *FORBIDDEN_PATHS.values())
    ]
    violations: list[dict[str, Any]] = []

    for requirement_name, relative_path in REQUIRED_PATHS.items():
        candidate = root_path / relative_path
        if candidate.exists():
            continue
        violations.append(
            {
                "path": str(candidate),
                "reason": "missing_required_file_organization_path",
                "requirement": requirement_name,
            }
        )

    for requirement_name, relative_path in FORBIDDEN_PATHS.items():
        candidate = root_path / relative_path
        if not candidate.exists():
            continue
        violations.append(
            {
                "path": str(candidate),
                "reason": "forbidden_legacy_file_organization_path_present",
                "requirement": requirement_name,
            }
        )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_file_organization_contract",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the file organization contract audit as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    exit_with_report(run_audit(root))


if __name__ == "__main__":
    main(sys.argv)
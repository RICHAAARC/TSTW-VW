"""
文件用途：提供仓库 intake 检查与空仓库分类能力。
File purpose: Provide repository intake inspection and empty bootstrap classification.
Module type: General module
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_DIRECTORIES = [
    "configs",
    "docs",
    "tools",
    "tests",
    "main",
    "paper_workflow",
    "scripts",
    "experiments",
    "audit_reports",
    ".codex",
    "examples",
    "release",
]
DIRECTORY_BOUNDARY_CONTRACT_RELATIVE_PATH = "docs/file_organization.md"
REAL_VIDEO_VAE_LATENT_REQUIRED_PATHS = {
    "real_video_vae_latent_protocol_config": "configs/protocol/real_video_vae_latent_probe.json",
    "real_video_vae_latent_backend_config": "configs/backend/real_video_vae_latent.json",
    "real_video_vae_latent_attack_matrix_config": "configs/attacks/real_video_attack_matrix.json",
    "real_video_vae_latent_ablation_config": "configs/ablation/real_video_vae_latent_ablation.json",
    "real_video_vae_latent_backend_module": "main/backends/real_video_vae_latent.py",
    "real_video_vae_latent_vae_registry_module": "main/vae/vae_registry.py",
    "real_video_vae_latent_runner_module": "experiments/real_video_vae_latent_probe/runner.py",
    "real_video_vae_latent_artifact_builder_module": "experiments/real_video_vae_latent_probe/artifact_builder.py",
    "real_video_vae_latent_result_checker_module": "scripts/check_results/real_video_vae_latent_output_checker.py",
    "real_video_vae_latent_drive_packager_module": "scripts/package_results/drive_packager.py",
    "real_video_vae_latent_colab_notebook": (
        "paper_workflow/Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb"
    ),
}
STAGE_ONE_REQUIRED_PATHS = {
    "protocol_support_config": "experiments/synthetic_tubelet_sync_probe/configs/protocol/synthetic_tubelet_sync_probe.json",
    "temporal_attack_matrix_config": "experiments/synthetic_tubelet_sync_probe/configs/attacks/temporal_attack_matrix.json",
    "ablation_support_config": "experiments/synthetic_tubelet_sync_probe/configs/ablation/synthetic_tubelet_sync_ablation.json",
    "frame_prc_method_config": "configs/method/frame_prc.json",
    "tubelet_only_method_config": "configs/method/tubelet_only.json",
    "tubelet_sync_method_config": "configs/method/tubelet_sync.json",
    "synthetic_video_latent_module": "experiments/synthetic_tubelet_sync_probe/synthetic_video_latent.py",
    "temporal_attack_module": "main/attacks/temporal.py",
    "synthetic_tubelet_sync_contract_module": "experiments/synthetic_tubelet_sync_probe/synthetic_tubelet_sync_contract.py",
}


NEXT_STAGE_TARGET = "real_video_vae_latent_probe"


def _read_project_contract(root_path: Path) -> dict[str, Any]:
    """Read the governed project contract when it exists.

    Args:
        root_path: Repository root path.

    Returns:
        Parsed contract payload or an empty dictionary.
    """
    contract_path = root_path / "configs" / "project" / "project_contract.json"
    if not contract_path.exists():
        return {}
    try:
        return json.loads(contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _build_required_paths(root_path: Path, path_map: dict[str, str]) -> tuple[int, dict[str, dict[str, Any]]]:
    """Build a normalized required-path readiness payload.

    Args:
        root_path: Repository root path.
        path_map: Artifact-name to relative-path map.

    Returns:
        The present-path count and the normalized required-path payload.
    """
    required_paths: dict[str, dict[str, Any]] = {}
    present_count = 0
    for artifact_name, relative_path in path_map.items():
        candidate = root_path / Path(relative_path)
        exists = candidate.exists()
        if exists:
            present_count += 1
        required_paths[artifact_name] = {
            "exists": exists,
            "path": str(candidate),
        }
    return present_count, required_paths


def _inspect_next_stage_readiness(root_path: Path, project_stage: str | None) -> dict[str, Any]:
    """Inspect whether the repository carries the reserved next-stage entry artifacts.

    Args:
        root_path: Repository root path.

    Returns:
        A readiness payload for the synthetic tubelet sync probe entry contract.
    """
    project_contract = _read_project_contract(root_path)
    target_construction_phase = project_contract.get(
        "target_construction_phase",
        NEXT_STAGE_TARGET,
    )
    if project_stage == "synthetic_tubelet_sync_probe":
        present_count, required_paths = _build_required_paths(
            root_path,
            REAL_VIDEO_VAE_LATENT_REQUIRED_PATHS,
        )
        return {
            "target_construction_phase": target_construction_phase,
            "all_required_paths_present": present_count == len(REAL_VIDEO_VAE_LATENT_REQUIRED_PATHS),
            "present_required_path_count": present_count,
            "required_path_count": len(REAL_VIDEO_VAE_LATENT_REQUIRED_PATHS),
            "required_paths": required_paths,
        }

    present_count, required_paths = _build_required_paths(root_path, STAGE_ONE_REQUIRED_PATHS)

    return {
        "target_construction_phase": "synthetic_tubelet_sync_probe",
        "all_required_paths_present": present_count == len(STAGE_ONE_REQUIRED_PATHS),
        "present_required_path_count": present_count,
        "required_path_count": len(STAGE_ONE_REQUIRED_PATHS),
        "required_paths": required_paths,
    }


def _build_directory_boundary_contract_status(root_path: Path) -> dict[str, Any]:
    """Build the governed directory-boundary contract status payload.

    Args:
        root_path: Repository root path.

    Returns:
        A normalized status payload for `docs/file_organization.md`.
    """
    contract_path = root_path / DIRECTORY_BOUNDARY_CONTRACT_RELATIVE_PATH
    return {
        "exists": contract_path.exists(),
        "path": str(contract_path),
        "source_of_truth": DIRECTORY_BOUNDARY_CONTRACT_RELATIVE_PATH,
    }


def inspect_repository(root: str | Path) -> dict[str, Any]:
    """Inspect repository structure and classify bootstrap status.

    Args:
        root: Repository root path.

    Returns:
        A structure summary with repository mode and governed directory status.
    """
    root_path = Path(root)
    directory_status: dict[str, dict[str, Any]] = {}
    present_count = 0
    for directory_name in EXPECTED_DIRECTORIES:
        directory_path = root_path / directory_name
        exists = directory_path.exists()
        if exists:
            present_count += 1
        directory_status[directory_name] = {
            "exists": exists,
            "path": str(directory_path),
        }

    project_stage = None
    project_contract = _read_project_contract(root_path)
    if project_contract:
        project_stage = project_contract.get("project_stage")
    elif (root_path / "configs" / "project" / "project_contract.json").exists():
        project_stage = "unreadable"

    repository_mode = (
        "empty_repository_bootstrap" if present_count == 0 else "governed_repository"
    )
    directory_boundary_contract = _build_directory_boundary_contract_status(root_path)
    return {
        "repository_mode": repository_mode,
        "directory_status": directory_status,
        "directory_boundary_contract": directory_boundary_contract,
        "directory_boundary_source_of_truth_confirmed": directory_boundary_contract[
            "exists"
        ],
        "project_stage": project_stage,
        "next_stage_readiness": _inspect_next_stage_readiness(root_path, project_stage),
    }


def main(argv: list[str] | None = None) -> None:
    """Run the repository intake inspector as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    print(json.dumps(inspect_repository(root), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)

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
    "outputs",
]
STAGE_ONE_REQUIRED_PATHS = {
    "protocol_support_config": "configs/protocol/synthetic_tubelet_sync_probe.json",
    "temporal_attack_matrix_config": "configs/attacks/temporal_attack_matrix.json",
    "ablation_support_config": "configs/ablation/synthetic_tubelet_sync_ablation.json",
    "frame_prc_method_config": "configs/method/frame_prc.json",
    "tubelet_only_method_config": "configs/method/tubelet_only.json",
    "tubelet_sync_method_config": "configs/method/tubelet_sync.json",
    "synthetic_video_latent_module": "main/backends/synthetic_video_latent.py",
    "temporal_attack_module": "main/attacks/temporal.py",
    "synthetic_tubelet_sync_contract_module": "main/methods/temporal_tubelet_watermark/synthetic_tubelet_sync_contract.py",
}


NEXT_STAGE_TARGET = "real_video_vae_latent_probe"


def _inspect_next_stage_readiness(root_path: Path, project_stage: str | None) -> dict[str, Any]:
    """Inspect whether the repository carries the reserved next-stage entry artifacts.

    Args:
        root_path: Repository root path.

    Returns:
        A readiness payload for the synthetic tubelet sync probe entry contract.
    """
    if project_stage == "synthetic_tubelet_sync_probe":
        return {
            "target_construction_phase": NEXT_STAGE_TARGET,
            "all_required_paths_present": False,
            "present_required_path_count": 0,
            "required_path_count": 0,
            "required_paths": {},
        }

    required_paths: dict[str, dict[str, Any]] = {}
    present_count = 0
    for artifact_name, relative_path in STAGE_ONE_REQUIRED_PATHS.items():
        candidate = root_path / Path(relative_path)
        exists = candidate.exists()
        if exists:
            present_count += 1
        required_paths[artifact_name] = {
            "exists": exists,
            "path": str(candidate),
        }

    return {
        "target_construction_phase": "synthetic_tubelet_sync_probe",
        "all_required_paths_present": present_count == len(STAGE_ONE_REQUIRED_PATHS),
        "present_required_path_count": present_count,
        "required_path_count": len(STAGE_ONE_REQUIRED_PATHS),
        "required_paths": required_paths,
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
    contract_path = root_path / "configs" / "project" / "project_contract.json"
    if contract_path.exists():
        try:
            project_stage = json.loads(contract_path.read_text(encoding="utf-8")).get(
                "project_stage"
            )
        except json.JSONDecodeError:
            project_stage = "unreadable"

    repository_mode = (
        "empty_repository_bootstrap" if present_count == 0 else "governed_repository"
    )
    return {
        "repository_mode": repository_mode,
        "directory_status": directory_status,
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

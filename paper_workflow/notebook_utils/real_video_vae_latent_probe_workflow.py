"""
File purpose: Provide notebook-specific orchestration for the real-video VAE latent probe.
Module type: Notebook workflow helper
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from experiments.real_video_vae_latent_probe.artifact_builder import (
    RealVideoVaeLatentArtifactBuilder,
)
from paper_workflow.colab_utils.runtime_check import run_runtime_preflight_check
from scripts.check_results.check_real_video_vae_latent_outputs import (
    check_real_video_vae_latent_outputs,
)
from scripts.package_results.package_real_video_vae_latent_outputs import (
    package_real_video_vae_latent_outputs,
)
from scripts.package_results.package_real_video_vae_latent_tar_zst import (
    package_real_video_vae_latent_tar_zst,
)
from scripts.prepare_models.prepare_session_autoencoder_kl import (
    prepare_session_autoencoder_kl,
)


def _json_safe(value: Any) -> Any:
    """Convert workflow return values to JSON-serializable values."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def prepare_probe_runtime_workspace(
    *,
    processed_dataset_root: str | Path,
    local_dataset_root: str | Path,
    family_root: str | Path,
    run_root: str | Path,
    copy_processed_dataset: bool = False,
) -> dict[str, Any]:
    """Prepare the local notebook workspace and optional processed dataset copy."""
    processed_dataset_path = Path(processed_dataset_root)
    local_dataset_path = Path(local_dataset_root)
    family_root_path = Path(family_root)
    run_root_path = Path(run_root)

    for directory_path in (
        local_dataset_path,
        family_root_path,
        run_root_path / "artifacts",
    ):
        directory_path.mkdir(parents=True, exist_ok=True)

    if copy_processed_dataset:
        if not processed_dataset_path.exists():
            raise FileNotFoundError(processed_dataset_path)
        shutil.copytree(
            processed_dataset_path,
            local_dataset_path,
            dirs_exist_ok=True,
        )

    return {
        "processed_dataset_root": str(processed_dataset_path),
        "local_dataset_root": str(local_dataset_path),
        "family_root": str(family_root_path),
        "run_root": str(run_root_path),
        "local_dataset_ready": local_dataset_path.exists(),
    }


def prepare_probe_session_model(
    *,
    model_id: str,
    local_model_root: str | Path,
    session_manifest_path: str | Path,
    revision: str = "main",
) -> dict[str, Any]:
    """Prepare a session-only model checkout for the probe notebook."""
    manifest_payload = prepare_session_autoencoder_kl(
        model_id=model_id,
        local_model_root=local_model_root,
        revision=revision,
        session_manifest_path=session_manifest_path,
    )
    if manifest_payload.get("model_policy") != "session_only_no_drive_model_storage":
        raise RuntimeError(manifest_payload)
    return _json_safe(manifest_payload)


def write_probe_runtime_config(
    *,
    runtime_config_path: str | Path,
    execution_environment: str,
    processed_dataset_key: str,
    local_dataset_root: str | Path,
    processed_dataset_root: str | Path,
    vae_model_local_path: str | Path,
    require_formal_pass_criteria: bool,
    quality_metrics_mode: str = "real_video_frame_metrics",
    temporal_metrics_mode: str = "real_video_frame_metrics",
    attack_runtime_kind: str = "real_video",
    extra_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the probe runtime config used by the repository runner."""
    runtime_config_payload: dict[str, Any] = {
        "execution_environment": execution_environment,
        "processed_dataset_key": processed_dataset_key,
        "local_dataset_root": str(Path(local_dataset_root)),
        "processed_dataset_root": str(Path(processed_dataset_root)),
        "vae_model_local_path": str(Path(vae_model_local_path)),
        "local_vae_model_root": str(Path(vae_model_local_path)),
        "quality_metrics_mode": quality_metrics_mode,
        "temporal_metrics_mode": temporal_metrics_mode,
        "attack_runtime_kind": attack_runtime_kind,
        "require_formal_pass_criteria": bool(require_formal_pass_criteria),
    }
    if extra_config:
        runtime_config_payload.update(extra_config)

    runtime_config_file = Path(runtime_config_path)
    runtime_config_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_config_file.write_text(
        json.dumps(runtime_config_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "runtime_config_path": str(runtime_config_file),
        "runtime_config": runtime_config_payload,
    }


def run_probe_runtime_preflight(
    *,
    run_mode: str,
    local_dataset_root: str | Path,
    local_model_dirs: list[str | Path],
) -> dict[str, Any]:
    """Run the Colab runtime preflight through the notebook helper layer."""
    return _json_safe(
        run_runtime_preflight_check(
            run_mode=run_mode,
            local_dataset_dir=local_dataset_root,
            local_model_dirs=[Path(model_dir) for model_dir in local_model_dirs],
        )
    )


def run_probe_runner(
    *,
    run_root: str | Path,
    run_mode: str,
    runtime_profile: str,
    runtime_config_path: str | Path,
    protocol_config: str | Path = "configs/protocol/real_video_vae_latent_probe.json",
    backend_config: str | Path = "configs/backend/real_video_vae_latent.json",
    attack_matrix: str | Path = "configs/attacks/real_video_attack_matrix.json",
    ablation_config: str | Path = "configs/ablation/real_video_vae_latent_ablation.json",
    dataset_manifest: str | Path | None = None,
    samples_per_role: int | None = None,
    python_executable: str = sys.executable,
) -> None:
    """Run the governed probe runner module."""
    runner_command = [
        python_executable,
        "-m",
        "experiments.real_video_vae_latent_probe.runner",
        "--run-mode",
        run_mode,
        "--runtime-profile",
        runtime_profile,
        "--run-root",
        str(Path(run_root)),
        "--protocol-config",
        str(protocol_config),
        "--backend-config",
        str(backend_config),
        "--attack-matrix",
        str(attack_matrix),
        "--ablation-config",
        str(ablation_config),
        "--runtime-config",
        str(Path(runtime_config_path)),
    ]
    if dataset_manifest is not None:
        runner_command.extend(["--dataset-manifest", str(dataset_manifest)])
    if samples_per_role is not None:
        runner_command.extend(["--samples-per-role", str(int(samples_per_role))])
    subprocess.run(runner_command, check=True)


def rebuild_probe_tables_and_reports(
    *,
    run_root: str | Path,
) -> None:
    """Rebuild probe tables, figure, report, and failure gallery from records."""
    RealVideoVaeLatentArtifactBuilder().rebuild_artifacts(run_root)


def check_probe_outputs(
    *,
    run_root: str | Path,
    construction_phase: str = "real_video_vae_latent_probe",
    run_mode: str = "formal",
    require_formal_pass_criteria: bool = True,
) -> dict[str, Any]:
    """Check probe outputs through the governed checker script."""
    return _json_safe(
        check_real_video_vae_latent_outputs(
            run_root=run_root,
            construction_phase=construction_phase,
            run_mode=run_mode,
            require_formal_pass_criteria=require_formal_pass_criteria,
        )
    )


def package_probe_family_results(
    *,
    run_root: str | Path,
    family_root: str | Path,
    require_formal_pass_criteria: bool,
    formal_validation_summary: dict[str, Any],
    drive_root: str | Path | None = None,
    family_id: str | None = None,
    workflow_key: str | None = None,
    step_key: str | None = None,
    run_mode: str = "formal",
    exclude_large_intermediate_latents: bool = False,
) -> dict[str, Any]:
    """Package checked probe outputs and optionally append registry entries."""
    zip_pack = package_real_video_vae_latent_outputs(
        run_root=run_root,
        family_root=family_root,
        exclude_large_intermediate_latents=exclude_large_intermediate_latents,
    )
    tar_pack = package_real_video_vae_latent_tar_zst(
        run_root=run_root,
        family_root=family_root,
        require_formal_pass_criteria=require_formal_pass_criteria,
        exclude_large_intermediate_latents=exclude_large_intermediate_latents,
    )
    package_payload: dict[str, Any] = {
        "zip_pack": _json_safe(zip_pack),
        "tar_pack": _json_safe(tar_pack),
        "drive_archive_path": str(tar_pack["archive_path"]),
        "compat_pack_root": str(Path(run_root)),
        "formal_validation_summary": formal_validation_summary,
    }

    if drive_root is not None and family_id is not None:
        registry_entry = {
            "family_id": family_id,
            "workflow_key": workflow_key,
            "step_key": step_key,
            "run_mode": run_mode,
            "archive_path": package_payload["drive_archive_path"],
            "zip_path": str(zip_pack["zip_path"]),
            "compat_pack_root": package_payload["compat_pack_root"],
            "formal_validation_summary": formal_validation_summary,
        }
        registry_paths = _append_registry_entries(
            drive_root=drive_root,
            registry_entry=registry_entry,
        )
        package_payload["registry_paths"] = registry_paths

    return _json_safe(package_payload)


def _append_registry_entries(
    *,
    drive_root: str | Path,
    registry_entry: dict[str, Any],
) -> dict[str, str]:
    """Append result and family registry entries for notebook handoff."""
    drive_root_path = Path(drive_root)
    registry_root = drive_root_path / "TSTW" / "registry"
    result_registry_path = registry_root / "result_registry.jsonl"
    family_registry_path = registry_root / "family_registry.jsonl"
    for registry_path in (result_registry_path, family_registry_path):
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        existing_text = registry_path.read_text(encoding="utf-8") if registry_path.exists() else ""
        registry_path.write_text(
            existing_text + json.dumps(registry_entry, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return {
        "result_registry.jsonl": str(result_registry_path),
        "family_registry.jsonl": str(family_registry_path),
    }

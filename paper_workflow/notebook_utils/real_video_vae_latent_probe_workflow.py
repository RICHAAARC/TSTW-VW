"""
File purpose: Provide notebook-specific orchestration for the real-video VAE latent probe.
Module type: Notebook workflow helper
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from experiments.real_video_vae_latent_probe.artifact_builder import (
    RealVideoVaeLatentArtifactBuilder,
)
from experiments.real_video_vae_latent_probe.mechanism_audit import (
    run_stage2_mechanism_audit,
)
from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)
from paper_workflow.colab_utils.runtime_check import run_runtime_preflight_check
from main.video.dataset_manifest import load_dataset_manifest, resolve_manifest_samples
from scripts.check_results.check_real_video_vae_latent_outputs import (
    check_real_video_vae_latent_outputs,
)
from scripts.package_results.package_real_video_vae_latent_outputs import (
    package_real_video_vae_latent_outputs,
)
from scripts.package_results.package_real_video_vae_latent_tar_zst import (
    package_real_video_vae_latent_tar_zst,
)
from scripts.profile_runtime import iso_timestamp_utc
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


def materialize_family_id(
    *,
    family_id_template: str,
    git_commit: str | None,
    utc_timestamp: str | None = None,
) -> str:
    """Materialize a governed family identifier from template tokens.

    Args:
        family_id_template: Family-id template or pre-materialized id.
        git_commit: Git commit string.
        utc_timestamp: Optional UTC timestamp override.

    Returns:
        The materialized family id.

    Raises:
        ValueError: Raised when the family-id template is empty.
    """
    normalized_template = str(family_id_template).strip()
    if not normalized_template:
        raise ValueError("family_id_template must not be empty")

    short_commit = _normalize_short_commit(git_commit)
    compact_utc_timestamp = _compact_utc_timestamp(utc_timestamp or iso_timestamp_utc())
    materialized_family_id = normalized_template.replace("utc_time", compact_utc_timestamp)
    materialized_family_id = materialized_family_id.replace("short_commit", short_commit)
    materialized_family_id = materialized_family_id.replace("unknown_short_commit", short_commit)
    return materialized_family_id


def _normalize_short_commit(git_commit: str | None) -> str:
    normalized_commit = (git_commit or "").strip()
    if not normalized_commit:
        return "unknown_commit"
    if normalized_commit.lower() in {"short_commit", "commit", "unknown", "template"}:
        return "unknown_commit"
    return normalized_commit[:7]


def _compact_utc_timestamp(timestamp_value: str) -> str:
    normalized_value = str(timestamp_value).strip()
    if not normalized_value:
        return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if re.fullmatch(r"\d{8}T\d{6}Z", normalized_value):
        return normalized_value
    parsed_value = dt.datetime.fromisoformat(normalized_value.replace("Z", "+00:00"))
    if parsed_value.tzinfo is None:
        parsed_value = parsed_value.replace(tzinfo=dt.timezone.utc)
    return parsed_value.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _dataset_root_is_complete(dataset_root: Path, manifest_path: Path) -> bool:
    """Return whether a dataset root contains a complete manifest-backed sample set."""
    if not dataset_root.exists() or not manifest_path.exists():
        return False

    try:
        manifest_payload = load_dataset_manifest(manifest_path)
        resolve_manifest_samples(
            manifest_payload,
            dataset_root,
            formal_mode=True,
        )
    except (FileNotFoundError, TypeError, ValueError, json.JSONDecodeError):
        # 这里返回 False 而不是抛错，因为调用方需要在多个候选数据根目录之间选择可用目录。
        return False
    return True


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
    processed_dataset_manifest_path = processed_dataset_path / "dataset_manifest.json"
    local_dataset_manifest_path = local_dataset_path / "dataset_manifest.json"
    family_root_path = Path(family_root)
    run_root_path = Path(run_root)
    dataset_copy_error: str | None = None

    for directory_path in (
        local_dataset_path,
        family_root_path,
        run_root_path / "artifacts",
    ):
        directory_path.mkdir(parents=True, exist_ok=True)

    if copy_processed_dataset:
        if not processed_dataset_path.exists():
            raise FileNotFoundError(processed_dataset_path)
        if not processed_dataset_manifest_path.exists():
            raise FileNotFoundError(processed_dataset_manifest_path)
        try:
            shutil.copytree(
                processed_dataset_path,
                local_dataset_path,
                dirs_exist_ok=True,
            )
        except (shutil.Error, OSError) as error:
            # Google Drive 挂载在 Colab 中可能瞬时失联；后续会回退到已验证可用的数据根目录。
            dataset_copy_error = str(error)

    if _dataset_root_is_complete(local_dataset_path, local_dataset_manifest_path):
        effective_local_dataset_path = local_dataset_path
        effective_local_dataset_manifest_path = local_dataset_manifest_path
        dataset_source_mode = "local_runtime_dataset"
    elif _dataset_root_is_complete(processed_dataset_path, processed_dataset_manifest_path):
        effective_local_dataset_path = processed_dataset_path
        effective_local_dataset_manifest_path = processed_dataset_manifest_path
        if copy_processed_dataset and dataset_copy_error is not None:
            dataset_source_mode = "processed_dataset_in_place_fallback"
        else:
            dataset_source_mode = "processed_dataset_in_place"
    elif dataset_copy_error is not None:
        raise RuntimeError(
            "prepare_probe_runtime_workspace could not materialize a complete local dataset.\n"
            f"processed_dataset_root: {processed_dataset_path}\n"
            f"local_dataset_root: {local_dataset_path}\n"
            f"copy_error: {dataset_copy_error}"
        )
    else:
        raise FileNotFoundError(processed_dataset_manifest_path)

    return {
        "processed_dataset_root": str(processed_dataset_path),
        "requested_local_dataset_root": str(local_dataset_path),
        "local_dataset_root": str(effective_local_dataset_path),
        "local_dataset_manifest_path": str(effective_local_dataset_manifest_path),
        "family_root": str(family_root_path),
        "run_root": str(run_root_path),
        "local_dataset_ready": True,
        "dataset_source_mode": dataset_source_mode,
        "dataset_copy_error": dataset_copy_error,
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
    dataset_manifest_path: str | Path | None,
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
        "dataset_manifest_path": str(
            Path(dataset_manifest_path)
            if dataset_manifest_path is not None
            else Path(local_dataset_root) / "dataset_manifest.json"
        ),
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
    batch_size_frames: int | None = None,
    method_variants: list[str] | None = None,
    python_executable: str = sys.executable,
) -> None:
    """Run the governed probe runner module.

    Args:
        run_root: Run-root path.
        run_mode: Runtime mode.
        runtime_profile: Runtime profile label.
        runtime_config_path: Runtime configuration path.
        protocol_config: Protocol configuration path.
        backend_config: Backend configuration path.
        attack_matrix: Attack-matrix configuration path.
        ablation_config: Ablation configuration path.
        dataset_manifest: Optional dataset manifest path.
        samples_per_role: Optional sample count override.
        batch_size_frames: Optional VAE frame-batch override.
        method_variants: Optional governed method-variant allowlist for method shards.
        python_executable: Python executable used for the subprocess.

    Returns:
        None.
    """
    repository_root = Path(__file__).resolve().parents[2]
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
    if batch_size_frames is not None:
        runner_command.extend(["--batch-size-frames", str(int(batch_size_frames))])
    if method_variants is not None:
        normalized_method_variants = [str(method_variant) for method_variant in method_variants]
        if not normalized_method_variants or any(not value for value in normalized_method_variants):
            raise ValueError("method_variants must contain non-empty values")
        runner_command.extend(["--method-variants", *normalized_method_variants])
    runner_env = dict(os.environ)
    existing_pythonpath = runner_env.get("PYTHONPATH")
    repository_root_text = str(repository_root)
    if existing_pythonpath:
        pythonpath_entries = existing_pythonpath.split(os.pathsep)
        if repository_root_text not in pythonpath_entries:
            runner_env["PYTHONPATH"] = os.pathsep.join(
                [repository_root_text, *pythonpath_entries]
            )
    else:
        runner_env["PYTHONPATH"] = repository_root_text

    process = subprocess.Popen(
        runner_command,
        cwd=repository_root,
        env=runner_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined_output_lines: list[str] = []
    if process.stdout is not None:
        for output_line in process.stdout:
            print(output_line, end="")
            combined_output_lines.append(output_line)
    return_code = process.wait()
    if return_code != 0:
        combined_output = "".join(combined_output_lines).strip()
        raise RuntimeError(
            "run_probe_runner failed while executing the governed runner.\n"
            f"command: {subprocess.list2cmdline(runner_command)}\n"
            f"cwd: {repository_root}\n"
            f"runner_output:\n{combined_output or '<no runner output>'}"
        )


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


def run_probe_stage2_mechanism_audit(
    *,
    run_root: str | Path,
    mechanism_config_path: str | Path = "configs/protocol/stage2_mechanism_gate.json",
    target_fpr: float | None = None,
) -> dict[str, Any]:
    """Run the stage-two mechanism audit through the notebook helper layer."""
    return _json_safe(
        run_stage2_mechanism_audit(
            run_root=run_root,
            mechanism_config_path=mechanism_config_path,
            target_fpr=target_fpr,
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
    mechanism_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Package checked probe outputs and optionally append registry entries."""
    resolved_mechanism_summary = mechanism_summary or _load_stage2_mechanism_summary(run_root)
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
        "package_path": str(tar_pack["archive_path"]),
        "package_format": "tar.zst",
        "archive_format": "tar.zst",
        "compat_pack_root": str(Path(run_root)),
        "formal_validation_summary": formal_validation_summary,
    }
    if resolved_mechanism_summary is not None:
        package_payload["stage2_mechanism_summary"] = _json_safe(resolved_mechanism_summary)

    if drive_root is not None and family_id is not None:
        registry_entry = {
            "family_id": family_id,
            "workflow_key": workflow_key,
            "step_key": step_key,
            "run_mode": run_mode,
            "package_format": "tar.zst",
            "archive_format": "tar.zst",
            "archive_path": package_payload["drive_archive_path"],
            "package_path": package_payload["package_path"],
            "zip_path": str(zip_pack["zip_path"]),
            "compat_pack_root": package_payload["compat_pack_root"],
            "formal_validation_summary": formal_validation_summary,
        }
        if resolved_mechanism_summary is not None:
            registry_entry["stage2_mechanism_summary"] = _json_safe(
                resolved_mechanism_summary
            )
        registry_paths = _append_registry_entries(
            drive_root=drive_root,
            registry_entry=registry_entry,
        )
        package_payload["registry_paths"] = registry_paths

    return _json_safe(package_payload)


def _load_stage2_mechanism_summary(run_root: str | Path) -> dict[str, Any] | None:
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    if not output_paths.stage2_mechanism_decision_path.exists():
        return None
    return json.loads(output_paths.stage2_mechanism_decision_path.read_text(encoding="utf-8"))


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

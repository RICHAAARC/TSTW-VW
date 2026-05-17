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
from experiments.real_video_vae_latent_probe.mechanism_calibration_runner import (
    run_stage2_mechanism_calibration,
)
from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)
from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner
from main.core.digest import compute_object_digest, compute_path_collection_digest
from main.core.records import RecordWriter
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
    shard_count: int | None = None,
    shard_index: int | None = None,
    worker_count: int | None = None,
    method_variants: list[str] | None = None,
    cross_event_vae_batching_enabled: bool | None = None,
    cross_event_vae_decode_batch_size: int | None = None,
    cross_event_vae_encode_batch_size: int | None = None,
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
        shard_count: Optional event-shard count override.
        shard_index: Optional selected event-shard index override.
        worker_count: Optional in-shard worker count override.
        method_variants: Optional governed method-variant allowlist for legacy method-variant splits.
        cross_event_vae_batching_enabled: Optional cross-event VAE batching enable override.
        cross_event_vae_decode_batch_size: Optional cross-event decode request batch size.
        cross_event_vae_encode_batch_size: Optional cross-event encode request batch size.
        python_executable: Python executable used for the subprocess.

    Returns:
        None.
    """
    repository_root = Path(__file__).resolve().parents[2]
    runner_command = _build_probe_runner_command(
        run_root=run_root,
        run_mode=run_mode,
        runtime_profile=runtime_profile,
        runtime_config_path=runtime_config_path,
        protocol_config=protocol_config,
        backend_config=backend_config,
        attack_matrix=attack_matrix,
        ablation_config=ablation_config,
        dataset_manifest=dataset_manifest,
        samples_per_role=samples_per_role,
        batch_size_frames=batch_size_frames,
        shard_count=shard_count,
        shard_index=shard_index,
        worker_count=worker_count,
        method_variants=method_variants,
        cross_event_vae_batching_enabled=cross_event_vae_batching_enabled,
        cross_event_vae_decode_batch_size=cross_event_vae_decode_batch_size,
        cross_event_vae_encode_batch_size=cross_event_vae_encode_batch_size,
        python_executable=python_executable,
    )
    runner_env = _build_probe_runner_environment(repository_root)

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


def _build_probe_runner_command(
    *,
    run_root: str | Path,
    run_mode: str,
    runtime_profile: str,
    runtime_config_path: str | Path,
    protocol_config: str | Path,
    backend_config: str | Path,
    attack_matrix: str | Path,
    ablation_config: str | Path,
    dataset_manifest: str | Path | None,
    samples_per_role: int | None,
    batch_size_frames: int | None,
    shard_count: int | None,
    shard_index: int | None,
    worker_count: int | None,
    method_variants: list[str] | None,
    cross_event_vae_batching_enabled: bool | None,
    cross_event_vae_decode_batch_size: int | None,
    cross_event_vae_encode_batch_size: int | None,
    python_executable: str,
) -> list[str]:
    """Build the governed runner command line.

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
        batch_size_frames: Optional frame-batch override.
        shard_count: Optional event-shard count override.
        shard_index: Optional selected event-shard index override.
        worker_count: Optional in-shard worker count override.
        method_variants: Optional method-variant allowlist for legacy method-variant splits.
        cross_event_vae_batching_enabled: Optional cross-event VAE batching enable override.
        cross_event_vae_decode_batch_size: Optional cross-event decode request batch size.
        cross_event_vae_encode_batch_size: Optional cross-event encode request batch size.
        python_executable: Python executable used for the subprocess.

    Returns:
        The normalized runner command.
    """
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
    if shard_count is not None:
        runner_command.extend(["--shard-count", str(int(shard_count))])
    if shard_index is not None:
        runner_command.extend(["--shard-index", str(int(shard_index))])
    if worker_count is not None:
        runner_command.extend(["--worker-count", str(int(worker_count))])
    if method_variants is not None:
        normalized_method_variants = [str(method_variant) for method_variant in method_variants]
        if not normalized_method_variants or any(not value for value in normalized_method_variants):
            raise ValueError("method_variants must contain non-empty values")
        runner_command.extend(["--method-variants", *normalized_method_variants])
    if cross_event_vae_batching_enabled is not None:
        runner_command.extend(
            [
                "--cross-event-vae-batching-enabled",
                "true" if cross_event_vae_batching_enabled else "false",
            ]
        )
    if cross_event_vae_decode_batch_size is not None:
        runner_command.extend(
            ["--cross-event-vae-decode-batch-size", str(int(cross_event_vae_decode_batch_size))]
        )
    if cross_event_vae_encode_batch_size is not None:
        runner_command.extend(
            ["--cross-event-vae-encode-batch-size", str(int(cross_event_vae_encode_batch_size))]
        )
    return runner_command


def _build_probe_runner_environment(repository_root: Path) -> dict[str, str]:
    """Build the subprocess environment for the governed runner.

    Args:
        repository_root: Repository root path.

    Returns:
        The normalized subprocess environment.
    """
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
    return runner_env


def run_probe_method_variant_splits(
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
    method_variant_split_count: int = 2,
    cross_event_vae_batching_enabled: bool | None = None,
    cross_event_vae_decode_batch_size: int | None = None,
    cross_event_vae_encode_batch_size: int | None = None,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    """Run the governed probe runner as legacy method-variant splits and merge outputs.

    Args:
        run_root: Final merged run-root path.
        run_mode: Runtime mode.
        runtime_profile: Runtime profile label.
        runtime_config_path: Runtime configuration path.
        protocol_config: Protocol configuration path.
        backend_config: Backend configuration path.
        attack_matrix: Attack-matrix configuration path.
        ablation_config: Ablation configuration path.
        dataset_manifest: Optional dataset manifest path.
        samples_per_role: Optional sample count override.
        batch_size_frames: Optional frame-batch override.
        method_variants: Optional method-variant allowlist.
        method_variant_split_count: Requested legacy method-variant split count.
        cross_event_vae_batching_enabled: Optional cross-event VAE batching enable override.
        cross_event_vae_decode_batch_size: Optional cross-event decode request batch size.
        cross_event_vae_encode_batch_size: Optional cross-event encode request batch size.
        python_executable: Python executable used for subprocesses.

    Returns:
        A split execution and merge summary payload.
    """
    run_root_path = Path(run_root)
    repository_root = Path(__file__).resolve().parents[2]
    resolved_method_variant_split_count = int(method_variant_split_count)
    if resolved_method_variant_split_count < 1:
        raise ValueError("method_variant_split_count must be a positive integer")
    if cross_event_vae_batching_enabled and resolved_method_variant_split_count > 1:
        raise ValueError(
            "cross-event VAE batching requires method_variant_split_count == 1 in the first governed helper implementation"
        )

    resolved_method_variants = _resolve_probe_runtime_method_variants(
        repository_root=repository_root,
        ablation_config=ablation_config,
        runtime_profile=runtime_profile,
        method_variants=method_variants,
    )
    method_variant_split_plan = _plan_probe_method_variant_splits(
        method_variants=resolved_method_variants,
        split_count=resolved_method_variant_split_count,
    )
    if len(method_variant_split_plan) <= 1:
        run_probe_runner(
            run_root=run_root_path,
            run_mode=run_mode,
            runtime_profile=runtime_profile,
            runtime_config_path=runtime_config_path,
            protocol_config=protocol_config,
            backend_config=backend_config,
            attack_matrix=attack_matrix,
            ablation_config=ablation_config,
            dataset_manifest=dataset_manifest,
            samples_per_role=samples_per_role,
            batch_size_frames=batch_size_frames,
            shard_count=None,
            shard_index=None,
            worker_count=None,
            method_variants=resolved_method_variants,
            cross_event_vae_batching_enabled=cross_event_vae_batching_enabled,
            cross_event_vae_decode_batch_size=cross_event_vae_decode_batch_size,
            cross_event_vae_encode_batch_size=cross_event_vae_encode_batch_size,
            python_executable=python_executable,
        )
        return {
            "run_root": str(run_root_path),
            "method_variant_split_count": 1,
            "method_variant_split_plan": [
                {
                    "split_name": "split_01_full_run",
                    "method_variants": resolved_method_variants,
                }
            ],
            "method_variant_split_run_roots": [str(run_root_path)],
        }

    method_variant_splits_root = run_root_path / "method_variant_splits"
    method_variant_splits_root.mkdir(parents=True, exist_ok=True)
    runner_env = _build_probe_runner_environment(repository_root)
    split_processes: list[dict[str, Any]] = []
    for split_entry in method_variant_split_plan:
        split_run_root = method_variant_splits_root / str(split_entry["split_name"])
        split_run_root.parent.mkdir(parents=True, exist_ok=True)
        runner_command = _build_probe_runner_command(
            run_root=split_run_root,
            run_mode=run_mode,
            runtime_profile=runtime_profile,
            runtime_config_path=runtime_config_path,
            protocol_config=protocol_config,
            backend_config=backend_config,
            attack_matrix=attack_matrix,
            ablation_config=ablation_config,
            dataset_manifest=dataset_manifest,
            samples_per_role=samples_per_role,
            batch_size_frames=batch_size_frames,
            shard_count=None,
            shard_index=None,
            worker_count=None,
            method_variants=split_entry["method_variants"],
            cross_event_vae_batching_enabled=cross_event_vae_batching_enabled,
            cross_event_vae_decode_batch_size=cross_event_vae_decode_batch_size,
            cross_event_vae_encode_batch_size=cross_event_vae_encode_batch_size,
            python_executable=python_executable,
        )
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
        split_processes.append(
            {
                "split_name": split_entry["split_name"],
                "method_variants": list(split_entry["method_variants"]),
                "run_root": split_run_root,
                "command": runner_command,
                "process": process,
            }
        )

    split_outputs: list[dict[str, Any]] = []
    for split_process in split_processes:
        process = split_process["process"]
        if hasattr(process, "communicate"):
            combined_output, _ = process.communicate()
        else:
            combined_output = ""
            if process.stdout is not None:
                combined_output = process.stdout.read()
        combined_output = str(combined_output or "")
        if combined_output:
            print(f"[{split_process['split_name']}]\n{combined_output}", end="")
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                "run_probe_method_variant_splits failed while executing a governed runner split.\n"
                f"split_name: {split_process['split_name']}\n"
                f"command: {subprocess.list2cmdline(split_process['command'])}\n"
                f"cwd: {repository_root}\n"
                f"runner_output:\n{combined_output or '<no runner output>'}"
            )
        split_outputs.append(
            {
                "split_name": split_process["split_name"],
                "method_variants": list(split_process["method_variants"]),
                "run_root": str(split_process["run_root"]),
                "runner_output": combined_output.strip(),
            }
        )

    merge_summary = merge_probe_method_variant_split_outputs(
        run_root=run_root_path,
        split_run_roots=[Path(split_process["run_root"]) for split_process in split_processes],
        runtime_config_path=runtime_config_path,
        method_variant_split_plan=method_variant_split_plan,
    )
    return {
        "run_root": str(run_root_path),
        "method_variant_split_count": len(method_variant_split_plan),
        "method_variant_split_plan": _json_safe(method_variant_split_plan),
        "method_variant_split_run_roots": [
            str(split_process["run_root"]) for split_process in split_processes
        ],
        "method_variant_split_outputs": split_outputs,
        "merge_summary": _json_safe(merge_summary),
    }


def _resolve_probe_runtime_method_variants(
    *,
    repository_root: Path,
    ablation_config: str | Path,
    runtime_profile: str,
    method_variants: list[str] | None,
) -> list[str]:
    """Resolve the governed runtime method variants for sharding.

    Args:
        repository_root: Repository root path.
        ablation_config: Ablation configuration path.
        runtime_profile: Runtime profile label.
        method_variants: Optional method-variant allowlist.

    Returns:
        The ordered runtime method variants.
    """
    ablation_config_path = Path(ablation_config)
    if not ablation_config_path.is_absolute():
        ablation_config_path = repository_root / ablation_config_path
    ablation_payload = json.loads(ablation_config_path.read_text(encoding="utf-8"))
    runner = RealVideoVaeLatentRunner(repository_root)
    runtime_method_configs = runner._build_runtime_method_configs(
        ablation_payload,
        runner._build_method_config_paths(ablation_payload),
        runtime_profile,
        method_variants,
    )
    return [str(method_config["method_variant"]) for method_config in runtime_method_configs]


def _plan_probe_method_variant_splits(
    *,
    method_variants: list[str],
    split_count: int,
) -> list[dict[str, Any]]:
    """Plan the legacy method-variant splits for a runner invocation.

    Args:
        method_variants: Ordered runtime method variants.
        split_count: Requested split count.

    Returns:
        An ordered split plan payload.
    """
    normalized_method_variants = [str(method_variant) for method_variant in method_variants]
    if not normalized_method_variants:
        raise ValueError("method_variants must not be empty")
    if split_count <= 1 or len(normalized_method_variants) <= 1:
        return [
            {
                "split_name": "split_01_full_run",
                "method_variants": normalized_method_variants,
            }
        ]

    primary_order = ["frame_prc", "tubelet_only", "tubelet_sync"]
    primary_variants = [
        method_variant
        for method_variant in primary_order
        if method_variant in normalized_method_variants
    ]
    sweep_variants = [
        method_variant
        for method_variant in normalized_method_variants
        if method_variant not in set(primary_order)
    ]
    if split_count == 2 and primary_variants and sweep_variants:
        return [
            {
                "split_name": "split_01_main_variants",
                "method_variants": primary_variants,
            },
            {
                "split_name": "split_02_tubelet_sweep",
                "method_variants": sweep_variants,
            },
        ]

    resolved_split_count = min(int(split_count), len(normalized_method_variants))
    planned_groups: list[list[str]] = [[] for _ in range(resolved_split_count)]
    for method_index, method_variant in enumerate(normalized_method_variants):
        planned_groups[method_index % resolved_split_count].append(method_variant)
    return [
        {
            "split_name": f"split_{group_index + 1:02d}",
            "method_variants": planned_groups[group_index],
        }
        for group_index in range(resolved_split_count)
        if planned_groups[group_index]
    ]


def merge_probe_method_variant_split_outputs(
    *,
    run_root: str | Path,
    split_run_roots: list[str | Path],
    runtime_config_path: str | Path | None = None,
    method_variant_split_plan: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge legacy method-variant split outputs into one governed probe run root.

    Args:
        run_root: Final merged run-root path.
        split_run_roots: Split run-root paths.
        runtime_config_path: Optional notebook runtime-config path.
        method_variant_split_plan: Optional explicit split plan metadata.

    Returns:
        A merge summary payload.
    """
    run_root_path = Path(run_root)
    normalized_split_roots = [Path(split_root) for split_root in split_run_roots]
    if not normalized_split_roots:
        raise ValueError("split_run_roots must not be empty")

    combined_event_score_records: list[dict[str, Any]] = []
    combined_threshold_records: list[dict[str, Any]] = []
    combined_artifact_manifest: dict[tuple[str, str], dict[str, Any]] = {}
    split_summaries: list[dict[str, Any]] = []
    split_runtime_manifests: list[dict[str, Any]] = []
    split_run_manifests: list[dict[str, Any]] = []
    split_runtime_configs: list[dict[str, Any]] = []

    plan_lookup = {
        str(split_entry.get("split_name")): split_entry
        for split_entry in (method_variant_split_plan or [])
        if isinstance(split_entry, dict)
    }
    for split_root_path in normalized_split_roots:
        split_record_writer = RecordWriter(split_root_path)
        split_event_score_records = split_record_writer.read_event_score_records()
        split_threshold_records = split_record_writer.read_threshold_records()
        if not split_event_score_records or not split_threshold_records:
            raise ValueError(f"method-variant split output is incomplete: {split_root_path}")
        combined_event_score_records.extend(split_event_score_records)
        combined_threshold_records.extend(split_threshold_records)

        split_output_paths = build_real_video_vae_latent_output_paths(split_root_path)
        if split_output_paths.artifact_manifest_path.exists():
            for artifact_entry in json.loads(
                split_output_paths.artifact_manifest_path.read_text(encoding="utf-8")
            ):
                artifact_key = (
                    str(artifact_entry.get("artifact_kind")),
                    str(artifact_entry.get("relpath")),
                )
                combined_artifact_manifest[artifact_key] = artifact_entry
        if split_output_paths.runtime_manifest_path.exists():
            split_runtime_manifests.append(
                json.loads(split_output_paths.runtime_manifest_path.read_text(encoding="utf-8"))
            )
        if split_output_paths.run_manifest_path.exists():
            split_run_manifests.append(
                json.loads(split_output_paths.run_manifest_path.read_text(encoding="utf-8"))
            )
        if split_output_paths.runtime_config_path.exists():
            split_runtime_configs.append(
                json.loads(split_output_paths.runtime_config_path.read_text(encoding="utf-8"))
            )

        split_name = split_root_path.name
        planned_variants = plan_lookup.get(split_name, {}).get("method_variants")
        if planned_variants is None:
            planned_variants = sorted(
                {str(record.get("method_variant")) for record in split_event_score_records}
            )
        split_summaries.append(
            {
                "split_name": split_name,
                "split_run_root": str(split_root_path),
                "method_variants": list(planned_variants),
                "event_record_count": len(split_event_score_records),
                "threshold_record_count": len(split_threshold_records),
            }
        )

    merged_record_writer = RecordWriter(run_root_path)
    merged_record_writer.write_event_score_records(combined_event_score_records)
    merged_record_writer.write_threshold_records(combined_threshold_records)

    artifact_builder = RealVideoVaeLatentArtifactBuilder()
    artifact_paths = artifact_builder.build_artifacts(
        combined_event_score_records,
        combined_threshold_records,
        run_root_path,
    )
    output_paths = build_real_video_vae_latent_output_paths(run_root_path)
    output_paths.artifact_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.artifact_manifest_path.write_text(
        json.dumps(
            [combined_artifact_manifest[key] for key in sorted(combined_artifact_manifest.keys())],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    base_runtime_config: dict[str, Any] = {}
    if runtime_config_path is not None and Path(runtime_config_path).exists():
        base_runtime_config = json.loads(Path(runtime_config_path).read_text(encoding="utf-8"))
    elif split_runtime_configs:
        base_runtime_config = dict(split_runtime_configs[0])
    merged_method_variants = sorted(
        {str(record.get("method_variant")) for record in combined_event_score_records}
    )
    merged_runtime_config = {
        **base_runtime_config,
        "method_variants": merged_method_variants,
        "method_variant_split_mode": "legacy_parallel_method_variants",
        "method_variant_split_count": len(split_summaries),
        "method_variant_split_schedule": split_summaries,
        "merged_from_method_variant_splits": True,
    }
    output_paths.runtime_config_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.runtime_config_path.write_text(
        json.dumps(merged_runtime_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    base_runtime_manifest = dict(split_runtime_manifests[0]) if split_runtime_manifests else {}
    merged_runtime_manifest = {
        **base_runtime_manifest,
        "run_id": run_root_path.name,
        "method_variants": merged_method_variants,
        "method_variant_split_schedule": split_summaries,
        "method_variant_split_count": len(split_summaries),
        "merged_from_method_variant_splits": True,
    }
    output_paths.runtime_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.runtime_manifest_path.write_text(
        json.dumps(merged_runtime_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    base_run_manifest = dict(split_run_manifests[0]) if split_run_manifests else {}
    merged_run_manifest = {
        **base_run_manifest,
        "run_id": run_root_path.name,
        "created_at": str(base_run_manifest.get("created_at", iso_timestamp_utc())),
        "runtime_config_digest": compute_object_digest(merged_runtime_config),
        "records_digest": compute_object_digest(combined_event_score_records),
        "thresholds_digest": compute_object_digest(combined_threshold_records),
        "tables_digest": compute_path_collection_digest(output_paths.table_paths()),
        "figures_digest": compute_path_collection_digest(output_paths.figure_paths()),
        "method_config_digest": compute_object_digest(
            sorted(
                str(run_manifest.get("method_config_digest"))
                for run_manifest in split_run_manifests
            )
        ),
        "placeholder_fields": sorted(
            {
                str(field_name)
                for run_manifest in split_run_manifests
                for field_name in run_manifest.get("placeholder_fields", [])
            }
        ),
        "random_fields": sorted(
            {
                str(field_name)
                for run_manifest in split_run_manifests
                for field_name in run_manifest.get("random_fields", [])
            }
        ),
        "method_variant_split_schedule": split_summaries,
    }
    output_paths.run_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.run_manifest_path.write_text(
        json.dumps(merged_run_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    method_variant_split_summary_path = (
        output_paths.root_path / "artifacts" / "method_variant_split_summary.json"
    )
    method_variant_split_summary_path.parent.mkdir(parents=True, exist_ok=True)
    method_variant_split_summary_path.write_text(
        json.dumps(
            {
                "run_root": str(run_root_path),
                "method_variants": merged_method_variants,
                "method_variant_split_count": len(split_summaries),
                "method_variant_split_schedule": split_summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "run_root": str(run_root_path),
        "event_record_count": len(combined_event_score_records),
        "threshold_record_count": len(combined_threshold_records),
        "method_variants": merged_method_variants,
        "method_variant_split_count": len(split_summaries),
        "method_variant_split_schedule": split_summaries,
        "artifact_paths": _json_safe(artifact_paths),
        "method_variant_split_summary_path": str(method_variant_split_summary_path),
    }


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


def run_probe_stage2_mechanism_calibration(
    *,
    run_root: str | Path,
    run_mode: str = "formal",
    runtime_profile: str = "formal",
    grid_config_path: str | Path = "configs/ablation/stage2_vae_mechanism_calibration_grid.json",
    protocol_config_path: str | Path = "configs/protocol/real_video_vae_latent_probe.json",
    backend_config_path: str | Path = "configs/backend/real_video_vae_latent.json",
    attack_matrix_path: str | Path = "configs/attacks/real_video_attack_matrix.json",
    ablation_config_path: str | Path = "configs/ablation/real_video_vae_latent_ablation.json",
    mechanism_config_path: str | Path = "configs/protocol/stage2_mechanism_gate.json",
    dataset_manifest_path: str | Path | None = None,
    runtime_config_path: str | Path | None = None,
    samples_per_role: int | None = None,
    batch_size_frames: int | None = None,
    output_method_config_path: str | Path = "configs/method/tubelet_sync_real_video_vae_candidate.json",
) -> dict[str, Any]:
    """Run the stage-two mechanism calibration through the notebook helper layer."""
    return _json_safe(
        run_stage2_mechanism_calibration(
            run_root=run_root,
            run_mode=run_mode,
            runtime_profile=runtime_profile,
            grid_config_path=grid_config_path,
            protocol_config_path=protocol_config_path,
            backend_config_path=backend_config_path,
            attack_matrix_path=attack_matrix_path,
            ablation_config_path=ablation_config_path,
            mechanism_config_path=mechanism_config_path,
            dataset_manifest_path=dataset_manifest_path,
            runtime_config_path=runtime_config_path,
            samples_per_role=samples_per_role,
            batch_size_frames=batch_size_frames,
            output_method_config_path=output_method_config_path,
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

"""
文件用途：为 run_real_video_vae_latent_probe notebook 提供 runtime profiling wrapper。
File purpose: Provide runtime profiling wrappers for the run_real_video_vae_latent_probe notebook.
Module type: General module
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.profile_runtime import iso_timestamp_utc, read_json_file, write_json_file


def _repository_root() -> Path:
    """功能：返回仓库根目录。

    Return the repository root directory.

    Args:
        None.

    Returns:
        The repository root path.
    """
    return Path(__file__).resolve().parents[2]


def _build_python_env() -> dict[str, str]:
    """功能：构建 notebook helper 的 Python 执行环境。

    Build the Python execution environment used by notebook helpers.

    Args:
        None.

    Returns:
        The normalized environment mapping.
    """
    repository_root = _repository_root()
    environment = dict(os.environ)
    existing_pythonpath = environment.get("PYTHONPATH", "")
    pythonpath_entries = [entry for entry in existing_pythonpath.split(os.pathsep) if entry]
    repository_root_text = str(repository_root)
    if repository_root_text not in pythonpath_entries:
        pythonpath_entries.insert(0, repository_root_text)
    environment["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return environment


def _runtime_profile_dir(run_root: str | Path) -> Path:
    """功能：返回 run_root 下的 runtime_profile 目录。

    Return the runtime_profile directory under the run root.

    Args:
        run_root: Run-root path.

    Returns:
        The runtime_profile directory path.
    """
    runtime_profile_dir = Path(run_root) / "runtime_profile"
    runtime_profile_dir.mkdir(parents=True, exist_ok=True)
    return runtime_profile_dir


ALLOWED_RUNTIME_PROFILE_KEYS = {
    "runtime_profile",
    "gpu_target",
    "device",
    "vae_dtype",
    "vae_batch_size_frames",
    "batch_size_frames",
    "lpips_batch_size",
    "clip_batch_size",
    "video_io_worker_count",
    "attack_worker_count",
    "shard_count",
    "reuse_encoded_latents",
    "reuse_decoded_videos",
    "reuse_attacked_videos",
    "local_cache_policy",
    "precision_mode",
    "checkpointing_policy",
    "profile_gpu_runtime",
    "profile_run_timing",
    "profile_drive_io",
    "write_runtime_recommendation",
    "gpu_profile_interval_seconds",
    "drive_io_sample_size_mb",
}

FORBIDDEN_RUNTIME_PROFILE_KEYS = {
    "target_fpr",
    "target_fpr_override",
    "shared_target_fpr",
    "threshold_override",
    "threshold_policy",
    "score_weight_override",
    "method_variant_selection_from_test",
    "method_variants",
    "sample_roles",
    "splits",
    "attack_matrix",
    "attack_severity_override",
    "decision_rule_override",
    "formal_pass_override",
}

BOOLEAN_RUNTIME_PROFILE_KEYS = {
    "reuse_encoded_latents",
    "reuse_decoded_videos",
    "reuse_attacked_videos",
    "profile_gpu_runtime",
    "profile_run_timing",
    "profile_drive_io",
    "write_runtime_recommendation",
}

POSITIVE_INTEGER_RUNTIME_PROFILE_KEYS = {
    "vae_batch_size_frames",
    "batch_size_frames",
    "lpips_batch_size",
    "clip_batch_size",
    "video_io_worker_count",
    "attack_worker_count",
    "shard_count",
    "gpu_profile_interval_seconds",
    "drive_io_sample_size_mb",
}

STRING_RUNTIME_PROFILE_KEYS = {
    "runtime_profile",
    "gpu_target",
    "device",
    "vae_dtype",
    "local_cache_policy",
    "precision_mode",
    "checkpointing_policy",
}

DEFAULT_RUNTIME_PROFILE_VALUES: dict[str, Any] = {
    "device": "cuda",
    "vae_dtype": "float16",
    "vae_batch_size_frames": 8,
    "batch_size_frames": 8,
    "lpips_batch_size": 8,
    "clip_batch_size": 16,
    "video_io_worker_count": 2,
    "attack_worker_count": 2,
    "shard_count": 1,
    "reuse_encoded_latents": True,
    "reuse_decoded_videos": True,
    "reuse_attacked_videos": False,
    "local_cache_policy": "session_local_prefer_local_runtime",
    "precision_mode": "mixed_precision_fp16",
    "checkpointing_policy": "disabled",
    "profile_gpu_runtime": True,
    "profile_run_timing": True,
    "profile_drive_io": True,
    "write_runtime_recommendation": True,
    "gpu_profile_interval_seconds": 2,
    "drive_io_sample_size_mb": 64,
}


def _runtime_profile_config_root() -> Path:
    """功能：返回受治理 runtime profile 配置目录。

    Return the governed runtime-profile config root.

    Args:
        None.

    Returns:
        The runtime-profile config root path.
    """
    return _repository_root() / "configs" / "runtime_profiles"


def _runtime_profile_config_path(runtime_profile: str) -> Path:
    """功能：根据 profile 名称返回配置文件路径。

    Resolve the config file path for a runtime profile name.

    Args:
        runtime_profile: Runtime-profile name.

    Returns:
        The resolved config path.

    Raises:
        ValueError: Raised when the runtime profile name is empty.
    """
    normalized_profile = str(runtime_profile).strip()
    if not normalized_profile:
        raise ValueError("runtime_profile must be a non-empty string")
    if normalized_profile.endswith(".json"):
        normalized_profile = normalized_profile[:-5]
    return _runtime_profile_config_root() / f"{normalized_profile}.json"


def _runtime_profile_config_digest(payload: dict[str, Any]) -> str:
    """功能：计算 runtime profile 配置摘要。

    Compute a stable digest for a runtime-profile configuration payload.

    Args:
        payload: Runtime-profile payload.

    Returns:
        The normalized SHA-256 digest string.
    """
    serialized_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()


def _validate_runtime_profile_payload(
    *,
    runtime_profile: str,
    payload: dict[str, Any],
    config_path: Path,
) -> dict[str, Any]:
    """功能：校验并标准化 runtime profile 配置载荷。

    Validate and normalize a runtime-profile configuration payload.

    Args:
        runtime_profile: Requested runtime-profile name.
        payload: Parsed configuration payload.
        config_path: Source configuration path.

    Returns:
        The normalized runtime-profile payload.

    Raises:
        ValueError: Raised when forbidden, unknown, or malformed fields are present.
    """
    if not isinstance(payload, dict):
        raise ValueError(f"runtime_profile config must be a JSON object: {config_path}")

    payload_keys = set(payload.keys())
    forbidden_keys = sorted(payload_keys & FORBIDDEN_RUNTIME_PROFILE_KEYS)
    if forbidden_keys:
        # 中文：runtime_profile 只能描述执行层参数，不能承载 threshold 或判决语义覆盖。
        raise ValueError(
            f"runtime_profile config contains forbidden semantic keys: {forbidden_keys}"
        )

    unknown_keys = sorted(payload_keys - ALLOWED_RUNTIME_PROFILE_KEYS)
    if unknown_keys:
        raise ValueError(
            f"runtime_profile config contains unknown keys: {unknown_keys}"
        )

    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            raise ValueError(
                f"runtime_profile config values must stay flat and scalar-like: {key}"
            )

    normalized_payload: dict[str, Any] = dict(DEFAULT_RUNTIME_PROFILE_VALUES)
    normalized_payload.update(payload)
    normalized_payload["runtime_profile"] = str(
        normalized_payload.get("runtime_profile", runtime_profile)
    ).strip()
    if normalized_payload["runtime_profile"] != str(runtime_profile).strip():
        raise ValueError(
            "runtime_profile field must exactly match the requested profile name"
        )

    for key in STRING_RUNTIME_PROFILE_KEYS:
        if key not in normalized_payload:
            continue
        value = normalized_payload[key]
        if value is None:
            continue
        normalized_value = str(value).strip()
        if not normalized_value:
            raise ValueError(f"runtime_profile field {key} must be a non-empty string")
        normalized_payload[key] = normalized_value

    for key in BOOLEAN_RUNTIME_PROFILE_KEYS:
        if key not in normalized_payload:
            continue
        value = normalized_payload[key]
        if not isinstance(value, bool):
            raise ValueError(f"runtime_profile field {key} must be boolean")

    for key in POSITIVE_INTEGER_RUNTIME_PROFILE_KEYS:
        if key not in normalized_payload:
            continue
        value = normalized_payload[key]
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"runtime_profile field {key} must be a positive integer")

    vae_batch_size_frames = int(
        payload.get(
            "vae_batch_size_frames",
            DEFAULT_RUNTIME_PROFILE_VALUES["vae_batch_size_frames"],
        )
    )
    batch_size_frames = int(payload.get("batch_size_frames", vae_batch_size_frames))
    if "vae_batch_size_frames" in payload and "batch_size_frames" in payload and vae_batch_size_frames != batch_size_frames:
        raise ValueError(
            "vae_batch_size_frames and batch_size_frames must match when both are provided"
        )
    normalized_payload["vae_batch_size_frames"] = vae_batch_size_frames
    normalized_payload["batch_size_frames"] = batch_size_frames
    normalized_payload["profile_runtime"] = bool(
        normalized_payload["profile_gpu_runtime"]
        or normalized_payload["profile_run_timing"]
        or normalized_payload["profile_drive_io"]
        or normalized_payload["write_runtime_recommendation"]
    )
    normalized_payload["config_path"] = str(config_path)
    normalized_payload["config_digest"] = _runtime_profile_config_digest(
        {
            key: normalized_payload[key]
            for key in sorted(ALLOWED_RUNTIME_PROFILE_KEYS)
            if key in normalized_payload
        }
    )
    return normalized_payload


def load_runtime_profile_config(
    *,
    runtime_profile: str,
    run_root: str | Path | None = None,
) -> dict[str, Any]:
    """功能：加载并校验 notebook 的 runtime profile 配置。

    Load and validate the notebook runtime-profile configuration.

    Args:
        runtime_profile: Requested runtime-profile name.
        run_root: Optional run-root path used to persist the profile plan.

    Returns:
        The normalized runtime-profile payload.

    Raises:
        FileNotFoundError: Raised when the governed profile config is missing.
        ValueError: Raised when the profile config violates execution-only boundaries.
    """
    config_path = _runtime_profile_config_path(runtime_profile)
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    payload = read_json_file(config_path)
    normalized_payload = _validate_runtime_profile_payload(
        runtime_profile=str(runtime_profile).strip(),
        payload=payload,
        config_path=config_path,
    )
    if run_root is not None:
        persist_runtime_profile_plan(
            run_root=run_root,
            runtime_profile_payload=normalized_payload,
        )
    return normalized_payload


def persist_runtime_profile_plan(
    *,
    run_root: str | Path,
    runtime_profile_payload: dict[str, Any],
) -> dict[str, Any]:
    """功能：将 runtime profile 计划写入 run_root/runtime_profile/。

    Persist the normalized runtime-profile plan under run_root/runtime_profile/.

    Args:
        run_root: Run-root path.
        runtime_profile_payload: Normalized runtime-profile payload.

    Returns:
        The persisted runtime-profile payload.
    """
    normalized_payload = dict(runtime_profile_payload)
    write_json_file(
        _runtime_profile_dir(run_root) / "runtime_profile_plan.json",
        normalized_payload,
    )
    return normalized_payload


def _gpu_profiler_session_path(run_root: str | Path) -> Path:
    """功能：返回 GPU profiler session 状态文件路径。

    Return the GPU-profiler session status path.

    Args:
        run_root: Run-root path.

    Returns:
        The profiler-session JSON path.
    """
    return _runtime_profile_dir(run_root) / "gpu_runtime_profiler_session.json"


def _read_gpu_profiler_session(run_root: str | Path) -> dict[str, Any]:
    """功能：读取 GPU profiler session 状态。

    Read the GPU-profiler session state payload.

    Args:
        run_root: Run-root path.

    Returns:
        The normalized session payload.
    """
    session_path = _gpu_profiler_session_path(run_root)
    if not session_path.exists():
        return {"warnings": []}
    try:
        payload = read_json_file(session_path)
    except Exception:
        # session 状态文件损坏时回退到空载荷，避免 notebook helper 因 warning 写盘失败而中断。
        return {"warnings": []}
    if not isinstance(payload, dict):
        return {"warnings": []}
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list):
        payload["warnings"] = []
    return payload


def _write_gpu_profiler_session(
    run_root: str | Path,
    *,
    status: bool,
    process_started: bool,
    interval_seconds: int | None,
    command: list[str],
    pid: int | None = None,
    error_message: str | None = None,
    forced_termination: bool | None = None,
    forced_kill: bool | None = None,
) -> dict[str, Any]:
    """功能：写出 GPU profiler session 状态。

    Persist the GPU-profiler session status.

    Args:
        run_root: Run-root path.
        status: Session status flag.
        process_started: Whether the profiler process started successfully.
        interval_seconds: Sampling interval in seconds.
        command: Profiler command list.
        pid: Optional process identifier.
        error_message: Optional error message.
        forced_termination: Optional forced-termination marker.
        forced_kill: Optional forced-kill marker.

    Returns:
        The normalized session payload.
    """
    payload = _read_gpu_profiler_session(run_root)
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = []
    payload.update(
        {
            "status": status,
            "process_started": process_started,
            "interval_seconds": interval_seconds,
            "pid": pid,
            "command": subprocess.list2cmdline(command),
            "updated_at_utc": iso_timestamp_utc(),
            "warnings": warnings,
            "warning_count": len(warnings),
        }
    )
    if error_message is not None:
        payload["error_message"] = error_message
    if forced_termination is not None:
        payload["forced_termination"] = forced_termination
    if forced_kill is not None:
        payload["forced_kill"] = forced_kill
    write_json_file(_gpu_profiler_session_path(run_root), payload)
    return payload


def _append_gpu_profiler_warning(
    run_root: str | Path,
    *,
    warning_type: str,
    message: str,
) -> dict[str, Any]:
    """功能：追加 GPU profiler warning 记录。

    Append a GPU-profiler warning record.

    Args:
        run_root: Run-root path.
        warning_type: Warning category.
        message: Warning message.

    Returns:
        The normalized session payload after the warning is appended.
    """
    payload = _read_gpu_profiler_session(run_root)
    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = []
    warnings.append(
        {
            "warning_type": warning_type,
            "message": message,
            "timestamp_utc": iso_timestamp_utc(),
        }
    )
    payload["warnings"] = warnings
    payload["warning_count"] = len(warnings)
    payload["updated_at_utc"] = iso_timestamp_utc()
    write_json_file(_gpu_profiler_session_path(run_root), payload)
    return payload


def _run_json_module(module_name: str, *, output_json: Path, arguments: list[str]) -> dict[str, Any]:
    """功能：执行生成 JSON 的脚本模块并返回结果。

    Execute a JSON-producing script module and return its result payload.

    Args:
        module_name: Target Python module name.
        output_json: Expected output JSON path.
        arguments: Additional CLI arguments.

    Returns:
        The parsed JSON payload, or a normalized failure payload.
    """
    command = [sys.executable, "-m", module_name, *arguments]
    try:
        completed_process = subprocess.run(
            command,
            cwd=_repository_root(),
            env=_build_python_env(),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as error:
        if output_json.exists():
            try:
                payload = json.loads(output_json.read_text(encoding="utf-8"))
                payload.setdefault("status", False)
                payload.setdefault("error_message", error.stderr.strip() or error.stdout.strip())
                return payload
            except Exception:
                pass
        return {
            "status": False,
            "module_name": module_name,
            "error_message": error.stderr.strip() or error.stdout.strip() or str(error),
            "command": subprocess.list2cmdline(command),
        }

    if not output_json.exists():
        return {
            "status": False,
            "module_name": module_name,
            "error_message": "expected output JSON was not created",
            "stdout": completed_process.stdout.strip(),
        }
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    payload.setdefault("status", True)
    return payload


def capture_colab_environment(*, run_root: str | Path, run_id: str, run_mode: str, runtime_profile: str) -> dict[str, Any]:
    """功能：捕获 notebook 运行环境快照。

    Capture the notebook runtime environment snapshot.

    Args:
        run_root: Run-root path.
        run_id: Run identifier.
        run_mode: Runtime mode.
        runtime_profile: Runtime profile.

    Returns:
        The environment-snapshot payload.
    """
    output_json = _runtime_profile_dir(run_root) / "colab_environment_snapshot.json"
    return _run_json_module(
        "scripts.profile_runtime.capture_colab_environment",
        output_json=output_json,
        arguments=[
            "--run-root",
            str(run_root),
            "--run-id",
            run_id,
            "--run-mode",
            run_mode,
            "--runtime-profile",
            runtime_profile,
            "--output-json",
            str(output_json),
        ],
    )


def profile_drive_io(
    *,
    run_root: str | Path,
    drive_root: str | Path,
    local_root: str | Path,
    sample_size_mb: int = 64,
) -> dict[str, Any]:
    """功能：执行 Drive IO profiling。

    Execute the Drive IO profiling workflow.

    Args:
        run_root: Run-root path.
        drive_root: Drive root path.
        local_root: Local root path.
        sample_size_mb: Probe sample size in MB.

    Returns:
        The Drive-IO profile payload.
    """
    output_json = _runtime_profile_dir(run_root) / "drive_io_profile.json"
    return _run_json_module(
        "scripts.profile_runtime.profile_drive_io",
        output_json=output_json,
        arguments=[
            "--drive-root",
            str(drive_root),
            "--local-root",
            str(local_root),
            "--output-json",
            str(output_json),
            "--sample-size-mb",
            str(int(sample_size_mb)),
        ],
    )


def estimate_real_video_vae_latent_run_scale(
    *,
    run_root: str | Path,
    dataset_manifest: str | Path,
    attack_matrix: str | Path,
    ablation_config: str | Path,
    runtime_profile: str,
) -> dict[str, Any]:
    """功能：估算 real-video VAE latent run 规模。

    Estimate the real-video VAE latent run scale.

    Args:
        run_root: Run-root path.
        dataset_manifest: Dataset-manifest path.
        attack_matrix: Attack-matrix path.
        ablation_config: Ablation-config path.
        runtime_profile: Runtime profile.

    Returns:
        The scale-estimation payload.
    """
    output_json = _runtime_profile_dir(run_root) / "run_scale_estimate.json"
    return _run_json_module(
        "scripts.profile_runtime.estimate_real_video_vae_latent_run_scale",
        output_json=output_json,
        arguments=[
            "--dataset-manifest",
            str(dataset_manifest),
            "--attack-matrix",
            str(attack_matrix),
            "--ablation-config",
            str(ablation_config),
            "--runtime-profile",
            runtime_profile,
            "--output-json",
            str(output_json),
        ],
    )


def start_gpu_runtime_profile(*, run_root: str | Path, interval_seconds: int = 2) -> subprocess.Popen[str] | None:
    """功能：启动后台 GPU profiler 进程。

    Start the background GPU profiler process.

    Args:
        run_root: Run-root path.
        interval_seconds: Sampling interval in seconds.

    Returns:
        The profiler subprocess handle, or None when startup fails.
    """
    runtime_profile_dir = _runtime_profile_dir(run_root)
    stop_file = runtime_profile_dir / "gpu_profile_stop.flag"
    trace_csv = runtime_profile_dir / "gpu_runtime_trace.csv"
    event_tag_file = runtime_profile_dir / "current_runtime_event_tag.txt"
    if stop_file.exists():
        stop_file.unlink()
    if not event_tag_file.exists():
        event_tag_file.write_text("unlabeled\n", encoding="utf-8")
    command = [
        sys.executable,
        "-m",
        "scripts.profile_runtime.profile_gpu_runtime",
        "--run-root",
        str(run_root),
        "--interval-seconds",
        str(int(interval_seconds)),
        "--output-csv",
        str(trace_csv),
        "--stop-file",
        str(stop_file),
        "--current-event-tag-file",
        str(event_tag_file),
    ]
    try:
        process = subprocess.Popen(
            command,
            cwd=_repository_root(),
            env=_build_python_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        _write_gpu_profiler_session(
            run_root,
            status=True,
            process_started=True,
            interval_seconds=int(interval_seconds),
            command=command,
            pid=process.pid,
            error_message="",
            forced_termination=False,
            forced_kill=False,
        )
        return process
    except Exception as error:
        error_message = f"failed to start background GPU profiler: {error}"
        _write_gpu_profiler_session(
            run_root,
            status=False,
            process_started=False,
            interval_seconds=int(interval_seconds),
            command=command,
            pid=None,
            error_message=error_message,
            forced_termination=False,
            forced_kill=False,
        )
        _append_gpu_profiler_warning(
            run_root,
            warning_type="gpu_runtime_profiler_start_failed",
            message=error_message,
        )
        return None


def stop_gpu_runtime_profile(process: subprocess.Popen[str] | None, *, run_root: str | Path) -> None:
    """功能：停止后台 GPU profiler 进程。

    Stop the background GPU profiler process.

    Args:
        process: Profiler subprocess handle.
        run_root: Run-root path.

    Returns:
        None.
    """
    runtime_profile_dir = _runtime_profile_dir(run_root)
    stop_file = runtime_profile_dir / "gpu_profile_stop.flag"
    stop_file.write_text("stop\n", encoding="utf-8")
    if process is None:
        return
    command = [str(process.args)] if isinstance(process.args, str) else [str(item) for item in process.args]
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        # profiler 无法在合理时间内退出时显式终止，防止 notebook 挂起。
        _append_gpu_profiler_warning(
            run_root,
            warning_type="gpu_runtime_profiler_force_terminate",
            message="GPU profiler did not exit within 15 seconds and required terminate().",
        )
        _write_gpu_profiler_session(
            run_root,
            status=True,
            process_started=True,
            interval_seconds=None,
            command=command,
            pid=process.pid,
            forced_termination=True,
        )
        try:
            process.terminate()
        except Exception as error:
            # profiler terminate 失败时仅记录 warning，避免覆盖正式 runner 的结果状态。
            _append_gpu_profiler_warning(
                run_root,
                warning_type="gpu_runtime_profiler_terminate_failed",
                message=f"GPU profiler terminate() failed: {error}",
            )
            _write_gpu_profiler_session(
                run_root,
                status=False,
                process_started=True,
                interval_seconds=None,
                command=command,
                pid=process.pid,
                error_message=f"GPU profiler terminate() failed: {error}",
                forced_termination=True,
            )
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _append_gpu_profiler_warning(
                run_root,
                warning_type="gpu_runtime_profiler_force_kill",
                message="GPU profiler still did not exit after terminate() and required kill().",
            )
            _write_gpu_profiler_session(
                run_root,
                status=True,
                process_started=True,
                interval_seconds=None,
                command=command,
                pid=process.pid,
                forced_termination=True,
                forced_kill=True,
            )
            try:
                process.kill()
            except Exception as error:
                # profiler kill 失败时也只记录 warning，避免 finally 清理路径反向导致 notebook 失败。
                _append_gpu_profiler_warning(
                    run_root,
                    warning_type="gpu_runtime_profiler_kill_failed",
                    message=f"GPU profiler kill() failed: {error}",
                )
                _write_gpu_profiler_session(
                    run_root,
                    status=False,
                    process_started=True,
                    interval_seconds=None,
                    command=command,
                    pid=process.pid,
                    error_message=f"GPU profiler kill() failed: {error}",
                    forced_termination=True,
                    forced_kill=True,
                )
                return
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _append_gpu_profiler_warning(
                    run_root,
                    warning_type="gpu_runtime_profiler_still_running_after_kill",
                    message="GPU profiler still did not exit after kill(); notebook cleanup continued with a warning.",
                )
                _write_gpu_profiler_session(
                    run_root,
                    status=False,
                    process_started=True,
                    interval_seconds=None,
                    command=command,
                    pid=process.pid,
                    error_message="GPU profiler remained alive after kill().",
                    forced_termination=True,
                    forced_kill=True,
                )


def summarize_gpu_runtime_profile(*, run_root: str | Path) -> dict[str, Any]:
    """功能：汇总 GPU runtime profile。

    Summarize the GPU runtime profile.

    Args:
        run_root: Run-root path.

    Returns:
        The GPU-summary payload.
    """
    runtime_profile_dir = _runtime_profile_dir(run_root)
    output_json = runtime_profile_dir / "gpu_runtime_summary.json"
    output_md = runtime_profile_dir / "gpu_runtime_report.md"
    trace_csv = runtime_profile_dir / "gpu_runtime_trace.csv"
    return _run_json_module(
        "scripts.profile_runtime.summarize_gpu_profile",
        output_json=output_json,
        arguments=[
            "--run-root",
            str(run_root),
            "--trace-csv",
            str(trace_csv),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
    )


def watch_real_video_vae_latent_progress(*, run_root: str | Path) -> dict[str, Any]:
    """功能：生成当前进度快照。

    Generate the current run progress snapshot.

    Args:
        run_root: Run-root path.

    Returns:
        The progress snapshot payload.
    """
    output_json = _runtime_profile_dir(run_root) / "run_progress_snapshot.json"
    return _run_json_module(
        "scripts.profile_runtime.watch_real_video_vae_latent_progress",
        output_json=output_json,
        arguments=[
            "--run-root",
            str(run_root),
            "--output-json",
            str(output_json),
        ],
    )


def summarize_run_failures(*, run_root: str | Path) -> dict[str, Any]:
    """功能：汇总运行失败原因。

    Summarize run failures.

    Args:
        run_root: Run-root path.

    Returns:
        The failure-summary payload.
    """
    runtime_profile_dir = _runtime_profile_dir(run_root)
    output_json = runtime_profile_dir / "run_failure_summary.json"
    output_md = runtime_profile_dir / "run_failure_summary.md"
    return _run_json_module(
        "scripts.check_results.summarize_run_failures",
        output_json=output_json,
        arguments=[
            "--run-root",
            str(run_root),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
    )


def recommend_runtime_parameters(*, run_root: str | Path) -> dict[str, Any]:
    """功能：生成下一轮运行参数建议。

    Generate next-round runtime parameter recommendations.

    Args:
        run_root: Run-root path.

    Returns:
        The runtime-parameter recommendation payload.
    """
    output_json = _runtime_profile_dir(run_root) / "runtime_parameter_recommendation.json"
    return _run_json_module(
        "scripts.profile_runtime.recommend_runtime_parameters",
        output_json=output_json,
        arguments=[
            "--run-root",
            str(run_root),
            "--output-json",
            str(output_json),
        ],
    )

"""
文件用途：将阶段 2 运行目录打包为 tar.zst 并写出检查摘要。
File purpose: Package stage-two run outputs into tar.zst with checks summaries.
Module type: General module
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
import tarfile
import tempfile
from typing import Any

from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)


def _supports_tar_zstd() -> bool:
    """功能：检测 tar --zstd 是否可用。

    Detect whether `tar --zstd` is supported in the current environment.

    Args:
        None.

    Returns:
        True if tar --zstd is supported, otherwise False.
    """
    tar_binary = shutil.which("tar")
    if tar_binary is None:
        return False
    try:
        help_text = subprocess.check_output([tar_binary, "--help"], text=True)
    except Exception:
        return False
    return "--zstd" in help_text


def _load_zstandard_module() -> Any | None:
    """功能：按需导入 Python zstandard 模块。

    Import the optional Python zstandard module when available.

    Args:
        None.

    Returns:
        The imported zstandard module, or None when unavailable.
    """
    try:
        import zstandard  # type: ignore
    except ImportError:
        return None
    return zstandard


def _build_tar_inputs(
    run_root_path: Path,
    include_relpaths: list[str],
) -> list[str]:
    """功能：构建 tar 打包输入列表。

    Build the relative archive inputs for the current run root.

    Args:
        run_root_path: Run-root path.
        include_relpaths: Relative paths to consider.

    Returns:
        A list of archive-relative input paths.
    """
    tar_inputs: list[str] = []
    for relative_path in include_relpaths:
        candidate = run_root_path / relative_path
        if candidate.exists():
            tar_inputs.append(f"{run_root_path.name}/{relative_path}")
    return tar_inputs


def _pack_with_external_tar_zstd(
    *,
    archive_path: Path,
    run_root_path: Path,
    tar_inputs: list[str],
) -> None:
    """功能：使用外部 tar --zstd 执行打包。

    Package the run root through the external tar --zstd command.

    Args:
        archive_path: Target archive path.
        run_root_path: Run-root path.
        tar_inputs: Archive-relative input paths.

    Returns:
        None.

    Raises:
        CalledProcessError: Raised when the external tar command fails.
    """
    command = [
        "tar",
        "--zstd",
        "-cf",
        str(archive_path),
        "-C",
        str(run_root_path.parent),
        *tar_inputs,
    ]
    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _pack_with_python_zstandard(
    *,
    archive_path: Path,
    run_root_path: Path,
    tar_inputs: list[str],
) -> None:
    """功能：使用 Python zstandard fallback 执行 tar.zst 打包。

    Package the run root through a Python tar plus zstandard fallback path.

    Args:
        archive_path: Target archive path.
        run_root_path: Run-root path.
        tar_inputs: Archive-relative input paths.

    Returns:
        None.

    Raises:
        RuntimeError: Raised when Python zstandard support is unavailable.
    """
    zstandard_module = _load_zstandard_module()
    if zstandard_module is None:
        raise RuntimeError("python zstandard support is unavailable")

    temporary_handle = tempfile.NamedTemporaryFile(
        suffix=".tar",
        delete=False,
        dir=str(archive_path.parent),
    )
    temporary_tar_path = Path(temporary_handle.name)
    temporary_handle.close()
    try:
        with tarfile.open(temporary_tar_path, mode="w") as tar_handle:
            for relative_path in tar_inputs:
                source_path = run_root_path.parent / relative_path
                tar_handle.add(source_path, arcname=relative_path, recursive=True)
        with temporary_tar_path.open("rb") as source_handle, archive_path.open("wb") as target_handle:
            compressor = zstandard_module.ZstdCompressor()
            with compressor.stream_writer(target_handle) as compressed_handle:
                shutil.copyfileobj(source_handle, compressed_handle)
    finally:
        if temporary_tar_path.exists():
            temporary_tar_path.unlink()


def pack_run_to_tar_zst(
    run_root: str | Path,
    drive_result_dir: str | Path,
    checks_payload: dict[str, Any],
    *,
    exclude_large_intermediate_latents: bool = False,
) -> dict[str, Path]:
    """功能：将运行目录打包为 tar.zst，并写出 summary 与 checks。

    Package run outputs into tar.zst and write summary/check JSON files.

    Args:
        run_root: Run root path.
        drive_result_dir: Drive result output directory.
        checks_payload: Checker payload for summary and checks files.
        exclude_large_intermediate_latents: Whether to exclude heavy artifact trees.

    Returns:
        A dictionary containing archive, summary, and checks paths.

    Raises:
        RuntimeError: Raised when both external tar.zst and Python fallback are unavailable.
    """
    run_root_path = Path(run_root)
    if not run_root_path.exists():
        raise FileNotFoundError(run_root_path)

    output_paths = build_real_video_vae_latent_output_paths(run_root_path)
    run_manifest = json.loads(output_paths.run_manifest_path.read_text(encoding="utf-8"))
    run_id = str(run_manifest.get("run_id", run_root_path.name))
    drive_dir = Path(drive_result_dir)
    drive_dir.mkdir(parents=True, exist_ok=True)

    archive_path = drive_dir / f"{run_id}.tar.zst"
    summary_path = drive_dir / f"{run_id}_summary.json"
    checks_path = drive_dir / f"{run_id}_checks.json"

    include_relpaths = [
        "records",
        "thresholds",
        "tables",
        "figures",
        "reports",
        "failure_case_gallery",
        "artifacts",
        "logs",
    ]
    if exclude_large_intermediate_latents:
        include_relpaths.remove("artifacts")
        include_relpaths.append("artifacts/run_manifest.json")
        include_relpaths.append("artifacts/artifact_manifest.json")
        include_relpaths.append("artifacts/runtime_manifest.json")
        include_relpaths.append("artifacts/runtime_config.json")
        include_relpaths.append(
            output_paths.stage2_mechanism_decision_path.relative_to(run_root_path).as_posix()
        )

    tar_inputs = _build_tar_inputs(run_root_path, include_relpaths)
    tar_failure_message: str | None = None
    if _supports_tar_zstd():
        try:
            _pack_with_external_tar_zstd(
                archive_path=archive_path,
                run_root_path=run_root_path,
                tar_inputs=tar_inputs,
            )
        except subprocess.CalledProcessError as error:
            if archive_path.exists():
                archive_path.unlink()
            stderr_text = (error.stderr or "").strip()
            stdout_text = (error.stdout or "").strip()
            tar_failure_message = (
                "external tar --zstd packaging failed"
                f" (returncode={error.returncode})"
            )
            if stderr_text:
                tar_failure_message += f"; stderr={stderr_text}"
            elif stdout_text:
                tar_failure_message += f"; stdout={stdout_text}"
    else:
        tar_failure_message = "tar --zstd is unavailable"

    if not archive_path.exists():
        try:
            _pack_with_python_zstandard(
                archive_path=archive_path,
                run_root_path=run_root_path,
                tar_inputs=tar_inputs,
            )
        except RuntimeError as error:
            if tar_failure_message is None:
                tar_failure_message = "tar.zst packaging failed before archive creation"
            raise RuntimeError(
                f"{tar_failure_message}; python fallback requires the zstandard package"
            ) from error

    decision = str(checks_payload.get("RealVideoVaeLatentDecision", "INCONCLUSIVE"))
    if not decision:
        decision = "INCONCLUSIVE"
    archive_relpath = archive_path.relative_to(drive_dir.parent) if drive_dir.parent in archive_path.parents else archive_path.name
    summary_payload = {
        "run_id": run_id,
        "construction_phase": run_manifest.get("construction_phase"),
        "decision": decision,
        "status": bool(checks_payload.get("status", False)),
        "archive_format": "tar.zst",
        "archive_path": str(archive_path),
        "archive_relpath": str(archive_relpath),
        "summary_path": str(summary_path),
        "checks_path": str(checks_path),
        "excluded_patterns": [
            "*.pth",
            "*.pt",
            "*.ckpt",
            "*.safetensors",
            "*.bin",
            "session_models/**",
            "model_cache/**",
            ".cache/**",
            "__pycache__/**",
            "tmp/**",
        ] if exclude_large_intermediate_latents else [],
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks_path.write_text(json.dumps(checks_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "archive_path": archive_path,
        "summary_path": summary_path,
        "checks_path": checks_path,
    }

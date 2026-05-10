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
from typing import Any

from main.protocol.real_video_vae_latent_paths import build_real_video_vae_latent_output_paths


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
        RuntimeError: Raised when tar --zstd is unavailable.
    """
    run_root_path = Path(run_root)
    if not run_root_path.exists():
        raise FileNotFoundError(run_root_path)
    if not _supports_tar_zstd():
        # 当前实现要求 tar --zstd 可用，缺失时显式阻断。
        raise RuntimeError("tar --zstd is unavailable")

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
        include_relpaths.append("artifacts/colab_runtime_manifest.json")
        include_relpaths.append("artifacts/colab_real_video_vae_latent_runtime_config.json")

    tar_inputs: list[str] = []
    for relative_path in include_relpaths:
        candidate = run_root_path / relative_path
        if candidate.exists():
            tar_inputs.append(f"{run_root_path.name}/{relative_path}")

    command = [
        "tar",
        "--zstd",
        "-cf",
        str(archive_path),
        "-C",
        str(run_root_path.parent),
        *tar_inputs,
    ]
    subprocess.run(command, check=True)

    decision = str(checks_payload.get("RealVideoVaeLatentDecision", "INCONCLUSIVE"))
    summary_payload = {
        "run_id": run_id,
        "construction_phase": run_manifest.get("construction_phase"),
        "decision": decision,
        "status": bool(checks_payload.get("status", False)),
        "archive_path": str(archive_path),
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks_path.write_text(json.dumps(checks_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "archive_path": archive_path,
        "summary_path": summary_path,
        "checks_path": checks_path,
    }

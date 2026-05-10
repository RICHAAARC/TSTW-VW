"""
文件用途：提供 Colab formal 运行前的环境预检。
File purpose: Provide runtime preflight checks for Colab formal execution.
Module type: General module
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def _has_tar_zstd_support() -> bool:
    """功能：检查当前环境是否支持 tar --zstd。

    Check whether the current environment supports `tar --zstd`.

    Args:
        None.

    Returns:
        True if supported, otherwise False.
    """
    tar_binary = shutil.which("tar")
    if tar_binary is None:
        return False
    try:
        help_text = subprocess.check_output([tar_binary, "--help"], text=True)
    except Exception:
        return False
    return "--zstd" in help_text


def run_runtime_preflight_check(
    run_mode: str,
    local_dataset_dir: str | Path,
    local_model_dirs: list[Path],
) -> dict[str, Any]:
    """功能：执行 Colab formal 预检并返回报告。

    Run Colab preflight checks and return a normalized report.

    Args:
        run_mode: Runtime mode label.
        local_dataset_dir: Local dataset directory.
        local_model_dirs: Required local model directories.

    Returns:
        A dictionary containing preflight checks.

    Raises:
        RuntimeError: Raised when formal mode requirements are not satisfied.
    """
    dataset_path = Path(local_dataset_dir)
    ffmpeg_available = shutil.which("ffmpeg") is not None
    tar_zstd_available = _has_tar_zstd_support()
    nvidia_smi_available = shutil.which("nvidia-smi") is not None

    gpu_name = ""
    if nvidia_smi_available:
        try:
            gpu_name = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                text=True,
            ).strip()
        except Exception:
            gpu_name = ""

    model_dir_status: list[dict[str, Any]] = []
    all_model_dirs_ready = True
    for model_path in local_model_dirs:
        file_count = 0
        exists = model_path.exists()
        if exists:
            file_count = len([path for path in model_path.rglob("*") if path.is_file()])
        ready = exists and file_count > 0
        all_model_dirs_ready = all_model_dirs_ready and ready
        model_dir_status.append(
            {
                "path": str(model_path),
                "exists": exists,
                "file_count": file_count,
                "ready": ready,
            }
        )

    dataset_file_count = 0
    if dataset_path.exists():
        dataset_file_count = len([path for path in dataset_path.rglob("*.mp4") if path.is_file()])

    report = {
        "run_mode": run_mode,
        "ffmpeg_available": ffmpeg_available,
        "tar_zstd_available": tar_zstd_available,
        "nvidia_smi_available": nvidia_smi_available,
        "gpu_name": gpu_name or "not_available",
        "dataset_exists": dataset_path.exists(),
        "dataset_mp4_count": dataset_file_count,
        "model_dirs": model_dir_status,
    }

    if run_mode == "formal":
        if not ffmpeg_available:
            # formal 模式必须可用 ffmpeg。
            raise RuntimeError("formal preflight failed: ffmpeg is unavailable")
        if not tar_zstd_available:
            # formal 模式必须支持 tar --zstd。
            raise RuntimeError("formal preflight failed: tar --zstd is unavailable")
        if not gpu_name:
            # formal 模式必须检测到 GPU。
            raise RuntimeError("formal preflight failed: gpu is unavailable")
        if dataset_file_count < 1:
            # formal 模式要求本地数据集至少包含一个 mp4 文件。
            raise RuntimeError("formal preflight failed: no mp4 files in local dataset")
        if not all_model_dirs_ready:
            # formal 模式要求必需模型目录完整。
            raise RuntimeError("formal preflight failed: required model directories are incomplete")

    return report

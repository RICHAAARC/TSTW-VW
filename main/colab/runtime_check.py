"""
文件用途：提供 Colab formal 运行前的环境预检。
File purpose: Provide runtime preflight checks for Colab formal execution.
Module type: General module
"""

from __future__ import annotations

import importlib
import sys
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


def _probe_module(module_name: str) -> tuple[bool, str]:
    """功能：探测 Python 模块是否可导入并读取版本。

    Probe whether a Python module can be imported and expose its version.

    Args:
        module_name: Module import name.

    Returns:
        A tuple of (imported, version).
    """
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return False, ""
    return True, str(getattr(module, "__version__", "") or "")


def _probe_torch_runtime() -> dict[str, Any]:
    """功能：探测 torch、CUDA、GPU 名称与显存信息。

    Probe torch, CUDA, GPU name, and GPU memory information.

    Args:
        None.

    Returns:
        A dictionary containing torch runtime details.
    """
    torch_imported = False
    torch_version = ""
    cuda_available = False
    gpu_name = ""
    gpu_memory_mb: int | None = None

    try:
        torch = importlib.import_module("torch")
        torch_imported = True
        torch_version = str(getattr(torch, "__version__", "") or "")
        cuda = getattr(torch, "cuda", None)
        if cuda is not None:
            cuda_available = bool(cuda.is_available())
            if cuda_available:
                try:
                    gpu_name = str(cuda.get_device_name(0) or "")
                except Exception:
                    gpu_name = ""
                try:
                    device_properties = cuda.get_device_properties(0)
                    total_memory = int(getattr(device_properties, "total_memory", 0) or 0)
                    if total_memory > 0:
                        gpu_memory_mb = total_memory // (1024 * 1024)
                except Exception:
                    gpu_memory_mb = None
    except Exception:
        torch_imported = False

    return {
        "torch_imported": torch_imported,
        "torch_version": torch_version,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "gpu_memory_mb": gpu_memory_mb,
    }


def _probe_command_version(command: list[str]) -> str:
    """功能：读取外部命令的版本首行。

    Read the first version line of an external command.

    Args:
        command: Command and arguments.

    Returns:
        The first output line, or an empty string on failure.
    """
    try:
        output = subprocess.check_output(command, text=True)
    except Exception:
        return ""
    return output.splitlines()[0].strip() if output else ""


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
    python_version = sys.version.split()[0]
    ffmpeg_path = shutil.which("ffmpeg")
    ffmpeg_available = ffmpeg_path is not None
    ffmpeg_version = _probe_command_version([ffmpeg_path, "-version"]) if ffmpeg_path else ""
    tar_zstd_available = _has_tar_zstd_support()
    nvidia_smi_available = shutil.which("nvidia-smi") is not None

    torch_runtime = _probe_torch_runtime()
    gpu_name = torch_runtime["gpu_name"]
    gpu_memory_mb = torch_runtime["gpu_memory_mb"]

    if not gpu_name and nvidia_smi_available:
        try:
            gpu_name = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                text=True,
            ).strip()
        except Exception:
            gpu_name = ""

    dependency_versions: dict[str, str] = {}
    dependency_imports: dict[str, bool] = {}
    for module_name in ("diffusers", "lpips", "cv2", "skimage"):
        imported, version = _probe_module(module_name)
        dependency_imports[module_name] = imported
        dependency_versions[module_name] = version

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
        "python_version": python_version,
        "torch_imported": torch_runtime["torch_imported"],
        "torch_version": torch_runtime["torch_version"],
        "cuda_available": torch_runtime["cuda_available"],
        "gpu_name": gpu_name or "not_available",
        "gpu_memory_mb": gpu_memory_mb,
        "run_mode": run_mode,
        "ffmpeg_available": ffmpeg_available,
        "ffmpeg_version": ffmpeg_version,
        "tar_zstd_available": tar_zstd_available,
        "nvidia_smi_available": nvidia_smi_available,
        "dataset_exists": dataset_path.exists(),
        "dataset_mp4_count": dataset_file_count,
        "model_dirs": model_dir_status,
        "dependency_imports": dependency_imports,
        "dependency_versions": dependency_versions,
    }

    if run_mode == "formal":
        if not ffmpeg_available:
            # formal 模式必须可用 ffmpeg。
            raise RuntimeError("formal preflight failed: ffmpeg is unavailable")
        if not ffmpeg_version:
            # formal 模式必须能读取 ffmpeg 版本。
            raise RuntimeError("formal preflight failed: ffmpeg version is unavailable")
        if not tar_zstd_available:
            # formal 模式必须支持 tar --zstd。
            raise RuntimeError("formal preflight failed: tar --zstd is unavailable")
        if not torch_runtime["torch_imported"]:
            # formal 模式必须可导入 torch。
            raise RuntimeError("formal preflight failed: torch is unavailable")
        if not torch_runtime["cuda_available"]:
            # formal 模式必须检测到 GPU。
            raise RuntimeError("formal preflight failed: cuda is unavailable")
        if not gpu_name:
            # formal 模式必须检测到 GPU 名称。
            raise RuntimeError("formal preflight failed: gpu name is unavailable")
        if gpu_memory_mb is None or gpu_memory_mb <= 0:
            # formal 模式必须能读取 GPU 显存。
            raise RuntimeError("formal preflight failed: gpu memory is unavailable")
        missing_dependencies = [
            module_name for module_name, imported in dependency_imports.items() if not imported
        ]
        if missing_dependencies:
            # formal 模式必须具备完整的依赖导入能力。
            raise RuntimeError(
                "formal preflight failed: required python dependencies are unavailable: "
                + ", ".join(missing_dependencies)
            )
        if dataset_file_count < 1:
            # formal 模式要求本地数据集至少包含一个 mp4 文件。
            raise RuntimeError("formal preflight failed: no mp4 files in local dataset")
        if not all_model_dirs_ready:
            # formal 模式要求必需模型目录完整。
            raise RuntimeError("formal preflight failed: required model directories are incomplete")

    return report

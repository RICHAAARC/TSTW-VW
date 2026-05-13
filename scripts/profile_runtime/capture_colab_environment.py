"""
文件用途：捕获 Colab 或本地运行环境快照并写入 runtime_profile 目录。
File purpose: Capture a Colab or local runtime environment snapshot into runtime_profile outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import importlib
import platform
import shutil
import subprocess
import sys
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from scripts.profile_runtime import ensure_runtime_profile_dir, iso_timestamp_utc, write_json_file


DEPENDENCY_PACKAGE_MAP = {
    "diffusers": "diffusers",
    "lpips": "lpips",
    "cv2": "opencv-python",
    "skimage": "scikit-image",
    "imageio": "imageio",
    "numpy": "numpy",
    "pandas": "pandas",
}


def _probe_dependency(module_name: str, package_name: str) -> tuple[bool, str]:
    """功能：检测依赖导入与版本信息。

    Probe dependency import availability and its version.

    Args:
        module_name: Python import name.
        package_name: Installed package name.

    Returns:
        A tuple containing the import status and resolved version string.
    """
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return False, ""

    try:
        version = importlib_metadata.version(package_name)
    except Exception:
        version = str(getattr(module, "__version__", "") or "")
    return True, version


def _probe_torch_runtime() -> dict[str, Any]:
    """功能：检测 torch 与 CUDA 运行时信息。

    Probe torch and CUDA runtime information.

    Args:
        None.

    Returns:
        A normalized torch runtime payload.
    """
    payload: dict[str, Any] = {
        "torch_imported": False,
        "torch_version": "",
        "cuda_available": False,
        "cuda_device_count": 0,
        "gpu_name": None,
        "gpu_memory_mb": None,
    }
    try:
        torch = importlib.import_module("torch")
    except Exception:
        return payload

    payload["torch_imported"] = True
    payload["torch_version"] = str(getattr(torch, "__version__", "") or "")
    cuda = getattr(torch, "cuda", None)
    if cuda is None:
        return payload

    try:
        payload["cuda_available"] = bool(cuda.is_available())
    except Exception:
        payload["cuda_available"] = False
        return payload

    if not payload["cuda_available"]:
        return payload

    try:
        payload["cuda_device_count"] = int(cuda.device_count())
    except Exception:
        payload["cuda_device_count"] = 0

    if payload["cuda_device_count"] < 1:
        return payload

    try:
        payload["gpu_name"] = str(cuda.get_device_name(0) or "")
    except Exception:
        payload["gpu_name"] = None

    try:
        device_properties = cuda.get_device_properties(0)
        total_memory = int(getattr(device_properties, "total_memory", 0) or 0)
        if total_memory > 0:
            payload["gpu_memory_mb"] = total_memory // (1024 * 1024)
    except Exception:
        payload["gpu_memory_mb"] = None
    return payload


def _probe_command(command_name: str, version_args: list[str]) -> tuple[bool, str]:
    """功能：检测外部命令及其版本首行。

    Probe an external command and return the first version line.

    Args:
        command_name: Command executable name.
        version_args: Command version arguments.

    Returns:
        A tuple containing availability and version line.
    """
    command_path = shutil.which(command_name)
    if command_path is None:
        return False, ""
    try:
        output = subprocess.check_output(
            [command_path, *version_args],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return True, ""
    first_line = output.splitlines()[0].strip() if output else ""
    return True, first_line


def _has_tar_zstd_support() -> bool:
    """功能：检测 tar 是否支持 --zstd。

    Detect whether tar supports the --zstd option.

    Args:
        None.

    Returns:
        True when tar --zstd is available; otherwise False.
    """
    tar_path = shutil.which("tar")
    if tar_path is None:
        return False
    try:
        help_text = subprocess.check_output(
            [tar_path, "--help"],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return False
    return "--zstd" in help_text


def _probe_ram() -> tuple[float | None, float | None]:
    """功能：检测 RAM 总量与可用量。

    Probe total and available RAM information.

    Args:
        None.

    Returns:
        A tuple of (total_gb, available_gb).
    """
    try:
        psutil = importlib.import_module("psutil")
    except Exception:
        return None, None

    try:
        virtual_memory = psutil.virtual_memory()
    except Exception:
        return None, None
    total_gb = round(float(virtual_memory.total) / (1024**3), 3)
    available_gb = round(float(virtual_memory.available) / (1024**3), 3)
    return total_gb, available_gb


def _probe_git_state(working_directory: Path) -> tuple[str | None, str]:
    """功能：检测 git commit 与工作区状态。

    Probe the git commit and short working-tree status.

    Args:
        working_directory: Working directory to inspect.

    Returns:
        A tuple of (git_commit, git_status_short).
    """
    git_path = shutil.which("git")
    if git_path is None:
        return None, ""
    try:
        git_commit = subprocess.check_output(
            [git_path, "-C", str(working_directory), "rev-parse", "HEAD"],
            text=True,
            encoding="utf-8",
            errors="replace",
        ).strip()
    except Exception:
        git_commit = None
    try:
        git_status_short = subprocess.check_output(
            [git_path, "-C", str(working_directory), "status", "--short"],
            text=True,
            encoding="utf-8",
            errors="replace",
        ).strip()
    except Exception:
        git_status_short = ""
    return git_commit, git_status_short


def capture_colab_environment(
    *,
    run_root: str | Path,
    run_id: str,
    run_mode: str,
    runtime_profile: str,
    output_json: str | Path,
    fail_on_missing_required: bool = False,
) -> dict[str, Any]:
    """功能：捕获运行环境快照并写入 JSON。

    Capture the current runtime environment snapshot and persist it to JSON.

    Args:
        run_root: Run-root path.
        run_id: Run identifier.
        run_mode: Runtime mode label.
        runtime_profile: Runtime profile label.
        output_json: Output JSON path.
        fail_on_missing_required: Whether missing required tools should raise an error.

    Returns:
        The captured runtime environment payload.

    Raises:
        RuntimeError: Raised when fail_on_missing_required is enabled and required probes fail.
    """
    run_root_path = Path(run_root)
    runtime_profile_dir = ensure_runtime_profile_dir(run_root_path)
    working_directory = Path.cwd()
    torch_payload = _probe_torch_runtime()
    ffmpeg_available, ffmpeg_version = _probe_command("ffmpeg", ["-version"])
    nvidia_smi_available, _ = _probe_command("nvidia-smi", ["--help"])
    tar_zstd_available = _has_tar_zstd_support()
    ram_total_gb, ram_available_gb = _probe_ram()
    dependency_imports: dict[str, bool] = {}
    dependency_versions: dict[str, str] = {}
    for module_name, package_name in DEPENDENCY_PACKAGE_MAP.items():
        imported, version = _probe_dependency(module_name, package_name)
        dependency_imports[module_name] = imported
        dependency_versions[module_name] = version

    disk_usage = shutil.disk_usage(run_root_path if run_root_path.exists() else working_directory)
    disk_free_gb = round(float(disk_usage.free) / (1024**3), 3)
    git_commit, git_status_short = _probe_git_state(working_directory)

    payload = {
        "status": True,
        "run_id": run_id,
        "run_mode": run_mode,
        "runtime_profile": runtime_profile,
        "timestamp_utc": iso_timestamp_utc(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "working_directory": str(working_directory),
        "torch_imported": torch_payload["torch_imported"],
        "torch_version": torch_payload["torch_version"],
        "cuda_available": torch_payload["cuda_available"],
        "cuda_device_count": torch_payload["cuda_device_count"],
        "gpu_name": torch_payload["gpu_name"],
        "gpu_memory_mb": torch_payload["gpu_memory_mb"],
        "nvidia_smi_available": nvidia_smi_available,
        "ffmpeg_available": ffmpeg_available,
        "ffmpeg_version": ffmpeg_version,
        "tar_zstd_available": tar_zstd_available,
        "dependency_imports": dependency_imports,
        "dependency_versions": dependency_versions,
        "disk_free_gb": disk_free_gb,
        "ram_total_gb": ram_total_gb,
        "ram_available_gb": ram_available_gb,
        "git_commit": git_commit,
        "git_status_short": git_status_short,
        "output_json": str(Path(output_json)),
        "runtime_profile_dir": str(runtime_profile_dir),
    }

    missing_required: list[str] = []
    if fail_on_missing_required:
        if not ffmpeg_available:
            missing_required.append("ffmpeg")
        if not tar_zstd_available:
            missing_required.append("tar --zstd")
        if not dependency_imports.get("diffusers", False):
            missing_required.append("diffusers")
        if run_mode == "formal" and not torch_payload["cuda_available"]:
            missing_required.append("cuda")
    if missing_required:
        payload["status"] = False
        payload["missing_required"] = missing_required
        write_json_file(output_json, payload)
        # 当前显式要求 fail-fast 时，缺失关键依赖必须抛出异常。
        raise RuntimeError(
            "required runtime probes are unavailable: " + ", ".join(missing_required)
        )

    write_json_file(output_json, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    """功能：执行环境快照 CLI。

    Execute the runtime environment snapshot CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Capture the Colab or local runtime environment snapshot.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-mode", required=True)
    parser.add_argument("--runtime-profile", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument(
        "--fail-on-missing-required",
        action="store_true",
    )
    args = parser.parse_args(argv)
    capture_colab_environment(
        run_root=args.run_root,
        run_id=args.run_id,
        run_mode=args.run_mode,
        runtime_profile=args.runtime_profile,
        output_json=args.output_json,
        fail_on_missing_required=args.fail_on_missing_required,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

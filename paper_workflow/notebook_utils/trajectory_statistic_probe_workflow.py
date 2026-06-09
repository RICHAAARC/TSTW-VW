"""
文件用途：为 Colab notebook 提供阶段 3 trajectory statistic probe 调度工具。
File purpose: Provide Colab notebook utilities for the trajectory statistic probe.
Module type: Notebook utility module
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from typing import Any


def prepare_repository_environment(repository_root: str | Path) -> dict[str, str]:
    """功能：构建调用仓库 CLI 所需的最小环境变量。

    该函数属于通用工程写法。notebook 只负责 session 调度, 因此所有子进程都显式设置
    `PYTHONPATH`、`PYTHONUTF8` 和 `PYTHONIOENCODING`, 避免 Colab / Windows / Linux shell
    差异影响仓库模块读取 UTF-8 文本。
    """
    root_path = Path(repository_root).resolve()
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(root_path)
        if not existing_pythonpath
        else str(root_path) + os.pathsep + existing_pythonpath
    )
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def extract_frozen_baseline_package(
    package_path: str | Path,
    extract_root: str | Path,
) -> Path:
    """功能：解压阶段 2 frozen baseline zip package 并返回 run root。

    当前 helper 只支持 `.zip`, 因为 Colab 标准 Python 可直接解压 zip。若用户只有
    `.tar.zst`, 应优先在阶段 2 notebook 中同时保留 zip package, 或在 Colab 中安装 zstd
    后手动解压。
    """
    package = Path(package_path).expanduser()
    if not package.exists():
        raise FileNotFoundError(package)
    if package.suffix.lower() != ".zip":
        raise ValueError("stage 2 frozen baseline package must be a .zip file")

    output_root = Path(extract_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as zip_file:
        zip_file.extractall(output_root)

    candidates = [
        path
        for path in output_root.iterdir()
        if path.is_dir()
        and (path / "records" / "event_scores.jsonl").exists()
        and (path / "artifacts" / "stage2_mechanism_decision.json").exists()
    ]
    if len(candidates) != 1:
        raise ValueError(
            "expected exactly one extracted frozen baseline run root, "
            f"found {len(candidates)}"
        )
    return candidates[0]


def run_formal_replay_cli(
    repository_root: str | Path,
    frozen_baseline_root: str | Path,
    output_root: str | Path,
    runtime_profile: str,
    samples_per_role: int,
) -> dict[str, Any]:
    """功能：调用仓库阶段 3 replay CLI 并读取机制决策。

    该函数是 notebook 到 repository module 的边界。它不直接写 records、thresholds 或
    tables, 这些正式输出只能由 `formal_replay_cli` 和 runner 生成。
    """
    root_path = Path(repository_root).resolve()
    output_path = Path(output_root)
    if output_path.exists():
        shutil.rmtree(output_path)
    command = [
        "python",
        "-m",
        "experiments.trajectory_statistic_probe.formal_replay_cli",
        "--repository-root",
        str(root_path),
        "--frozen-baseline-root",
        str(Path(frozen_baseline_root)),
        "--output-root",
        str(output_path),
        "--runtime-profile",
        runtime_profile,
        "--samples-per-role",
        str(samples_per_role),
    ]
    subprocess.run(
        command,
        cwd=root_path,
        env=prepare_repository_environment(root_path),
        check=True,
    )
    decision_path = output_path / "artifacts" / "trajectory_mechanism_decision.json"
    return json.loads(decision_path.read_text(encoding="utf-8"))


def package_trajectory_probe_run(
    run_root: str | Path,
    package_root: str | Path,
    package_name: str,
) -> Path:
    """功能：把阶段 3 run root 打包为 zip, 便于从 Google Drive 手动下载。

    该函数只对已经由仓库 runner 生成的 run root 做整体归档, 不手工拼接正式表格或记录。
    """
    run_path = Path(run_root)
    if not run_path.exists():
        raise FileNotFoundError(run_path)
    output_root = Path(package_root)
    output_root.mkdir(parents=True, exist_ok=True)
    archive_base = output_root / package_name
    archive_path = Path(
        shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=run_path.parent,
            base_dir=run_path.name,
        )
    )
    return archive_path

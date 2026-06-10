"""
文件用途: 为 Colab notebook 提供 trajectory-aware sampling probe 调度工具。
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
    """功能: 构建 notebook 调用仓库 CLI 所需的 UTF-8 Python 环境。

    该函数属于通用工程写法。notebook 只负责 session 调度, 所有正式 scaffold 产物都由仓库模块生成。
    显式设置 `PYTHONPATH`、`PYTHONUTF8` 和 `PYTHONIOENCODING` 可以减少 Colab 与本地环境差异。
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


def find_latest_trajectory_probe_root(stage3_result_root: str | Path) -> Path:
    """功能: 在 Google Drive 结果目录中查找最新的阶段 3 输出根目录。

    查找条件是目录中存在 `records/event_scores.jsonl` 和 `artifacts/trajectory_mechanism_decision.json`。
    这是项目特定的 handoff 约定, 用于让 sampling scaffold 复用阶段 3 formal 产物。
    """
    root_path = Path(stage3_result_root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)
    candidates = [
        path
        for path in root_path.iterdir()
        if path.is_dir()
        and (path / "records" / "event_scores.jsonl").exists()
        and (path / "artifacts" / "trajectory_mechanism_decision.json").exists()
    ]
    if not candidates:
        raise FileNotFoundError(
            "no trajectory statistic probe run root found under "
            f"{root_path}"
        )
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[0]


def find_latest_trajectory_probe_package(stage3_result_root: str | Path) -> Path:
    """功能: 在 Google Drive 结果目录中查找最新的阶段 3 zip package。"""
    root_path = Path(stage3_result_root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)
    candidates = sorted(
        root_path.glob("*/packages/trajectory_statistic_probe_formal_gpu_validation_*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            "no trajectory statistic probe zip package found under "
            f"{root_path}"
        )
    return candidates[0]


def extract_trajectory_probe_package(
    package_path: str | Path,
    extract_root: str | Path,
) -> Path:
    """功能: 解压阶段 3 zip package 并返回其中的 run root。

    该 helper 只处理整体 package handoff, 不直接修改 records 或正式报告。正式 sampling scaffold 仍由仓库 CLI 生成。
    """
    package = Path(package_path).expanduser()
    if not package.exists():
        raise FileNotFoundError(package)
    if package.suffix.lower() != ".zip":
        raise ValueError("trajectory probe package must be a .zip file")

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
        and (path / "artifacts" / "trajectory_mechanism_decision.json").exists()
    ]
    if len(candidates) != 1:
        raise ValueError(
            "expected exactly one extracted trajectory probe run root, "
            f"found {len(candidates)}"
        )
    return candidates[0]


def run_sampling_scaffold_cli(
    repository_root: str | Path,
    upstream_trajectory_root: str | Path,
    output_root: str | Path,
    sampling_config_path: str | Path = "configs/protocol/trajectory_aware_sampling_probe.json",
) -> dict[str, Any]:
    """功能: 调用 trajectory-aware sampling scaffold CLI 并读取 policy manifest。

    该函数是 notebook 到 repository module 的边界。notebook 不直接写 readiness、selection plan、manifest 或 report,
    这些产物只由 `experiments.trajectory_aware_sampling_probe.scaffold_cli` 和 runner 生成。
    """
    root_path = Path(repository_root).resolve()
    output_path = Path(output_root)
    if output_path.exists():
        shutil.rmtree(output_path)
    command = [
        "python",
        "-m",
        "experiments.trajectory_aware_sampling_probe.scaffold_cli",
        "--repository-root",
        str(root_path),
        "--upstream-trajectory-root",
        str(Path(upstream_trajectory_root)),
        "--output-root",
        str(output_path),
        "--sampling-config-path",
        str(Path(sampling_config_path)),
    ]
    subprocess.run(
        command,
        cwd=root_path,
        env=prepare_repository_environment(root_path),
        check=True,
    )
    manifest_path = output_path / "artifacts" / "sampling_policy_manifest.json"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def read_gpu_validation_contract(run_root: str | Path) -> dict[str, Any]:
    """鍔熻兘: 璇诲彇 runner 鐢熸垚鐨勭湡瀹?GPU 楠岃瘉鍚堝悓銆?

    璇ュ嚱鏁板彧妫€鏌ュ苟璇诲彇 repository runner 宸茬粡钀藉湴鐨?contract artifact銆?
    notebook 浣跨敤瀹冩潵鏄剧ず涓嬩竴姝ラ渶瑕佺殑 GPU 楠岃瘉杈圭晫, 涓嶇洿鎺ョ敓鎴愭寮忓崗璁骇鐗┿€?
    """
    contract_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_gpu_validation_contract.json"
    )
    if not contract_path.exists():
        raise FileNotFoundError(contract_path)
    return json.loads(contract_path.read_text(encoding="utf-8"))


def read_backend_transition_guard(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取 runner 生成的后端切换前治理守卫。

    该 helper 只负责读取已落盘 artifact, 便于 notebook 在最终摘要中明确提示:
    下一步不是直接接入真实后端, 而是需要单独的 backend-transition 决策。
    """
    guard_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_backend_transition_guard.json"
    )
    if not guard_path.exists():
        raise FileNotFoundError(guard_path)
    return json.loads(guard_path.read_text(encoding="utf-8"))


def read_backend_transition_decision(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取 runner 生成的显式后端切换决策。

    该 helper 只读取 repository runner 产物。当前决策只允许真实 GPU runtime
    接口脚手架, 不允许 notebook 直接启用真实生成或真实 watermark 后端。
    """
    decision_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_backend_transition_decision.json"
    )
    if not decision_path.exists():
        raise FileNotFoundError(decision_path)
    return json.loads(decision_path.read_text(encoding="utf-8"))


def read_runtime_interface_scaffold(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取真实 GPU runtime 接口脚手架产物。

    该 helper 只读取 repository runner 写出的接口 schema artifact。当前 artifact
    只描述后续真实 GPU runtime 的请求和结果边界, 不代表 notebook 已连接真实后端。
    """
    scaffold_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_runtime_interface_scaffold.json"
    )
    if not scaffold_path.exists():
        raise FileNotFoundError(scaffold_path)
    return json.loads(scaffold_path.read_text(encoding="utf-8"))


def read_runtime_interface_implementation(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取非后端连接版 runtime interface implementation 产物。

    该 helper 只读取 repository runner 写出的 dry-run artifact, 用于 notebook 汇总接口实现层状态。
    它不连接真实生成后端, 不生成视频, 不执行 watermark 嵌入或检测。
    """
    implementation_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_runtime_interface_implementation.json"
    )
    if not implementation_path.exists():
        raise FileNotFoundError(implementation_path)
    return json.loads(implementation_path.read_text(encoding="utf-8"))


def read_backend_integration_decision(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取 backend integration decision gate 产物。

    该 helper 只读取 repository runner 已经生成的决策 artifact, 便于 notebook 显示下一步是否可以构建
    backend adapter scaffold。它不连接真实生成后端, 不生成视频, 也不执行 watermark 算法。
    """
    decision_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_backend_integration_decision.json"
    )
    if not decision_path.exists():
        raise FileNotFoundError(decision_path)
    return json.loads(decision_path.read_text(encoding="utf-8"))


def read_backend_adapter_scaffold(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取 backend adapter scaffold 产物。

    该 helper 只读取 repository runner 生成的 schema-only scaffold artifact。它用于 notebook 展示 adapter
    配置 schema、请求转换 schema、结果归一化 schema 和失败 manifest schema 是否已经冻结。
    它不连接真实后端, 不生成视频, 也不执行 watermark 算法。
    """
    scaffold_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_backend_adapter_scaffold.json"
    )
    if not scaffold_path.exists():
        raise FileNotFoundError(scaffold_path)
    return json.loads(scaffold_path.read_text(encoding="utf-8"))


def package_sampling_probe_run(
    run_root: str | Path,
    package_root: str | Path,
    package_name: str,
) -> Path:
    """功能: 将 sampling scaffold run root 整体打包为 zip 供 Google Drive 下载。

    该函数只归档仓库 runner 已生成的 run root, 不手工拼接正式 scaffold 产物。
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

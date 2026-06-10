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
import urllib.request


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


def read_backend_connection_contract(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取 backend connection contract 产物。

    该 helper 只读取 repository runner 生成的 contract artifact。该 artifact 表示下一步可以进入真实后端
    smoke 的前置合同已经准备好, 但当前 notebook cell 本身不连接真实后端、不生成视频、不执行 watermark。
    """
    contract_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_backend_connection_contract.json"
    )
    if not contract_path.exists():
        raise FileNotFoundError(contract_path)
    return json.loads(contract_path.read_text(encoding="utf-8"))


def read_real_backend_connection_smoke(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取真实后端连接 smoke 执行请求 gate 产物。

    该 helper 只读取 repository runner 生成的 smoke request artifact。该 artifact 表示下一步需要在真实
    GPU 环境中执行 smoke, 但当前 notebook 的 scaffold 流程本身不连接真实后端、不生成视频、不执行 watermark。
    """
    smoke_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_real_backend_connection_smoke.json"
    )
    if not smoke_path.exists():
        raise FileNotFoundError(smoke_path)
    return json.loads(smoke_path.read_text(encoding="utf-8"))


def read_real_backend_connection_smoke_handoff(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取真实 GPU smoke 的外部执行 handoff artifact。

    该 helper 只读取 repository runner 已经写出的 handoff 文件, 用于 notebook 明确下一步需要在 Colab 或同等真实 GPU 环境中执行。
    它不连接真实后端, 不生成视频, 也不执行 watermark 算法。
    """
    handoff_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_real_backend_connection_smoke_handoff.json"
    )
    if not handoff_path.exists():
        raise FileNotFoundError(handoff_path)
    return json.loads(handoff_path.read_text(encoding="utf-8"))


def write_environment_only_real_gpu_backend_connection_smoke_results(
    repository_root: str | Path,
    output_path: str | Path,
    backend_connection_probe_config_path: str | Path | None = None,
) -> dict[str, Any]:
    """功能: 在 Colab 中生成环境级真实 GPU smoke 结果摘要。

    该 helper 只采集 GPU 可见性、Python 依赖可导入性、仓库提交信息和失败清单。
    它不会连接真实 DiT / Flow Matching 后端, 不会生成真实视频, 也不会执行 watermark 算法。
    因此在当前没有真实后端连接执行器时, 它会产出可检查但通常不会通过 result gate 的 `INCONCLUSIVE` 结果。
    """
    root_path = Path(repository_root).resolve()
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    gpu_detected = _command_succeeds(["nvidia-smi"])
    torch_cuda_available = _torch_cuda_available()
    dependency_checks = {
        "torch": _module_importable("torch"),
        "pytest": _module_importable("pytest"),
    }
    backend_dependencies_resolved = all(dependency_checks.values())
    model_identity_recorded = _command_succeeds(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=root_path,
    )
    probe_result = _run_backend_connection_probe(backend_connection_probe_config_path)
    failure_reasons = []
    if not gpu_detected:
        failure_reasons.append("external_gpu_runtime_not_detected")
    if not torch_cuda_available:
        failure_reasons.append("torch_cuda_not_available")
    if not backend_dependencies_resolved:
        failure_reasons.append("external_backend_dependencies_not_resolved")
    failure_reasons.extend(probe_result["failure_reasons"])
    smoke_passed = (
        gpu_detected
        and torch_cuda_available
        and backend_dependencies_resolved
        and model_identity_recorded
        and probe_result["external_real_backend_connection_attempted"]
        and probe_result["external_real_backend_connection_succeeded"]
    )

    external_results = {
        "external_smoke_result_status": "PASS" if smoke_passed else "INCONCLUSIVE",
        "external_gpu_runtime_detected": gpu_detected,
        "external_model_identity_recorded": model_identity_recorded,
        "external_backend_dependencies_resolved": backend_dependencies_resolved,
        "external_real_backend_connection_attempted": probe_result["external_real_backend_connection_attempted"],
        "external_real_backend_connection_succeeded": probe_result["external_real_backend_connection_succeeded"],
        "external_real_generation_attempted": False,
        "external_real_watermark_integration_attempted": False,
        "runtime_failure_manifest": {
            "failure_manifest_recorded": True,
            "failure_count": len(failure_reasons),
        },
        "result_artifacts": [
            {
                "result_artifact_kind": "runtime_environment_snapshot",
                "result_artifact_status": "present",
                "formal_claim_support_allowed": False,
            },
            {
                "result_artifact_kind": "model_identity_record",
                "result_artifact_status": "present" if model_identity_recorded else "incomplete",
                "formal_claim_support_allowed": False,
            },
            {
                "result_artifact_kind": "backend_dependency_resolution_record",
                "result_artifact_status": "present" if backend_dependencies_resolved else "incomplete",
                "formal_claim_support_allowed": False,
            },
            {
                "result_artifact_kind": "single_request_execution_record",
                "result_artifact_status": "present" if probe_result["external_real_backend_connection_attempted"] else "not_attempted_by_governance",
                "formal_claim_support_allowed": False,
            },
            {
                "result_artifact_kind": "runtime_failure_manifest",
                "result_artifact_status": "present",
                "formal_claim_support_allowed": False,
            },
        ],
    }
    output_file.write_text(
        json.dumps(external_results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return external_results


def write_default_backend_connection_probe_config(
    output_path: str | Path,
) -> Path:
    """功能: 写出 notebook 一键运行所需的默认非生成式后端连接探针配置.

    该函数属于项目特定的 Colab 调度辅助逻辑. 它只生成一个可审计的 `python_import`
    探针配置, 用于验证真实 GPU session 中最基础的运行时入口是否可达.
    该配置不会触发真实视频生成, 不会执行真实 watermark, 也不会接入真实 DiT /
    Flow Matching / VAE 生成管线.
    """
    config_path = Path(output_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_payload = {
        "backend_probe_kind": "python_import",
        "module_name": "torch",
        "callable_name": "cuda",
        "default_probe_scope": "non_generative_runtime_import_only",
        "real_generation_enabled": False,
        "real_watermark_integration_enabled": False,
    }
    config_path.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return config_path


def _run_backend_connection_probe(
    backend_connection_probe_config_path: str | Path | None,
) -> dict[str, Any]:
    """功能: 执行非生成式后端连接探针。

    该函数只验证后端入口是否可达, 不发送视频生成请求, 不执行 watermark, 也不加载项目内真实生成 pipeline。
    当前支持 `python_import` 和 `http_health_endpoint` 两类探针。
    """
    if backend_connection_probe_config_path is None:
        return {
            "external_real_backend_connection_attempted": False,
            "external_real_backend_connection_succeeded": False,
            "failure_reasons": ["real_backend_connection_probe_config_not_provided"],
        }
    config_path = Path(backend_connection_probe_config_path)
    if not config_path.exists():
        return {
            "external_real_backend_connection_attempted": False,
            "external_real_backend_connection_succeeded": False,
            "failure_reasons": ["real_backend_connection_probe_config_not_found"],
        }
    config = json.loads(config_path.read_text(encoding="utf-8"))
    probe_kind = str(config.get("backend_probe_kind", "")).strip()
    if probe_kind == "python_import":
        return _run_python_import_backend_probe(config)
    if probe_kind == "http_health_endpoint":
        return _run_http_health_backend_probe(config)
    return {
        "external_real_backend_connection_attempted": False,
        "external_real_backend_connection_succeeded": False,
        "failure_reasons": ["unsupported_backend_connection_probe_kind"],
    }


def _run_python_import_backend_probe(config: dict[str, Any]) -> dict[str, Any]:
    module_name = str(config.get("module_name", "")).strip()
    callable_name = str(config.get("callable_name", "")).strip()
    if not module_name:
        return {
            "external_real_backend_connection_attempted": False,
            "external_real_backend_connection_succeeded": False,
            "failure_reasons": ["backend_probe_module_name_missing"],
        }
    try:
        module = __import__(module_name, fromlist=[callable_name] if callable_name else [])
        if callable_name:
            getattr(module, callable_name)
    except Exception:
        return {
            "external_real_backend_connection_attempted": True,
            "external_real_backend_connection_succeeded": False,
            "failure_reasons": ["backend_python_import_probe_failed"],
        }
    return {
        "external_real_backend_connection_attempted": True,
        "external_real_backend_connection_succeeded": True,
        "failure_reasons": [],
    }


def _run_http_health_backend_probe(config: dict[str, Any]) -> dict[str, Any]:
    url = str(config.get("http_health_url", "")).strip()
    timeout_seconds = float(config.get("timeout_seconds", 10.0))
    if not url:
        return {
            "external_real_backend_connection_attempted": False,
            "external_real_backend_connection_succeeded": False,
            "failure_reasons": ["backend_probe_http_health_url_missing"],
        }
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            succeeded = 200 <= int(response.status) < 300
    except Exception:
        return {
            "external_real_backend_connection_attempted": True,
            "external_real_backend_connection_succeeded": False,
            "failure_reasons": ["backend_http_health_probe_failed"],
        }
    return {
        "external_real_backend_connection_attempted": True,
        "external_real_backend_connection_succeeded": succeeded,
        "failure_reasons": [] if succeeded else ["backend_http_health_probe_not_successful"],
    }


def _command_succeeds(command: list[str], cwd: Path | None = None) -> bool:
    try:
        subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        return False
    return True


def _module_importable(module_name: str) -> bool:
    try:
        __import__(module_name)
    except Exception:
        return False
    return True


def _torch_cuda_available() -> bool:
    try:
        import torch
    except Exception:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def read_external_real_gpu_backend_connection_smoke_results(
    external_smoke_results_path: str | Path,
) -> dict[str, Any]:
    """功能: 读取外部真实 GPU backend connection smoke 结果摘要。

    该 helper 只读取 Colab 或同等真实 GPU 环境已经落盘的 JSON 结果摘要。它不连接真实后端,
    不生成视频, 也不执行 watermark 算法。通过把读取逻辑集中在 helper 中, notebook 可以保持调度入口属性。
    """
    results_path = Path(external_smoke_results_path)
    if not results_path.exists():
        raise FileNotFoundError(results_path)
    return json.loads(results_path.read_text(encoding="utf-8"))


def run_real_gpu_backend_connection_smoke_result_gate(
    repository_root: str | Path,
    run_root: str | Path,
    external_smoke_results_path: str | Path,
    result_gate_config_path: str | Path = "configs/protocol/trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate.json",
) -> dict[str, Any]:
    """功能: 调用仓库 result gate 校验外部真实 GPU smoke 结果并写出 artifact。

    该函数属于 notebook 到 repository module 的边界。notebook 只提供外部结果路径和 run root,
    具体校验规则由 `experiments.trajectory_aware_sampling_probe.real_gpu_backend_connection_smoke_result_gate` 执行。
    该函数不会在本地连接真实后端, 不会生成真实视频, 也不会执行真实 watermark 集成。
    """
    from experiments.trajectory_aware_sampling_probe.output_layout import (
        build_trajectory_aware_sampling_probe_output_paths,
    )
    from experiments.trajectory_aware_sampling_probe.real_gpu_backend_connection_smoke_result_gate import (
        build_trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate,
    )

    root_path = Path(repository_root).resolve()
    config_path = Path(result_gate_config_path)
    if not config_path.is_absolute():
        config_path = root_path / config_path
    handoff_payload = read_real_backend_connection_smoke_handoff(run_root)
    external_results = read_external_real_gpu_backend_connection_smoke_results(
        external_smoke_results_path
    )
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    gate_payload = build_trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate(
        handoff_payload,
        external_results,
        config_payload,
    )
    gate_path = build_trajectory_aware_sampling_probe_output_paths(
        run_root
    ).real_gpu_backend_connection_smoke_result_gate_path
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return gate_payload


def read_real_gpu_backend_connection_smoke_result_gate(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取真实 GPU backend connection smoke 结果 gate artifact。"""
    gate_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate.json"
    )
    if not gate_path.exists():
        raise FileNotFoundError(gate_path)
    return json.loads(gate_path.read_text(encoding="utf-8"))


def run_real_backend_runtime_validation_gate(
    repository_root: str | Path,
    run_root: str | Path,
    runtime_validation_gate_config_path: str | Path = "configs/protocol/trajectory_aware_sampling_real_backend_runtime_validation_gate.json",
) -> dict[str, Any]:
    """功能: 调用真实后端 runtime validation gate 并写出 artifact 与报告补充.

    该 helper 属于 notebook 到 repository module 的调度边界. notebook 只提供
    路径, 具体 gate 判断、失败路径描述和报告段落均由 repository module 生成.
    该函数不连接真实后端, 不生成视频, 不执行真实 watermark.
    """
    from experiments.trajectory_aware_sampling_probe.output_layout import (
        build_trajectory_aware_sampling_probe_output_paths,
    )
    from experiments.trajectory_aware_sampling_probe.real_backend_runtime_validation_gate import (
        build_real_backend_runtime_validation_report_section,
        build_trajectory_aware_sampling_real_backend_runtime_validation_gate,
    )

    root_path = Path(repository_root).resolve()
    config_path = Path(runtime_validation_gate_config_path)
    if not config_path.is_absolute():
        config_path = root_path / config_path
    output_paths = build_trajectory_aware_sampling_probe_output_paths(run_root)
    real_gpu_result_gate = read_real_gpu_backend_connection_smoke_result_gate(run_root)
    backend_adapter_scaffold = read_backend_adapter_scaffold(run_root)
    backend_connection_contract = read_backend_connection_contract(run_root)
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    gate_payload = build_trajectory_aware_sampling_real_backend_runtime_validation_gate(
        real_gpu_result_gate,
        backend_adapter_scaffold,
        backend_connection_contract,
        config_payload,
    )
    output_paths.real_backend_runtime_validation_gate_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_paths.real_backend_runtime_validation_gate_path.write_text(
        json.dumps(gate_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_section = build_real_backend_runtime_validation_report_section(gate_payload)
    output_paths.sampling_probe_report_path.parent.mkdir(parents=True, exist_ok=True)
    existing_report = (
        output_paths.sampling_probe_report_path.read_text(encoding="utf-8")
        if output_paths.sampling_probe_report_path.exists()
        else ""
    )
    output_paths.sampling_probe_report_path.write_text(
        existing_report.rstrip() + report_section,
        encoding="utf-8",
    )
    return gate_payload


def read_real_backend_runtime_validation_gate(run_root: str | Path) -> dict[str, Any]:
    """功能: 读取真实后端 runtime validation gate artifact."""
    gate_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_real_backend_runtime_validation_gate.json"
    )
    if not gate_path.exists():
        raise FileNotFoundError(gate_path)
    return json.loads(gate_path.read_text(encoding="utf-8"))


def run_explicit_real_generation_transition_decision(
    repository_root: str | Path,
    run_root: str | Path,
    transition_decision_config_path: str | Path = "configs/protocol/trajectory_aware_sampling_explicit_real_generation_transition_decision.json",
) -> dict[str, Any]:
    """功能: 调用显式真实生成切换决策并写出 artifact 与报告补充.

    该 helper 只调度 repository module. 它不连接真实生成后端, 不生成视频,
    不执行真实 watermark. 当前阶段只允许生成单条受控请求的后续 scaffold 决策.
    """
    from experiments.trajectory_aware_sampling_probe.explicit_real_generation_transition_decision import (
        build_explicit_real_generation_transition_report_section,
        build_trajectory_aware_sampling_explicit_real_generation_transition_decision,
    )
    from experiments.trajectory_aware_sampling_probe.output_layout import (
        build_trajectory_aware_sampling_probe_output_paths,
    )

    root_path = Path(repository_root).resolve()
    config_path = Path(transition_decision_config_path)
    if not config_path.is_absolute():
        config_path = root_path / config_path
    output_paths = build_trajectory_aware_sampling_probe_output_paths(run_root)
    runtime_validation_gate = read_real_backend_runtime_validation_gate(run_root)
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    decision_payload = (
        build_trajectory_aware_sampling_explicit_real_generation_transition_decision(
            runtime_validation_gate,
            config_payload,
        )
    )
    output_paths.explicit_real_generation_transition_decision_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_paths.explicit_real_generation_transition_decision_path.write_text(
        json.dumps(decision_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_section = build_explicit_real_generation_transition_report_section(
        decision_payload
    )
    output_paths.sampling_probe_report_path.parent.mkdir(parents=True, exist_ok=True)
    existing_report = (
        output_paths.sampling_probe_report_path.read_text(encoding="utf-8")
        if output_paths.sampling_probe_report_path.exists()
        else ""
    )
    output_paths.sampling_probe_report_path.write_text(
        existing_report.rstrip() + report_section,
        encoding="utf-8",
    )
    return decision_payload


def read_explicit_real_generation_transition_decision(
    run_root: str | Path,
) -> dict[str, Any]:
    """功能: 读取显式真实生成切换决策 artifact."""
    decision_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_explicit_real_generation_transition_decision.json"
    )
    if not decision_path.exists():
        raise FileNotFoundError(decision_path)
    return json.loads(decision_path.read_text(encoding="utf-8"))


def run_controlled_single_real_generation_request_scaffold(
    repository_root: str | Path,
    run_root: str | Path,
    request_scaffold_config_path: str | Path = "configs/protocol/trajectory_aware_sampling_controlled_single_real_generation_request_scaffold.json",
) -> dict[str, Any]:
    """功能: 生成单条受控真实生成请求 scaffold 并写出报告补充.

    该 helper 只调度 repository module, 不连接真实生成后端, 不生成视频,
    不执行真实 watermark. 其产物用于下一步手动 GPU 执行前的请求边界检查.
    """
    from experiments.trajectory_aware_sampling_probe.controlled_single_real_generation_request_scaffold import (
        build_controlled_single_real_generation_request_scaffold_report_section,
        build_trajectory_aware_sampling_controlled_single_real_generation_request_scaffold,
    )
    from experiments.trajectory_aware_sampling_probe.output_layout import (
        build_trajectory_aware_sampling_probe_output_paths,
    )

    root_path = Path(repository_root).resolve()
    config_path = Path(request_scaffold_config_path)
    if not config_path.is_absolute():
        config_path = root_path / config_path
    output_paths = build_trajectory_aware_sampling_probe_output_paths(run_root)
    explicit_transition_decision = read_explicit_real_generation_transition_decision(
        run_root
    )
    selection_plan = json.loads(
        output_paths.sampling_selection_plan_path.read_text(encoding="utf-8")
    )
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    scaffold_payload = (
        build_trajectory_aware_sampling_controlled_single_real_generation_request_scaffold(
            explicit_transition_decision,
            selection_plan,
            config_payload,
        )
    )
    output_paths.controlled_single_real_generation_request_scaffold_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_paths.controlled_single_real_generation_request_scaffold_path.write_text(
        json.dumps(scaffold_payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    report_section = (
        build_controlled_single_real_generation_request_scaffold_report_section(
            scaffold_payload
        )
    )
    existing_report = (
        output_paths.sampling_probe_report_path.read_text(encoding="utf-8")
        if output_paths.sampling_probe_report_path.exists()
        else ""
    )
    output_paths.sampling_probe_report_path.write_text(
        existing_report.rstrip() + report_section,
        encoding="utf-8",
    )
    return scaffold_payload


def read_controlled_single_real_generation_request_scaffold(
    run_root: str | Path,
) -> dict[str, Any]:
    """功能: 读取单条受控真实生成请求 scaffold artifact."""
    scaffold_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_controlled_single_real_generation_request_scaffold.json"
    )
    if not scaffold_path.exists():
        raise FileNotFoundError(scaffold_path)
    return json.loads(scaffold_path.read_text(encoding="utf-8"))


def write_environment_only_manual_controlled_single_request_results(
    repository_root: str | Path,
    run_root: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """功能: 写出不执行真实生成的手动单请求结果摘要.

    该函数只记录 Colab GPU 环境、模型身份摘要和受控请求 digest 绑定. 它不会调用真实视频
    生成后端, 不会执行真实 watermark, 也不会把结果声明为 formal claim.
    """
    scaffold = read_controlled_single_real_generation_request_scaffold(run_root)
    request_descriptor = scaffold.get("request_descriptor", {})
    if not isinstance(request_descriptor, dict):
        request_descriptor = {}
    controlled_request_digest = str(
        request_descriptor.get("controlled_request_digest", "")
    )
    result_artifact_kinds = [
        "runtime_environment_snapshot",
        "model_identity_record",
        "controlled_single_request_result_record",
        "runtime_failure_manifest",
    ]
    result_payload: dict[str, Any] = {
        "manual_controlled_single_request_result_status": "PASS",
        "controlled_request_digest": controlled_request_digest,
        "external_gpu_runtime_detected": _torch_cuda_available(),
        "external_model_identity_recorded": True,
        "controlled_single_request_result_recorded": True,
        "external_real_generation_attempted": False,
        "external_real_watermark_integration_attempted": False,
        "formal_claim_support_allowed": False,
        "repository_root": str(Path(repository_root).resolve()),
        "runtime_failure_manifest": {
            "failure_manifest_recorded": True,
            "failure_count": 0,
        },
        "result_artifacts": [
            {
                "result_artifact_kind": kind,
                "result_artifact_status": "present",
                "formal_claim_support_allowed": False,
            }
            for kind in result_artifact_kinds
        ],
    }
    result_path = Path(output_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result_payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return result_payload


def read_external_manual_controlled_single_request_results(
    external_results_path: str | Path,
) -> dict[str, Any]:
    """功能: 读取外部手动单请求运行结果摘要."""
    results_path = Path(external_results_path)
    if not results_path.exists():
        raise FileNotFoundError(results_path)
    return json.loads(results_path.read_text(encoding="utf-8"))


def run_manual_controlled_single_request_result_gate(
    repository_root: str | Path,
    run_root: str | Path,
    external_manual_request_results_path: str | Path,
    result_gate_config_path: str | Path = "configs/protocol/trajectory_aware_sampling_manual_controlled_single_request_result_gate.json",
) -> dict[str, Any]:
    """功能: 校验外部手动单请求结果并写出受治理 gate artifact.

    该 helper 只调度 repository module. 它不连接真实生成后端, 不生成视频, 不执行真实 watermark.
    结果 gate 只判断外部结果摘要是否满足当前阶段允许的 non-claim 记录边界.
    """
    from experiments.trajectory_aware_sampling_probe.manual_controlled_single_request_result_gate import (
        build_manual_controlled_single_request_result_gate_report_section,
        build_trajectory_aware_sampling_manual_controlled_single_request_result_gate,
    )
    from experiments.trajectory_aware_sampling_probe.output_layout import (
        build_trajectory_aware_sampling_probe_output_paths,
    )

    root_path = Path(repository_root).resolve()
    config_path = Path(result_gate_config_path)
    if not config_path.is_absolute():
        config_path = root_path / config_path
    output_paths = build_trajectory_aware_sampling_probe_output_paths(run_root)
    scaffold = read_controlled_single_real_generation_request_scaffold(run_root)
    external_results = read_external_manual_controlled_single_request_results(
        external_manual_request_results_path
    )
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    gate_payload = build_trajectory_aware_sampling_manual_controlled_single_request_result_gate(
        scaffold,
        external_results,
        config_payload,
    )
    output_paths.manual_controlled_single_request_result_gate_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_paths.manual_controlled_single_request_result_gate_path.write_text(
        json.dumps(gate_payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    report_section = build_manual_controlled_single_request_result_gate_report_section(
        gate_payload
    )
    existing_report = (
        output_paths.sampling_probe_report_path.read_text(encoding="utf-8")
        if output_paths.sampling_probe_report_path.exists()
        else ""
    )
    output_paths.sampling_probe_report_path.write_text(
        existing_report.rstrip() + report_section,
        encoding="utf-8",
    )
    return gate_payload


def read_manual_controlled_single_request_result_gate(
    run_root: str | Path,
) -> dict[str, Any]:
    """功能: 读取手动单请求结果 gate artifact."""
    gate_path = (
        Path(run_root)
        / "artifacts"
        / "trajectory_aware_sampling_manual_controlled_single_request_result_gate.json"
    )
    if not gate_path.exists():
        raise FileNotFoundError(gate_path)
    return json.loads(gate_path.read_text(encoding="utf-8"))


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

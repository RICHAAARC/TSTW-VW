"""阶段三 baseline smoke runner。

该模块只负责调度统一 adapter、写出 records、manifest 和 limitation report。
当前默认 adapter 是阻断型 skeleton, 因此本地 dry-run 不会产生正式 baseline 分数。
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from experiments.baseline_comparison_gate.baseline_adapter import BaselineRuntimeContext
from experiments.baseline_comparison_gate.baseline_registry import get_baseline_adapter
from experiments.baseline_comparison_gate.record_schema import validate_baseline_record
from experiments.baseline_comparison_gate.source_intake import (
    REQUIRED_BASELINE_NAMES,
    build_source_intake_summary,
    load_all_source_manifests,
)
from main.core.digest import compute_object_digest

WORKFLOW_KEY = "baseline_comparison_gate"
SMOKE_RUN_ID_PREFIX = "baseline_comparison_smoke"
LARGE_CACHE_SUFFIXES = (".pth", ".pt", ".ckpt", ".safetensors")


def utc_timestamp() -> str:
    """生成用于 run_id 的 UTC 时间戳。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_smoke_run_id(short_commit: str, timestamp_utc: str | None = None) -> str:
    """生成阶段三 smoke run_id。"""
    commit = short_commit.strip() or "unknown"
    timestamp = timestamp_utc or utc_timestamp()
    return f"{SMOKE_RUN_ID_PREFIX}_{timestamp}_{commit}"


def run_baseline_smoke(
    *,
    run_root: str | Path,
    config_dir: str | Path,
    short_commit: str = "unknown",
    timestamp_utc: str | None = None,
) -> dict[str, Any]:
    """执行不依赖真实 GPU 的 baseline smoke skeleton。

    该函数的作用是验证阶段三的 records、manifest、limitation report 和 adapter 阻断语义。
    它不会下载权重, 不会运行真实嵌入, 也不会产生可用于论文 claim 的正式分数。
    """
    run_root_path = Path(run_root)
    run_id = build_smoke_run_id(short_commit=short_commit, timestamp_utc=timestamp_utc)
    layout = prepare_smoke_layout(run_root_path)
    manifests = load_all_source_manifests(config_dir)
    source_summary = build_source_intake_summary(manifests)

    records: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []
    for baseline_name in REQUIRED_BASELINE_NAMES:
        source_manifest = manifests[baseline_name]
        adapter = get_baseline_adapter(baseline_name)
        context = BaselineRuntimeContext(
            baseline_name=baseline_name,
            run_id=run_id,
            work_dir=run_root_path / "work" / baseline_name,
            source_manifest=source_manifest,
        )
        prepare_result = adapter.prepare(context)
        detection_result = adapter.detect(run_root_path / "inputs" / "smoke_input.mp4", {})
        evaluation_result = adapter.evaluate(
            detection_output=detection_result,
            payload_bits=[0, 1, 0, 1],
            threshold=0.0,
            target_fpr=0.001,
        )
        record = build_skeleton_smoke_record(
            run_id=run_id,
            baseline_name=baseline_name,
            source_manifest=source_manifest,
            prepare_result=prepare_result,
            detection_result=detection_result,
            evaluation_result=evaluation_result,
        )
        violations = validate_baseline_record(record)
        if violations:
            raise ValueError(f"invalid baseline smoke record for {baseline_name}: {violations}")
        records.append(record)
        limitations.append(
            {
                "baseline_name": baseline_name,
                "adapter_status": source_manifest.get("adapter_status"),
                "model_availability_status": source_manifest.get("model_availability_status"),
                "failure_reason": record["failure_reason"],
                "claim_support_allowed": False,
            }
        )

    write_jsonl(layout["records_path"], records)
    source_summary_path = layout["configs_dir"] / "baseline_source_intake_summary.json"
    source_summary_path.write_text(
        json.dumps(source_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    limitation_report_path = layout["reports_dir"] / "baseline_limitation_report.md"
    limitation_report_path.write_text(
        build_limitation_report(limitations),
        encoding="utf-8",
    )
    manifest = build_smoke_manifest(
        run_id=run_id,
        short_commit=short_commit,
        records=records,
        source_summary=source_summary,
        limitation_report_path=limitation_report_path,
    )
    layout["manifest_path"].write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "run_id": run_id,
        "run_root": str(run_root_path),
        "record_count": len(records),
        "records_path": str(layout["records_path"]),
        "manifest_path": str(layout["manifest_path"]),
        "limitation_report_path": str(limitation_report_path),
        "requires_colab_validation": True,
        "colab_blocking_reason": "external_baseline_weights_and_gpu_smoke_not_verified",
    }



def ignore_large_runtime_cache(directory: str, names: list[str]) -> set[str]:
    """复制 smoke 结果包时排除大型模型权重缓存。

    smoke manifest 和 records 已保存 model_digest。Drive 结果包默认不再重复保存 checkpoint 文件,
    以避免每次 Colab 验证产生数百 MB 的重复权重副本。
    """
    ignored: set[str] = set()
    for name in names:
        path = Path(directory) / name
        if path.is_file() and path.suffix.lower() in LARGE_CACHE_SUFFIXES:
            ignored.add(name)
    return ignored

def materialize_completed_smoke_run(
    *,
    run_root: str | Path,
    result_root: str | Path,
    workflow_key: str = WORKFLOW_KEY,
    run_id: str,
    overwrite: bool = False,
    required_relative_paths: list[str] | None = None,
    include_large_cache: bool = False,
) -> Path:
    """将已完成的 smoke 运行目录复制到结果根目录下.

    该函数的作用是服务 Colab 冷启动工作流: 先在会话本地目录完成
    smoke 运行, 确认记录、manifest 和 limitation report 均已生成后, 再把
    完整目录复制到 Google Drive。这样可以避免运行失败时在 Drive 中留下
    空结果目录。
    """
    run_root_path = Path(run_root)
    result_root_path = Path(result_root)
    destination = result_root_path / workflow_key / run_id

    required_relative_paths = required_relative_paths or [
        "manifest.json",
        "records/baseline_smoke_records.jsonl",
        "reports/baseline_limitation_report.md",
    ]
    required_files = [run_root_path / relative_path for relative_path in required_relative_paths]
    missing_files = [path.as_posix() for path in required_files if not path.exists()]
    if missing_files:
        raise FileNotFoundError(
            "baseline smoke run is incomplete; missing files: " + ", ".join(missing_files)
        )
    if destination.exists():
        if not overwrite:
            raise FileExistsError(f"destination already exists: {destination}")
        shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    copy_ignore = None if include_large_cache else ignore_large_runtime_cache
    shutil.copytree(run_root_path, destination, ignore=copy_ignore)
    return destination


def prepare_smoke_layout(run_root: Path) -> dict[str, Path]:
    """创建 smoke run 的最小输出目录。"""
    directories = {
        "configs_dir": run_root / "configs",
        "records_dir": run_root / "records",
        "reports_dir": run_root / "reports",
        "logs_dir": run_root / "logs",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    return {
        **directories,
        "records_path": directories["records_dir"] / "baseline_smoke_records.jsonl",
        "manifest_path": run_root / "manifest.json",
    }


def build_skeleton_smoke_record(
    *,
    run_id: str,
    baseline_name: str,
    source_manifest: dict[str, Any],
    prepare_result: dict[str, Any],
    detection_result: Any,
    evaluation_result: Any,
) -> dict[str, Any]:
    """将阻断型 adapter 输出转换为统一 baseline record。"""
    source_digest = compute_object_digest(source_manifest)
    return {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "sample_id": "baseline_smoke_sample",
        "split": "dev",
        "sample_role": "attacked_positive",
        "baseline_name": baseline_name,
        "baseline_family": source_manifest["baseline_family"],
        "method_name": baseline_name,
        "method_family": source_manifest["baseline_family"],
        "payload_length_bits": 4,
        "payload_digest": compute_object_digest([0, 1, 0, 1]),
        "attack_name": "clean",
        "attack_family": "clean",
        "attack_config_digest": compute_object_digest({"attack_name": "clean"}),
        "baseline_score": detection_result.baseline_score,
        "baseline_raw_detector_output": detection_result.baseline_raw_detector_output,
        "threshold": evaluation_result.threshold,
        "target_fpr": evaluation_result.target_fpr,
        "decision": evaluation_result.decision,
        "bit_accuracy": evaluation_result.bit_accuracy,
        "ber": evaluation_result.ber,
        "quality_metrics": {},
        "temporal_metrics": {},
        "runtime_metrics": detection_result.runtime_metrics,
        "baseline_trace": {
            "source_digest": source_digest,
            "model_digest": "pending_colab_download",
            "adapter_version": prepare_result.get("adapter_status", "adapter_skeleton_only"),
            "score_mapping_rule": source_manifest.get("score_mapping_rule"),
            "license_status": source_manifest.get("source_intake_status"),
            "unsupported_attack_reason": None,
        },
        "failure_reason": evaluation_result.failure_reason,
    }


def build_smoke_manifest(
    *,
    run_id: str,
    short_commit: str,
    records: list[dict[str, Any]],
    source_summary: dict[str, Any],
    limitation_report_path: Path,
) -> dict[str, Any]:
    """生成 baseline smoke manifest。"""
    return {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": short_commit,
        "run_kind": "local_adapter_skeleton_smoke",
        "record_count": len(records),
        "records_digest": compute_object_digest(records),
        "source_summary_digest": compute_object_digest(source_summary),
        "limitation_report_path": limitation_report_path.as_posix(),
        "claim_support_allowed": False,
        "requires_colab_validation": True,
        "blocking_reason": "external_baseline_weights_and_gpu_smoke_not_verified",
    }


def build_limitation_report(limitations: list[dict[str, Any]]) -> str:
    """生成本地 smoke 的 baseline limitation report。"""
    lines = [
        "# baseline limitation report",
        "",
        "该报告由本地 adapter skeleton smoke 生成, 不能支撑正式论文 claim。",
        "",
        "| baseline_name | adapter_status | model_availability_status | failure_reason | claim_support_allowed |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in limitations:
        lines.append(
            "| {baseline_name} | {adapter_status} | {model_availability_status} | {failure_reason} | {claim_support_allowed} |".format(
                **item
            )
        )
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "必须在 Colab 中完成真实权重下载、权重 digest、单视频 embed/detect smoke 和记录打包后, 才能将对应 baseline 升级为正式可比较对象。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """写出 JSONL records。"""
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

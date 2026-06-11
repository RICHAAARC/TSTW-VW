"""阶段三正式 baseline comparison scoring runner 的工作计划层。

该模块负责把阶段二 real-video VAE records 转换为外部 baseline 的正式 scoring work items。
它不会伪造外部 baseline 分数, 也不会生成 TPR/FPR 表。后续执行层必须逐条完成 embed、attack、detect、
calibration 和 test 冻结后, 才能生成投稿 claim 可用的正式表格。
"""

from __future__ import annotations

from collections import OrderedDict
import json
from pathlib import Path
import shutil
from typing import Any, Iterable

from experiments.baseline_comparison_gate.formal_input_contract import load_json
from experiments.baseline_comparison_gate.source_intake import REQUIRED_BASELINE_NAMES
from main.core.digest import compute_file_digest, compute_object_digest

WORKFLOW_KEY = "baseline_comparison_gate"
WORK_ITEMS_FILENAME = "baseline_scoring_work_items.jsonl"


def iter_jsonl(path: str | Path):
    """逐行读取 UTF-8 JSONL 文件。"""
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def normalize_baseline_filter(baseline_names: Iterable[str] | None) -> list[str]:
    """规范化 baseline 过滤参数。"""
    if baseline_names is None:
        return list(REQUIRED_BASELINE_NAMES)
    normalized = [name for name in baseline_names if name]
    unsupported = sorted(set(normalized) - set(REQUIRED_BASELINE_NAMES))
    if unsupported:
        raise ValueError(f"unsupported baseline names: {unsupported}")
    if not normalized:
        raise ValueError("baseline filter must contain at least one baseline")
    return normalized


def validate_shard(shard_count: int, shard_index: int) -> None:
    """校验 shard 参数。"""
    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must be in [0, shard_count)")


def build_stage_two_event_universe(stage_two_package_root: str | Path) -> list[dict[str, Any]]:
    """从阶段二 records 中抽取与内部 method_variant 无关的唯一事件宇宙。"""
    root = Path(stage_two_package_root)
    event_scores_path = root / "records" / "event_scores.jsonl"
    if not event_scores_path.exists():
        raise FileNotFoundError(f"missing stage-two event_scores: {event_scores_path}")

    unique_events: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for record in iter_jsonl(event_scores_path):
        mechanism_trace = record.get("mechanism_trace") or {}
        attack_params = record.get("attack_params") or {}
        key_payload = {
            "split": record.get("split"),
            "sample_role": record.get("sample_role"),
            "sample_id": record.get("sample_id"),
            "attack_name": record.get("attack_name"),
            "attack_params": attack_params,
        }
        event_key = compute_object_digest(key_payload)
        if event_key in unique_events:
            continue
        unique_events[event_key] = {
            "stage_two_event_key": event_key,
            "stage_two_event_id": record.get("event_id"),
            "split": record.get("split"),
            "sample_role": record.get("sample_role"),
            "sample_id": record.get("sample_id"),
            "attack_name": record.get("attack_name"),
            "attack_params": attack_params,
            "attack_config_digest": compute_object_digest(
                {"attack_name": record.get("attack_name"), "attack_params": attack_params}
            ),
            "target_fpr": record.get("target_fpr"),
            "payload_digest": mechanism_trace.get("payload_digest"),
            "source_video_relpath": mechanism_trace.get("video_source_relpath"),
            "source_video_digest": mechanism_trace.get("video_source_digest"),
            "video_frame_count": mechanism_trace.get("video_frame_count"),
            "video_fps": mechanism_trace.get("video_fps"),
            "video_resolution": mechanism_trace.get("video_resolution"),
        }
    return list(unique_events.values())


def build_scoring_work_items(
    *,
    stage_two_package_root: str | Path,
    baseline_names: Iterable[str] | None = None,
    shard_count: int = 1,
    shard_index: int = 0,
) -> list[dict[str, Any]]:
    """构建外部 baseline 正式 scoring work items。"""
    validate_shard(shard_count, shard_index)
    selected_baselines = normalize_baseline_filter(baseline_names)
    event_universe = build_stage_two_event_universe(stage_two_package_root)
    all_items: list[dict[str, Any]] = []
    for baseline_name in selected_baselines:
        for event in event_universe:
            item_payload = {"baseline_name": baseline_name, **event}
            item_id = compute_object_digest(item_payload)
            all_items.append(
                {
                    "workflow_key": WORKFLOW_KEY,
                    "work_item_id": item_id,
                    "baseline_name": baseline_name,
                    "baseline_family": "external_video_watermark",
                    "execution_status": "pending_external_baseline_scoring",
                    "claim_support_allowed": False,
                    **event,
                }
            )
    return [item for index, item in enumerate(all_items) if index % shard_count == shard_index]


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    """写出 JSONL 文件。"""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def run_formal_scoring_plan(
    *,
    run_root: str | Path,
    stage_two_package_root: str | Path,
    formal_input_contract_path: str | Path,
    baseline_names: Iterable[str] | None = None,
    shard_count: int = 1,
    shard_index: int = 0,
) -> dict[str, Any]:
    """生成正式 scoring work-item 计划。"""
    run_root_path = Path(run_root)
    contract = load_json(formal_input_contract_path)
    if contract.get("ready_for_formal_baseline_runner") is not True:
        raise ValueError("formal input contract is not ready for formal baseline runner")
    work_items = build_scoring_work_items(
        stage_two_package_root=stage_two_package_root,
        baseline_names=baseline_names,
        shard_count=shard_count,
        shard_index=shard_index,
    )
    work_items_path = run_root_path / "work_items" / WORK_ITEMS_FILENAME
    write_jsonl(work_items_path, work_items)
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_kind": "baseline_comparison_formal_scoring_plan",
        "formal_input_contract_path": Path(formal_input_contract_path).as_posix(),
        "formal_input_contract_digest": compute_file_digest(formal_input_contract_path),
        "stage_two_package_root": Path(stage_two_package_root).as_posix(),
        "baseline_names": sorted({item["baseline_name"] for item in work_items}),
        "shard_count": shard_count,
        "shard_index": shard_index,
        "work_item_count": len(work_items),
        "work_items_path": work_items_path.as_posix(),
        "work_items_digest": compute_file_digest(work_items_path),
        "claim_support_allowed": False,
        "formal_fixed_fpr_complete": False,
        "blocking_reason": "scoring_plan_only_external_baseline_execution_not_complete",
    }
    manifest_path = run_root_path / "artifacts" / "baseline_comparison_formal_scoring_plan_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix()}


def materialize_formal_scoring_plan_run(
    *,
    run_root: str | Path,
    result_root: str | Path,
    run_id: str,
    workflow_key: str = WORKFLOW_KEY,
    overwrite: bool = False,
) -> Path:
    """将已完成的 scoring plan 运行目录复制到 Drive。"""
    run_root_path = Path(run_root)
    destination = Path(result_root) / workflow_key / run_id
    required_files = [
        run_root_path / "work_items" / WORK_ITEMS_FILENAME,
        run_root_path / "artifacts" / "baseline_comparison_formal_scoring_plan_manifest.json",
    ]
    missing_files = [path.as_posix() for path in required_files if not path.exists()]
    if missing_files:
        raise FileNotFoundError("formal scoring plan run is incomplete: " + ", ".join(missing_files))
    if destination.exists():
        if not overwrite:
            raise FileExistsError(f"destination already exists: {destination}")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run_root_path, destination)
    return destination

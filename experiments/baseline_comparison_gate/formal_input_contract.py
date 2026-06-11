"""构建正式 baseline comparison 的输入契约。

该模块读取已经解压的阶段二 real-video VAE 正式结果包, 汇总 split、sample role、attack
和内部方法变体, 并与阶段三配置及真实 smoke 摘要做一致性检查。它是正式 runner 的前置
输入冻结步骤, 不执行外部 baseline 推理, 也不生成论文主表。
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
from typing import Any

from experiments.baseline_comparison_gate.real_smoke_summary import load_json as load_smoke_json
from main.core.digest import compute_file_digest, compute_object_digest

WORKFLOW_KEY = "baseline_comparison_gate"


def load_json(path: str | Path) -> dict[str, Any]:
    """读取 UTF-8 JSON 文件。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iter_event_records(event_scores_path: str | Path):
    """逐行读取阶段二 event_scores records。"""
    path = Path(event_scores_path)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def summarize_stage_two_records(stage_two_package_root: str | Path) -> dict[str, Any]:
    """汇总阶段二 records 的正式 comparison 输入宇宙。"""
    root = Path(stage_two_package_root)
    event_scores_path = root / "records" / "event_scores.jsonl"
    if not event_scores_path.exists():
        raise FileNotFoundError(f"缺少阶段二 event_scores: {event_scores_path}")

    split_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    attack_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    target_fprs: set[float] = set()
    sample_ids: set[str] = set()
    record_count = 0
    for record in iter_event_records(event_scores_path):
        record_count += 1
        split_counts[str(record.get("split"))] += 1
        role_counts[str(record.get("sample_role"))] += 1
        attack_counts[str(record.get("attack_name"))] += 1
        method_counts[str(record.get("method_variant"))] += 1
        sample_ids.add(str(record.get("sample_id")))
        if record.get("target_fpr") is not None:
            target_fprs.add(float(record["target_fpr"]))

    return {
        "stage_two_package_root": root.as_posix(),
        "event_scores_path": event_scores_path.as_posix(),
        "event_scores_digest": compute_file_digest(event_scores_path),
        "record_count": record_count,
        "sample_id_count": len(sample_ids),
        "split_counts": dict(sorted(split_counts.items())),
        "sample_role_counts": dict(sorted(role_counts.items())),
        "attack_counts": dict(sorted(attack_counts.items())),
        "method_variant_counts": dict(sorted(method_counts.items())),
        "target_fprs": sorted(target_fprs),
    }


def build_formal_input_contract(
    *,
    stage_two_package_root: str | Path,
    baseline_config_path: str | Path,
    real_smoke_summary_path: str | Path | None = None,
) -> dict[str, Any]:
    """构建阶段三正式 runner 的输入契约。"""
    config = load_json(baseline_config_path)
    stage_two_summary = summarize_stage_two_records(stage_two_package_root)
    smoke_summary = load_smoke_json(real_smoke_summary_path) if real_smoke_summary_path else None

    expected_splits = set(config["splits"])
    actual_splits = set(stage_two_summary["split_counts"])
    expected_methods = set(config["internal_method_variants"])
    actual_methods = set(stage_two_summary["method_variant_counts"])
    expected_attacks = set(config["formal_attack_names"])
    actual_attacks = set(stage_two_summary["attack_counts"])
    expected_target_fprs = {float(value) for value in config["threshold_protocol"]["target_fprs"]}
    actual_target_fprs = {float(value) for value in stage_two_summary["target_fprs"]}

    violations: list[dict[str, Any]] = []
    if actual_splits != expected_splits:
        violations.append({"field": "splits", "expected": sorted(expected_splits), "actual": sorted(actual_splits)})
    if actual_methods != expected_methods:
        violations.append({"field": "internal_method_variants", "expected": sorted(expected_methods), "actual": sorted(actual_methods)})
    if actual_attacks != expected_attacks:
        violations.append({"field": "formal_attack_names", "expected": sorted(expected_attacks), "actual": sorted(actual_attacks)})
    if actual_target_fprs != expected_target_fprs:
        violations.append({"field": "target_fprs", "expected": sorted(expected_target_fprs), "actual": sorted(actual_target_fprs)})
    if smoke_summary is not None and smoke_summary.get("package_ready_for_formal_planning") is not True:
        violations.append({"field": "real_smoke_summary", "reason": "package_not_ready_for_formal_planning"})

    ready = not violations
    contract = {
        "workflow_key": WORKFLOW_KEY,
        "contract_kind": "baseline_comparison_formal_input_contract",
        "input_stage_package": config["input_stage_package"],
        "stage_two_summary": stage_two_summary,
        "baseline_names": config["baselines"],
        "internal_method_variants": config["internal_method_variants"],
        "formal_attack_names": config["formal_attack_names"],
        "attack_display_names": config.get("attack_display_names", []),
        "threshold_protocol": config["threshold_protocol"],
        "real_smoke_summary_digest": compute_object_digest(smoke_summary) if smoke_summary is not None else None,
        "real_smoke_status_by_baseline": {
            entry["baseline_name"]: entry["status"] for entry in (smoke_summary or {}).get("entries", [])
        },
        "required_output_artifacts": config["required_output_artifacts"],
        "violations": violations,
        "ready_for_formal_baseline_runner": ready,
        "claim_support_allowed": False,
        "blocking_reason": None if ready else "baseline_comparison_formal_inputs_not_ready",
    }
    contract["contract_digest"] = compute_object_digest({k: v for k, v in contract.items() if k != "contract_digest"})
    return contract


def write_formal_input_contract(contract: dict[str, Any], run_root: str | Path) -> dict[str, str]:
    """写出正式 runner 输入契约和最小 manifest。"""
    root = Path(run_root)
    configs_dir = root / "configs"
    artifacts_dir = root / "artifacts"
    configs_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    contract_path = configs_dir / "baseline_comparison_formal_input_contract.json"
    manifest_path = artifacts_dir / "baseline_comparison_formal_input_manifest.json"
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "manifest_kind": "baseline_comparison_formal_input_manifest",
        "contract_path": contract_path.as_posix(),
        "contract_digest": contract["contract_digest"],
        "ready_for_formal_baseline_runner": contract["ready_for_formal_baseline_runner"],
        "claim_support_allowed": False,
        "blocking_reason": contract["blocking_reason"],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"contract_path": contract_path.as_posix(), "manifest_path": manifest_path.as_posix()}



def materialize_formal_input_contract_run(
    *,
    run_root: str | Path,
    result_root: str | Path,
    run_id: str,
    workflow_key: str = WORKFLOW_KEY,
    overwrite: bool = False,
) -> Path:
    """将已完成的 formal input contract 运行目录复制到 Drive 结果目录。

    该函数服务于 Colab 冷启动流程: 先在 session-local 目录生成并校验输入契约, 确认必要文件
    存在后, 再一次性复制到 Google Drive。这样可以避免运行失败时在 Drive 中留下空目录或半成品。
    """
    run_root_path = Path(run_root)
    result_root_path = Path(result_root)
    destination = result_root_path / workflow_key / run_id
    required_files = [
        run_root_path / "configs" / "baseline_comparison_formal_input_contract.json",
        run_root_path / "artifacts" / "baseline_comparison_formal_input_manifest.json",
    ]
    missing_files = [path.as_posix() for path in required_files if not path.exists()]
    if missing_files:
        raise FileNotFoundError(
            "baseline comparison formal input contract run is incomplete; missing files: "
            + ", ".join(missing_files)
        )
    if destination.exists():
        if not overwrite:
            raise FileExistsError(f"destination already exists: {destination}")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run_root_path, destination)
    return destination

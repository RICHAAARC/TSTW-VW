"""baseline comparison score records 聚合与 fixed-FPR 表格构建。"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from main.core.digest import compute_file_digest, compute_object_digest

WORKFLOW_KEY = "baseline_comparison_gate"
TARGET_FPR = 0.001
POSITIVE_ROLES = {"watermarked_positive", "attacked_positive"}
NEGATIVE_ROLES = {"clean_negative", "attacked_negative"}


def iter_jsonl(path: str | Path):
    """逐行读取 JSONL records。"""
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_score_records(record_paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    """从一个或多个 shard 结果中读取 baseline score records。"""
    records: list[dict[str, Any]] = []
    for path in record_paths:
        records.extend(iter_jsonl(path))
    return records


def calibrate_threshold(scores: list[float], target_fpr: float = TARGET_FPR) -> tuple[float | None, float | None]:
    """基于 calibration negatives 计算保守 fixed-FPR 阈值。

    score 方向为 higher_is_more_watermarked。若 calibration negatives 数量不足以支持目标 FPR,
    使用 max_negative_score + epsilon 的保守阈值, 使经验 FPR 为0。
    """
    clean_scores = sorted(float(score) for score in scores if score is not None)
    if not clean_scores:
        return None, None
    if target_fpr < 1.0 / len(clean_scores):
        threshold = clean_scores[-1] + 1e-12
    else:
        allowed_false_positives = int(len(clean_scores) * target_fpr)
        index = max(0, len(clean_scores) - allowed_false_positives - 1)
        threshold = clean_scores[index]
    empirical_fpr = sum(score >= threshold for score in clean_scores) / len(clean_scores)
    return float(threshold), float(empirical_fpr)


def summarize_group(records: list[dict[str, Any]], threshold: float | None) -> dict[str, Any]:
    """汇总一组 records 的检测指标。"""
    scored = [row for row in records if row.get("baseline_score") is not None]
    positives = [row for row in scored if row.get("sample_role") in POSITIVE_ROLES]
    negatives = [row for row in scored if row.get("sample_role") in NEGATIVE_ROLES]
    if threshold is None:
        tpr = None
        fpr = None
    else:
        tpr = None if not positives else sum(float(row["baseline_score"]) >= threshold for row in positives) / len(positives)
        fpr = None if not negatives else sum(float(row["baseline_score"]) >= threshold for row in negatives) / len(negatives)
    return {
        "record_count": len(records),
        "scored_count": len(scored),
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "tpr_at_target_fpr": tpr,
        "fpr_at_threshold": fpr,
        "mean_score": None if not scored else sum(float(row["baseline_score"]) for row in scored) / len(scored),
    }


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """写出 UTF-8 CSV 表格。"""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def run_baseline_score_aggregation(
    *,
    run_root: str | Path,
    record_paths: Iterable[str | Path],
    target_fpr: float = TARGET_FPR,
) -> dict[str, Any]:
    """聚合 baseline score records 并生成正式表格骨架。

    该函数不伪造缺失实验结果。若输入 records 尚未覆盖 calibration/test split,
    输出 manifest 会保持 claim_support_allowed=false。
    """
    run_root_path = Path(run_root)
    records = load_score_records(record_paths)
    records_path = run_root_path / "records" / "baseline_formal_score_records.jsonl"
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")

    by_baseline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_baseline[str(row.get("baseline_name"))].append(row)

    threshold_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    attack_rows: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
    complete = True
    for baseline_name, baseline_records in sorted(by_baseline.items()):
        calibration_negatives = [
            float(row["baseline_score"])
            for row in baseline_records
            if row.get("split") == "calibration"
            and row.get("sample_role") in NEGATIVE_ROLES
            and row.get("baseline_score") is not None
        ]
        threshold, empirical_fpr = calibrate_threshold(calibration_negatives, target_fpr)
        has_test_positive = any(row.get("split") == "test" and row.get("sample_role") in POSITIVE_ROLES for row in baseline_records)
        has_test_negative = any(row.get("split") == "test" and row.get("sample_role") in NEGATIVE_ROLES for row in baseline_records)
        complete = complete and threshold is not None and has_test_positive and has_test_negative
        threshold_rows.append({
            "baseline_name": baseline_name,
            "target_fpr": target_fpr,
            "threshold": threshold,
            "calibration_negative_count": len(calibration_negatives),
            "empirical_calibration_fpr": empirical_fpr,
        })
        test_summary = summarize_group([row for row in baseline_records if row.get("split") == "test"], threshold)
        comparison_rows.append({"baseline_name": baseline_name, "target_fpr": target_fpr, **test_summary})
        by_attack: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in baseline_records:
            if row.get("split") == "test":
                by_attack[str(row.get("attack_name"))].append(row)
        for attack_name, attack_records in sorted(by_attack.items()):
            attack_rows.append({"baseline_name": baseline_name, "attack_name": attack_name, "target_fpr": target_fpr, **summarize_group(attack_records, threshold)})
        runtime_seconds = []
        for row in baseline_records:
            metrics = row.get("runtime_metrics") or {}
            for key, value in metrics.items():
                if key.endswith("_seconds") and isinstance(value, (int, float)):
                    runtime_seconds.append(float(value))
        runtime_rows.append({
            "baseline_name": baseline_name,
            "record_count": len(baseline_records),
            "runtime_seconds_sum": sum(runtime_seconds),
            "runtime_seconds_mean": None if not runtime_seconds else sum(runtime_seconds) / len(runtime_seconds),
        })

    write_csv(run_root_path / "thresholds" / "baseline_threshold_table.csv", threshold_rows, ["baseline_name", "target_fpr", "threshold", "calibration_negative_count", "empirical_calibration_fpr"])
    write_csv(run_root_path / "tables" / "baseline_comparison_table.csv", comparison_rows, ["baseline_name", "target_fpr", "record_count", "scored_count", "positive_count", "negative_count", "tpr_at_target_fpr", "fpr_at_threshold", "mean_score"])
    write_csv(run_root_path / "tables" / "baseline_attack_breakdown.csv", attack_rows, ["baseline_name", "attack_name", "target_fpr", "record_count", "scored_count", "positive_count", "negative_count", "tpr_at_target_fpr", "fpr_at_threshold", "mean_score"])
    write_csv(run_root_path / "tables" / "baseline_runtime_table.csv", runtime_rows, ["baseline_name", "record_count", "runtime_seconds_sum", "runtime_seconds_mean"])
    limitation_report = run_root_path / "reports" / "baseline_limitation_report.md"
    limitation_report.parent.mkdir(parents=True, exist_ok=True)
    limitation_report.write_text("# baseline limitation report\n\n当前聚合结果是否完整: `{}`。\n".format(complete), encoding="utf-8")
    claim_path = run_root_path / "claim_audit" / "baseline_claim_audit.csv"
    write_csv(
        claim_path,
        [
            {
                "claim_name": "baseline_comparison_fixed_fpr",
                "claim_support_allowed": complete,
                "blocking_reason": None if complete else "missing_calibration_or_test_records",
            }
        ],
        ["claim_name", "claim_support_allowed", "blocking_reason"],
    )
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_kind": "baseline_score_records_aggregation",
        "record_count": len(records),
        "baseline_count": len(by_baseline),
        "target_fpr": target_fpr,
        "records_digest": compute_file_digest(records_path),
        "tables_digest": compute_object_digest(comparison_rows),
        "claim_support_allowed": bool(complete),
        "formal_fixed_fpr_complete": bool(complete),
        "blocking_reason": None if complete else "missing_calibration_or_test_records",
    }
    manifest_path = run_root_path / "artifacts" / "baseline_score_records_aggregation_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix()}

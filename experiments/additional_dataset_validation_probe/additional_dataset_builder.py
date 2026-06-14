"""构建 `additional_dataset_validation_probe` 的聚合表、图表数据和 manifest。

该模块只聚合已经由 Colab shard run 产生的附加数据集 score records。
它不直接下载 UCF101, 不运行 VAE, 也不执行水印嵌入或攻击算子。
这样设计的主要考虑在于: GPU 运行与论文图表重建分离, 后续可以用同一个聚合器复现表格和 claim audit。
"""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from main.core.digest import compute_file_digest, compute_object_digest

WORKFLOW_KEY = "additional_dataset_validation_probe"
DEFAULT_DATASET_NAME = "ucf101"
INTERNAL_METHODS = ("frame_prc", "tubelet_only", "tubelet_sync")
POSITIVE_ROLES = {"watermarked_positive", "attacked_positive"}
NEGATIVE_ROLES = {"clean_negative", "attacked_negative"}


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """读取 UTF-8 JSONL 文件。"""
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    """写出 UTF-8 JSONL 文件。"""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """写出 UTF-8 CSV 表格。"""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def resolve_short_commit() -> str:
    """读取当前仓库短 commit, 用于默认 run_id。"""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=Path(__file__).resolve().parents[2],
        ).strip()
    except Exception:
        return "unknown"


def utc_timestamp() -> str:
    """生成 UTC 时间戳。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def latest_child_dir(root: str | Path) -> Path | None:
    """返回目录下最近修改的子目录。"""
    root_path = Path(root)
    if not root_path.exists():
        return None
    children = [path for path in root_path.iterdir() if path.is_dir()]
    if not children:
        return None
    return max(children, key=lambda path: path.stat().st_mtime)


def discover_record_paths(result_root: str | Path, dataset_name: str = DEFAULT_DATASET_NAME) -> list[Path]:
    """从默认 shard_runs 目录自动发现附加数据集 score records。"""
    shard_root = Path(result_root) / WORKFLOW_KEY / dataset_name / "shard_runs"
    if not shard_root.exists():
        return []
    return sorted(shard_root.glob("*/records/additional_dataset_event_scores.jsonl"))


def score_of(record: dict[str, Any]) -> float | None:
    """从兼容 record 字段中解析检测分数。"""
    if record.get("score") is not None:
        return float(record["score"])
    if record.get("S_final") is not None:
        return float(record["S_final"])
    evidence_scores = record.get("evidence_scores") or {}
    if evidence_scores.get("S_final") is not None:
        return float(evidence_scores["S_final"])
    return None


def is_positive(record: dict[str, Any]) -> bool:
    """判断记录是否属于正样本。"""
    return record.get("sample_role") in POSITIVE_ROLES


def is_negative(record: dict[str, Any]) -> bool:
    """判断记录是否属于负样本。"""
    return record.get("sample_role") in NEGATIVE_ROLES


def calibrate_threshold(scores: list[float], target_fpr: float) -> float | None:
    """只使用 calibration negatives 校准固定 FPR 阈值。

    该函数属于通用工程写法: 聚合器只接收已冻结 records, 阈值选择不读取 test split。
    项目特定约束是 target FPR 固定为论文协议中的低 FPR 设置, 默认值为 1%。
    """
    if not scores:
        return None
    sorted_scores = sorted(scores, reverse=True)
    false_positive_budget = max(0, int(len(sorted_scores) * target_fpr))
    index = min(false_positive_budget, len(sorted_scores) - 1)
    return float(sorted_scores[index])


def compute_auc(labels_and_scores: list[tuple[int, float]]) -> float | None:
    """计算二分类 ROC AUC, 支持并列分数。"""
    positives = sum(label == 1 for label, _ in labels_and_scores)
    negatives = sum(label == 0 for label, _ in labels_and_scores)
    if positives == 0 or negatives == 0:
        return None
    ordered = sorted(labels_and_scores, key=lambda item: item[1])
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        for tie_index in range(index, end):
            if ordered[tie_index][0] == 1:
                rank_sum += average_rank
        index = end
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def normalize_records(records: list[dict[str, Any]], dataset_name: str) -> list[dict[str, Any]]:
    """标准化附加数据集验证 records 的关键字段。"""
    normalized: list[dict[str, Any]] = []
    for record in records:
        score = score_of(record)
        if score is None:
            continue
        normalized.append(
            {
                "dataset_name": record.get("dataset_name") or dataset_name,
                "dataset_subset_id": record.get("dataset_subset_id") or record.get("subset_id") or "unspecified",
                "method_name": record.get("method_name") or record.get("method_variant"),
                "attack_name": record.get("attack_name") or "no_attack",
                "split": record.get("split"),
                "sample_role": record.get("sample_role"),
                "score": float(score),
                "source_artifact": record.get("source_artifact", "records/additional_dataset_event_scores.jsonl"),
            }
        )
    return normalized


def build_additional_dataset_tables(
    records: list[dict[str, Any]],
    *,
    target_fpr: float = 0.01,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """从标准化 records 构建主表、攻击分解表和 figure_data。"""
    thresholds: dict[tuple[str, str, str], float | None] = {}
    for dataset_name in sorted({str(row["dataset_name"]) for row in records}):
        for dataset_subset_id in sorted({str(row["dataset_subset_id"]) for row in records if row["dataset_name"] == dataset_name}):
            for method_name in sorted({str(row["method_name"]) for row in records if row["dataset_name"] == dataset_name and row["dataset_subset_id"] == dataset_subset_id}):
                calibration_negative_scores = [
                    row["score"]
                    for row in records
                    if row["dataset_name"] == dataset_name
                    and row["dataset_subset_id"] == dataset_subset_id
                    and row["method_name"] == method_name
                    and row["split"] == "calibration"
                    and is_negative(row)
                ]
                thresholds[(dataset_name, dataset_subset_id, method_name)] = calibrate_threshold(
                    calibration_negative_scores,
                    target_fpr,
                )

    method_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    attack_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in records:
        if row["split"] != "test":
            continue
        method_key = (str(row["dataset_name"]), str(row["dataset_subset_id"]), str(row["method_name"]))
        method_groups.setdefault(method_key, []).append(row)
        attack_groups.setdefault((*method_key, str(row["attack_name"])), []).append(row)

    def summarize_group(dataset_name: str, dataset_subset_id: str, method_name: str, group_rows: list[dict[str, Any]]) -> dict[str, Any]:
        threshold = thresholds.get((dataset_name, dataset_subset_id, method_name))
        positives = [row for row in group_rows if is_positive(row)]
        negatives = [row for row in group_rows if is_negative(row)]
        positive_count = len(positives)
        negative_count = len(negatives)
        tpr = None if threshold is None or positive_count == 0 else sum(row["score"] >= threshold for row in positives) / positive_count
        fpr = None if threshold is None or negative_count == 0 else sum(row["score"] >= threshold for row in negatives) / negative_count
        labels_and_scores = [(1, row["score"]) for row in positives] + [(0, row["score"]) for row in negatives]
        return {
            "dataset_name": dataset_name,
            "dataset_subset_id": dataset_subset_id,
            "method_name": method_name,
            "target_fpr": target_fpr,
            "threshold": threshold,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "tpr_at_target_fpr": tpr,
            "fpr_at_threshold": fpr,
            "auc": compute_auc(labels_and_scores),
            "source_artifact": "records/additional_dataset_event_scores.jsonl",
        }

    main_rows = [
        summarize_group(dataset_name, dataset_subset_id, method_name, group_rows)
        for (dataset_name, dataset_subset_id, method_name), group_rows in sorted(method_groups.items())
    ]
    attack_rows = [
        {
            **summarize_group(dataset_name, dataset_subset_id, method_name, group_rows),
            "attack_name": attack_name,
        }
        for (dataset_name, dataset_subset_id, method_name, attack_name), group_rows in sorted(attack_groups.items())
    ]
    figure_rows = [
        {
            "dataset_name": row["dataset_name"],
            "dataset_subset_id": row["dataset_subset_id"],
            "method_name": row["method_name"],
            "attack_name": row.get("attack_name", "overall"),
            "target_fpr": row["target_fpr"],
            "tpr_at_target_fpr": row["tpr_at_target_fpr"],
            "fpr_at_threshold": row["fpr_at_threshold"],
            "auc": row["auc"],
        }
        for row in attack_rows
    ]
    return main_rows, attack_rows, figure_rows


def read_records_from_paths(record_paths: list[Path]) -> list[dict[str, Any]]:
    """读取多个 shard record 文件。"""
    records: list[dict[str, Any]] = []
    for record_path in record_paths:
        records.extend(read_jsonl(record_path))
    return records


def build_additional_dataset_artifacts(
    *,
    output_root: str | Path,
    record_paths: list[Path],
    dataset_name: str = DEFAULT_DATASET_NAME,
    run_id: str | None = None,
    target_fpr: float = 0.01,
) -> dict[str, Any]:
    """聚合附加数据集 records 并写出论文可消费产物。"""
    if not record_paths:
        raise FileNotFoundError("additional_dataset_event_scores.jsonl 记录路径不能为空。")
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)
    actual_run_id = run_id or f"{WORKFLOW_KEY}_{dataset_name}_{utc_timestamp()}_{resolve_short_commit()[:7]}"

    records = normalize_records(read_records_from_paths(record_paths), dataset_name)
    record_path = output_root_path / "records" / "additional_dataset_event_scores.jsonl"
    write_jsonl(record_path, records)
    main_rows, attack_rows, figure_rows = build_additional_dataset_tables(records, target_fpr=target_fpr)

    main_fields = [
        "dataset_name", "dataset_subset_id", "method_name", "target_fpr", "threshold",
        "positive_count", "negative_count", "tpr_at_target_fpr", "fpr_at_threshold", "auc", "source_artifact",
    ]
    attack_fields = [
        "dataset_name", "dataset_subset_id", "method_name", "attack_name", "target_fpr", "threshold",
        "positive_count", "negative_count", "tpr_at_target_fpr", "fpr_at_threshold", "auc", "source_artifact",
    ]
    figure_fields = [
        "dataset_name", "dataset_subset_id", "method_name", "attack_name", "target_fpr",
        "tpr_at_target_fpr", "fpr_at_threshold", "auc",
    ]
    write_csv(output_root_path / "tables" / "additional_dataset_main_tpr_fpr_table.csv", main_rows, main_fields)
    write_csv(output_root_path / "tables" / "additional_dataset_attack_breakdown_table.csv", attack_rows, attack_fields)
    write_csv(output_root_path / "figure_data" / "additional_dataset_comparison_figure_data.csv", figure_rows, figure_fields)

    complete_methods = sorted({row["method_name"] for row in main_rows})
    complete_datasets = sorted({row["dataset_name"] for row in main_rows})
    claim_support_allowed = bool(main_rows) and all(method in complete_methods for method in INTERNAL_METHODS)
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": actual_run_id,
        "dataset_name": dataset_name,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "record_paths": [path.as_posix() for path in record_paths],
        "record_count": len(records),
        "main_row_count": len(main_rows),
        "attack_row_count": len(attack_rows),
        "target_fpr": target_fpr,
        "complete_methods": complete_methods,
        "complete_datasets": complete_datasets,
        "claim_support_allowed": claim_support_allowed,
        "source_digest": compute_object_digest({"record_paths": [path.as_posix() for path in record_paths]}),
        "artifact_digests": {
            "additional_dataset_event_scores": compute_file_digest(record_path),
            "additional_dataset_main_tpr_fpr_table": compute_file_digest(
                output_root_path / "tables" / "additional_dataset_main_tpr_fpr_table.csv"
            ),
            "additional_dataset_attack_breakdown_table": compute_file_digest(
                output_root_path / "tables" / "additional_dataset_attack_breakdown_table.csv"
            ),
            "additional_dataset_comparison_figure_data": compute_file_digest(
                output_root_path / "figure_data" / "additional_dataset_comparison_figure_data.csv"
            ),
        },
    }
    manifest_path = output_root_path / "artifacts" / "additional_dataset_validation_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix(), "output_root": output_root_path.as_posix()}


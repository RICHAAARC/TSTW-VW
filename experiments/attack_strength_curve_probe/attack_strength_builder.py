"""构建 `attack_strength_curve_probe` 的聚合表、曲线数据和 manifest。

该模块负责把多强度攻击实验的 score records 聚合为 TPR@固定 FPR 和 AUC 曲线。
它不直接运行 VAE 或攻击算子; 正式 records 应由后续 Colab runner 产生。
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from main.core.digest import compute_file_digest, compute_object_digest

WORKFLOW_KEY = "attack_strength_curve_probe"
INTERNAL_METHODS = ("frame_prc", "tubelet_only", "tubelet_sync")
ATTACKS = ("h264_compression", "h265_compression", "temporal_crop", "frame_dropping")
CALIBRATION_ONLY_ATTACKS = ("no_attack",)
POSITIVE_ROLES = {"watermarked_positive", "attacked_positive"}
NEGATIVE_ROLES = {"clean_negative", "attacked_negative"}
INTERNAL_SWEEP_RUN_RE = re.compile(
    r"^attack_strength_curve_probe_internal_sweep_sc(?P<shard_count>\d+)_"
    r"si(?P<shard_index>\d+)_(?P<short_commit>[0-9a-fA-F]+|unknown)$"
)


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


def latest_child_dir(root: str | Path) -> Path | None:
    """返回目录下最近修改的子目录。"""
    root_path = Path(root)
    if not root_path.exists():
        return None
    children = [path for path in root_path.iterdir() if path.is_dir()]
    if not children:
        return None
    return max(children, key=lambda path: path.stat().st_mtime)


def _parse_internal_sweep_run_dir(path: Path) -> dict[str, Any] | None:
    """解析内部多强度 sweep shard 目录名。"""
    match = INTERNAL_SWEEP_RUN_RE.match(path.name)
    if match is None:
        return None
    return {
        "family_root": path,
        "shard_count": int(match.group("shard_count")),
        "shard_index": int(match.group("shard_index")),
        "short_commit": match.group("short_commit"),
        "record_path": path / "records" / "attack_strength_event_scores.jsonl",
        "latest_mtime": path.stat().st_mtime,
    }


def _jsonable_group(group: dict[str, Any]) -> dict[str, Any]:
    """把 Path 转为字符串, 便于写入 JSON manifest。"""
    payload = dict(group)
    payload["record_paths"] = [Path(path).as_posix() for path in group.get("record_paths", [])]
    return payload


def _jsonable_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量转换 shard group JSON 表示。"""
    return [_jsonable_group(group) for group in groups]


def discover_internal_sweep_record_paths(
    result_root: str | Path,
    *,
    required_short_commit: str | None = None,
    required_shard_count: int | None = None,
) -> tuple[list[Path], dict[str, Any]]:
    """自动发现一组完整的内部多强度 sweep shard records。"""
    shard_root = Path(result_root) / WORKFLOW_KEY / "shard_runs"
    if not shard_root.exists():
        return [], {"mode": "internal_sweep", "candidate_group_count": 0, "selected_group": None}
    candidates = []
    for child in sorted(path for path in shard_root.iterdir() if path.is_dir()):
        parsed = _parse_internal_sweep_run_dir(child)
        if parsed is None or not parsed["record_path"].exists():
            continue
        if required_short_commit and parsed["short_commit"] != required_short_commit:
            continue
        if required_shard_count is not None and parsed["shard_count"] != int(required_shard_count):
            continue
        candidates.append(parsed)
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for item in candidates:
        groups.setdefault((str(item["short_commit"]), int(item["shard_count"])), []).append(item)
    group_payloads: list[dict[str, Any]] = []
    for (short_commit, shard_count), items in groups.items():
        by_index = {int(item["shard_index"]): item for item in items}
        missing = [index for index in range(shard_count) if index not in by_index]
        group_payloads.append(
            {
                "short_commit": short_commit,
                "shard_count": shard_count,
                "shard_indexes": sorted(by_index),
                "complete": not missing,
                "missing_shard_indexes": missing,
                "record_paths": [by_index[index]["record_path"] for index in sorted(by_index)],
                "latest_mtime": max(float(item["latest_mtime"]) for item in items),
            }
        )
    complete_groups = [group for group in group_payloads if group["complete"]]
    if not complete_groups:
        return [], {
            "mode": "internal_sweep",
            "candidate_group_count": len(group_payloads),
            "selected_group": None,
            "candidate_groups": _jsonable_groups(group_payloads),
        }
    selected = max(complete_groups, key=lambda group: float(group["latest_mtime"]))
    return list(selected["record_paths"]), {
        "mode": "internal_sweep",
        "candidate_group_count": len(group_payloads),
        "selected_group": _jsonable_group(selected),
    }


def discover_record_paths(
    result_root: str | Path,
    *,
    source_mode: str = "all",
    required_short_commit: str | None = None,
    required_shard_count: int | None = None,
) -> tuple[list[Path], dict[str, Any]]:
    """从默认 shard_runs 目录自动发现 attack strength records。"""
    if source_mode == "internal_sweep":
        return discover_internal_sweep_record_paths(
            result_root,
            required_short_commit=required_short_commit,
            required_shard_count=required_shard_count,
        )
    shard_root = Path(result_root) / WORKFLOW_KEY / "shard_runs"
    if not shard_root.exists():
        return [], {"mode": source_mode, "record_count": 0}
    patterns = {
        "base_records": "attack_strength_curve_probe_base_records_*/records/attack_strength_event_scores.jsonl",
        "all": "*/records/attack_strength_event_scores.jsonl",
    }
    if source_mode not in patterns:
        raise ValueError("source_mode must be internal_sweep, base_records, or all")
    paths = sorted(shard_root.glob(patterns[source_mode]))
    return paths, {"mode": source_mode, "record_count": len(paths)}


def resolve_short_commit() -> str:
    """读取当前仓库短 commit。"""
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


def score_of(record: dict[str, Any]) -> float | None:
    """从记录中解析检测分数。"""
    if record.get("score") is not None:
        return float(record["score"])
    if record.get("S_final") is not None:
        return float(record["S_final"])
    evidence_scores = record.get("evidence_scores") or {}
    if evidence_scores.get("S_final") is not None:
        return float(evidence_scores["S_final"])
    return None


def is_positive(record: dict[str, Any]) -> bool:
    """判断记录是否为正样本。"""
    return record.get("sample_role") in POSITIVE_ROLES


def is_negative(record: dict[str, Any]) -> bool:
    """判断记录是否为负样本。"""
    return record.get("sample_role") in NEGATIVE_ROLES


def calibrate_threshold(scores: list[float], target_fpr: float) -> float | None:
    """从 calibration negatives 校准固定 FPR 阈值。

    阈值只依赖 calibration split 的 negatives。实现采用保守分位策略, 使 test split 不参与阈值选择。
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


def normalize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """标准化 attack strength records 的关键字段。"""
    normalized: list[dict[str, Any]] = []
    for record in records:
        score = score_of(record)
        if score is None:
            continue
        attack_strength_value = record.get("attack_strength_value", record.get("attack_strength"))
        normalized.append(
            {
                "method_name": record.get("method_name") or record.get("method_variant"),
                "attack_name": record.get("attack_name"),
                "attack_strength_name": record.get("attack_strength_name") or str(attack_strength_value),
                "attack_strength_value": float(attack_strength_value),
                "split": record.get("split"),
                "sample_role": record.get("sample_role"),
                "score": float(score),
                "source_mode": record.get("source_mode", "full_multi_strength_sweep"),
                "source_artifact": record.get("source_artifact", "records/attack_strength_event_scores.jsonl"),
            }
        )
    return normalized


def build_attack_strength_tables(
    records: list[dict[str, Any]],
    *,
    target_fpr: float = 0.01,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """从标准化 records 构建 TPR 表、AUC 表和曲线数据。"""
    normalized = normalize_records(records)
    thresholds: dict[str, float | None] = {}
    for method_name in sorted({str(row["method_name"]) for row in normalized}):
        calibration_negative_scores = [
            row["score"]
            for row in normalized
            if row["method_name"] == method_name and row["split"] == "calibration" and is_negative(row)
        ]
        thresholds[method_name] = calibrate_threshold(calibration_negative_scores, target_fpr)

    grouped: dict[tuple[str, str, str, float], list[dict[str, Any]]] = {}
    for row in normalized:
        if row["split"] != "test":
            continue
        if row["attack_name"] in CALIBRATION_ONLY_ATTACKS:
            continue
        grouped.setdefault(
            (
                str(row["method_name"]),
                str(row["attack_name"]),
                str(row["attack_strength_name"]),
                float(row["attack_strength_value"]),
            ),
            [],
        ).append(row)

    tpr_rows: list[dict[str, Any]] = []
    auc_rows: list[dict[str, Any]] = []
    for (method_name, attack_name, strength_name, strength_value), group_rows in sorted(grouped.items()):
        threshold = thresholds.get(method_name)
        positives = [row for row in group_rows if is_positive(row)]
        negatives = [row for row in group_rows if is_negative(row)]
        positive_count = len(positives)
        negative_count = len(negatives)
        tpr = None if threshold is None or positive_count == 0 else sum(row["score"] >= threshold for row in positives) / positive_count
        fpr = None if threshold is None or negative_count == 0 else sum(row["score"] >= threshold for row in negatives) / negative_count
        labels_and_scores = [(1, row["score"]) for row in positives] + [(0, row["score"]) for row in negatives]
        auc = compute_auc(labels_and_scores)
        common = {
            "method_name": method_name,
            "attack_name": attack_name,
            "attack_strength_name": strength_name,
            "attack_strength_value": strength_value,
            "target_fpr": target_fpr,
            "threshold": threshold,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "source_artifact": "records/attack_strength_event_scores.jsonl",
        }
        tpr_rows.append({**common, "tpr_at_target_fpr": tpr, "fpr_at_threshold": fpr})
        auc_rows.append({**common, "auc": auc})
    figure_rows = [
        {
            "method_name": row["method_name"],
            "attack_name": row["attack_name"],
            "attack_strength_name": row["attack_strength_name"],
            "attack_strength_value": row["attack_strength_value"],
            "target_fpr": row["target_fpr"],
            "metric_name": "tpr_at_target_fpr",
            "metric_value": row["tpr_at_target_fpr"],
        }
        for row in tpr_rows
    ] + [
        {
            "method_name": row["method_name"],
            "attack_name": row["attack_name"],
            "attack_strength_name": row["attack_strength_name"],
            "attack_strength_value": row["attack_strength_value"],
            "target_fpr": row["target_fpr"],
            "metric_name": "auc",
            "metric_value": row["auc"],
        }
        for row in auc_rows
    ]
    return tpr_rows, auc_rows, figure_rows


def read_records_from_paths(record_paths: list[Path]) -> list[dict[str, Any]]:
    """读取多个 shard record 文件。"""
    records: list[dict[str, Any]] = []
    for record_path in record_paths:
        records.extend(read_jsonl(record_path))
    return records


def build_attack_strength_artifacts(
    *,
    output_root: str | Path,
    record_paths: list[Path],
    run_id: str | None = None,
    target_fpr: float = 0.01,
) -> dict[str, Any]:
    """聚合 attack strength records 并写出论文可消费产物。"""
    if not record_paths:
        raise FileNotFoundError("attack_strength_event_scores.jsonl 记录路径不能为空。")
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)
    actual_run_id = run_id or f"{WORKFLOW_KEY}_{utc_timestamp()}_{resolve_short_commit()[:7]}"
    records = normalize_records(read_records_from_paths(record_paths))
    record_path = output_root_path / "records" / "attack_strength_event_scores.jsonl"
    write_jsonl(record_path, records)
    tpr_rows, auc_rows, figure_rows = build_attack_strength_tables(records, target_fpr=target_fpr)
    tpr_fields = [
        "method_name", "attack_name", "attack_strength_name", "attack_strength_value", "target_fpr", "threshold",
        "positive_count", "negative_count", "tpr_at_target_fpr", "fpr_at_threshold", "source_artifact",
    ]
    auc_fields = [
        "method_name", "attack_name", "attack_strength_name", "attack_strength_value", "target_fpr", "threshold",
        "positive_count", "negative_count", "auc", "source_artifact",
    ]
    figure_fields = [
        "method_name", "attack_name", "attack_strength_name", "attack_strength_value",
        "target_fpr", "metric_name", "metric_value",
    ]
    write_csv(output_root_path / "tables" / "attack_strength_tpr_table.csv", tpr_rows, tpr_fields)
    write_csv(output_root_path / "tables" / "attack_strength_auc_table.csv", auc_rows, auc_fields)
    write_csv(output_root_path / "figure_data" / "attack_strength_curve_figure_data.csv", figure_rows, figure_fields)
    complete_attacks = sorted({row["attack_name"] for row in tpr_rows})
    complete_methods = sorted({row["method_name"] for row in tpr_rows})
    source_modes = sorted({str(row.get("source_mode", "full_multi_strength_sweep")) for row in records})
    base_records_only = "from_stage_two_existing_records" in source_modes
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": actual_run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "record_paths": [path.as_posix() for path in record_paths],
        "record_count": len(records),
        "tpr_row_count": len(tpr_rows),
        "auc_row_count": len(auc_rows),
        "target_fpr": target_fpr,
        "complete_attacks": complete_attacks,
        "complete_methods": complete_methods,
        "source_modes": source_modes,
        "claim_support_allowed": (
            bool(tpr_rows)
            and all(method in complete_methods for method in INTERNAL_METHODS)
            and not base_records_only
        ),
        "claim_support_blocking_reason": (
            "base_records_only_not_full_multi_strength_sweep" if base_records_only else None
        ),
        "source_digest": compute_object_digest({"record_paths": [path.as_posix() for path in record_paths]}),
        "artifact_digests": {
            "attack_strength_event_scores": compute_file_digest(record_path),
            "attack_strength_tpr_table": compute_file_digest(output_root_path / "tables" / "attack_strength_tpr_table.csv"),
            "attack_strength_auc_table": compute_file_digest(output_root_path / "tables" / "attack_strength_auc_table.csv"),
            "attack_strength_curve_figure_data": compute_file_digest(output_root_path / "figure_data" / "attack_strength_curve_figure_data.csv"),
        },
    }
    manifest_path = output_root_path / "artifacts" / "attack_strength_curve_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix(), "output_root": output_root_path.as_posix()}

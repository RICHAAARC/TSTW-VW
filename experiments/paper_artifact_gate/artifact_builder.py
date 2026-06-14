"""阶段四 paper artifact gate 的论文表格与 claim audit 构建器。

该模块只读取已经完成的阶段二聚合包和阶段三 baseline 聚合包, 不重新运行模型, 也不手工拼接结论。
它的职责是把受治理 records/tables/manifest 转换为投稿图表和 claim audit 可以直接消费的统一产物。
"""

from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from main.core.digest import compute_file_digest, compute_object_digest
from experiments.paper_artifact_gate.figure_builder import build_paper_figures

WORKFLOW_KEY = "paper_artifact_gate"
STAGE_TWO_ZIP_MEMBER_PREFIX = "real_video_vae_latent_probe_shard_aggregated"
INTERNAL_METHODS = ("frame_prc", "tubelet_only", "tubelet_sync")
EXTERNAL_BASELINES = ("external_videoseal", "external_rivagan", "external_hidden_framewise")
TEMPORAL_SYNC_ATTACKS = {"local_clip", "temporal_crop", "frame_dropping", "speed_change"}
POSITIVE_ROLES = {"watermarked_positive", "attacked_positive"}
NEGATIVE_ROLES = {"clean_negative", "attacked_negative"}


@dataclass(frozen=True)
class PaperArtifactInputs:
    """阶段四构建所需的受治理输入路径。"""

    stage_two_root: Path
    baseline_aggregation_roots: dict[str, Path]
    temporal_quality_root: Path | None = None


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    """读取 UTF-8 CSV 文件并返回字典行。"""
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """写出 UTF-8 CSV 表格, 字段顺序由 fieldnames 固定。"""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def read_json(path: str | Path) -> dict[str, Any]:
    """读取 UTF-8 JSON 文件。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latest_child_dir(root: str | Path) -> Path | None:
    """返回目录下最近修改的子目录。"""
    root_path = Path(root)
    if not root_path.exists():
        return None
    children = [path for path in root_path.iterdir() if path.is_dir()]
    if not children:
        return None
    return max(children, key=lambda path: path.stat().st_mtime)


def discover_latest_inputs(result_root: str | Path, baseline_names: Iterable[str] = EXTERNAL_BASELINES) -> PaperArtifactInputs:
    """从结果根目录自动发现最新阶段二聚合包与每个 baseline 的最新聚合包。"""
    result_root_path = Path(result_root)
    stage_two_root = latest_child_dir(result_root_path / "real_video_vae_latent_probe" / "shard_aggregated")
    if stage_two_root is None:
        raise FileNotFoundError("未找到 real_video_vae_latent_probe/shard_aggregated 下的阶段二聚合结果。")
    baseline_roots: dict[str, Path] = {}
    for baseline_name in baseline_names:
        baseline_root = latest_child_dir(
            result_root_path / "baseline_comparison_gate" / baseline_name / "shard_aggregated"
        )
        if baseline_root is None:
            raise FileNotFoundError(f"未找到 {baseline_name} 的 baseline shard_aggregated 聚合结果。")
        baseline_roots[baseline_name] = baseline_root
    temporal_quality_root = latest_child_dir(result_root_path / "temporal_quality_metric_probe" / "shard_aggregated")
    return PaperArtifactInputs(
        stage_two_root=stage_two_root,
        baseline_aggregation_roots=baseline_roots,
        temporal_quality_root=temporal_quality_root,
    )


def resolve_stage_two_zip(stage_two_root: str | Path) -> Path:
    """定位阶段二聚合包 zip 文件。"""
    root = Path(stage_two_root)
    candidates = sorted((root / "packages").glob("*.zip"))
    if not candidates:
        raise FileNotFoundError(f"阶段二聚合目录缺少 packages/*.zip: {root}")
    return candidates[0]


def read_stage_two_csv(stage_two_root: str | Path, relative_name: str) -> list[dict[str, str]]:
    """从阶段二瘦身 zip 中读取指定 CSV。"""
    archive_path = resolve_stage_two_zip(stage_two_root)
    member_name = f"{STAGE_TWO_ZIP_MEMBER_PREFIX}/{relative_name}"
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(member_name) as handle:
            text = handle.read().decode("utf-8")
    return list(csv.DictReader(text.splitlines()))


def safe_float(value: Any) -> float | None:
    """把 CSV 字段转换为 float, 空字段返回 None。"""
    if value is None or value == "":
        return None
    return float(value)


def safe_int(value: Any) -> int:
    """把 CSV 计数字段转换为 int, 空字段视为 0。"""
    if value is None or value == "":
        return 0
    return int(float(value))


def summarize_internal_methods(stage_two_root: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """汇总阶段二内部方法总体表和攻击分解表。"""
    rows = read_stage_two_csv(stage_two_root, "tables/real_video_attack_breakdown.csv")
    method_rows: list[dict[str, Any]] = []
    attack_rows: list[dict[str, Any]] = []
    for method in INTERNAL_METHODS:
        method_source_rows = [row for row in rows if row.get("method_variant") == method]
        positive_count = 0
        positive_hits = 0.0
        negative_count = 0
        false_positives = 0.0
        for row in method_source_rows:
            pos_count = safe_int(row.get("positive_count"))
            tpr = safe_float(row.get("attacked_positive_TPR") or row.get("clean_positive_TPR"))
            if pos_count and tpr is not None:
                positive_count += pos_count
                positive_hits += pos_count * tpr
            neg_count = safe_int(row.get("negative_count"))
            fpr = safe_float(row.get("attacked_negative_FPR") or row.get("clean_negative_FPR"))
            if neg_count and fpr is not None:
                negative_count += neg_count
                false_positives += neg_count * fpr
        method_rows.append(
            {
                "method_name": method,
                "method_group": "internal_ablation",
                "target_fpr": 0.01,
                "record_count": positive_count + negative_count,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "tpr_at_target_fpr": None if positive_count == 0 else positive_hits / positive_count,
                "fpr_at_threshold": None if negative_count == 0 else false_positives / negative_count,
                "source_artifact": "real_video_vae_latent_probe/tables/real_video_attack_breakdown.csv",
            }
        )
        for row in method_source_rows:
            attack_rows.append(
                {
                    "method_name": method,
                    "method_group": "internal_ablation",
                    "attack_name": row.get("attack_name"),
                    "target_fpr": 0.01,
                    "positive_count": safe_int(row.get("positive_count")),
                    "negative_count": safe_int(row.get("negative_count")),
                    "tpr_at_target_fpr": safe_float(row.get("attacked_positive_TPR") or row.get("clean_positive_TPR")),
                    "fpr_at_threshold": safe_float(row.get("attacked_negative_FPR") or row.get("clean_negative_FPR")),
                    "source_artifact": "real_video_vae_latent_probe/tables/real_video_attack_breakdown.csv",
                }
            )
    return method_rows, attack_rows


def summarize_external_baselines(baseline_roots: dict[str, Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """读取三个外部 baseline 聚合包并转换为统一论文表。"""
    method_rows: list[dict[str, Any]] = []
    attack_rows: list[dict[str, Any]] = []
    for baseline_name, root in sorted(baseline_roots.items()):
        manifest = read_json(root / "artifacts" / "baseline_score_records_aggregation_manifest.json")
        if not manifest.get("formal_fixed_fpr_complete") or not manifest.get("claim_support_allowed"):
            raise ValueError(f"baseline 聚合结果未通过 fixed-FPR claim 支撑检查: {baseline_name}")
        comparison_rows = read_csv_rows(root / "tables" / "baseline_comparison_table.csv")
        if len(comparison_rows) != 1:
            raise ValueError(f"baseline_comparison_table 应只有一行: {baseline_name}")
        comparison = comparison_rows[0]
        method_rows.append(
            {
                "method_name": baseline_name,
                "method_group": "external_baseline",
                "target_fpr": safe_float(comparison.get("target_fpr")),
                "record_count": safe_int(comparison.get("record_count")),
                "positive_count": safe_int(comparison.get("positive_count")),
                "negative_count": safe_int(comparison.get("negative_count")),
                "tpr_at_target_fpr": safe_float(comparison.get("tpr_at_target_fpr")),
                "fpr_at_threshold": safe_float(comparison.get("fpr_at_threshold")),
                "source_artifact": f"baseline_comparison_gate/{baseline_name}/tables/baseline_comparison_table.csv",
            }
        )
        for row in read_csv_rows(root / "tables" / "baseline_attack_breakdown.csv"):
            attack_rows.append(
                {
                    "method_name": baseline_name,
                    "method_group": "external_baseline",
                    "attack_name": row.get("attack_name"),
                    "target_fpr": safe_float(row.get("target_fpr")),
                    "positive_count": safe_int(row.get("positive_count")),
                    "negative_count": safe_int(row.get("negative_count")),
                    "tpr_at_target_fpr": safe_float(row.get("tpr_at_target_fpr")),
                    "fpr_at_threshold": safe_float(row.get("fpr_at_threshold")),
                    "source_artifact": f"baseline_comparison_gate/{baseline_name}/tables/baseline_attack_breakdown.csv",
                }
            )
    return method_rows, attack_rows


def build_sync_gain_rows(attack_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """构建显式同步机制相对 tubelet_only 的增益表。"""
    by_attack_method = {(row["attack_name"], row["method_name"]): row for row in attack_rows}
    output_rows: list[dict[str, Any]] = []
    for attack_name in sorted({row["attack_name"] for row in attack_rows if row["method_group"] == "internal_ablation"}):
        only = by_attack_method.get((attack_name, "tubelet_only"))
        sync = by_attack_method.get((attack_name, "tubelet_sync"))
        if not only or not sync:
            continue
        only_tpr = safe_float(only.get("tpr_at_target_fpr"))
        sync_tpr = safe_float(sync.get("tpr_at_target_fpr"))
        only_fpr = safe_float(only.get("fpr_at_threshold"))
        sync_fpr = safe_float(sync.get("fpr_at_threshold"))
        output_rows.append(
            {
                "attack_name": attack_name,
                "attack_group": "temporal_sync_sensitive" if attack_name in TEMPORAL_SYNC_ATTACKS else "general_robustness",
                "tubelet_only_tpr": only_tpr,
                "tubelet_sync_tpr": sync_tpr,
                "sync_gain_tpr": None if only_tpr is None or sync_tpr is None else sync_tpr - only_tpr,
                "tubelet_only_fpr": only_fpr,
                "tubelet_sync_fpr": sync_fpr,
                "sync_fpr_delta": None if only_fpr is None or sync_fpr is None else sync_fpr - only_fpr,
                "claim_support_allowed": (sync_tpr is not None and only_tpr is not None and sync_tpr > only_tpr and (sync_fpr or 0.0) <= 0.01),
            }
        )
    return output_rows


def build_claim_audit_rows(
    *,
    method_rows: list[dict[str, Any]],
    sync_gain_rows: list[dict[str, Any]],
    baseline_roots: dict[str, Path],
) -> list[dict[str, Any]]:
    """生成阶段四 claim audit 总表。"""
    by_name = {row["method_name"]: row for row in method_rows}
    tubelet_sync = by_name.get("tubelet_sync")
    tubelet_only = by_name.get("tubelet_only")
    external_rows = [row for row in method_rows if row["method_group"] == "external_baseline"]
    temporal_rows = [row for row in sync_gain_rows if row["attack_group"] == "temporal_sync_sensitive"]
    sync_beats_only = bool(
        tubelet_sync
        and tubelet_only
        and safe_float(tubelet_sync["tpr_at_target_fpr"]) is not None
        and safe_float(tubelet_only["tpr_at_target_fpr"]) is not None
        and float(tubelet_sync["tpr_at_target_fpr"]) > float(tubelet_only["tpr_at_target_fpr"])
    )
    sync_beats_external = bool(
        tubelet_sync
        and external_rows
        and all(float(tubelet_sync["tpr_at_target_fpr"]) > float(row["tpr_at_target_fpr"]) for row in external_rows)
    )
    temporal_sync_gain = bool(temporal_rows and all(float(row["sync_gain_tpr"]) > 0.0 for row in temporal_rows))
    all_baselines_ready = all(
        read_json(root / "artifacts" / "baseline_score_records_aggregation_manifest.json").get("formal_fixed_fpr_complete")
        for root in baseline_roots.values()
    )
    rows = [
        {
            "claim_name": "fixed_low_fpr_protocol_complete",
            "claim_support_allowed": all_baselines_ready,
            "evidence_artifact": "tables/paper_method_comparison_table.csv; tables/paper_external_baseline_table.csv",
            "blocking_reason": "" if all_baselines_ready else "missing_baseline_fixed_fpr_artifact",
        },
        {
            "claim_name": "explicit_sync_beats_tubelet_only",
            "claim_support_allowed": sync_beats_only,
            "evidence_artifact": "tables/paper_sync_gain_table.csv",
            "blocking_reason": "" if sync_beats_only else "tubelet_sync_not_greater_than_tubelet_only",
        },
        {
            "claim_name": "explicit_sync_improves_temporal_attacks",
            "claim_support_allowed": temporal_sync_gain,
            "evidence_artifact": "tables/paper_sync_gain_table.csv",
            "blocking_reason": "" if temporal_sync_gain else "missing_positive_temporal_sync_gain",
        },
        {
            "claim_name": "tubelet_sync_beats_external_video_watermark_baselines",
            "claim_support_allowed": sync_beats_external,
            "evidence_artifact": "tables/paper_method_comparison_table.csv; tables/paper_external_baseline_table.csv",
            "blocking_reason": "" if sync_beats_external else "tubelet_sync_not_greater_than_all_external_baselines",
        },
    ]
    return rows



def read_stage_two_jsonl(stage_two_root: str | Path, relative_name: str) -> list[dict[str, Any]]:
    """从阶段二瘦身 zip 中读取指定 JSONL。"""
    archive_path = resolve_stage_two_zip(stage_two_root)
    member_name = f"{STAGE_TWO_ZIP_MEMBER_PREFIX}/{relative_name}"
    with zipfile.ZipFile(archive_path) as archive:
        text = archive.read(member_name).decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def compute_auc_from_scores(labels_and_scores: list[tuple[int, float]]) -> float | None:
    """计算二分类 ROC AUC。

    该实现使用秩统计公式, 可处理并列分数。标签 1 表示 positive, 标签 0 表示 negative。
    """
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


def normalized_detection_records(inputs: PaperArtifactInputs) -> list[dict[str, Any]]:
    """把内部方法 records 和外部 baseline records 统一为 ROC/AUC 计算输入。"""
    records: list[dict[str, Any]] = []
    for row in read_stage_two_jsonl(inputs.stage_two_root, "records/event_scores.jsonl"):
        if row.get("split") != "test":
            continue
        score = ((row.get("evidence_scores") or {}).get("S_final"))
        if score is None:
            continue
        records.append(
            {
                "method_name": row.get("method_variant"),
                "method_group": "internal_ablation",
                "attack_name": row.get("attack_name"),
                "sample_role": row.get("sample_role"),
                "score": float(score),
                "source_artifact": "real_video_vae_latent_probe/records/event_scores.jsonl",
            }
        )
    for baseline_name, root in sorted(inputs.baseline_aggregation_roots.items()):
        record_path = root / "records" / "baseline_formal_score_records.jsonl"
        for row in record_path.read_text(encoding="utf-8").splitlines():
            if not row.strip():
                continue
            payload = json.loads(row)
            if payload.get("split") != "test" or payload.get("baseline_score") is None:
                continue
            records.append(
                {
                    "method_name": baseline_name,
                    "method_group": "external_baseline",
                    "attack_name": payload.get("attack_name"),
                    "sample_role": payload.get("sample_role"),
                    "score": float(payload.get("baseline_score")),
                    "source_artifact": f"baseline_comparison_gate/{baseline_name}/records/baseline_formal_score_records.jsonl",
                }
            )
    return records


def build_roc_auc_rows(inputs: PaperArtifactInputs) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """构建总体和分攻击 AUC 表, 同时生成轻量 ROC 曲线采样数据。"""
    records = normalized_detection_records(inputs)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in records:
        groups.setdefault((row["method_name"], row["method_group"], "overall"), []).append(row)
        groups.setdefault((row["method_name"], row["method_group"], str(row["attack_name"])), []).append(row)
    auc_rows: list[dict[str, Any]] = []
    roc_rows: list[dict[str, Any]] = []
    for (method_name, method_group, attack_name), group_rows in sorted(groups.items()):
        labels_and_scores = []
        for row in group_rows:
            role = row.get("sample_role")
            if role in POSITIVE_ROLES:
                labels_and_scores.append((1, float(row["score"])))
            elif role in NEGATIVE_ROLES:
                labels_and_scores.append((0, float(row["score"])))
        positive_count = sum(label == 1 for label, _ in labels_and_scores)
        negative_count = sum(label == 0 for label, _ in labels_and_scores)
        auc_value = compute_auc_from_scores(labels_and_scores)
        auc_rows.append(
            {
                "method_name": method_name,
                "method_group": method_group,
                "attack_name": attack_name,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "auc": auc_value,
                "source_artifact": group_rows[0].get("source_artifact") if group_rows else "",
            }
        )
        if positive_count and negative_count:
            unique_scores = sorted({score for _, score in labels_and_scores}, reverse=True)
            if len(unique_scores) > 101:
                step = max(1, len(unique_scores) // 100)
                thresholds = unique_scores[::step]
                if unique_scores[-1] not in thresholds:
                    thresholds.append(unique_scores[-1])
            else:
                thresholds = unique_scores
            for threshold in thresholds:
                tp = sum(label == 1 and score >= threshold for label, score in labels_and_scores)
                fp = sum(label == 0 and score >= threshold for label, score in labels_and_scores)
                roc_rows.append(
                    {
                        "method_name": method_name,
                        "method_group": method_group,
                        "attack_name": attack_name,
                        "threshold": threshold,
                        "tpr": tp / positive_count,
                        "fpr": fp / negative_count,
                    }
                )
    return auc_rows, roc_rows


def build_quality_summary_rows(stage_two_root: str | Path) -> list[dict[str, Any]]:
    """从阶段二 quality_table 汇总论文质量指标。

    当前项目已正式支持 PSNR、SSIM、LPIPS 和 CLIP similarity evidence。FID/FVD/BLIP 不在本轮已冻结结果中,
    因此不在该表中伪造。
    """
    rows = read_stage_two_csv(stage_two_root, "tables/quality_table.csv")
    by_method: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_method.setdefault(row["method_variant"], []).append(row)
    output_rows: list[dict[str, Any]] = []
    for method, method_rows in sorted(by_method.items()):
        total = sum(safe_int(row.get("video_count")) for row in method_rows)
        def weighted_mean(field: str) -> float | None:
            numerator = 0.0
            denominator = 0
            for row in method_rows:
                count = safe_int(row.get("video_count"))
                value = safe_float(row.get(field))
                if count and value is not None:
                    numerator += count * value
                    denominator += count
            return None if denominator == 0 else numerator / denominator
        output_rows.append(
            {
                "method_name": method,
                "video_count": total,
                "watermarked_video_psnr_finite_mean": weighted_mean("watermarked_video_psnr_finite_mean"),
                "watermarked_video_ssim_mean": weighted_mean("watermarked_video_ssim_mean"),
                "watermarked_video_lpips_mean": weighted_mean("watermarked_video_lpips_mean"),
                "quality_failure_count": sum(safe_int(row.get("quality_failure_count")) for row in method_rows),
                "source_artifact": "real_video_vae_latent_probe/tables/quality_table.csv",
            }
        )
    return output_rows


def build_runtime_efficiency_rows(baseline_roots: dict[str, Path]) -> list[dict[str, Any]]:
    """汇总外部 baseline 的正式计分运行耗时证据。

    该表只读取阶段三聚合包中的 `baseline_runtime_table.csv`, 不重新估算或伪造内部方法耗时。
    后续如果阶段二补充了内部方法逐方法耗时, 可以在同一表中追加 `internal_ablation` 行。
    """
    rows: list[dict[str, Any]] = []
    for baseline_name, root in sorted(baseline_roots.items()):
        runtime_rows = read_csv_rows(root / "tables" / "baseline_runtime_table.csv")
        if len(runtime_rows) != 1:
            raise ValueError(f"baseline_runtime_table 应只包含一行: {baseline_name}")
        runtime = runtime_rows[0]
        record_count = safe_int(runtime.get("record_count"))
        runtime_sum = safe_float(runtime.get("runtime_seconds_sum"))
        runtime_mean = safe_float(runtime.get("runtime_seconds_mean"))
        rows.append(
            {
                "method_name": baseline_name,
                "method_group": "external_baseline",
                "record_count": record_count,
                "runtime_seconds_sum": runtime_sum,
                "runtime_hours_sum": None if runtime_sum is None else runtime_sum / 3600.0,
                "runtime_seconds_mean": runtime_mean,
                "runtime_seconds_per_1000_records": None
                if runtime_sum is None or record_count == 0
                else runtime_sum / record_count * 1000.0,
                "source_artifact": f"baseline_comparison_gate/{baseline_name}/tables/baseline_runtime_table.csv",
            }
        )
    return rows


def discover_stage_two_shard_roots(stage_two_root: str | Path) -> list[Path]:
    """根据阶段二聚合目录发现同一 Drive 结果树中的 shard run 目录。

    聚合 zip 为了瘦身通常不包含 mp4 样例, 因此视觉样例图需要回到已落盘的 shard run。
    该函数只做路径发现, 不重新运行实验。
    """
    root = Path(stage_two_root)
    result_root = root.parents[2]
    shard_root = result_root / "real_video_vae_latent_probe" / "shard_runs"
    if not shard_root.exists():
        return []
    return sorted(path for path in shard_root.iterdir() if path.is_dir() and (path / "compat_run_root").exists())


def build_visual_example_rows(stage_two_root: str | Path) -> list[dict[str, Any]]:
    """从已完成的阶段二 shard run 中抽取可追溯视觉样例。

    输出只记录已存在的 source / decoded / attacked mp4 路径, 后续图表生成器再抽帧排版。
    """
    preferred_attacks = ("h264_compression", "h265_compression", "temporal_crop", "local_clip", "crop_resize", "blur")
    rows: list[dict[str, Any]] = []
    seen_attacks: set[str] = set()
    seen_source_ids: set[str] = set()
    for shard_root in discover_stage_two_shard_roots(stage_two_root):
        compat_root = shard_root / "compat_run_root"
        record_path = compat_root / "records" / "event_scores.jsonl"
        if not record_path.exists():
            continue
        for line in record_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            attack_name = payload.get("attack_name")
            if attack_name not in preferred_attacks or attack_name in seen_attacks:
                continue
            if (
                payload.get("split") != "test"
                or payload.get("sample_role") != "attacked_positive"
                or payload.get("method_variant") != "tubelet_sync"
            ):
                continue
            trace = payload.get("mechanism_trace") or {}
            source_id = str(trace.get("video_source_id", ""))
            if source_id in seen_source_ids:
                continue
            source_path = compat_root / str(trace.get("video_source_relpath", ""))
            decoded_path = compat_root / str(trace.get("decoded_video_relpath", ""))
            attacked_path = compat_root / str(trace.get("attacked_video_relpath", ""))
            if not (source_path.exists() and decoded_path.exists() and attacked_path.exists()):
                continue
            rows.append(
                {
                    "method_name": "tubelet_sync",
                    "attack_name": attack_name,
                    "sample_id": payload.get("sample_id"),
                    "event_id": payload.get("event_id"),
                    "decision": payload.get("decision"),
                    "score": (payload.get("evidence_scores") or {}).get("S_final"),
                    "video_source_id": source_id,
                    "shard_root": shard_root.as_posix(),
                    "source_video_path": source_path.as_posix(),
                    "decoded_video_path": decoded_path.as_posix(),
                    "attacked_video_path": attacked_path.as_posix(),
                    "source_artifact": "real_video_vae_latent_probe/shard_runs/compat_run_root/records/event_scores.jsonl",
                }
            )
            seen_attacks.add(str(attack_name))
            seen_source_ids.add(source_id)
            if len(rows) >= 4:
                return rows
    return rows


def build_temporal_quality_rows(temporal_quality_root: Path | None) -> list[dict[str, Any]]:
    """读取可选的时间质量补充 probe 聚合表。"""
    if temporal_quality_root is None:
        return []
    table_path = temporal_quality_root / "tables" / "temporal_quality_metric_table.csv"
    if not table_path.exists():
        return []
    rows = read_csv_rows(table_path)
    for row in rows:
        row["source_artifact"] = "temporal_quality_metric_probe/tables/temporal_quality_metric_table.csv"
    return rows


def build_submission_gap_audit_rows(
    *,
    has_visual_examples: bool,
    temporal_quality_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """生成与主流视频水印论文图表习惯对齐的差距审计表。

    该表用于明确哪些论文级图表已经由冻结结果支撑, 哪些仍需要新增实验。
    它不是性能结果表, 不能作为未完成指标的替代证据。
    """
    temporal_quality_rows = temporal_quality_rows or []
    t_lpips_supported = any(str(row.get("t_lpips_available")) == "True" for row in temporal_quality_rows)
    return [
        {
            "artifact_need": "fixed_fpr_tpr_table",
            "status": "supported",
            "current_artifact": "tables/paper_method_comparison_table.csv",
            "next_action": "",
        },
        {
            "artifact_need": "attack_breakdown_table",
            "status": "supported",
            "current_artifact": "tables/paper_attack_breakdown_table.csv",
            "next_action": "",
        },
        {
            "artifact_need": "roc_auc_table_and_curve",
            "status": "supported",
            "current_artifact": "tables/paper_roc_auc_table.csv; figure_data/paper_roc_curve_data.csv",
            "next_action": "",
        },
        {
            "artifact_need": "psnr_ssim_lpips_quality_table",
            "status": "supported",
            "current_artifact": "tables/paper_quality_table.csv",
            "next_action": "",
        },
        {
            "artifact_need": "temporal_quality_t_lpips_t_ssim",
            "status": (
                "supported"
                if t_lpips_supported
                else ("supported_t_ssim_only" if temporal_quality_rows else "not_supported_by_frozen_results")
            ),
            "current_artifact": "tables/paper_temporal_quality_table.csv" if temporal_quality_rows else "",
            "next_action": ""
            if t_lpips_supported
            else "当前仅支持 t-SSIM; t-LPIPS 需要在 Colab 配置 LPIPS 模型后重跑 temporal_quality_metric_probe。",
        },
        {
            "artifact_need": "baseline_runtime_efficiency_table",
            "status": "supported_external_baselines_only",
            "current_artifact": "tables/paper_runtime_efficiency_table.csv",
            "next_action": "如需内部方法端到端耗时, 需要阶段二补充逐方法 runtime records。",
        },
        {
            "artifact_need": "fid_fvd_blip_quality_table",
            "status": "not_supported_by_frozen_results",
            "current_artifact": "",
            "next_action": "需要新增真实视频生成质量评估流程后再进入 submission_readiness_gate。",
        },
        {
            "artifact_need": "attack_strength_curves",
            "status": "not_supported_by_frozen_results",
            "current_artifact": "",
            "next_action": "需要补跑多强度攻击矩阵, 不能由当前固定攻击协议外推。",
        },
        {
            "artifact_need": "visual_example_grid",
            "status": "supported" if has_visual_examples else "not_supported_by_current_builder",
            "current_artifact": "figures/paper_visual_example_grid.pdf; figures/paper_visual_example_grid.png"
            if has_visual_examples
            else "",
            "next_action": "" if has_visual_examples else "需要从冻结视频样例或可公开复现帧中导出 clean / watermarked / attacked 视觉条带。",
        },
        {
            "artifact_need": "additional_dataset_validation",
            "status": "not_supported_by_frozen_results",
            "current_artifact": "",
            "next_action": "需要在 UCF101 或 WebVid 等附加数据集上复用相同协议补跑。",
        },
    ]


def build_paper_artifacts(
    *,
    output_root: str | Path,
    inputs: PaperArtifactInputs,
    run_id: str | None = None,
    build_figures: bool = True,
) -> dict[str, Any]:
    """构建阶段四论文表格、图表数据和 claim audit 总表。"""
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)
    run_id = run_id or "paper_artifact_gate"

    internal_method_rows, internal_attack_rows = summarize_internal_methods(inputs.stage_two_root)
    external_method_rows, external_attack_rows = summarize_external_baselines(inputs.baseline_aggregation_roots)
    method_rows = internal_method_rows + external_method_rows
    attack_rows = internal_attack_rows + external_attack_rows
    sync_gain_rows = build_sync_gain_rows(attack_rows)
    roc_auc_rows, roc_curve_rows = build_roc_auc_rows(inputs)
    quality_rows = build_quality_summary_rows(inputs.stage_two_root)
    runtime_rows = build_runtime_efficiency_rows(inputs.baseline_aggregation_roots)
    visual_example_rows = build_visual_example_rows(inputs.stage_two_root)
    temporal_quality_rows = build_temporal_quality_rows(inputs.temporal_quality_root)
    gap_audit_rows = build_submission_gap_audit_rows(
        has_visual_examples=bool(visual_example_rows),
        temporal_quality_rows=temporal_quality_rows,
    )
    external_rows = [row for row in method_rows if row["method_group"] == "external_baseline"]
    claim_rows = build_claim_audit_rows(
        method_rows=method_rows,
        sync_gain_rows=sync_gain_rows,
        baseline_roots=inputs.baseline_aggregation_roots,
    )

    method_fields = [
        "method_name", "method_group", "target_fpr", "record_count", "positive_count", "negative_count",
        "tpr_at_target_fpr", "fpr_at_threshold", "source_artifact",
    ]
    attack_fields = [
        "method_name", "method_group", "attack_name", "target_fpr", "positive_count", "negative_count",
        "tpr_at_target_fpr", "fpr_at_threshold", "source_artifact",
    ]
    sync_fields = [
        "attack_name", "attack_group", "tubelet_only_tpr", "tubelet_sync_tpr", "sync_gain_tpr",
        "tubelet_only_fpr", "tubelet_sync_fpr", "sync_fpr_delta", "claim_support_allowed",
    ]
    claim_fields = ["claim_name", "claim_support_allowed", "evidence_artifact", "blocking_reason"]
    roc_auc_fields = ["method_name", "method_group", "attack_name", "positive_count", "negative_count", "auc", "source_artifact"]
    roc_curve_fields = ["method_name", "method_group", "attack_name", "threshold", "tpr", "fpr"]
    quality_fields = ["method_name", "video_count", "watermarked_video_psnr_finite_mean", "watermarked_video_ssim_mean", "watermarked_video_lpips_mean", "quality_failure_count", "source_artifact"]
    runtime_fields = [
        "method_name", "method_group", "record_count", "runtime_seconds_sum", "runtime_hours_sum",
        "runtime_seconds_mean", "runtime_seconds_per_1000_records", "source_artifact",
    ]
    visual_example_fields = [
        "method_name", "attack_name", "sample_id", "event_id", "decision", "score", "video_source_id", "shard_root",
        "source_video_path", "decoded_video_path", "attacked_video_path", "source_artifact",
    ]
    temporal_quality_fields = [
        "method_name", "attack_name", "video_role", "video_count",
        "mean_t_lpips", "std_t_lpips", "mean_t_ssim", "std_t_ssim",
        "t_lpips_available", "t_ssim_available", "source_artifact",
    ]
    gap_audit_fields = ["artifact_need", "status", "current_artifact", "next_action"]

    write_csv(output_root_path / "tables" / "paper_method_comparison_table.csv", method_rows, method_fields)
    write_csv(output_root_path / "tables" / "paper_attack_breakdown_table.csv", attack_rows, attack_fields)
    write_csv(output_root_path / "tables" / "paper_sync_gain_table.csv", sync_gain_rows, sync_fields)
    write_csv(output_root_path / "tables" / "paper_external_baseline_table.csv", external_rows, method_fields)
    write_csv(output_root_path / "figure_data" / "paper_method_comparison_figure_data.csv", method_rows, method_fields)
    write_csv(output_root_path / "figure_data" / "paper_sync_gain_figure_data.csv", sync_gain_rows, sync_fields)
    write_csv(output_root_path / "tables" / "paper_roc_auc_table.csv", roc_auc_rows, roc_auc_fields)
    write_csv(output_root_path / "figure_data" / "paper_roc_curve_data.csv", roc_curve_rows, roc_curve_fields)
    write_csv(output_root_path / "tables" / "paper_quality_table.csv", quality_rows, quality_fields)
    write_csv(output_root_path / "figure_data" / "paper_quality_figure_data.csv", quality_rows, quality_fields)
    write_csv(output_root_path / "tables" / "paper_runtime_efficiency_table.csv", runtime_rows, runtime_fields)
    write_csv(output_root_path / "figure_data" / "paper_runtime_efficiency_figure_data.csv", runtime_rows, runtime_fields)
    write_csv(output_root_path / "figure_data" / "paper_visual_example_figure_data.csv", visual_example_rows, visual_example_fields)
    write_csv(output_root_path / "tables" / "paper_temporal_quality_table.csv", temporal_quality_rows, temporal_quality_fields)
    write_csv(output_root_path / "figure_data" / "paper_temporal_quality_figure_data.csv", temporal_quality_rows, temporal_quality_fields)
    write_csv(output_root_path / "claim_audit" / "paper_submission_gap_audit.csv", gap_audit_rows, gap_audit_fields)
    write_csv(output_root_path / "claim_audit" / "paper_claim_audit.csv", claim_rows, claim_fields)

    supported_claims = [row for row in claim_rows if bool(row["claim_support_allowed"])]
    figure_summary = build_paper_figures(output_root_path) if build_figures else None

    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "stage_two_root": inputs.stage_two_root.as_posix(),
        "baseline_aggregation_roots": {name: path.as_posix() for name, path in sorted(inputs.baseline_aggregation_roots.items())},
        "temporal_quality_root": None if inputs.temporal_quality_root is None else inputs.temporal_quality_root.as_posix(),
        "method_count": len(method_rows),
        "attack_row_count": len(attack_rows),
        "sync_gain_row_count": len(sync_gain_rows),
        "claim_count": len(claim_rows),
        "roc_auc_row_count": len(roc_auc_rows),
        "quality_row_count": len(quality_rows),
        "runtime_efficiency_row_count": len(runtime_rows),
        "visual_example_row_count": len(visual_example_rows),
        "temporal_quality_row_count": len(temporal_quality_rows),
        "submission_gap_audit_row_count": len(gap_audit_rows),
        "supported_claim_count": len(supported_claims),
        "paper_artifact_gate_complete": len(supported_claims) == len(claim_rows) and (figure_summary is not None or not build_figures),
        "paper_figure_count": None if figure_summary is None else figure_summary.get("figure_count"),
        "blocking_reason": None if len(supported_claims) == len(claim_rows) else "unsupported_claims_present",
        "source_digest": compute_object_digest(
            {
                "stage_two_root": inputs.stage_two_root.as_posix(),
                "baseline_aggregation_roots": {name: path.as_posix() for name, path in sorted(inputs.baseline_aggregation_roots.items())},
                "temporal_quality_root": None if inputs.temporal_quality_root is None else inputs.temporal_quality_root.as_posix(),
            }
        ),
        "artifact_digests": {
            "paper_method_comparison_table": compute_file_digest(output_root_path / "tables" / "paper_method_comparison_table.csv"),
            "paper_attack_breakdown_table": compute_file_digest(output_root_path / "tables" / "paper_attack_breakdown_table.csv"),
            "paper_sync_gain_table": compute_file_digest(output_root_path / "tables" / "paper_sync_gain_table.csv"),
            "paper_claim_audit": compute_file_digest(output_root_path / "claim_audit" / "paper_claim_audit.csv"),
            "paper_roc_auc_table": compute_file_digest(output_root_path / "tables" / "paper_roc_auc_table.csv"),
            "paper_quality_table": compute_file_digest(output_root_path / "tables" / "paper_quality_table.csv"),
            "paper_runtime_efficiency_table": compute_file_digest(output_root_path / "tables" / "paper_runtime_efficiency_table.csv"),
            "paper_visual_example_figure_data": compute_file_digest(output_root_path / "figure_data" / "paper_visual_example_figure_data.csv"),
            "paper_temporal_quality_table": compute_file_digest(output_root_path / "tables" / "paper_temporal_quality_table.csv"),
            "paper_submission_gap_audit": compute_file_digest(output_root_path / "claim_audit" / "paper_submission_gap_audit.csv"),
            "paper_figure_manifest": None if figure_summary is None else compute_file_digest(output_root_path / "figures" / "paper_figure_manifest.json"),
        },
    }
    manifest_path = output_root_path / "artifacts" / "paper_artifact_gate_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix()}

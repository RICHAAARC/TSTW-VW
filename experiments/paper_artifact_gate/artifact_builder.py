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

WORKFLOW_KEY = "paper_artifact_gate"
STAGE_TWO_ZIP_MEMBER_PREFIX = "real_video_vae_latent_probe_shard_aggregated"
INTERNAL_METHODS = ("frame_prc", "tubelet_only", "tubelet_sync")
EXTERNAL_BASELINES = ("external_videoseal", "external_rivagan", "external_hidden_framewise")
TEMPORAL_SYNC_ATTACKS = {"local_clip", "temporal_crop", "frame_dropping", "speed_change"}


@dataclass(frozen=True)
class PaperArtifactInputs:
    """阶段四构建所需的受治理输入路径。"""

    stage_two_root: Path
    baseline_aggregation_roots: dict[str, Path]


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
    return PaperArtifactInputs(stage_two_root=stage_two_root, baseline_aggregation_roots=baseline_roots)


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


def build_paper_artifacts(
    *,
    output_root: str | Path,
    inputs: PaperArtifactInputs,
    run_id: str | None = None,
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

    write_csv(output_root_path / "tables" / "paper_method_comparison_table.csv", method_rows, method_fields)
    write_csv(output_root_path / "tables" / "paper_attack_breakdown_table.csv", attack_rows, attack_fields)
    write_csv(output_root_path / "tables" / "paper_sync_gain_table.csv", sync_gain_rows, sync_fields)
    write_csv(output_root_path / "tables" / "paper_external_baseline_table.csv", external_rows, method_fields)
    write_csv(output_root_path / "figure_data" / "paper_method_comparison_figure_data.csv", method_rows, method_fields)
    write_csv(output_root_path / "figure_data" / "paper_sync_gain_figure_data.csv", sync_gain_rows, sync_fields)
    write_csv(output_root_path / "claim_audit" / "paper_claim_audit.csv", claim_rows, claim_fields)

    supported_claims = [row for row in claim_rows if bool(row["claim_support_allowed"])]
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "stage_two_root": inputs.stage_two_root.as_posix(),
        "baseline_aggregation_roots": {name: path.as_posix() for name, path in sorted(inputs.baseline_aggregation_roots.items())},
        "method_count": len(method_rows),
        "attack_row_count": len(attack_rows),
        "sync_gain_row_count": len(sync_gain_rows),
        "claim_count": len(claim_rows),
        "supported_claim_count": len(supported_claims),
        "paper_artifact_gate_complete": len(supported_claims) == len(claim_rows),
        "blocking_reason": None if len(supported_claims) == len(claim_rows) else "unsupported_claims_present",
        "source_digest": compute_object_digest(
            {
                "stage_two_root": inputs.stage_two_root.as_posix(),
                "baseline_aggregation_roots": {name: path.as_posix() for name, path in sorted(inputs.baseline_aggregation_roots.items())},
            }
        ),
        "artifact_digests": {
            "paper_method_comparison_table": compute_file_digest(output_root_path / "tables" / "paper_method_comparison_table.csv"),
            "paper_attack_breakdown_table": compute_file_digest(output_root_path / "tables" / "paper_attack_breakdown_table.csv"),
            "paper_sync_gain_table": compute_file_digest(output_root_path / "tables" / "paper_sync_gain_table.csv"),
            "paper_claim_audit": compute_file_digest(output_root_path / "claim_audit" / "paper_claim_audit.csv"),
        },
    }
    manifest_path = output_root_path / "artifacts" / "paper_artifact_gate_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix()}

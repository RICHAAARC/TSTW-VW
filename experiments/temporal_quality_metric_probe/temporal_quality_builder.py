"""构建 `temporal_quality_metric_probe` 的记录、表格和 manifest。

该模块只读取已经落盘的阶段二真实视频 shard run, 不重新运行水印方法或 VAE。
它的职责是从 source / decoded / attacked mp4 中计算相邻帧时间质量指标, 为阶段四论文图表提供可重建输入。
"""

from __future__ import annotations

import csv
import json
import statistics
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from skimage.metrics import structural_similarity

from main.analysis.real_video_quality_metrics import _compute_lpips_score
from main.core.digest import compute_file_digest, compute_object_digest
from main.video.video_io import read_video_frames

WORKFLOW_KEY = "temporal_quality_metric_probe"
INTERNAL_METHODS = ("frame_prc", "tubelet_only", "tubelet_sync")
DEFAULT_ATTACKS = ("no_attack", "h264_compression", "h265_compression", "temporal_crop", "frame_dropping")
VIDEO_ROLES = ("source", "decoded_watermarked", "attacked")


@dataclass(frozen=True)
class TemporalQualityInputs:
    """时间质量流程的输入路径。"""

    stage_two_aggregation_root: Path
    shard_roots: tuple[Path, ...]


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """写出 UTF-8 CSV, 保持字段顺序稳定。"""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """读取 JSONL 记录。"""
    records: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def latest_child_dir(root: str | Path) -> Path | None:
    """返回目录下最近修改的子目录。"""
    root_path = Path(root)
    if not root_path.exists():
        return None
    children = [path for path in root_path.iterdir() if path.is_dir()]
    if not children:
        return None
    return max(children, key=lambda path: path.stat().st_mtime)


def discover_latest_inputs(result_root: str | Path) -> TemporalQualityInputs:
    """从 TSTW results 根目录发现最新阶段二聚合包和对应 shard run。"""
    result_root_path = Path(result_root)
    stage_two_root = latest_child_dir(result_root_path / "real_video_vae_latent_probe" / "shard_aggregated")
    if stage_two_root is None:
        raise FileNotFoundError("未找到 real_video_vae_latent_probe/shard_aggregated 下的阶段二聚合结果。")
    shard_root = result_root_path / "real_video_vae_latent_probe" / "shard_runs"
    shard_roots = tuple(sorted(path for path in shard_root.glob("*") if (path / "compat_run_root").exists()))
    if not shard_roots:
        raise FileNotFoundError("未找到 real_video_vae_latent_probe/shard_runs 下的 compat_run_root。")
    return TemporalQualityInputs(stage_two_aggregation_root=stage_two_root, shard_roots=shard_roots)


def resolve_short_commit() -> str:
    """读取当前仓库短 commit, 失败时返回 unknown。"""
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
    """生成 UTC 时间戳, 用于 run_id。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def compute_temporal_ssim(frames: np.ndarray) -> tuple[float | None, float | None]:
    """计算单个视频内部相邻帧的 t-SSIM 均值和标准差。

    该指标衡量同一视频相邻帧结构相似度, 不比较两个不同视频。
    """
    if frames.ndim != 4 or frames.shape[0] < 2:
        return None, None
    scores: list[float] = []
    for index in range(frames.shape[0] - 1):
        current_frame = np.clip(frames[index], 0.0, 1.0)
        next_frame = np.clip(frames[index + 1], 0.0, 1.0)
        scores.append(
            float(
                structural_similarity(
                    current_frame,
                    next_frame,
                    channel_axis=2,
                    data_range=1.0,
                )
            )
        )
    return float(np.mean(scores)), float(np.std(scores))


def compute_temporal_lpips(
    frames: np.ndarray,
    *,
    lpips_model_root: str | Path | None,
    lpips_backbone: str,
    lpips_device: str,
    lpips_batch_size: int,
) -> tuple[float | None, str | None]:
    """计算单个视频内部相邻帧的 t-LPIPS。

    如果没有配置 LPIPS 模型目录, 返回显式缺失原因, 避免把未计算指标误标记为 supported。
    """
    if frames.ndim != 4 or frames.shape[0] < 2:
        return None, "insufficient_frames_for_t_lpips"
    if not lpips_model_root:
        return None, "lpips_model_not_configured"
    try:
        value = _compute_lpips_score(
            frames[:-1],
            frames[1:],
            lpips_model_root,
            lpips_backbone=lpips_backbone,
            lpips_device=lpips_device,
            lpips_batch_size=lpips_batch_size,
        )
    except Exception as exc:
        return None, f"t_lpips_computation_error: {str(exc)}"
    return float(value), None


def select_events(
    shard_roots: Iterable[Path],
    *,
    method_names: Iterable[str],
    attack_names: Iterable[str],
    max_events_per_method_attack: int | None,
) -> list[dict[str, Any]]:
    """从阶段二 shard run 中选择需要计算时间质量的视频事件。"""
    methods = set(method_names)
    attacks = set(attack_names)
    selected: list[dict[str, Any]] = []
    counts: dict[tuple[str, str], int] = {}
    for shard_root in shard_roots:
        compat_root = shard_root / "compat_run_root"
        record_path = compat_root / "records" / "event_scores.jsonl"
        if not record_path.exists():
            continue
        for payload in read_jsonl(record_path):
            method_name = payload.get("method_variant")
            attack_name = payload.get("attack_name")
            if payload.get("split") != "test":
                continue
            if payload.get("sample_role") != "attacked_positive":
                continue
            if method_name not in methods or attack_name not in attacks:
                continue
            key = (str(method_name), str(attack_name))
            if max_events_per_method_attack is not None and counts.get(key, 0) >= max_events_per_method_attack:
                continue
            trace = payload.get("mechanism_trace") or {}
            paths = {
                "source": compat_root / str(trace.get("video_source_relpath", "")),
                "decoded_watermarked": compat_root / str(trace.get("decoded_video_relpath", "")),
                "attacked": compat_root / str(trace.get("attacked_video_relpath", "")),
            }
            if not all(path.exists() for path in paths.values()):
                continue
            selected.append(
                {
                    "payload": payload,
                    "trace": trace,
                    "shard_root": shard_root,
                    "paths": paths,
                }
            )
            counts[key] = counts.get(key, 0) + 1
    return selected


def build_temporal_quality_records(
    *,
    inputs: TemporalQualityInputs,
    method_names: Iterable[str] = INTERNAL_METHODS,
    attack_names: Iterable[str] = DEFAULT_ATTACKS,
    max_events_per_method_attack: int | None = 5,
    lpips_model_root: str | Path | None = None,
    lpips_backbone: str = "alex",
    lpips_device: str = "cuda",
    lpips_batch_size: int = 8,
) -> list[dict[str, Any]]:
    """计算时间质量 records。"""
    selected_events = select_events(
        inputs.shard_roots,
        method_names=method_names,
        attack_names=attack_names,
        max_events_per_method_attack=max_events_per_method_attack,
    )
    records: list[dict[str, Any]] = []
    for event in selected_events:
        payload = event["payload"]
        trace = event["trace"]
        for video_role in VIDEO_ROLES:
            video_path = event["paths"][video_role]
            video = read_video_frames(video_path)
            t_ssim_mean, t_ssim_std = compute_temporal_ssim(video.frames)
            t_lpips_mean, t_lpips_failure_reason = compute_temporal_lpips(
                video.frames,
                lpips_model_root=lpips_model_root,
                lpips_backbone=lpips_backbone,
                lpips_device=lpips_device,
                lpips_batch_size=lpips_batch_size,
            )
            records.append(
                {
                    "workflow_key": WORKFLOW_KEY,
                    "method_name": payload.get("method_variant"),
                    "attack_name": payload.get("attack_name"),
                    "sample_id": payload.get("sample_id"),
                    "event_id": payload.get("event_id"),
                    "video_source_id": trace.get("video_source_id"),
                    "video_role": video_role,
                    "frame_count": int(video.frames.shape[0]),
                    "fps": video.fps,
                    "mean_t_lpips": None if t_lpips_mean is None else round(t_lpips_mean, 6),
                    "std_t_lpips": None,
                    "mean_t_ssim": None if t_ssim_mean is None else round(t_ssim_mean, 6),
                    "std_t_ssim": None if t_ssim_std is None else round(t_ssim_std, 6),
                    "lpips_model_name": f"lpips_{lpips_backbone}" if lpips_model_root else None,
                    "lpips_model_digest": None,
                    "t_lpips_failure_reason": t_lpips_failure_reason,
                    "video_path": video_path.as_posix(),
                    "source_artifact": "real_video_vae_latent_probe/shard_runs/compat_run_root/records/event_scores.jsonl",
                }
            )
    return records


def mean_or_none(values: list[float]) -> float | None:
    """计算均值, 空列表返回 None。"""
    return None if not values else float(statistics.fmean(values))


def std_or_none(values: list[float]) -> float | None:
    """计算总体标准差, 空列表返回 None。"""
    return None if not values else float(statistics.pstdev(values))


def build_temporal_quality_table(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将时间质量 records 聚合为论文可消费表。"""
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(
            (str(record["method_name"]), str(record["attack_name"]), str(record["video_role"])),
            [],
        ).append(record)
    rows: list[dict[str, Any]] = []
    for (method_name, attack_name, video_role), group_records in sorted(groups.items()):
        t_ssim_values = [float(row["mean_t_ssim"]) for row in group_records if row.get("mean_t_ssim") not in (None, "")]
        t_lpips_values = [float(row["mean_t_lpips"]) for row in group_records if row.get("mean_t_lpips") not in (None, "")]
        rows.append(
            {
                "method_name": method_name,
                "attack_name": attack_name,
                "video_role": video_role,
                "video_count": len(group_records),
                "mean_t_lpips": mean_or_none(t_lpips_values),
                "std_t_lpips": std_or_none(t_lpips_values),
                "mean_t_ssim": mean_or_none(t_ssim_values),
                "std_t_ssim": std_or_none(t_ssim_values),
                "t_lpips_available": bool(t_lpips_values),
                "t_ssim_available": bool(t_ssim_values),
                "source_artifact": "records/temporal_quality_records.jsonl",
            }
        )
    return rows


def write_temporal_quality_outputs(
    *,
    output_root: str | Path,
    inputs: TemporalQualityInputs,
    records: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    """写出 records、tables、figure_data 和 manifest。"""
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)
    record_path = output_root_path / "records" / "temporal_quality_records.jsonl"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    table_rows = build_temporal_quality_table(records)
    fields = [
        "method_name", "attack_name", "video_role", "video_count",
        "mean_t_lpips", "std_t_lpips", "mean_t_ssim", "std_t_ssim",
        "t_lpips_available", "t_ssim_available", "source_artifact",
    ]
    write_csv(output_root_path / "tables" / "temporal_quality_metric_table.csv", table_rows, fields)
    write_csv(output_root_path / "figure_data" / "temporal_quality_metric_figure_data.csv", table_rows, fields)
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "stage_two_aggregation_root": inputs.stage_two_aggregation_root.as_posix(),
        "shard_roots": [path.as_posix() for path in inputs.shard_roots],
        "record_count": len(records),
        "table_row_count": len(table_rows),
        "t_ssim_supported": any(row["t_ssim_available"] for row in table_rows),
        "t_lpips_supported": any(row["t_lpips_available"] for row in table_rows),
        "source_digest": compute_object_digest(
            {
                "stage_two_aggregation_root": inputs.stage_two_aggregation_root.as_posix(),
                "shard_roots": [path.as_posix() for path in inputs.shard_roots],
            }
        ),
        "artifact_digests": {
            "temporal_quality_records": compute_file_digest(record_path),
            "temporal_quality_metric_table": compute_file_digest(output_root_path / "tables" / "temporal_quality_metric_table.csv"),
            "temporal_quality_metric_figure_data": compute_file_digest(output_root_path / "figure_data" / "temporal_quality_metric_figure_data.csv"),
        },
        "claim_audit": {
            "temporal_quality_claim_supported": any(row["t_ssim_available"] for row in table_rows),
            "t_lpips_claim_supported": any(row["t_lpips_available"] for row in table_rows),
            "blocking_reason": None if table_rows else "no_temporal_quality_records",
        },
    }
    manifest_path = output_root_path / "artifacts" / "temporal_quality_metric_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix(), "output_root": output_root_path.as_posix()}


def run_temporal_quality_probe(
    *,
    output_root: str | Path,
    inputs: TemporalQualityInputs,
    run_id: str | None = None,
    method_names: Iterable[str] = INTERNAL_METHODS,
    attack_names: Iterable[str] = DEFAULT_ATTACKS,
    max_events_per_method_attack: int | None = 5,
    lpips_model_root: str | Path | None = None,
    lpips_backbone: str = "alex",
    lpips_device: str = "cuda",
    lpips_batch_size: int = 8,
) -> dict[str, Any]:
    """运行本地可验证的时间质量 probe。"""
    actual_run_id = run_id or f"{WORKFLOW_KEY}_{utc_timestamp()}_{resolve_short_commit()[:7]}"
    records = build_temporal_quality_records(
        inputs=inputs,
        method_names=method_names,
        attack_names=attack_names,
        max_events_per_method_attack=max_events_per_method_attack,
        lpips_model_root=lpips_model_root,
        lpips_backbone=lpips_backbone,
        lpips_device=lpips_device,
        lpips_batch_size=lpips_batch_size,
    )
    return write_temporal_quality_outputs(
        output_root=output_root,
        inputs=inputs,
        records=records,
        run_id=actual_run_id,
    )


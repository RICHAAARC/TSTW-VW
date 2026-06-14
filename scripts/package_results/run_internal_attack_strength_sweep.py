"""运行内部三方法多强度攻击曲线 shard 并产出基础 records。

该脚本属于 notebook 委托的仓库模块。它负责构造多强度攻击矩阵, 调用已经受治理的
real-video VAE runner, 再把 runner 产生的 event_scores 转换为
attack_strength_curve_probe 可以聚合的 records。Notebook 只负责传参和调度。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.attack_strength_curve_probe.attack_strength_builder import (  # noqa: E402
    ATTACKS,
    CALIBRATION_ONLY_ATTACKS,
    INTERNAL_METHODS,
    WORKFLOW_KEY,
    resolve_short_commit,
    utc_timestamp,
    write_jsonl,
)
from experiments.attack_strength_curve_probe.stage_two_record_adapter import (  # noqa: E402
    convert_stage_two_records_to_attack_strength_records,
)
from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner  # noqa: E402
from main.core.digest import compute_file_digest, compute_object_digest  # noqa: E402

FULL_SWEEP_SOURCE_MODE = "full_multi_strength_sweep"


def _parse_number_list(raw_value: str, *, value_type: type = float) -> list[Any]:
    """解析逗号分隔的数值列表, 便于 notebook 配置区直接传入曲线横轴。"""
    values: list[Any] = []
    for item in str(raw_value).split(","):
        stripped = item.strip()
        if not stripped:
            continue
        values.append(value_type(stripped))
    if not values:
        raise ValueError("数值列表不能为空")
    return values


def build_internal_multi_strength_attack_matrix(
    *,
    h264_crfs: list[int],
    h265_crfs: list[int],
    temporal_crop_keep_ratios: list[float],
    frame_drop_rates: list[float],
    target_frame_count: int,
) -> dict[str, Any]:
    """构造内部三方法曲线使用的多强度攻击矩阵。

    通用工程写法是把攻击名和参数显式写入 JSON 配置。项目特定写法是保留
    `no_attack`, 因为 fixed-FPR 阈值校准需要 clean negative 和 watermarked positive
    的无攻击记录, 而曲线本身只聚合四类受攻击 records。
    """
    attacks: list[dict[str, Any]] = [{"attack_name": "no_attack", "attack_params": {}}]
    for crf in h264_crfs:
        attacks.append(
            {
                "attack_name": "h264_compression",
                "attack_params": {"codec": "libx264", "crf": int(crf), "preset": "medium"},
            }
        )
    for crf in h265_crfs:
        attacks.append(
            {
                "attack_name": "h265_compression",
                "attack_params": {"codec": "libx265", "crf": int(crf), "preset": "medium"},
            }
        )
    for keep_ratio in temporal_crop_keep_ratios:
        bounded_keep_ratio = max(1.0 / float(target_frame_count), min(1.0, float(keep_ratio)))
        crop_length = max(1, min(int(target_frame_count), int(round(target_frame_count * bounded_keep_ratio))))
        attacks.append(
            {
                "attack_name": "temporal_crop",
                "attack_params": {
                    "crop_start_candidates": [0],
                    "crop_length": int(crop_length),
                    "requested_keep_ratio": float(bounded_keep_ratio),
                },
            }
        )
    for drop_rate in frame_drop_rates:
        attacks.append(
            {
                "attack_name": "frame_dropping",
                "attack_params": {
                    "drop_rate": float(drop_rate),
                    "drop_policy": "deterministic_keyed",
                },
            }
        )
    return {
        "project_stage": "paper_artifact_gate",
        "construction_phase": WORKFLOW_KEY,
        "target_construction_phase": "submission_readiness_gate",
        "attack_matrix_name": "internal_multi_strength_attack_matrix",
        "attacks": attacks,
        "attack_names_by_profile": {
            "formal": ["no_attack", *ATTACKS],
            "proof": ["no_attack", *ATTACKS],
            "smoke": ["no_attack", *ATTACKS],
        },
    }


def build_attack_strength_runtime_config(
    *,
    local_dataset_root: Path,
    dataset_manifest_path: Path,
    vae_model_local_path: Path,
    batch_size_frames: int,
    worker_count: int,
    video_io_worker_count: int,
    attack_worker_count: int,
    cross_event_vae_batching_enabled: bool,
    cross_event_vae_decode_batch_size: int,
    cross_event_vae_encode_batch_size: int,
) -> dict[str, Any]:
    """构造多强度曲线 runner 的 runtime config。

    该配置为了先产出检测曲线基础数据, 默认关闭质量指标和时序质量指标, 避免 LPIPS/CLIP
    等与曲线无关的计算显著拉长 Colab 运行时间。
    """
    return {
        "local_dataset_root": local_dataset_root.as_posix(),
        "dataset_manifest_path": dataset_manifest_path.as_posix(),
        "local_vae_model_root": vae_model_local_path.as_posix(),
        "vae_model_local_path": vae_model_local_path.as_posix(),
        "batch_size_frames": int(batch_size_frames),
        "worker_count": int(worker_count),
        "video_io_worker_count": int(video_io_worker_count),
        "attack_worker_count": int(attack_worker_count),
        "reuse_encoded_latents": True,
        "reuse_decoded_videos": True,
        "reuse_attacked_videos": True,
        "profile_run_timing": True,
        "profile_gpu_runtime": True,
        "gpu_profile_interval_seconds": 2,
        "quality_metrics": {
            "enable_quality_metrics": False,
            "enable_lpips": False,
            "enable_clip_similarity": False,
        },
        "temporal_metrics": {
            "enable_temporal_metrics": False,
        },
        "cross_event_vae_batching_enabled": bool(cross_event_vae_batching_enabled),
        "cross_event_vae_decode_batch_size": int(cross_event_vae_decode_batch_size),
        "cross_event_vae_encode_batch_size": int(cross_event_vae_encode_batch_size),
        "cross_event_vae_batch_fallback_on_oom": True,
        "cross_event_vae_batching_write_trace": True,
    }


def _read_event_scores(run_root: Path) -> list[dict[str, Any]]:
    event_scores_path = run_root / "records" / "event_scores.jsonl"
    if not event_scores_path.exists():
        raise FileNotFoundError(event_scores_path)
    return [
        json.loads(line)
        for line in event_scores_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _copy_optional_run_diagnostics(run_root: Path, output_root: Path) -> dict[str, str]:
    """复制轻量诊断文件, 避免把 mp4/latent 大文件写入 Drive 结果包。"""
    copied: dict[str, str] = {}
    for relpath in (
        Path("artifacts") / "run_manifest.json",
        Path("artifacts") / "runtime_config.json",
        Path("artifacts") / "runtime_manifest.json",
        Path("runtime_profile") / "run_timing_summary.json",
        Path("runtime_profile") / "cross_event_vae_batching_summary.json",
    ):
        source_path = run_root / relpath
        if not source_path.exists():
            continue
        destination_path = output_root / "runner_diagnostics" / relpath
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        copied[relpath.as_posix()] = destination_path.relative_to(output_root).as_posix()
    runtime_profile_root = run_root / "runtime_profile"
    if runtime_profile_root.exists():
        for source_path in sorted(path for path in runtime_profile_root.rglob("*") if path.is_file()):
            relpath = source_path.relative_to(run_root)
            destination_path = output_root / "runner_diagnostics" / relpath
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
            copied[relpath.as_posix()] = destination_path.relative_to(output_root).as_posix()
    return copied


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="运行内部三方法多强度攻击曲线 shard。")
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--local-dataset-root", type=Path, required=True)
    parser.add_argument("--vae-model-local-path", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--short-commit", type=str, default=None)
    parser.add_argument("--samples-per-role", type=int, default=100)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--batch-size-frames", type=int, default=128)
    parser.add_argument("--worker-count", type=int, default=1)
    parser.add_argument("--video-io-worker-count", type=int, default=8)
    parser.add_argument("--attack-worker-count", type=int, default=8)
    parser.add_argument("--cross-event-vae-batching-enabled", action="store_true")
    parser.add_argument("--cross-event-vae-decode-batch-size", type=int, default=12)
    parser.add_argument("--cross-event-vae-encode-batch-size", type=int, default=12)
    parser.add_argument("--target-frame-count", type=int, default=32)
    parser.add_argument("--h264-crfs", type=str, default="18,23,28,33,38")
    parser.add_argument("--h265-crfs", type=str, default="20,25,30,35,40")
    parser.add_argument("--temporal-crop-keep-ratios", type=str, default="0.90,0.75,0.60,0.50")
    parser.add_argument("--frame-drop-rates", type=str, default="0.10,0.25,0.40,0.50")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    """命令行入口。"""
    args = parse_args()
    short_commit = args.short_commit or resolve_short_commit()
    run_id = args.run_id or (
        f"{WORKFLOW_KEY}_internal_sweep_sc{args.shard_count:02d}_"
        f"si{args.shard_index:02d}_{short_commit[:7]}"
    )
    output_root = args.output_root or args.result_root / WORKFLOW_KEY / "shard_runs" / run_id
    if output_root.exists():
        if not args.overwrite:
            raise FileExistsError(f"输出目录已存在, 如需覆盖请传入 --overwrite: {output_root}")
        shutil.rmtree(output_root)
    if args.run_root.exists():
        if not args.overwrite:
            raise FileExistsError(f"本地 run-root 已存在, 如需覆盖请传入 --overwrite: {args.run_root}")
        shutil.rmtree(args.run_root)
    output_root.mkdir(parents=True, exist_ok=True)
    args.run_root.mkdir(parents=True, exist_ok=True)

    attack_matrix = build_internal_multi_strength_attack_matrix(
        h264_crfs=[int(value) for value in _parse_number_list(args.h264_crfs, value_type=int)],
        h265_crfs=[int(value) for value in _parse_number_list(args.h265_crfs, value_type=int)],
        temporal_crop_keep_ratios=[float(value) for value in _parse_number_list(args.temporal_crop_keep_ratios)],
        frame_drop_rates=[float(value) for value in _parse_number_list(args.frame_drop_rates)],
        target_frame_count=args.target_frame_count,
    )
    runtime_config = build_attack_strength_runtime_config(
        local_dataset_root=args.local_dataset_root,
        dataset_manifest_path=args.dataset_manifest,
        vae_model_local_path=args.vae_model_local_path,
        batch_size_frames=args.batch_size_frames,
        worker_count=args.worker_count,
        video_io_worker_count=args.video_io_worker_count,
        attack_worker_count=args.attack_worker_count,
        cross_event_vae_batching_enabled=args.cross_event_vae_batching_enabled,
        cross_event_vae_decode_batch_size=args.cross_event_vae_decode_batch_size,
        cross_event_vae_encode_batch_size=args.cross_event_vae_encode_batch_size,
    )
    config_root = args.run_root / "configs"
    attack_matrix_path = config_root / "internal_multi_strength_attack_matrix.json"
    runtime_config_path = config_root / "internal_multi_strength_runtime_config.json"
    attack_matrix_path.parent.mkdir(parents=True, exist_ok=True)
    attack_matrix_path.write_text(json.dumps(attack_matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    runtime_config_path.write_text(json.dumps(runtime_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    runner_started_at = datetime.now(timezone.utc).replace(microsecond=0)
    runner_started_perf = time.perf_counter()
    RealVideoVaeLatentRunner(ROOT).run(
        output_root=args.run_root,
        run_mode="formal",
        samples_per_role=args.samples_per_role,
        shard_count=args.shard_count,
        shard_index=args.shard_index,
        worker_count=args.worker_count,
        runtime_profile_override="formal",
        method_variants=list(INTERNAL_METHODS),
        attack_matrix_path=attack_matrix_path,
        dataset_manifest_path=args.dataset_manifest,
        runtime_config_path=runtime_config_path,
        cross_event_vae_batching_enabled=args.cross_event_vae_batching_enabled,
        cross_event_vae_decode_batch_size=args.cross_event_vae_decode_batch_size,
        cross_event_vae_encode_batch_size=args.cross_event_vae_encode_batch_size,
        cross_event_vae_batch_fallback_on_oom=True,
    )
    runner_finished_at = datetime.now(timezone.utc).replace(microsecond=0)
    runner_duration_seconds = time.perf_counter() - runner_started_perf

    source_records = _read_event_scores(args.run_root)
    attack_strength_records = convert_stage_two_records_to_attack_strength_records(
        source_records,
        method_names=INTERNAL_METHODS,
        attack_names=tuple(CALIBRATION_ONLY_ATTACKS) + ATTACKS,
        max_records_per_group=None,
        source_mode=FULL_SWEEP_SOURCE_MODE,
    )
    if not attack_strength_records:
        raise ValueError("未能从 internal sweep runner 输出中转换出 attack_strength_event_scores。")
    record_path = output_root / "records" / "attack_strength_event_scores.jsonl"
    write_jsonl(record_path, attack_strength_records)
    copied_diagnostics = _copy_optional_run_diagnostics(args.run_root, output_root)
    timing_payload = {
        "runner_started_at": runner_started_at.isoformat().replace("+00:00", "Z"),
        "runner_finished_at": runner_finished_at.isoformat().replace("+00:00", "Z"),
        "runner_duration_seconds": round(float(runner_duration_seconds), 3),
        "runner_duration_minutes": round(float(runner_duration_seconds) / 60.0, 3),
        "record_count": len(attack_strength_records),
        "records_per_minute": (
            round(len(attack_strength_records) / max(float(runner_duration_seconds) / 60.0, 1e-9), 3)
            if attack_strength_records
            else 0.0
        ),
    }
    timing_path = output_root / "artifacts" / "attack_strength_internal_sweep_timing.json"
    timing_path.parent.mkdir(parents=True, exist_ok=True)
    timing_path.write_text(json.dumps(timing_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    strength_points = sorted(
        {f"{row['attack_name']}:{row['attack_strength_name']}" for row in attack_strength_records}
    )
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "source_mode": FULL_SWEEP_SOURCE_MODE,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "runner_run_root": args.run_root.as_posix(),
        "record_count": len(attack_strength_records),
        "method_names": sorted({row["method_name"] for row in attack_strength_records}),
        "attack_names": sorted({row["attack_name"] for row in attack_strength_records}),
        "curve_attack_names": sorted(
            {row["attack_name"] for row in attack_strength_records if row["attack_name"] in ATTACKS}
        ),
        "calibration_only_attack_names": sorted(
            {row["attack_name"] for row in attack_strength_records if row["attack_name"] in CALIBRATION_ONLY_ATTACKS}
        ),
        "strength_points": strength_points,
        "samples_per_role": args.samples_per_role,
        "shard_count": args.shard_count,
        "shard_index": args.shard_index,
        "claim_support_allowed": len(strength_points) > len(ATTACKS),
        "claim_support_blocking_reason": None if len(strength_points) > len(ATTACKS) else "single_strength_only",
        "attack_matrix_path": attack_matrix_path.as_posix(),
        "runtime_config_path": runtime_config_path.as_posix(),
        "copied_diagnostics": copied_diagnostics,
        "timing": timing_payload,
        "source_digest": compute_object_digest(
            {
                "attack_matrix": attack_matrix,
                "runtime_config": runtime_config,
                "samples_per_role": args.samples_per_role,
                "shard_count": args.shard_count,
                "shard_index": args.shard_index,
            }
        ),
        "artifact_digests": {
            "attack_strength_event_scores": compute_file_digest(record_path),
            "attack_strength_internal_sweep_timing": compute_file_digest(timing_path),
        },
    }
    manifest_path = output_root / "artifacts" / "attack_strength_internal_sweep_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": {**manifest, "manifest_path": manifest_path.as_posix()}, "output_root": output_root.as_posix()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

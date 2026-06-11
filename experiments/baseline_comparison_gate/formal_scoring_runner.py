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


# 下面的执行层只负责生成逐样本 baseline score records。
# fixed-FPR 阈值、TPR@FPR 表格和论文 claim 仍由后续聚合阶段完成。
FORMAL_SCORE_RECORDS_FILENAME = "baseline_formal_score_records.jsonl"
FORMAL_EXECUTION_MANIFEST_FILENAME = "baseline_comparison_formal_scoring_execution_manifest.json"


def build_payload_bits(payload_digest: str | None, *, length: int = 32) -> list[int]:
    """根据阶段二 payload digest 构造确定性 payload 位串。

    该函数不恢复阶段二内部 watermark payload, 只为外部 baseline 提供可复现的比较消息。
    外部 baseline 的正式比较关注同一 split 与同一攻击矩阵下的检测稳定性, 因此这里必须保证
    同一 work item 每次得到完全相同的 payload。
    """
    seed_text = payload_digest or "baseline_comparison_default_payload"
    digest = compute_object_digest({"payload_digest": seed_text, "length": length})
    bits: list[int] = []
    for hex_char in digest:
        value = int(hex_char, 16)
        bits.extend([(value >> shift) & 1 for shift in (3, 2, 1, 0)])
        if len(bits) >= length:
            return bits[:length]
    return (bits * ((length // max(1, len(bits))) + 1))[:length]


def resolve_source_video_path(stage_two_package_root: str | Path, work_item: dict[str, Any]) -> Path:
    """解析 work item 指向的阶段二源视频路径。"""
    relpath = work_item.get("source_video_relpath")
    if not isinstance(relpath, str) or not relpath:
        raise ValueError("work item is missing source_video_relpath")
    source_path = Path(stage_two_package_root) / relpath
    if not source_path.exists():
        raise FileNotFoundError(f"source video not found: {source_path}")
    return source_path


def prepare_video_for_detection(
    *,
    run_root: str | Path,
    stage_two_package_root: str | Path,
    work_item: dict[str, Any],
    adapter: Any,
    payload_bits: list[int],
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """为单个 work item 准备待检测视频。

    positive 样本会先调用外部 baseline embed, 再按 work item 的 attack_name 施加攻击。
    negative 样本不会 embed, 只在原始源视频或其攻击版本上检测, 用于后续 calibration split
    的 fixed-FPR 阈值估计。
    """
    run_root_path = Path(run_root)
    source_path = resolve_source_video_path(stage_two_package_root, work_item)
    work_item_id = str(work_item["work_item_id"])
    sample_role = str(work_item.get("sample_role"))
    attack_name = str(work_item.get("attack_name") or "no_attack")
    attack_params = dict(work_item.get("attack_params") or {})
    sample_dir = run_root_path / "artifacts" / "formal_scoring_videos" / work_item["baseline_name"] / work_item_id[:16]
    sample_dir.mkdir(parents=True, exist_ok=True)

    runtime_metrics: dict[str, Any] = {}
    trace_update: dict[str, Any] = {"source_video_digest": work_item.get("source_video_digest")}

    if sample_role in {"watermarked_positive", "attacked_positive"}:
        watermarked_path = sample_dir / "watermarked_clean.mp4"
        embed_result = adapter.embed(source_path, payload_bits, watermarked_path, {"work_item": work_item})
        if not embed_result.embed_success or embed_result.output_video_path is None:
            raise RuntimeError(embed_result.failure_reason or "baseline_embed_failed")
        input_for_attack = embed_result.output_video_path
        runtime_metrics.update(embed_result.runtime_metrics)
        trace_update.update(embed_result.baseline_trace)
    else:
        input_for_attack = source_path
        trace_update["negative_sample_policy"] = "detect_without_external_watermark_embedding"

    if attack_name == "no_attack":
        return input_for_attack, runtime_metrics, trace_update

    attacked_path = sample_dir / f"attacked_{attack_name}.mp4"
    attack_metadata = apply_formal_video_attack(
        input_video_path=input_for_attack,
        output_video_path=attacked_path,
        attack_name=attack_name,
        attack_params=attack_params,
        work_item=work_item,
    )
    runtime_metrics["attack_metadata_digest"] = compute_object_digest(attack_metadata)
    trace_update["attack_output_digest"] = attack_metadata.get("attacked_video_digest") or attack_metadata.get("video_digest")
    return attacked_path, runtime_metrics, trace_update


def apply_formal_video_attack(
    *,
    input_video_path: str | Path,
    output_video_path: str | Path,
    attack_name: str,
    attack_params: dict[str, Any],
    work_item: dict[str, Any],
) -> dict[str, Any]:
    """对 baseline 输出视频施加与阶段二同名的真实视频攻击。"""
    fps = int(work_item.get("video_fps") or 8)
    resolution_value = work_item.get("video_resolution") or [256, 256]
    resolution = (int(resolution_value[0]), int(resolution_value[1]))
    if attack_name == "h264_compression":
        from main.attacks.compression import H264CompressionAttack

        return H264CompressionAttack(attack_params).apply_video(input_video_path, output_video_path, fps=fps, resolution=resolution)
    if attack_name == "h265_compression":
        from main.attacks.compression import H265CompressionAttack

        return H265CompressionAttack(attack_params).apply_video(input_video_path, output_video_path, fps=fps, resolution=resolution)
    if attack_name in {"spatial_resize", "crop_resize", "blur", "gaussian_noise"}:
        return apply_frame_level_video_attack(
            input_video_path=input_video_path,
            output_video_path=output_video_path,
            attack_name=attack_name,
            attack_params=attack_params,
            work_item=work_item,
        )
    if attack_name in {"temporal_crop", "local_clip", "frame_dropping", "speed_change"}:
        return apply_temporal_video_attack(
            input_video_path=input_video_path,
            output_video_path=output_video_path,
            attack_name=attack_name,
            attack_params=attack_params,
            work_item=work_item,
        )
    raise ValueError(f"unsupported formal video attack: {attack_name}")


def apply_frame_level_video_attack(
    *,
    input_video_path: str | Path,
    output_video_path: str | Path,
    attack_name: str,
    attack_params: dict[str, Any],
    work_item: dict[str, Any],
) -> dict[str, Any]:
    """执行空间类逐帧攻击并写回 mp4。"""
    from main.attacks.spatial import BlurAttack, CropResizeAttack, SpatialResizeAttack
    from main.attacks.video_noise import GaussianNoiseVideoAttack
    from main.video.video_io import read_video_frames, write_video_mp4

    attack_by_name = {
        "spatial_resize": SpatialResizeAttack,
        "crop_resize": CropResizeAttack,
        "blur": BlurAttack,
        "gaussian_noise": GaussianNoiseVideoAttack,
    }
    video = read_video_frames(input_video_path)
    attack = attack_by_name[attack_name](attack_params)
    attacked_frames = attack.apply_frames(
        video.frames,
        runtime_config={"sample_id": work_item.get("sample_id"), "work_item_id": work_item.get("work_item_id")},
    )
    metadata = write_video_mp4(attacked_frames, output_video_path, fps=video.fps)
    metadata.update({"attack_name": attack_name, "attack_params": dict(attack_params)})
    metadata["attacked_video_digest"] = metadata.get("video_digest")
    return metadata


def apply_temporal_video_attack(
    *,
    input_video_path: str | Path,
    output_video_path: str | Path,
    attack_name: str,
    attack_params: dict[str, Any],
    work_item: dict[str, Any],
) -> dict[str, Any]:
    """执行轻量真实视频时间轴攻击。

    该实现属于通用工程写法: 先解码为帧序列, 按攻击参数选择或重采样帧, 再写回 mp4。
    项目特定部分是 attack_name 与阶段二 records 中的受治理攻击名保持一致。
    """
    import numpy as np
    from main.video.video_io import read_video_frames, write_video_mp4

    video = read_video_frames(input_video_path)
    frames = video.frames
    frame_count = int(frames.shape[0])
    if attack_name == "temporal_crop":
        crop_start = int(attack_params.get("crop_start", 0))
        candidates = attack_params.get("crop_start_candidates")
        if isinstance(candidates, list) and candidates:
            crop_start = int(candidates[0])
        crop_start = max(0, min(crop_start, frame_count - 1))
        crop_length = int(attack_params.get("crop_length", frame_count))
        selected = frames[crop_start : min(frame_count, crop_start + max(1, crop_length))]
    elif attack_name == "local_clip":
        clip_length = attack_params.get("clip_length")
        if clip_length is None:
            clip_lengths = attack_params.get("clip_lengths") or [frame_count]
            clip_length = int(clip_lengths[0])
        selected = frames[: max(1, min(frame_count, int(clip_length)))]
    elif attack_name == "frame_dropping":
        drop_rate = float(attack_params.get("drop_rate", 0.25))
        drop_stride = max(2, int(round(1.0 / max(1e-6, drop_rate))))
        kept_indices = [index for index in range(frame_count) if index % drop_stride != 0]
        selected = frames[kept_indices or [0]]
    elif attack_name == "speed_change":
        speed_ratio = float(attack_params.get("speed_ratio", 1.25))
        observed_count = max(1, int(round(frame_count / max(1e-6, speed_ratio))))
        source_indices = np.linspace(0, frame_count - 1, observed_count).round().astype(int)
        selected = frames[source_indices]
    else:
        raise ValueError(f"unsupported temporal attack: {attack_name}")
    metadata = write_video_mp4(selected, output_video_path, fps=video.fps)
    metadata.update({"attack_name": attack_name, "attack_params": dict(attack_params)})
    metadata["attacked_video_digest"] = metadata.get("video_digest")
    return metadata


def build_formal_score_record(
    *,
    run_id: str,
    source_manifest: dict[str, Any],
    work_item: dict[str, Any],
    payload_bits: list[int],
    detection_result: Any,
    extra_runtime_metrics: dict[str, Any],
    extra_trace: dict[str, Any],
) -> dict[str, Any]:
    """把 adapter 检测结果转换为 baseline_comparison_gate 统一 record。"""
    baseline_trace = {
        "source_digest": compute_object_digest(source_manifest),
        "model_digest": detection_result.baseline_trace.get("model_digest", "unknown"),
        "adapter_version": detection_result.baseline_trace.get("adapter_version", "unknown"),
        "score_mapping_rule": detection_result.baseline_trace.get("score_mapping_rule", source_manifest.get("score_mapping_rule")),
        "license_status": source_manifest.get("source_intake_status"),
        "unsupported_attack_reason": None,
        "stage_two_event_key": work_item.get("stage_two_event_key"),
        **extra_trace,
    }
    baseline_trace.update(detection_result.baseline_trace)
    runtime_metrics = dict(extra_runtime_metrics)
    runtime_metrics.update(detection_result.runtime_metrics)
    score = detection_result.baseline_score
    record = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "sample_id": work_item.get("sample_id"),
        "split": work_item.get("split"),
        "sample_role": work_item.get("sample_role"),
        "baseline_name": work_item.get("baseline_name"),
        "baseline_family": work_item.get("baseline_family", "external_video_watermark"),
        "method_name": work_item.get("baseline_name"),
        "method_family": work_item.get("baseline_family", "external_video_watermark"),
        "payload_length_bits": len(payload_bits),
        "payload_digest": compute_object_digest(payload_bits),
        "attack_name": work_item.get("attack_name"),
        "attack_family": infer_attack_family(str(work_item.get("attack_name"))),
        "attack_config_digest": work_item.get("attack_config_digest"),
        "baseline_score": score,
        "baseline_raw_detector_output": detection_result.baseline_raw_detector_output,
        "threshold": None,
        "target_fpr": float(work_item.get("target_fpr") or 0.001),
        "decision": "pending_threshold_calibration" if score is not None else "failed",
        "bit_accuracy": score,
        "ber": None if score is None else 1.0 - float(score),
        "quality_metrics": {},
        "temporal_metrics": {
            "video_frame_count": work_item.get("video_frame_count"),
            "video_fps": work_item.get("video_fps"),
            "video_resolution": work_item.get("video_resolution"),
        },
        "runtime_metrics": runtime_metrics,
        "baseline_trace": baseline_trace,
        "failure_reason": detection_result.failure_reason,
    }
    from experiments.baseline_comparison_gate.record_schema import validate_baseline_record

    violations = validate_baseline_record(record)
    if violations:
        raise ValueError(f"invalid formal baseline score record: {violations}")
    return record


def infer_attack_family(attack_name: str) -> str:
    """把受治理 attack_name 映射为粗粒度攻击族。"""
    if attack_name == "no_attack":
        return "clean"
    if attack_name in {"h264_compression", "h265_compression"}:
        return "compression"
    if attack_name in {"spatial_resize", "crop_resize", "blur", "gaussian_noise"}:
        return "spatial"
    if attack_name in {"temporal_crop", "local_clip", "frame_dropping", "speed_change"}:
        return "temporal"
    return "unknown"


def make_real_baseline_adapter(baseline_name: str, *, external_root: str | Path) -> Any:
    """按 baseline 名称创建真实外部 adapter。"""
    external_root_path = Path(external_root)
    if baseline_name == "external_videoseal":
        from experiments.baseline_comparison_gate.videoseal_adapter import ExternalVideoSealAdapter

        return ExternalVideoSealAdapter(upstream_root=external_root_path / baseline_name / "upstream", compile_model=False)
    if baseline_name == "external_rivagan":
        from experiments.baseline_comparison_gate.rivagan_adapter import ExternalRivaGANAdapter

        return ExternalRivaGANAdapter(upstream_root=external_root_path / baseline_name / "upstream")
    if baseline_name == "external_hidden_framewise":
        from experiments.baseline_comparison_gate.hidden_framewise_adapter import DEFAULT_EXPERIMENT_NAME, ExternalHiddenFramewiseAdapter

        return ExternalHiddenFramewiseAdapter(
            upstream_root=external_root_path / baseline_name / "upstream",
            experiment_name=DEFAULT_EXPERIMENT_NAME,
        )
    raise KeyError(f"unsupported baseline adapter: {baseline_name}")


def run_formal_scoring_execution(
    *,
    run_root: str | Path,
    stage_two_package_root: str | Path,
    formal_input_contract_path: str | Path,
    config_dir: str | Path,
    external_root: str | Path,
    run_id: str,
    baseline_names: Iterable[str] | None = None,
    shard_count: int = 1,
    shard_index: int = 0,
    max_work_items: int | None = None,
    adapter_factory: Any | None = None,
) -> dict[str, Any]:
    """执行小规模或分片 formal baseline scoring。

    该函数只生成 score records, 不计算 fixed-FPR 阈值。这样可以先在 Colab 上验证真实外部
    baseline、攻击链路和 Drive 落盘链路, 避免在全量运行前浪费 GPU 时间。
    """
    contract = load_json(formal_input_contract_path)
    if contract.get("ready_for_formal_baseline_runner") is not True:
        raise ValueError("formal input contract is not ready for formal baseline runner")
    from experiments.baseline_comparison_gate.source_intake import load_all_source_manifests

    run_root_path = Path(run_root)
    manifests = load_all_source_manifests(config_dir)
    work_items = build_scoring_work_items(
        stage_two_package_root=stage_two_package_root,
        baseline_names=baseline_names,
        shard_count=shard_count,
        shard_index=shard_index,
    )
    if max_work_items is not None:
        work_items = work_items[: max(0, int(max_work_items))]

    records: list[dict[str, Any]] = []
    adapters: dict[str, Any] = {}
    prepare_results: dict[str, Any] = {}
    factory = adapter_factory or (lambda name: make_real_baseline_adapter(name, external_root=external_root))
    for item in work_items:
        baseline_name = item["baseline_name"]
        if baseline_name not in adapters:
            adapter = factory(baseline_name)
            context = __import__("experiments.baseline_comparison_gate.baseline_adapter", fromlist=["BaselineRuntimeContext"]).BaselineRuntimeContext(
                baseline_name=baseline_name,
                run_id=run_id,
                work_dir=run_root_path / "work" / baseline_name,
                source_manifest=manifests[baseline_name],
            )
            prepare_results[baseline_name] = adapter.prepare(context)
            adapters[baseline_name] = adapter
        adapter = adapters[baseline_name]
        payload_bits = build_payload_bits(item.get("payload_digest"), length=32)
        detection_video_path, runtime_metrics, trace_update = prepare_video_for_detection(
            run_root=run_root_path,
            stage_two_package_root=stage_two_package_root,
            work_item=item,
            adapter=adapter,
            payload_bits=payload_bits,
        )
        detection = adapter.detect(detection_video_path, {"payload_bits": payload_bits, "work_item": item})
        records.append(
            build_formal_score_record(
                run_id=run_id,
                source_manifest=manifests[baseline_name],
                work_item=item,
                payload_bits=payload_bits,
                detection_result=detection,
                extra_runtime_metrics=runtime_metrics,
                extra_trace=trace_update,
            )
        )

    records_path = run_root_path / "records" / FORMAL_SCORE_RECORDS_FILENAME
    write_jsonl(records_path, records)
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "run_kind": "baseline_comparison_formal_scoring_execution",
        "formal_input_contract_path": Path(formal_input_contract_path).as_posix(),
        "formal_input_contract_digest": compute_file_digest(formal_input_contract_path),
        "stage_two_package_root": Path(stage_two_package_root).as_posix(),
        "baseline_names": sorted({item["baseline_name"] for item in work_items}),
        "shard_count": shard_count,
        "shard_index": shard_index,
        "planned_work_item_count": len(work_items),
        "completed_record_count": len(records),
        "records_path": records_path.as_posix(),
        "records_digest": compute_file_digest(records_path),
        "prepare_results": prepare_results,
        "claim_support_allowed": False,
        "formal_fixed_fpr_complete": False,
        "blocking_reason": "score_records_only_thresholds_tables_and_claim_audit_not_built",
    }
    manifest_path = run_root_path / "artifacts" / FORMAL_EXECUTION_MANIFEST_FILENAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix()}


def materialize_formal_scoring_execution_run(
    *,
    run_root: str | Path,
    result_root: str | Path,
    run_id: str,
    workflow_key: str = WORKFLOW_KEY,
    overwrite: bool = False,
) -> Path:
    """将已完成的 formal scoring execution 复制到 Drive。"""
    run_root_path = Path(run_root)
    destination = Path(result_root) / workflow_key / run_id
    required_files = [
        run_root_path / "records" / FORMAL_SCORE_RECORDS_FILENAME,
        run_root_path / "artifacts" / FORMAL_EXECUTION_MANIFEST_FILENAME,
    ]
    missing_files = [path.as_posix() for path in required_files if not path.exists()]
    if missing_files:
        raise FileNotFoundError("formal scoring execution run is incomplete: " + ", ".join(missing_files))
    if destination.exists():
        if not overwrite:
            raise FileExistsError(f"destination already exists: {destination}")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run_root_path, destination)
    return destination

"""运行 external_hidden_framewise 的 Colab 真实可运行性 smoke。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.baseline_adapter import BaselineRuntimeContext
from experiments.baseline_comparison_gate.hidden_framewise_adapter import (
    ADAPTER_VERSION,
    DEFAULT_EXPERIMENT_NAME,
    SCORE_MAPPING_RULE,
    ExternalHiddenFramewiseAdapter,
    create_hidden_probe_video,
)
from experiments.baseline_comparison_gate.record_schema import validate_baseline_record
from experiments.baseline_comparison_gate.smoke_runner import materialize_completed_smoke_run
from experiments.baseline_comparison_gate.source_intake import load_all_source_manifests
from main.attacks.compression import H264CompressionAttack
from main.core.digest import compute_file_digest, compute_object_digest


WORKFLOW_KEY = "baseline_comparison_gate"
BASELINE_NAME = "external_hidden_framewise"
RUN_ID_PREFIX = "external_hidden_framewise_real_smoke"


def utc_timestamp() -> str:
    """生成 UTC 时间戳。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_short_commit() -> str:
    """读取当前仓库短 commit。"""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).strip()
    except Exception:
        return "unknown"


def build_run_id(short_commit: str, timestamp_utc: str | None = None) -> str:
    """生成 external_hidden_framewise real smoke 的 run_id。"""
    return f"{RUN_ID_PREFIX}_{timestamp_utc or utc_timestamp()}_{short_commit or 'unknown'}"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """写出 JSONL records。"""
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def build_record(
    *,
    run_id: str,
    source_manifest: dict[str, Any],
    model_digest: str,
    source_digest: str,
    payload_bits: list[int],
    sample_id: str,
    sample_role: str,
    attack_name: str,
    attack_family: str,
    attack_config: dict[str, Any],
    detection_result: Any,
    evaluation_result: Any,
    extra_runtime_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把 HiDDeN framewise 检测结果转换为统一 baseline record。"""
    runtime_metrics = dict(detection_result.runtime_metrics)
    if extra_runtime_metrics:
        runtime_metrics.update(extra_runtime_metrics)
    record = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "sample_id": sample_id,
        "split": "dev",
        "sample_role": sample_role,
        "baseline_name": BASELINE_NAME,
        "baseline_family": source_manifest["baseline_family"],
        "method_name": BASELINE_NAME,
        "method_family": source_manifest["baseline_family"],
        "payload_length_bits": len(payload_bits),
        "payload_digest": compute_object_digest(payload_bits),
        "attack_name": attack_name,
        "attack_family": attack_family,
        "attack_config_digest": compute_object_digest(attack_config),
        "baseline_score": detection_result.baseline_score,
        "baseline_raw_detector_output": detection_result.baseline_raw_detector_output,
        "threshold": evaluation_result.threshold,
        "target_fpr": evaluation_result.target_fpr,
        "decision": evaluation_result.decision,
        "bit_accuracy": evaluation_result.bit_accuracy,
        "ber": evaluation_result.ber,
        "quality_metrics": {},
        "temporal_metrics": {
            "decoded_frame_count": detection_result.baseline_raw_detector_output.get("decoded_frame_count"),
            "fps": detection_result.baseline_raw_detector_output.get("fps"),
        },
        "runtime_metrics": runtime_metrics,
        "baseline_trace": {
            "source_digest": source_digest,
            "model_digest": model_digest,
            "adapter_version": ADAPTER_VERSION,
            "score_mapping_rule": SCORE_MAPPING_RULE,
            "license_status": source_manifest.get("source_intake_status"),
            "unsupported_attack_reason": "framewise_image_watermark_migrated_to_video_frames",
        },
        "failure_reason": evaluation_result.failure_reason,
    }
    violations = validate_baseline_record(record)
    if violations:
        raise ValueError(f"invalid external_hidden_framewise smoke record: {violations}")
    return record


def run_hidden_framewise_real_smoke(
    *,
    run_root: str | Path,
    config_dir: str | Path,
    external_root: str | Path,
    short_commit: str,
    timestamp_utc: str | None,
    input_video_path: str | Path | None = None,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """运行 HiDDeN framewise 的 clean 与 H.264 单视频真实 smoke。"""
    run_root_path = Path(run_root)
    run_id = build_run_id(short_commit=short_commit, timestamp_utc=timestamp_utc)
    manifests = load_all_source_manifests(config_dir)
    source_manifest = manifests[BASELINE_NAME]
    source_digest = compute_object_digest(source_manifest)

    records_dir = run_root_path / "records"
    reports_dir = run_root_path / "reports"
    artifacts_dir = run_root_path / "artifacts"
    inputs_dir = run_root_path / "inputs"
    work_dir = run_root_path / "work" / BASELINE_NAME
    for directory in (records_dir, reports_dir, artifacts_dir, inputs_dir, work_dir):
        directory.mkdir(parents=True, exist_ok=True)

    if input_video_path is None:
        input_path = inputs_dir / "hidden_framewise_probe_input.mp4"
        create_hidden_probe_video(input_path)
    else:
        input_path = Path(input_video_path)
        if not input_path.exists():
            raise FileNotFoundError(f"input video not found: {input_path}")

    adapter = ExternalHiddenFramewiseAdapter(
        upstream_root=Path(external_root) / BASELINE_NAME / "upstream",
        experiment_name=DEFAULT_EXPERIMENT_NAME,
    )
    context = BaselineRuntimeContext(
        baseline_name=BASELINE_NAME,
        run_id=run_id,
        work_dir=work_dir,
        source_manifest=source_manifest,
        adapter_version=ADAPTER_VERSION,
    )
    prepare_result = adapter.prepare(context)
    model_digest = prepare_result["model_digest"]
    payload_bits = [0, 1, 1, 0, 1, 0, 0, 1]

    watermarked_path = artifacts_dir / "external_hidden_framewise_watermarked_clean.mp4"
    embed_result = adapter.embed(input_path, payload_bits, watermarked_path, {})
    payload_bits = adapter.payload_bits or payload_bits
    clean_detection = adapter.detect(watermarked_path, {"payload_bits": payload_bits})
    clean_evaluation = adapter.evaluate(clean_detection, payload_bits, threshold, 0.001)
    records = [
        build_record(
            run_id=run_id,
            source_manifest=source_manifest,
            model_digest=model_digest,
            source_digest=source_digest,
            payload_bits=payload_bits,
            sample_id="external_hidden_framewise_probe_clean",
            sample_role="watermarked_positive",
            attack_name="clean",
            attack_family="clean",
            attack_config={"attack_name": "clean"},
            detection_result=clean_detection,
            evaluation_result=clean_evaluation,
            extra_runtime_metrics=embed_result.runtime_metrics,
        )
    ]

    attacked_path = artifacts_dir / "external_hidden_framewise_watermarked_h264_crf_28.mp4"
    attack = H264CompressionAttack({"crf": 28, "preset": "medium"})
    attack_metadata = attack.apply_video(watermarked_path, attacked_path, fps=8)
    attacked_detection = adapter.detect(attacked_path, {"payload_bits": payload_bits})
    attacked_evaluation = adapter.evaluate(attacked_detection, payload_bits, threshold, 0.001)
    records.append(
        build_record(
            run_id=run_id,
            source_manifest=source_manifest,
            model_digest=model_digest,
            source_digest=source_digest,
            payload_bits=payload_bits,
            sample_id="external_hidden_framewise_probe_h264_crf_28",
            sample_role="attacked_positive",
            attack_name="h264_crf_28",
            attack_family="compression",
            attack_config={"attack_name": "h264_compression", "crf": 28, "preset": "medium"},
            detection_result=attacked_detection,
            evaluation_result=attacked_evaluation,
            extra_runtime_metrics={"attack_metadata_digest": compute_object_digest(attack_metadata)},
        )
    )

    records_path = records_dir / "external_hidden_framewise_real_smoke_records.jsonl"
    write_jsonl(records_path, records)
    report_path = reports_dir / "external_hidden_framewise_real_smoke_report.md"
    report_path.write_text(build_report(records, prepare_result), encoding="utf-8")
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": run_id,
        "run_kind": "external_hidden_framewise_real_smoke",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": short_commit,
        "baseline_name": BASELINE_NAME,
        "record_count": len(records),
        "records_path": records_path.as_posix(),
        "records_digest": compute_file_digest(records_path),
        "report_path": report_path.as_posix(),
        "model_digest": model_digest,
        "adapter_version": ADAPTER_VERSION,
        "claim_support_allowed": False,
        "formal_fixed_fpr_complete": False,
        "blocking_reason": "single_baseline_smoke_only_not_full_baseline_comparison",
    }
    manifest_path = run_root_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "run_id": run_id,
        "run_root": str(run_root_path),
        "records_path": str(records_path),
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
        "record_count": len(records),
        "model_digest": model_digest,
        "claim_support_allowed": False,
        "formal_fixed_fpr_complete": False,
    }


def build_report(records: list[dict[str, Any]], prepare_result: dict[str, Any]) -> str:
    """生成 HiDDeN framewise 真实 smoke 报告。"""
    lines = [
        "# external_hidden_framewise real smoke report",
        "",
        "该报告只证明 HiDDeN 图像水印模型在当前环境中完成了逐帧视频 encode / decode smoke, 不能替代正式 fixed-FPR baseline comparison。",
        "",
        f"- adapter_version: `{ADAPTER_VERSION}`",
        f"- model_digest: `{prepare_result['model_digest']}`",
        f"- device: `{prepare_result['device']}`",
        f"- experiment_name: `{prepare_result['experiment_name']}`",
        "",
        "| sample_id | attack_name | baseline_score | decision | failure_reason |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for record in records:
        lines.append(
            "| {sample_id} | {attack_name} | {baseline_score} | {decision} | {failure_reason} |".format(
                sample_id=record["sample_id"],
                attack_name=record["attack_name"],
                baseline_score=record["baseline_score"],
                decision=record["decision"],
                failure_reason=record["failure_reason"],
            )
        )
    lines.extend(
        [
            "",
            "## 后续要求",
            "",
            "`external_hidden_framewise` 是图像水印逐帧迁移 baseline, 不能描述为原生视频水印方法。进入正式比较前, 仍需统一 split、统一攻击矩阵和 calibration-only fixed-FPR 协议。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_failure_summary(run_root: str | Path, exc: Exception) -> dict[str, Any]:
    """在真实 smoke 失败时写出可回传的失败摘要。"""
    logs_dir = Path(run_root) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    failure_payload = {
        "workflow_key": WORKFLOW_KEY,
        "baseline_name": BASELINE_NAME,
        "status": "failed",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback": traceback.format_exc(),
    }
    failure_path = logs_dir / "external_hidden_framewise_real_smoke_failure.json"
    failure_path.write_text(json.dumps(failure_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failure_payload["failure_path"] = failure_path.as_posix()
    return failure_payload


def main(argv: list[str] | None = None) -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, default=ROOT / "configs" / "baselines")
    parser.add_argument("--external-root", type=Path, default=ROOT / "external_baselines")
    parser.add_argument("--input-video-path", type=Path, default=None)
    parser.add_argument("--short-commit", default=None)
    parser.add_argument("--timestamp-utc", default=None)
    parser.add_argument("--result-root", type=Path, default=None)
    parser.add_argument("--overwrite-result", action="store_true")
    args = parser.parse_args(argv)

    try:
        summary = run_hidden_framewise_real_smoke(
            run_root=args.run_root,
            config_dir=args.config_dir,
            external_root=args.external_root,
            short_commit=args.short_commit or resolve_short_commit(),
            timestamp_utc=args.timestamp_utc,
            input_video_path=args.input_video_path,
        )
        if args.result_root is not None:
            destination = materialize_completed_smoke_run(
                run_root=args.run_root,
                result_root=args.result_root,
                run_id=summary["run_id"],
                overwrite=args.overwrite_result,
                required_relative_paths=[
                    "manifest.json",
                    "records/external_hidden_framewise_real_smoke_records.jsonl",
                    "reports/external_hidden_framewise_real_smoke_report.md",
                ],
            )
            summary["materialized_result_path"] = str(destination)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    except Exception as exc:
        failure_payload = write_failure_summary(args.run_root, exc)
        print(json.dumps(failure_payload, ensure_ascii=False, indent=2), file=sys.stderr)
        raise


if __name__ == "__main__":
    main()

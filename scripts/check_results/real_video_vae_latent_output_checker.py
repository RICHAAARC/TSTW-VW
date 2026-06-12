"""
文件用途：检查阶段 2 scaffold 输出完整性。
File purpose: Check the completeness of stage-two scaffold outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from main.core.digest import compute_file_digest
from main.core.records import RecordWriter
from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)


def check_real_video_vae_latent_outputs(
    run_root: str | Path,
    construction_phase: str = "real_video_vae_latent_probe",
    run_mode: str = "smoke",
    require_formal_pass_criteria: bool = False,
) -> dict[str, Any]:
    """功能：检查阶段 2 运行目录中的关键产物与约束。

    Check the required artifacts and constraints for a stage-two run directory.

    Args:
        run_root: Run root path.
        construction_phase: Expected construction phase.
        run_mode: Runtime mode label.
        require_formal_pass_criteria: Whether to require a formal PASS decision.

    Returns:
        A dictionary containing the check results.
    """
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    record_writer = RecordWriter(run_root)
    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    report_fields = _parse_report_fields(output_paths.report_path.read_text(encoding="utf-8"))
    artifact_manifest = _read_json_payload(output_paths.artifact_manifest_path, default=[])
    run_manifest = _read_json_payload(output_paths.run_manifest_path, default={})
    required_paths = {
        "event_scores": output_paths.event_scores_path.exists(),
        "thresholds": output_paths.thresholds_path.exists(),
        "main_tpr_fpr_table": output_paths.main_tpr_fpr_table_path.exists(),
        "real_video_attack_breakdown": output_paths.real_video_attack_breakdown_path.exists(),
        "quality_table": output_paths.quality_table_path.exists(),
        "temporal_consistency_table": output_paths.temporal_consistency_table_path.exists(),
        "real_video_vae_latent_governance_summary": output_paths.real_video_vae_latent_governance_summary_path.exists(),
        "report": output_paths.report_path.exists(),
        "runtime_manifest": output_paths.runtime_manifest_path.exists(),
        "artifact_manifest": output_paths.artifact_manifest_path.exists(),
    }
    real_video_vae_latent_decision = report_fields.get("RealVideoVaeLatentDecision", "INCONCLUSIVE")
    blocking_reasons = [
        reason.strip()
        for reason in report_fields.get("BlockingReasons", "").replace(";", ",").split(",")
        if reason.strip()
    ]
    next_allowed_stage = report_fields.get(
        "NextAllowedStage",
        "remain_in_real_video_vae_latent_probe",
    )
    all_s_traj_null = all(
        record["evidence_scores"].get("S_traj") is None
        for record in event_score_records
    )
    construction_phase_matches = all(
        record.get("mechanism_trace", {}).get("construction_phase") == construction_phase
        for record in event_score_records
    )
    status = all(required_paths.values()) and bool(event_score_records) and bool(threshold_records)
    status = status and all_s_traj_null and construction_phase_matches
    
    # formal 模式额外检查
    formal_checks = _perform_formal_checks(
        event_score_records,
        artifact_manifest,
        run_manifest,
        Path(run_root),
        require_formal_pass_criteria,
        real_video_vae_latent_decision,
        next_allowed_stage,
    )
    
    if require_formal_pass_criteria and run_mode == "formal":
        status = status and formal_checks["status"]
    
    return {
        "status": status,
        "required_paths": required_paths,
        "record_count": len(event_score_records),
        "threshold_count": len(threshold_records),
        "all_s_traj_null": all_s_traj_null,
        "construction_phase_matches": construction_phase_matches,
        "Stage2ImplementationDecision": real_video_vae_latent_decision,
        "RealVideoVaeLatentDecision": real_video_vae_latent_decision,
        "BlockingReasons": blocking_reasons,
        "NextAllowedStageByImplementation": next_allowed_stage,
        "NextAllowedStage": next_allowed_stage,
        "formal_checks": formal_checks if require_formal_pass_criteria else None,
    }


def _perform_formal_checks(
    event_score_records: list[dict[str, Any]],
    artifact_manifest: list[dict[str, Any]],
    run_manifest: dict[str, Any],
    run_root: Path,
    require_formal_pass_criteria: bool,
    real_video_vae_latent_decision: str,
    next_allowed_stage: str,
) -> dict[str, Any]:
    """功能：执行 formal 模式特定的检查。

    Perform formal-mode specific checks on event records.

    Args:
        event_score_records: Event score records.
        require_formal_pass_criteria: Whether to require formal PASS.
        real_video_vae_latent_decision: The governance summary decision.

    Returns:
        Dictionary with formal check results.
    """
    checks = {
        "status": True,
        "has_real_video_runtime": False,
        "has_real_vae_backend": False,
        "has_real_quality_metrics": False,
        "lpips_evidence_available": False,
        "has_real_temporal_metrics": False,
        "no_placeholder_containers": False,
        "has_mp4_artifacts": False,
        "compression_outputs_are_mp4": False,
        "reencoded_latents_recorded": False,
        "no_placeholder_run_manifest": False,
        "random_fields_governed": False,
        "decision_is_pass": real_video_vae_latent_decision == "PASS",
        "next_allowed_stage_valid": next_allowed_stage == "trajectory_statistic_probe",
        "details": {},
    }
    
    if not event_score_records:
        return checks

    artifact_manifest_entries = [
        artifact_entry
        for artifact_entry in artifact_manifest
        if isinstance(artifact_entry, dict)
    ]
    run_manifest_placeholder_fields = run_manifest.get("placeholder_fields", [])
    run_manifest_random_fields = run_manifest.get("random_fields", [])
    allow_record_only_artifact_validation = bool(run_manifest.get("shard_aggregation"))
    
    # 检查真实视频运行时
    checks["has_real_video_runtime"] = all(
        record.get("mechanism_trace", {}).get("video_runtime_status") == "real_mp4_runtime"
        for record in event_score_records
    )
    checks["details"]["video_runtime_status"] = [
        record.get("mechanism_trace", {}).get("video_runtime_status")
        for record in event_score_records[:1]  # 显示第一个样本
    ]
    
    # 检查真实 VAE backend
    placeholder_backends = {"video_vae_backend_placeholder", "video_vae_tensor_runtime"}
    checks["has_real_vae_backend"] = all(
        record.get("mechanism_trace", {}).get("vae_backend_name") not in placeholder_backends
        for record in event_score_records
    )
    checks["details"]["vae_backend_name"] = [
        record.get("mechanism_trace", {}).get("vae_backend_name")
        for record in event_score_records[:1]
    ]
    
    # 检查真实质量指标运行时
    checks["has_real_quality_metrics"] = all(
        record.get("mechanism_trace", {}).get("quality_metrics_runtime") == "real_video_frame_metrics"
        for record in event_score_records
    )
    checks["details"]["quality_metrics_runtime"] = [
        record.get("mechanism_trace", {}).get("quality_metrics_runtime")
        for record in event_score_records[:1]
    ]

    lpips_scores = [
        record.get("quality_metrics", {}).get("watermarked_video_lpips")
        for record in event_score_records
        if isinstance(record.get("quality_metrics", {}), dict)
    ]
    checks["lpips_evidence_available"] = any(
        _is_non_bool_number(lpips_score) for lpips_score in lpips_scores
    )
    checks["details"]["lpips_record_count"] = sum(
        1 for lpips_score in lpips_scores if _is_non_bool_number(lpips_score)
    )
    
    # 检查真实时序指标运行时
    checks["has_real_temporal_metrics"] = all(
        record.get("mechanism_trace", {}).get("temporal_metrics_runtime") == "real_video_frame_metrics"
        for record in event_score_records
    )
    checks["details"]["temporal_metrics_runtime"] = [
        record.get("mechanism_trace", {}).get("temporal_metrics_runtime")
        for record in event_score_records[:1]
    ]
    
    # 检查没有 tensor_npy 容器
    checks["no_placeholder_containers"] = all(
        record.get("mechanism_trace", {}).get("video_container") != "tensor_npy"
        for record in event_score_records
    )
    checks["details"]["video_container"] = [
        record.get("mechanism_trace", {}).get("video_container")
        for record in event_score_records[:1]
    ]

    # 检查 artifact manifest 中存在真实 mp4 artifact
    checks["has_mp4_artifacts"] = any(
        str(
            artifact_entry.get("relpath")
            or artifact_entry.get("artifact_relpath")
            or ""
        ).endswith(".mp4")
        for artifact_entry in artifact_manifest_entries
        if artifact_entry.get("artifact_kind") in {"source_video", "decoded_video", "attacked_video"}
    )
    checks["details"]["artifact_manifest_kinds"] = [
        artifact_entry.get("artifact_kind")
        for artifact_entry in artifact_manifest_entries[:6]
    ]

    # 检查压缩攻击输出为 mp4
    compression_records = [
        record for record in event_score_records
        if record.get("attack_name") in {"h264_compression", "h265_compression"}
    ]
    checks["compression_outputs_are_mp4"] = bool(compression_records) and all(
        str(record.get("mechanism_trace", {}).get("attacked_video_relpath", "")).endswith(".mp4")
        for record in compression_records
    )
    checks["details"]["compression_attack_names"] = [
        record.get("attack_name") for record in compression_records[:4]
    ]

    # 检查 re-encoded latent 文件存在且 digest 可校验
    checks["reencoded_latents_recorded"] = all(
        _validate_reencoded_latent_record(
            record,
            run_root,
            allow_record_only_artifact_validation=allow_record_only_artifact_validation,
        )
        for record in event_score_records
    )

    # 检查 run manifest 中没有 formal blocker 字段
    checks["no_placeholder_run_manifest"] = "video_vae_backend_placeholder" not in run_manifest_placeholder_fields
    checks["random_fields_governed"] = "latent_tensor_digest_random" not in run_manifest_random_fields
    checks["details"]["run_manifest_placeholder_fields"] = run_manifest_placeholder_fields
    checks["details"]["run_manifest_random_fields"] = run_manifest_random_fields
    
    # 综合判断
    checks["status"] = (
        checks["has_real_video_runtime"]
        and checks["has_real_vae_backend"]
        and checks["has_real_quality_metrics"]
        and checks["lpips_evidence_available"]
        and checks["has_real_temporal_metrics"]
        and checks["no_placeholder_containers"]
        and checks["has_mp4_artifacts"]
        and checks["compression_outputs_are_mp4"]
        and checks["reencoded_latents_recorded"]
        and checks["no_placeholder_run_manifest"]
        and checks["random_fields_governed"]
        and (
            checks["next_allowed_stage_valid"]
            or next_allowed_stage == "baseline_comparison_gate"
        )
    )
    
    if require_formal_pass_criteria:
        checks["status"] = checks["status"] and checks["decision_is_pass"]
    
    return checks


def _read_json_payload(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _is_non_bool_number(value: Any) -> bool:
    """判断 value 是否为非布尔数值。

    Args:
        value: 待检查对象。

    Returns:
        仅当 value 是 int 或 float 且不是 bool 时返回 True。
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_reencoded_latent_record(
    record: dict[str, Any],
    run_root: Path,
    *,
    allow_record_only_artifact_validation: bool = False,
) -> bool:
    mechanism_trace = record.get("mechanism_trace", {})
    relpath = mechanism_trace.get("reencoded_latent_relpath")
    expected_digest = mechanism_trace.get("reencoded_latent_digest")
    if not isinstance(relpath, str) or not relpath.endswith(".npy"):
        return False
    if not isinstance(expected_digest, str) or not expected_digest:
        return False
    artifact_path = run_root / relpath
    if allow_record_only_artifact_validation and not artifact_path.exists():
        # shard 聚合结果默认只保留 records、thresholds、tables、reports 与 manifest。
        # 大体积 video / latent artifact 已在 shard run 中生成并以 digest 记录, 聚合包不再重复复制。
        return True
    if not artifact_path.exists():
        return False
    return compute_file_digest(artifact_path) == expected_digest


def _parse_report_fields(report_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in report_text.splitlines():
        if not line.startswith("- ") or ": " not in line:
            continue
        field_name, field_value = line[2:].split(": ", 1)
        fields[field_name] = field_value
    return fields


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Check the governed placeholder stage-two outputs.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--construction-phase", default="real_video_vae_latent_probe")
    parser.add_argument("--run-mode", default="smoke")
    parser.add_argument("--require-formal-pass-criteria", action="store_true")
    parser.add_argument("--output-path", default=None)
    args = parser.parse_args(argv)
    result = check_real_video_vae_latent_outputs(
        run_root=args.run_root,
        construction_phase=args.construction_phase,
        run_mode=args.run_mode,
        require_formal_pass_criteria=args.require_formal_pass_criteria,
    )
    if args.output_path:
        output_path = Path(args.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

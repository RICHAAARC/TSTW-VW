"""
文件用途：从阶段 2 records 重建机制审计表、报告与机制门禁决策。
File purpose: Rebuild stage-two mechanism audit tables, report, and gate decision from governed records.
Module type: General module
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any

from experiments.real_video_vae_latent_probe.mechanism_semantics import (
    build_sync_gain_assessment,
)
from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)
from main.core.records import RecordWriter


STAGE2_MECHANISM_AUDIT_COLUMNS = [
    "run_id",
    "construction_phase",
    "method_variant",
    "base_method_variant",
    "attack_name",
    "sample_role",
    "count",
    "S_tubelet_mean",
    "S_tubelet_std",
    "S_sync_mean",
    "S_sync_std",
    "S_final_mean",
    "S_final_std",
    "decision_rate",
    "clean_negative_FPR",
    "attacked_negative_FPR",
    "clean_positive_TPR",
    "attacked_positive_TPR",
    "local_clip_TPR",
    "sync_alignment_error_mean",
    "sync_peak_rank_median",
    "quality_psnr_mean",
    "quality_psnr_finite_mean",
    "quality_psnr_finite_count",
    "quality_psnr_inf_count",
    "quality_psnr_total_count",
    "quality_ssim_mean",
    "temporal_consistency_score_mean",
    "flicker_score_mean",
]
STAGE2_SCORE_DISTRIBUTION_COLUMNS = [
    "run_id",
    "construction_phase",
    "method_variant",
    "attack_name",
    "sample_role",
    "count",
    "S_tubelet_mean",
    "S_tubelet_std",
    "S_sync_mean",
    "S_sync_std",
    "S_final_mean",
    "S_final_std",
]
STAGE2_SYNC_GAIN_COLUMNS = [
    "attack_name",
    "metric_name",
    "tubelet_only_value",
    "tubelet_sync_value",
    "sync_gain",
    "negative_fpr_delta",
    "positive_count",
    "negative_count",
    "mechanism_signal_status",
]
DEFAULT_MECHANISM_CONFIG_PATH = Path("configs/protocol/stage2_mechanism_gate.json")
TEMPORAL_ATTACKS = {"temporal_crop", "frame_dropping", "local_clip", "speed_change"}
STAGE2_MECHANISM_PROTOCOL = "aligned_payload_safety"


def run_stage2_mechanism_audit(
    *,
    run_root: str | Path,
    mechanism_config_path: str | Path = DEFAULT_MECHANISM_CONFIG_PATH,
    target_fpr: float | None = None,
) -> dict[str, Any]:
    """Run the governed stage-two mechanism audit over persisted records.

    Args:
        run_root: Run-root path.
        mechanism_config_path: Mechanism-gate config path.
        target_fpr: Optional target FPR override.

    Returns:
        Stage-two mechanism summary payload.
    """
    run_root_path = Path(run_root)
    output_paths = build_real_video_vae_latent_output_paths(run_root_path)
    record_writer = RecordWriter(run_root_path)
    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    mechanism_config = json.loads(Path(mechanism_config_path).read_text(encoding="utf-8"))
    governance_summary_row = _read_single_csv_row(
        output_paths.real_video_vae_latent_governance_summary_path
    )
    runtime_config = _read_json_payload(output_paths.runtime_config_path)

    audit_rows = build_stage2_mechanism_audit_rows(event_score_records, threshold_records)
    score_rows = build_stage2_score_distribution_rows(event_score_records)
    sync_gain_rows = build_stage2_sync_gain_rows(
        event_score_records,
        required_attacks=_string_list(mechanism_config.get("required_mechanism_attacks", [])),
    )
    decision_payload = build_stage2_mechanism_decision(
        event_score_records=event_score_records,
        threshold_records=threshold_records,
        mechanism_config=mechanism_config,
        governance_summary_row=governance_summary_row,
        runtime_config=runtime_config,
        target_fpr=target_fpr,
    )

    _write_csv(
        output_paths.stage2_mechanism_audit_table_path,
        STAGE2_MECHANISM_AUDIT_COLUMNS,
        audit_rows,
    )
    _write_csv(
        output_paths.stage2_score_distribution_table_path,
        STAGE2_SCORE_DISTRIBUTION_COLUMNS,
        score_rows,
    )
    _write_csv(
        output_paths.stage2_sync_gain_table_path,
        STAGE2_SYNC_GAIN_COLUMNS,
        sync_gain_rows,
    )
    output_paths.stage2_mechanism_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.stage2_mechanism_report_path.write_text(
        build_stage2_mechanism_report_text(decision_payload, sync_gain_rows),
        encoding="utf-8",
    )
    output_paths.stage2_mechanism_decision_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.stage2_mechanism_decision_path.write_text(
        json.dumps(decision_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        **decision_payload,
        "stage2_mechanism_audit_table_path": str(output_paths.stage2_mechanism_audit_table_path),
        "stage2_score_distribution_table_path": str(output_paths.stage2_score_distribution_table_path),
        "stage2_sync_gain_table_path": str(output_paths.stage2_sync_gain_table_path),
        "stage2_mechanism_report_path": str(output_paths.stage2_mechanism_report_path),
        "stage2_mechanism_decision_path": str(output_paths.stage2_mechanism_decision_path),
    }


def build_stage2_mechanism_audit_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
    *,
    allowed_splits: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Build the mechanism audit table rows from governed records.

    Args:
        event_score_records: Governed event score records.
        threshold_records: Governed threshold records.
        allowed_splits: Optional split allowlist. Defaults to `{"test"}`.

    Returns:
        Stage-two mechanism audit table rows.
    """
    rows: list[dict[str, Any]] = []
    threshold_index = _build_threshold_index(threshold_records)
    selected_records = _filter_records_by_splits(event_score_records, allowed_splits)
    grouped_keys = sorted(
        {
            (
                str(record.get("method_variant")),
                str(record.get("base_method_variant", record.get("method_variant"))),
                str(record.get("attack_name")),
                str(record.get("sample_role")),
            )
            for record in selected_records
        }
    )
    for method_variant, base_method_variant, attack_name, sample_role in grouped_keys:
        grouped_records = [
            record
            for record in selected_records
            if str(record.get("method_variant")) == method_variant
            and str(record.get("attack_name")) == attack_name
            and str(record.get("sample_role")) == sample_role
        ]
        if not grouped_records:
            continue
        psnr_stats = _build_payload_numeric_distribution_stats(
            grouped_records,
            "quality_metrics",
            "watermarked_video_psnr",
        )
        rows.append(
            {
                "run_id": grouped_records[0].get("run_id"),
                "construction_phase": grouped_records[0].get("mechanism_trace", {}).get(
                    "construction_phase"
                ),
                "method_variant": method_variant,
                "base_method_variant": base_method_variant,
                "attack_name": attack_name,
                "sample_role": sample_role,
                "count": len(grouped_records),
                "S_tubelet_mean": _mean_record_score(grouped_records, "S_tubelet"),
                "S_tubelet_std": _std_record_score(grouped_records, "S_tubelet"),
                "S_sync_mean": _mean_record_score(grouped_records, "S_sync"),
                "S_sync_std": _std_record_score(grouped_records, "S_sync"),
                "S_final_mean": _mean_record_score(grouped_records, "S_final"),
                "S_final_std": _std_record_score(grouped_records, "S_final"),
                "decision_rate": _decision_rate(grouped_records, threshold_index),
                "clean_negative_FPR": _decision_rate_for_role(
                    selected_records,
                    method_variant,
                    attack_name,
                    "clean_negative",
                    threshold_index,
                ),
                "attacked_negative_FPR": _decision_rate_for_role(
                    selected_records,
                    method_variant,
                    attack_name,
                    "attacked_negative",
                    threshold_index,
                ),
                "clean_positive_TPR": _decision_rate_for_role(
                    selected_records,
                    method_variant,
                    attack_name,
                    "watermarked_positive",
                    threshold_index,
                ),
                "attacked_positive_TPR": _decision_rate_for_role(
                    selected_records,
                    method_variant,
                    attack_name,
                    "attacked_positive",
                    threshold_index,
                ),
                "local_clip_TPR": _local_clip_tpr(
                    selected_records,
                    method_variant,
                    attack_name,
                    threshold_index,
                ),
                "sync_alignment_error_mean": _mean_mechanism_trace_value(grouped_records, "sync_alignment_error"),
                "sync_peak_rank_median": _median_mechanism_trace_value(grouped_records, "sync_peak_rank"),
                "quality_psnr_mean": _mean_payload_value(
                    grouped_records,
                    "quality_metrics",
                    "watermarked_video_psnr",
                    allow_positive_infinity=True,
                ),
                "quality_psnr_finite_mean": psnr_stats["finite_mean"],
                "quality_psnr_finite_count": psnr_stats["finite_count"],
                "quality_psnr_inf_count": psnr_stats["positive_infinity_count"],
                "quality_psnr_total_count": psnr_stats["total_count"],
                "quality_ssim_mean": _mean_payload_value(grouped_records, "quality_metrics", "watermarked_video_ssim"),
                "temporal_consistency_score_mean": _mean_payload_value(grouped_records, "temporal_metrics", "temporal_consistency_score"),
                "flicker_score_mean": _mean_payload_value(grouped_records, "temporal_metrics", "flicker_score"),
            }
        )
    return rows


def build_stage2_score_distribution_rows(
    event_score_records: list[dict[str, Any]],
    *,
    allowed_splits: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Build score-distribution rows from governed records.

    Args:
        event_score_records: Governed event score records.
        allowed_splits: Optional split allowlist. Defaults to `{"test"}`.

    Returns:
        Stage-two score distribution rows.
    """
    rows: list[dict[str, Any]] = []
    selected_records = _filter_records_by_splits(event_score_records, allowed_splits)
    grouped_keys = sorted(
        {
            (
                str(record.get("method_variant")),
                str(record.get("attack_name")),
                str(record.get("sample_role")),
            )
            for record in selected_records
        }
    )
    for method_variant, attack_name, sample_role in grouped_keys:
        grouped_records = [
            record
            for record in selected_records
            if str(record.get("method_variant")) == method_variant
            and str(record.get("attack_name")) == attack_name
            and str(record.get("sample_role")) == sample_role
        ]
        if not grouped_records:
            continue
        rows.append(
            {
                "run_id": grouped_records[0].get("run_id"),
                "construction_phase": grouped_records[0].get("mechanism_trace", {}).get(
                    "construction_phase"
                ),
                "method_variant": method_variant,
                "attack_name": attack_name,
                "sample_role": sample_role,
                "count": len(grouped_records),
                "S_tubelet_mean": _mean_record_score(grouped_records, "S_tubelet"),
                "S_tubelet_std": _std_record_score(grouped_records, "S_tubelet"),
                "S_sync_mean": _mean_record_score(grouped_records, "S_sync"),
                "S_sync_std": _std_record_score(grouped_records, "S_sync"),
                "S_final_mean": _mean_record_score(grouped_records, "S_final"),
                "S_final_std": _std_record_score(grouped_records, "S_final"),
            }
        )
    return rows


def build_stage2_sync_gain_rows(
    event_score_records: list[dict[str, Any]],
    *,
    required_attacks: list[str],
    allowed_splits: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Build sync-gain rows comparing tubelet_only and tubelet_sync.

    Args:
        event_score_records: Governed event score records.
        required_attacks: Required attack names to report.
        allowed_splits: Optional split allowlist. Defaults to `{"test"}`.

    Returns:
        Stage-two sync-gain rows.
    """
    selected_records = _filter_records_by_splits(event_score_records, allowed_splits)
    observed_attacks = sorted({str(record.get("attack_name")) for record in selected_records})
    attack_names = sorted(set(required_attacks) | set(observed_attacks))
    rows: list[dict[str, Any]] = []
    for attack_name in attack_names:
        metric_name = "clean_positive_tpr" if attack_name == "no_attack" else "attacked_positive_tpr"
        tubelet_only_positive_rate = _relevant_positive_rate(selected_records, "tubelet_only", attack_name)
        tubelet_sync_positive_rate = _relevant_positive_rate(selected_records, "tubelet_sync", attack_name)
        negative_fpr_delta = _difference(
            _relevant_negative_rate(selected_records, "tubelet_sync", attack_name),
            _relevant_negative_rate(selected_records, "tubelet_only", attack_name),
        )
        rows.append(
            {
                "attack_name": attack_name,
                "metric_name": metric_name,
                "tubelet_only_value": tubelet_only_positive_rate,
                "tubelet_sync_value": tubelet_sync_positive_rate,
                "sync_gain": _difference(tubelet_sync_positive_rate, tubelet_only_positive_rate),
                "negative_fpr_delta": negative_fpr_delta,
                "positive_count": _relevant_positive_count(selected_records, "tubelet_sync", attack_name),
                "negative_count": _relevant_negative_count(selected_records, "tubelet_sync", attack_name),
                "mechanism_signal_status": _mechanism_signal_status(
                    _difference(tubelet_sync_positive_rate, tubelet_only_positive_rate),
                    negative_fpr_delta,
                ),
            }
        )
        rows.append(
            {
                "attack_name": attack_name,
                "metric_name": "S_final_positive_mean",
                "tubelet_only_value": _relevant_positive_score_mean(selected_records, "tubelet_only", attack_name, "S_final"),
                "tubelet_sync_value": _relevant_positive_score_mean(selected_records, "tubelet_sync", attack_name, "S_final"),
                "sync_gain": _difference(
                    _relevant_positive_score_mean(selected_records, "tubelet_sync", attack_name, "S_final"),
                    _relevant_positive_score_mean(selected_records, "tubelet_only", attack_name, "S_final"),
                ),
                "negative_fpr_delta": negative_fpr_delta,
                "positive_count": _relevant_positive_count(selected_records, "tubelet_sync", attack_name),
                "negative_count": _relevant_negative_count(selected_records, "tubelet_sync", attack_name),
                "mechanism_signal_status": _mechanism_signal_status(
                    _difference(
                        _relevant_positive_score_mean(selected_records, "tubelet_sync", attack_name, "S_final"),
                        _relevant_positive_score_mean(selected_records, "tubelet_only", attack_name, "S_final"),
                    ),
                    negative_fpr_delta,
                ),
            }
        )
    return rows


def _filter_records_by_splits(
    event_score_records: list[dict[str, Any]],
    allowed_splits: set[str] | None,
) -> list[dict[str, Any]]:
    """Filter governed records to the requested split set.

    Args:
        event_score_records: Governed event score records.
        allowed_splits: Optional split allowlist. Defaults to `{"test"}`.

    Returns:
        The filtered event score records.
    """
    resolved_splits = {"test"} if allowed_splits is None else {str(split_name) for split_name in allowed_splits}
    return [
        record
        for record in event_score_records
        if str(record.get("split")) in resolved_splits
    ]


def build_stage2_mechanism_decision(
    *,
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
    mechanism_config: dict[str, Any],
    governance_summary_row: dict[str, Any],
    runtime_config: dict[str, Any],
    target_fpr: float | None,
) -> dict[str, Any]:
    """Build the stage-two mechanism gate decision from governed records."""
    mechanism_protocol = _resolve_stage2_mechanism_protocol(mechanism_config)
    implementation_decision = str(
        governance_summary_row.get("real_video_vae_latent_decision", "INCONCLUSIVE")
    )
    next_allowed_stage_by_implementation = str(
        governance_summary_row.get("next_allowed_stage", "remain_in_real_video_vae_latent_probe")
    )
    required_variants = _string_list(mechanism_config.get("required_main_variants", []))
    required_attacks = _string_list(mechanism_config.get("required_mechanism_attacks", []))
    observed_variants = {str(record.get("method_variant")) for record in event_score_records}
    test_records = [record for record in event_score_records if record.get("split") == "test"]
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    missing_variants = sorted(set(required_variants) - observed_variants)
    if missing_variants:
        blocking_reasons.append("missing_required_main_variants")

    missing_attacks = [
        attack_name
        for attack_name in required_attacks
        if not any(str(record.get("attack_name")) == attack_name for record in test_records)
    ]
    if missing_attacks:
        blocking_reasons.append("missing_required_mechanism_attacks")

    if implementation_decision != "PASS":
        warnings.append("implementation_decision_not_pass")

    minimum_positive_count = int(mechanism_config.get("minimum_positive_count_per_key", 0) or 0)
    minimum_negative_count = int(mechanism_config.get("minimum_negative_count_per_key", 0) or 0)
    insufficient_keys = [
        {
            "method_variant": method_variant,
            "attack_name": attack_name,
            "positive_count": _relevant_positive_count(test_records, method_variant, attack_name),
            "negative_count": _relevant_negative_count(test_records, method_variant, attack_name),
        }
        for method_variant in required_variants
        for attack_name in required_attacks
        if _relevant_positive_count(test_records, method_variant, attack_name) < minimum_positive_count
        or _relevant_negative_count(test_records, method_variant, attack_name) < minimum_negative_count
    ]
    if insufficient_keys:
        blocking_reasons.append("sample_count_insufficient")

    max_clean_negative_fpr = _safe_float(
        mechanism_config.get("max_clean_negative_fpr"),
    )
    if max_clean_negative_fpr is not None:
        clean_negative_failures = [
            method_variant
            for method_variant in required_variants
            if (_relevant_negative_rate(test_records, method_variant, "no_attack") or 0.0) > max_clean_negative_fpr
        ]
        if clean_negative_failures:
            blocking_reasons.append("clean_negative_fpr_not_controlled")

    max_attacked_negative_fpr = _safe_float(mechanism_config.get("max_attacked_negative_fpr"))
    attacked_negative_failures = [
        attack_name
        for attack_name in required_attacks
        if attack_name != "no_attack"
        and (_max_attacked_negative_rate(test_records, required_variants, attack_name) or 0.0) > (max_attacked_negative_fpr or 1.0)
    ]
    if attacked_negative_failures:
        blocking_reasons.append("attacked_negative_fpr_not_controlled")

    min_no_attack_clean_positive_tpr = _safe_float(
        mechanism_config.get("min_no_attack_clean_positive_tpr")
    )
    if min_no_attack_clean_positive_tpr is not None:
        for method_variant in ("tubelet_only", "tubelet_sync"):
            no_attack_positive_tpr = _relevant_positive_rate(test_records, method_variant, "no_attack")
            if no_attack_positive_tpr is None or no_attack_positive_tpr < min_no_attack_clean_positive_tpr:
                blocking_reasons.append(f"{method_variant}_no_attack_positive_tpr_low")

    min_tubelet_gain = _safe_float(mechanism_config.get("min_tubelet_only_gain_over_frame_prc"))
    tubelet_only_gain = _aggregate_positive_rate(test_records, "tubelet_only", required_attacks) - _aggregate_positive_rate(
        test_records,
        "frame_prc",
        required_attacks,
    )
    if min_tubelet_gain is not None and tubelet_only_gain < min_tubelet_gain:
        blocking_reasons.append("tubelet_only_not_above_frame_prc")

    temporal_attacks = [attack_name for attack_name in required_attacks if attack_name in TEMPORAL_ATTACKS]
    sync_temporal_gain = _aggregate_positive_rate(test_records, "tubelet_sync", temporal_attacks) - _aggregate_positive_rate(
        test_records,
        "tubelet_only",
        temporal_attacks,
    )
    sync_semantics = build_sync_gain_assessment(
        absolute_tprs={
            attack_name: _relevant_positive_rate(test_records, "tubelet_sync", attack_name)
            for attack_name in temporal_attacks
        },
        sync_gains={
            attack_name: _difference(
                _relevant_positive_rate(test_records, "tubelet_sync", attack_name),
                _relevant_positive_rate(test_records, "tubelet_only", attack_name),
            )
            for attack_name in temporal_attacks
        },
        mean_temporal_sync_gain=sync_temporal_gain,
        clean_negative_fpr=_relevant_negative_rate(test_records, "tubelet_sync", "no_attack"),
        max_attacked_negative_fpr=_max_numeric_value(
            [
                _relevant_negative_rate(test_records, "tubelet_sync", attack_name)
                for attack_name in temporal_attacks
            ]
        ),
        mechanism_config=mechanism_config,
    )
    if sync_semantics["sync_rescue_decision"] == "FAIL":
        blocking_reasons.append("tubelet_sync_not_above_tubelet_only_temporal")

    require_quality_not_collapsed = bool(mechanism_config.get("require_quality_not_collapsed", False))
    min_psnr = _safe_float(mechanism_config.get("min_watermarked_video_psnr"))
    min_ssim = _safe_float(mechanism_config.get("min_watermarked_video_ssim"))
    positive_quality_records = [
        record
        for record in test_records
        if str(record.get("sample_role")) in {"watermarked_positive", "attacked_positive"}
        and str(record.get("method_variant")) in set(required_variants)
    ]
    mean_psnr = _mean_payload_value(
        positive_quality_records,
        "quality_metrics",
        "watermarked_video_psnr",
        allow_positive_infinity=True,
    )
    psnr_stats = _build_payload_numeric_distribution_stats(
        positive_quality_records,
        "quality_metrics",
        "watermarked_video_psnr",
    )
    mean_ssim = _mean_payload_value(positive_quality_records, "quality_metrics", "watermarked_video_ssim")
    if require_quality_not_collapsed and (
        mean_psnr is None
        or mean_ssim is None
        or (min_psnr is not None and mean_psnr < min_psnr)
        or (min_ssim is not None and mean_ssim < min_ssim)
    ):
        blocking_reasons.append("quality_collapsed")

    quality_metrics_enabled = _quality_metrics_enabled(runtime_config, test_records)
    temporal_metrics_enabled = _temporal_metrics_enabled(runtime_config, test_records)
    if not quality_metrics_enabled["lpips"]:
        warnings.append("lpips_not_enabled")
    if not quality_metrics_enabled["clip_similarity"]:
        warnings.append("clip_similarity_not_enabled")
    if not temporal_metrics_enabled["motion_consistency"]:
        warnings.append("motion_consistency_not_enabled")

    inconclusive_reasons = {
        "missing_required_main_variants",
        "missing_required_mechanism_attacks",
        "sample_count_insufficient",
    }
    if implementation_decision != "PASS":
        mechanism_decision = "INCONCLUSIVE"
        recommended_next_action = "stage2_implementation_fix"
    elif any(reason in inconclusive_reasons for reason in blocking_reasons):
        mechanism_decision = "INCONCLUSIVE"
        recommended_next_action = "stage2_mechanism_calibration_run"
    elif blocking_reasons:
        mechanism_decision = "FAIL"
        recommended_next_action = "stage2_mechanism_calibration_run"
    else:
        mechanism_decision = "PASS"
        recommended_next_action = "trajectory_statistic_probe"

    next_allowed_stage_by_mechanism = (
        "trajectory_statistic_probe"
        if mechanism_decision == "PASS"
        else "remain_in_real_video_vae_latent_probe"
    )
    resolved_target_fpr = target_fpr
    if resolved_target_fpr is None:
        resolved_target_fpr = _safe_float(mechanism_config.get("target_fpr"))
    if resolved_target_fpr is None and event_score_records:
        resolved_target_fpr = _safe_float(event_score_records[0].get("target_fpr"))

    return {
        "run_id": event_score_records[0].get("run_id") if event_score_records else None,
        "construction_phase": mechanism_config.get("construction_phase", "real_video_vae_latent_probe"),
        "stage2_mechanism_protocol": mechanism_protocol,
        "target_fpr": resolved_target_fpr,
        "Stage2ImplementationDecision": implementation_decision,
        "Stage2MechanismDecision": mechanism_decision,
        "Stage2MechanismBlockingReasons": sorted(dict.fromkeys(blocking_reasons)),
        "Stage2MechanismWarnings": sorted(dict.fromkeys(warnings)),
        "NextAllowedStageByImplementation": next_allowed_stage_by_implementation,
        "NextAllowedStageByMechanism": next_allowed_stage_by_mechanism,
        "RecommendedNextAction": recommended_next_action,
        "quality_metrics_enabled": quality_metrics_enabled,
        "temporal_metrics_enabled": temporal_metrics_enabled,
        "sample_count_summary": {
            "minimum_positive_count_per_key": minimum_positive_count,
            "minimum_negative_count_per_key": minimum_negative_count,
            "insufficient_keys": insufficient_keys,
        },
        "mechanism_metrics": {
            "tubelet_only_gain_over_frame_prc": _round_or_none(tubelet_only_gain),
            "tubelet_sync_gain_over_tubelet_only_temporal": _round_or_none(sync_temporal_gain),
            "tubelet_sync_required_attack_gain_count": sync_semantics[
                "positive_gain_attack_count"
            ],
            "mean_watermarked_video_psnr": _round_or_none(mean_psnr),
            "mean_watermarked_video_psnr_finite": _round_or_none(
                psnr_stats["finite_mean"]
            ),
            "watermarked_video_psnr_finite_count": psnr_stats["finite_count"],
            "watermarked_video_psnr_inf_count": psnr_stats[
                "positive_infinity_count"
            ],
            "watermarked_video_psnr_total_count": psnr_stats["total_count"],
            "mean_watermarked_video_ssim": _round_or_none(mean_ssim),
        },
        "SyncRescueDecision": sync_semantics["sync_rescue_decision"],
        "SyncLeakageDecision": sync_semantics["sync_leakage_decision"],
        "SyncCandidateSelectionStatus": sync_semantics["candidate_selection_status"],
        "SyncAbsoluteRescueStatus": sync_semantics["absolute_rescue_status"],
        "SyncIncrementalGainStatus": sync_semantics["incremental_gain_status"],
        "SyncNegativeLeakageStatus": sync_semantics["negative_leakage_status"],
    }


def build_stage2_mechanism_report_text(
    decision_payload: dict[str, Any],
    sync_gain_rows: list[dict[str, Any]],
) -> str:
    """Build the stage-two mechanism audit report text."""
    sync_gain_preview = [
        row
        for row in sync_gain_rows
        if row.get("metric_name") in {"clean_positive_tpr", "attacked_positive_tpr"}
    ][:5]
    return "\n".join(
        [
            "# Stage2 Mechanism Audit Report",
            "",
            "## Decisions",
            f"- stage2_mechanism_protocol: {decision_payload['stage2_mechanism_protocol']}",
            f"- Stage2ImplementationDecision: {decision_payload['Stage2ImplementationDecision']}",
            f"- Stage2MechanismDecision: {decision_payload['Stage2MechanismDecision']}",
            f"- Stage2MechanismBlockingReasons: {', '.join(decision_payload['Stage2MechanismBlockingReasons']) or 'none'}",
            f"- Stage2MechanismWarnings: {', '.join(decision_payload['Stage2MechanismWarnings']) or 'none'}",
            f"- NextAllowedStageByImplementation: {decision_payload['NextAllowedStageByImplementation']}",
            f"- NextAllowedStageByMechanism: {decision_payload['NextAllowedStageByMechanism']}",
            f"- RecommendedNextAction: {decision_payload['RecommendedNextAction']}",
            f"- SyncRescueDecision: {decision_payload['SyncRescueDecision']}",
            f"- SyncLeakageDecision: {decision_payload['SyncLeakageDecision']}",
            f"- SyncCandidateSelectionStatus: {decision_payload['SyncCandidateSelectionStatus']}",
            f"- SyncAbsoluteRescueStatus: {decision_payload['SyncAbsoluteRescueStatus']}",
            f"- SyncIncrementalGainStatus: {decision_payload['SyncIncrementalGainStatus']}",
            f"- SyncNegativeLeakageStatus: {decision_payload['SyncNegativeLeakageStatus']}",
            "",
            "## Metric Enablement",
            f"- quality_metrics_enabled: {json.dumps(decision_payload['quality_metrics_enabled'], ensure_ascii=False)}",
            f"- temporal_metrics_enabled: {json.dumps(decision_payload['temporal_metrics_enabled'], ensure_ascii=False)}",
            "",
            "## Mechanism Metrics",
            *[
                f"- {metric_name}: {metric_value}"
                for metric_name, metric_value in decision_payload["mechanism_metrics"].items()
            ],
            "",
            "## Sync Gain Preview",
            *[
                f"- {row['attack_name']} / {row['metric_name']}: sync_gain={row['sync_gain']}, negative_fpr_delta={row['negative_fpr_delta']}, status={row['mechanism_signal_status']}"
                for row in sync_gain_preview
            ],
        ]
    ) + "\n"


def _resolve_stage2_mechanism_protocol(mechanism_config: dict[str, Any]) -> str:
    """解析阶段 2 机制证明协议, 并在启动时阻断旧 sync gap 口径。"""
    protocol = str(
        mechanism_config.get("stage2_mechanism_protocol", STAGE2_MECHANISM_PROTOCOL)
    ).strip()
    if protocol != STAGE2_MECHANISM_PROTOCOL:
        raise ValueError(
            "stage2_mechanism_protocol must be aligned_payload_safety"
        )
    forbidden_keys = [
        key_name
        for key_name in (
            "min_sync_positive_negative_score_gap",
            "sync_positive_negative_score_gap_min",
        )
        if key_name in mechanism_config
    ]
    if forbidden_keys:
        raise ValueError(
            "阶段 2 aligned_payload_safety 协议禁止使用旧 sync score gap 阻塞字段: "
            + ", ".join(sorted(forbidden_keys))
        )
    return protocol


def _read_single_csv_row(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            return dict(row)
    return {}


def _read_json_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _values_for_payload(records: list[dict[str, Any]], payload_key: str, value_key: str) -> list[float]:
    values: list[float] = []
    for record in records:
        payload = record.get(payload_key, {})
        if not isinstance(payload, dict):
            continue
        numeric_value = _safe_float(payload.get(value_key))
        if numeric_value is None:
            continue
        values.append(numeric_value)
    return values


def _build_payload_numeric_distribution_stats(
    records: list[dict[str, Any]],
    payload_key: str,
    value_key: str,
) -> dict[str, int | float | None]:
    """统计 payload 数值的有限值和正无穷值, 用于把 PSNR 的完美重建和普通均值分开记录。"""
    finite_values: list[float] = []
    positive_infinity_count = 0
    total_count = 0
    for value in _values_for_payload(records, payload_key, value_key):
        total_count += 1
        numeric_value = float(value)
        if math.isfinite(numeric_value):
            finite_values.append(numeric_value)
        elif math.isinf(numeric_value) and numeric_value > 0:
            positive_infinity_count += 1
    finite_mean = (
        round(statistics.fmean(finite_values), 6)
        if finite_values
        else None
    )
    return {
        "finite_mean": finite_mean,
        "finite_count": len(finite_values),
        "positive_infinity_count": positive_infinity_count,
        "total_count": total_count,
    }


def _values_for_score(records: list[dict[str, Any]], score_name: str) -> list[float]:
    values: list[float] = []
    for record in records:
        evidence_scores = record.get("evidence_scores", {})
        if not isinstance(evidence_scores, dict):
            continue
        numeric_value = _safe_float(evidence_scores.get(score_name))
        if numeric_value is None:
            continue
        values.append(numeric_value)
    return values


def _mean(
    values: list[float | None],
    *,
    allow_positive_infinity: bool = False,
) -> float | None:
    filtered_values: list[float] = []
    positive_infinity_present = False
    for value in values:
        if value is None:
            continue
        numeric_value = float(value)
        if math.isfinite(numeric_value):
            filtered_values.append(numeric_value)
            continue
        if allow_positive_infinity and math.isinf(numeric_value) and numeric_value > 0:
            positive_infinity_present = True
    if not filtered_values:
        if positive_infinity_present:
            return math.inf
        return None
    if positive_infinity_present:
        return math.inf
    return round(statistics.fmean(filtered_values), 6)


def _max_numeric_value(values: list[float | None]) -> float | None:
    filtered_values = [float(value) for value in values if value is not None]
    if not filtered_values:
        return None
    return round(max(filtered_values), 6)


def _std(values: list[float | None]) -> float | None:
    filtered_values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not filtered_values:
        return None
    if len(filtered_values) == 1:
        return 0.0
    return round(statistics.pstdev(filtered_values), 6)


def _median(values: list[float | None]) -> float | None:
    filtered_values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not filtered_values:
        return None
    return round(float(statistics.median(filtered_values)), 6)


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_threshold_index(threshold_records: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for threshold_record in threshold_records:
        threshold_id = threshold_record.get("threshold_id")
        if isinstance(threshold_id, str) and threshold_id:
            by_id[threshold_id] = threshold_record
        method_variant = threshold_record.get("method_variant")
        if isinstance(method_variant, str) and method_variant:
            by_variant.setdefault(method_variant, []).append(threshold_record)
    return {
        "by_id": by_id,
        "by_variant": by_variant,
    }


def _resolve_threshold_value(
    record: dict[str, Any],
    threshold_index: dict[str, Any] | None,
) -> float | None:
    if not isinstance(threshold_index, dict):
        return None
    by_id = threshold_index.get("by_id")
    by_variant = threshold_index.get("by_variant")
    threshold_id = record.get("threshold_id")
    if isinstance(by_id, dict) and isinstance(threshold_id, str) and threshold_id:
        threshold_record = by_id.get(threshold_id)
        if isinstance(threshold_record, dict):
            threshold_value = _safe_float(threshold_record.get("threshold_value"))
            if threshold_value is not None:
                return threshold_value

    method_variant = str(record.get("method_variant", ""))
    if not isinstance(by_variant, dict) or not method_variant:
        return None
    variant_threshold_records = by_variant.get(method_variant, [])
    if not isinstance(variant_threshold_records, list) or not variant_threshold_records:
        return None

    target_fpr = _safe_float(record.get("target_fpr"))
    if target_fpr is not None:
        matched_threshold_value = _resolve_unique_threshold_value(
            [
                threshold_record
                for threshold_record in variant_threshold_records
                if _target_fpr_matches(_safe_float(threshold_record.get("target_fpr")), target_fpr)
            ]
        )
        if matched_threshold_value is not None:
            return matched_threshold_value
    return _resolve_unique_threshold_value(variant_threshold_records)


def _resolve_unique_threshold_value(threshold_records: list[dict[str, Any]]) -> float | None:
    numeric_values = {
        float(threshold_value)
        for threshold_record in threshold_records
        for threshold_value in [_safe_float(threshold_record.get("threshold_value"))]
        if threshold_value is not None
    }
    if len(numeric_values) != 1:
        return None
    return next(iter(numeric_values))


def _target_fpr_matches(left_value: float | None, right_value: float) -> bool:
    if left_value is None:
        return False
    return math.isclose(float(left_value), float(right_value), rel_tol=1e-9, abs_tol=1e-12)


def _resolved_decision_value(
    record: dict[str, Any],
    threshold_index: dict[str, Any] | None,
) -> float:
    threshold_value = _resolve_threshold_value(record, threshold_index)
    if threshold_value is not None:
        evidence_scores = record.get("evidence_scores", {})
        final_score = None
        if isinstance(evidence_scores, dict):
            final_score = _safe_float(evidence_scores.get("S_final"))
        if final_score is None:
            return 0.0
        return 1.0 if float(final_score) >= float(threshold_value) else 0.0
    return 1.0 if bool(record.get("decision")) else 0.0


def _decision_rate(
    records: list[dict[str, Any]],
    threshold_index: dict[str, Any] | None = None,
) -> float | None:
    if not records:
        return None
    decision_values = [
        _resolved_decision_value(record, threshold_index)
        for record in records
    ]
    return _mean(decision_values)


def _decision_rate_for_role(
    records: list[dict[str, Any]],
    method_variant: str,
    attack_name: str,
    sample_role: str,
    threshold_index: dict[str, Any] | None = None,
) -> float | None:
    matched_records = [
        record
        for record in records
        if str(record.get("method_variant")) == method_variant
        and str(record.get("attack_name")) == attack_name
        and str(record.get("sample_role")) == sample_role
    ]
    return _decision_rate(matched_records, threshold_index)


def _local_clip_tpr(
    records: list[dict[str, Any]],
    method_variant: str,
    attack_name: str,
    threshold_index: dict[str, Any] | None = None,
) -> float | None:
    if attack_name != "local_clip":
        return None
    return _decision_rate_for_role(
        records,
        method_variant,
        attack_name,
        "attacked_positive",
        threshold_index,
    )


def _mean_record_score(records: list[dict[str, Any]], score_name: str) -> float | None:
    return _mean(_values_for_score(records, score_name))


def _std_record_score(records: list[dict[str, Any]], score_name: str) -> float | None:
    return _std(_values_for_score(records, score_name))


def _mean_mechanism_trace_value(records: list[dict[str, Any]], value_key: str) -> float | None:
    values = [
        _safe_float(record.get("mechanism_trace", {}).get(value_key))
        for record in records
        if isinstance(record.get("mechanism_trace"), dict)
    ]
    return _mean(values)


def _median_mechanism_trace_value(records: list[dict[str, Any]], value_key: str) -> float | None:
    values = [
        _safe_float(record.get("mechanism_trace", {}).get(value_key))
        for record in records
        if isinstance(record.get("mechanism_trace"), dict)
    ]
    return _median(values)


def _mean_payload_value(
    records: list[dict[str, Any]],
    payload_key: str,
    value_key: str,
    *,
    allow_positive_infinity: bool = False,
) -> float | None:
    return _mean(
        _values_for_payload(records, payload_key, value_key),
        allow_positive_infinity=allow_positive_infinity,
    )


def _relevant_positive_role(attack_name: str) -> str:
    return "watermarked_positive" if attack_name == "no_attack" else "attacked_positive"


def _relevant_negative_role(attack_name: str) -> str:
    return "clean_negative" if attack_name == "no_attack" else "attacked_negative"


def _records_for_variant_attack_role(
    records: list[dict[str, Any]],
    method_variant: str,
    attack_name: str,
    sample_role: str,
) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if str(record.get("method_variant")) == method_variant
        and str(record.get("attack_name")) == attack_name
        and str(record.get("sample_role")) == sample_role
    ]


def _relevant_positive_rate(records: list[dict[str, Any]], method_variant: str, attack_name: str) -> float | None:
    return _decision_rate(
        _records_for_variant_attack_role(
            records,
            method_variant,
            attack_name,
            _relevant_positive_role(attack_name),
        )
    )


def _relevant_negative_rate(records: list[dict[str, Any]], method_variant: str, attack_name: str) -> float | None:
    return _decision_rate(
        _records_for_variant_attack_role(
            records,
            method_variant,
            attack_name,
            _relevant_negative_role(attack_name),
        )
    )


def _relevant_positive_count(records: list[dict[str, Any]], method_variant: str, attack_name: str) -> int:
    return len(
        _records_for_variant_attack_role(
            records,
            method_variant,
            attack_name,
            _relevant_positive_role(attack_name),
        )
    )


def _relevant_negative_count(records: list[dict[str, Any]], method_variant: str, attack_name: str) -> int:
    return len(
        _records_for_variant_attack_role(
            records,
            method_variant,
            attack_name,
            _relevant_negative_role(attack_name),
        )
    )


def _relevant_positive_score_mean(
    records: list[dict[str, Any]],
    method_variant: str,
    attack_name: str,
    score_name: str,
) -> float | None:
    matched_records = _records_for_variant_attack_role(
        records,
        method_variant,
        attack_name,
        _relevant_positive_role(attack_name),
    )
    return _mean_record_score(matched_records, score_name)


def _sync_positive_negative_gap(records: list[dict[str, Any]], attack_name: str) -> float | None:
    positive_records = _records_for_variant_attack_role(
        records,
        "tubelet_sync",
        attack_name,
        _relevant_positive_role(attack_name),
    )
    negative_records = _records_for_variant_attack_role(
        records,
        "tubelet_sync",
        attack_name,
        _relevant_negative_role(attack_name),
    )
    positive_mean = _mean_record_score(positive_records, "S_sync")
    negative_mean = _mean_record_score(negative_records, "S_sync")
    return _difference(positive_mean, negative_mean)


def _difference(left_value: float | None, right_value: float | None) -> float | None:
    if left_value is None or right_value is None:
        return None
    return round(left_value - right_value, 6)


def _aggregate_positive_rate(records: list[dict[str, Any]], method_variant: str, attack_names: list[str]) -> float:
    return float(
        _mean([
            _relevant_positive_rate(records, method_variant, attack_name)
            for attack_name in attack_names
        ])
        or 0.0
    )


def _max_attacked_negative_rate(
    records: list[dict[str, Any]],
    method_variants: list[str],
    attack_name: str,
) -> float | None:
    """返回同一攻击下各方法 attacked-negative FPR 的最大值。"""
    return _max_numeric_value(
        [
            _relevant_negative_rate(records, method_variant, attack_name)
            for method_variant in method_variants
        ]
    )


def _mechanism_signal_status(sync_gain: float | None, negative_fpr_delta: float | None) -> str:
    if sync_gain is None:
        return "insufficient_signal"
    if sync_gain > 0 and (negative_fpr_delta is None or negative_fpr_delta <= 0):
        return "positive_gain_with_controlled_fpr"
    if sync_gain > 0:
        return "positive_gain_with_fpr_risk"
    if sync_gain == 0:
        return "flat_signal"
    return "no_positive_gain"


def _quality_metrics_enabled(runtime_config: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, bool]:
    quality_config = runtime_config.get("quality_metrics", {}) if isinstance(runtime_config, dict) else {}
    any_lpips_signal = any(
        record.get("quality_metrics", {}).get("watermarked_video_lpips") is not None
        or record.get("quality_metrics", {}).get("lpips_failure_reason") not in {None, "lpips_disabled_by_config"}
        for record in records
    )
    any_clip_signal = any(
        record.get("quality_metrics", {}).get("clip_similarity_score") is not None
        or record.get("quality_metrics", {}).get("clip_failure_reason") not in {None, "clip_similarity_disabled_by_config"}
        for record in records
    )
    return {
        "psnr": True,
        "ssim": True,
        "lpips": bool(quality_config.get("enable_lpips", any_lpips_signal)),
        "clip_similarity": bool(quality_config.get("enable_clip_similarity", any_clip_signal)),
    }


def _temporal_metrics_enabled(runtime_config: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, bool]:
    temporal_config = runtime_config.get("temporal_metrics", {}) if isinstance(runtime_config, dict) else {}
    any_motion_signal = any(
        record.get("temporal_metrics", {}).get("motion_consistency_score") is not None
        or record.get("temporal_metrics", {}).get("motion_consistency_failure_reason") not in {None, "motion_consistency_disabled_by_config"}
        for record in records
    )
    return {
        "flicker_score": True,
        "motion_consistency": bool(
            temporal_config.get("enable_motion_consistency", any_motion_signal)
        ),
    }


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)

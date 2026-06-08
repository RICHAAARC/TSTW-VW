"""
文件用途：从阶段 2 dev / calibration records 中选择 mechanism calibration 候选并写出受治理输出。
File purpose: Select a stage-two mechanism calibration candidate from dev/calibration records and write governed outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.real_video_vae_latent_probe.mechanism_audit import (
    _build_threshold_index,
    _resolved_decision_value,
    _resolve_threshold_value,
)
from experiments.real_video_vae_latent_probe.mechanism_semantics import (
    build_anchor_selection_assessment,
    build_sync_gain_assessment,
)
from main.core.records import RecordWriter
from main.core.registry import load_json_config
from main.methods.temporal_tubelet_watermark.embedding import DEFAULT_EMBEDDING_MARGIN


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRID_CONFIG_PATH = (
    ROOT / "configs" / "ablation" / "stage2_vae_mechanism_calibration_grid.json"
)
DEFAULT_MECHANISM_CONFIG_PATH = ROOT / "configs" / "protocol" / "stage2_mechanism_gate.json"

CALIBRATION_GRID_COLUMNS = [
    "selection_scope",
    "method_variant",
    "base_method_variant",
    "tubelet_length",
    "spatial_patch_size",
    "embedding_projection_support_weight",
    "embedding_margin",
    "fusion_rule",
    "lambda_sync",
    "sync_search_radius",
    "min_sync_positive_margin",
    "min_sync_alignment_coverage_ratio",
    "min_sync_alignment_matched_count",
    "min_sync_candidate_score",
    "sync_confidence_gate_rule",
    "min_payload_rescue_gain",
    "min_aligned_payload_score",
    "no_attack_clean_negative_fpr",
    "no_attack_clean_positive_tpr",
    "max_attacked_negative_fpr",
    "aligned_payload_clean_negative_fpr",
    "aligned_payload_attacked_negative_fpr",
    "aligned_payload_positive_tpr",
    "aligned_payload_temporal_crop_tpr",
    "aligned_payload_local_clip_tpr",
    "sync_rescue_applied_positive_rate",
    "sync_rescue_applied_attacked_negative_rate",
    "negative_rescue_over_threshold_count",
    "aligned_payload_negative_safety_status",
    "aligned_payload_clean_negative_over_threshold_count",
    "aligned_payload_attacked_negative_over_threshold_count",
    "temporal_crop_attacked_positive_tpr",
    "frame_dropping_attacked_positive_tpr",
    "local_clip_attacked_positive_tpr",
    "mean_temporal_attacked_positive_tpr",
    "quality_psnr_mean",
    "quality_ssim_mean",
    "temporal_crop_sync_gain",
    "frame_dropping_sync_gain",
    "local_clip_sync_gain",
    "mean_temporal_sync_gain",
    "sync_confident_attacked_negative_count",
    "temporal_crop_absolute_tpr",
    "local_clip_absolute_tpr",
    "temporal_crop_anchor_headroom",
    "local_clip_anchor_headroom",
    "temporal_crop_saturated_anchor",
    "local_clip_saturated_anchor",
    "absolute_rescue_status",
    "incremental_gain_status",
    "negative_leakage_status",
    "sync_rescue_decision",
    "sync_leakage_decision",
    "candidate_selection_status",
    "fpr_controlled",
    "quality_not_collapsed",
    "candidate_eligible",
    "selection_score",
]


def select_stage2_mechanism_candidate(
    *,
    run_root: str | Path,
    grid_config_path: str | Path = DEFAULT_GRID_CONFIG_PATH,
    mechanism_config_path: str | Path = DEFAULT_MECHANISM_CONFIG_PATH,
    selection_scope: str = "full",
    selected_tubelet_only_candidate: dict[str, Any] | None = None,
    top_candidate_limit: int = 5,
    output_path: str | Path | None = None,
    report_path: str | Path | None = None,
    grid_output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Select a governed stage-two mechanism calibration candidate.

    Args:
        run_root: Run-root path.
        grid_config_path: Calibration-grid config path.
        mechanism_config_path: Mechanism-gate config path.
        selection_scope: Selection scope identifier.
        selected_tubelet_only_candidate: Optional selected tubelet-only candidate used by sync-only stages.
        top_candidate_limit: Maximum number of top rows retained in the payload summary.
        output_path: Optional candidate JSON output path.
        report_path: Optional markdown report output path.
        grid_output_path: Optional CSV grid output path.

    Returns:
        A governed candidate-selection payload.
    """
    run_root_path = Path(run_root)
    if not run_root_path.exists():
        raise FileNotFoundError(run_root_path)

    grid_config = load_json_config(grid_config_path)
    mechanism_config = load_json_config(mechanism_config_path)
    allowed_splits = _read_string_list(grid_config, "allowed_splits")
    forbidden_splits = _read_string_list(grid_config, "forbidden_splits")
    if set(allowed_splits) & set(forbidden_splits):
        raise ValueError("allowed_splits and forbidden_splits must not overlap")
    if selection_scope not in {"full", "tubelet_only", "tubelet_sync"}:
        raise ValueError("selection_scope must be one of: full, tubelet_only, tubelet_sync")
    resolved_top_candidate_limit = int(top_candidate_limit)
    if resolved_top_candidate_limit < 1:
        raise ValueError("top_candidate_limit must be a positive integer")

    record_writer = RecordWriter(run_root_path)
    try:
        threshold_records = record_writer.read_threshold_records()
    except FileNotFoundError:
        threshold_records = []

    selection_snapshot = _build_selection_snapshot(
        record_writer,
        threshold_records,
        allowed_splits=set(allowed_splits),
    )
    if int(selection_snapshot["record_count"]) < 1:
        raise ValueError("event_score_records must not be empty")

    tubelet_only_rows = _build_tubelet_only_calibration_grid_rows(
        selection_snapshot["audit_lookup"],
        selection_snapshot["candidate_variants_by_base"]["tubelet_only"],
        selection_snapshot["representative_records"],
        mechanism_config,
    )
    selected_candidate = None
    sync_scan_seed = None
    tubelet_sync_rows: list[dict[str, Any]] = []
    selected_tubelet_sync_candidate = None
    selection_completion_status = "complete"
    selection_blocking_reason = None
    selection_blocking_details = None
    if selection_scope == "tubelet_only":
        selected_candidate = _select_tubelet_only_candidate(
            tubelet_only_rows,
            mechanism_config,
            grid_config,
        )
        calibration_rows = list(tubelet_only_rows)
    elif selection_scope == "tubelet_sync":
        if selected_tubelet_only_candidate is None:
            raise ValueError(
                "selected_tubelet_only_candidate must be provided for tubelet_sync selection"
            )
        selected_candidate = selected_tubelet_only_candidate
        sync_scan_seed = _build_tubelet_sync_scan_seed(
            selected_candidate,
            grid_config,
        )
        tubelet_sync_rows = _build_tubelet_sync_calibration_grid_rows(
            selection_snapshot["audit_lookup"],
            selection_snapshot["candidate_variants_by_base"]["tubelet_sync"],
            selection_snapshot["representative_records"],
            selection_snapshot["sync_confident_attacked_negative_counts"],
            selection_snapshot["method_safety_metrics"],
            mechanism_config,
            selected_candidate=selected_candidate,
        )
        if tubelet_sync_rows:
            selected_tubelet_sync_candidate = _select_tubelet_sync_candidate(
                tubelet_sync_rows,
                mechanism_config,
            )
            if selected_tubelet_sync_candidate is None:
                selection_completion_status = "incomplete_no_eligible_tubelet_sync_candidate"
                selection_blocking_reason = "no_tubelet_sync_candidate_passes_selection_gate"
        else:
            selection_completion_status = "incomplete_no_compatible_tubelet_sync_rows"
            selection_blocking_reason = "selected_anchor_not_covered_by_sync_stage_records"
            selection_blocking_details = _build_sync_stage_blocking_details(
                selection_snapshot["tubelet_sync_signatures"],
                selected_candidate,
            )
        calibration_rows = list(tubelet_sync_rows)
    else:
        selected_candidate = _select_tubelet_only_candidate(
            tubelet_only_rows,
            mechanism_config,
            grid_config,
        )
        sync_scan_seed = _build_tubelet_sync_scan_seed(
            selected_candidate,
            grid_config,
        )
        tubelet_sync_rows = _build_tubelet_sync_calibration_grid_rows(
            selection_snapshot["audit_lookup"],
            selection_snapshot["candidate_variants_by_base"]["tubelet_sync"],
            selection_snapshot["representative_records"],
            selection_snapshot["sync_confident_attacked_negative_counts"],
            selection_snapshot["method_safety_metrics"],
            mechanism_config,
            selected_candidate=selected_candidate,
        )
        if tubelet_sync_rows:
            selected_tubelet_sync_candidate = _select_tubelet_sync_candidate(
                tubelet_sync_rows,
                mechanism_config,
            )
            if selected_tubelet_sync_candidate is None:
                selection_completion_status = "incomplete_no_eligible_tubelet_sync_candidate"
                selection_blocking_reason = "no_tubelet_sync_candidate_passes_selection_gate"
        else:
            selection_completion_status = "incomplete_no_compatible_tubelet_sync_rows"
            selection_blocking_reason = "selected_anchor_not_covered_by_sync_stage_records"
            selection_blocking_details = _build_sync_stage_blocking_details(
                selection_snapshot["tubelet_sync_signatures"],
                selected_candidate,
            )
        calibration_rows = [*tubelet_only_rows, *tubelet_sync_rows]
    observed_splits = list(selection_snapshot["observed_splits"])
    observed_forbidden_splits = sorted(set(observed_splits) & set(forbidden_splits))

    candidate_payload = {
        "run_root": str(run_root_path),
        "construction_phase": grid_config.get(
            "construction_phase",
            mechanism_config.get("construction_phase", "real_video_vae_latent_probe"),
        ),
        "calibration_purpose": grid_config.get(
            "calibration_purpose",
            "stage2_mechanism_effect_calibration",
        ),
        "allowed_splits": allowed_splits,
        "forbidden_splits": forbidden_splits,
        "observed_splits": observed_splits,
        "observed_forbidden_splits": observed_forbidden_splits,
        "selection_scope": selection_scope,
        "selection_completion_status": selection_completion_status,
        "selection_blocking_reason": selection_blocking_reason,
        "selection_blocking_details": selection_blocking_details,
        "top_candidate_limit": resolved_top_candidate_limit,
        "selection_metrics": _read_string_list(grid_config, "selection_metrics"),
        "selected_tubelet_only_candidate": selected_candidate,
        "tubelet_sync_scan_seed": sync_scan_seed,
        "selected_tubelet_sync_candidate": selected_tubelet_sync_candidate,
        "top_tubelet_only_candidates": _build_top_candidate_rows(
            tubelet_only_rows,
            resolved_top_candidate_limit,
        ),
        "top_tubelet_sync_candidates": _build_top_candidate_rows(
            tubelet_sync_rows,
            resolved_top_candidate_limit,
        ),
        "parameter_interval_summary": {
            "tubelet_only": _build_parameter_interval_summary(
                tubelet_only_rows[:resolved_top_candidate_limit],
                [
                    "tubelet_length",
                    "spatial_patch_size",
                    "embedding_projection_support_weight",
                ],
            ),
            "tubelet_sync": _build_parameter_interval_summary(
                tubelet_sync_rows[:resolved_top_candidate_limit],
                [
                    "fusion_rule",
                    "lambda_sync",
                    "sync_search_radius",
                    "min_sync_positive_margin",
                    "min_sync_alignment_coverage_ratio",
                    "min_sync_alignment_matched_count",
                ],
            ),
        },
    }

    resolved_grid_output_path = Path(grid_output_path) if grid_output_path else (
        run_root_path / "tables" / "stage2_mechanism_calibration_grid.csv"
    )
    resolved_report_path = Path(report_path) if report_path else (
        run_root_path / "reports" / "stage2_mechanism_calibration_report.md"
    )
    resolved_output_path = Path(output_path) if output_path else (
        run_root_path / "artifacts" / "stage2_selected_mechanism_candidate.json"
    )
    _write_grid_csv(resolved_grid_output_path, calibration_rows)
    _write_text_report(resolved_report_path, candidate_payload, calibration_rows)
    _write_json(resolved_output_path, candidate_payload)

    return {
        **candidate_payload,
        "grid_output_path": str(resolved_grid_output_path),
        "report_path": str(resolved_report_path),
        "output_path": str(resolved_output_path),
    }


def _build_selection_snapshot(
    record_writer: RecordWriter,
    threshold_records: list[dict[str, Any]],
    *,
    allowed_splits: set[str],
) -> dict[str, Any]:
    threshold_index = _build_threshold_index(threshold_records)
    record_count = 0
    representative_records: dict[str, dict[str, Any]] = {}
    candidate_variants_by_base = {
        "tubelet_only": set(),
        "tubelet_sync": set(),
    }
    observed_splits: set[str] = set()
    tubelet_sync_signatures: set[tuple[int, str, float, float]] = set()
    sync_confident_attacked_negative_counts: dict[str, int] = defaultdict(int)
    method_safety_metrics: dict[str, dict[str, Any]] = defaultdict(
        _build_method_safety_state
    )
    grouped_metrics: dict[tuple[str, str, str], dict[str, Any]] = {}

    for event_record in record_writer.iter_event_score_records():
        record_count += 1
        method_variant = str(event_record.get("method_variant"))
        base_method_variant = str(
            event_record.get("base_method_variant", event_record.get("method_variant"))
        )
        split_name = str(event_record.get("split"))
        observed_splits.add(split_name)

        if method_variant not in representative_records:
            representative_records[method_variant] = event_record
        if base_method_variant in candidate_variants_by_base:
            candidate_variants_by_base[base_method_variant].add(method_variant)
        if base_method_variant == "tubelet_sync":
            tubelet_sync_signatures.add(_build_sync_stage_signature(event_record))

        if split_name not in allowed_splits:
            continue

        attack_name = str(event_record.get("attack_name"))
        sample_role = str(event_record.get("sample_role"))
        group_key = (method_variant, attack_name, sample_role)
        grouped_metrics.setdefault(
            group_key,
            _build_selection_group_state(event_record),
        )
        _update_selection_group_state(
            grouped_metrics[group_key],
            event_record,
            threshold_index,
        )
        if base_method_variant == "tubelet_sync":
            _update_method_safety_state(
                method_safety_metrics[method_variant],
                event_record,
                threshold_index,
            )
        if (
            base_method_variant == "tubelet_sync"
            and sample_role == "attacked_negative"
            and _record_sync_confident(event_record)
        ):
            sync_confident_attacked_negative_counts[method_variant] += 1

    return {
        "record_count": record_count,
        "audit_lookup": _build_selection_audit_lookup(grouped_metrics),
        "representative_records": representative_records,
        "candidate_variants_by_base": {
            base_method_variant: set(method_variants)
            for base_method_variant, method_variants in candidate_variants_by_base.items()
        },
        "observed_splits": sorted(observed_splits),
        "tubelet_sync_signatures": set(tubelet_sync_signatures),
        "sync_confident_attacked_negative_counts": dict(
            sync_confident_attacked_negative_counts
        ),
        "method_safety_metrics": {
            method_variant: _finalize_method_safety_state(method_safety_state)
            for method_variant, method_safety_state in method_safety_metrics.items()
        },
    }


def _build_selection_group_state(event_record: dict[str, Any]) -> dict[str, Any]:
    mechanism_trace = event_record.get("mechanism_trace", {})
    if not isinstance(mechanism_trace, dict):
        mechanism_trace = {}
    return {
        "run_id": event_record.get("run_id"),
        "construction_phase": mechanism_trace.get("construction_phase"),
        "decision_sum": 0.0,
        "decision_count": 0,
        "quality_psnr_state": _build_selection_mean_state(
            allow_positive_infinity=True,
        ),
        "quality_ssim_state": _build_selection_mean_state(),
        "aligned_payload_decision_sum": 0.0,
        "aligned_payload_decision_count": 0,
        "sync_rescue_applied_sum": 0.0,
        "sync_rescue_applied_count": 0,
    }


def _build_method_safety_state() -> dict[str, Any]:
    return {
        "negative_rescue_over_threshold_count": 0,
        "aligned_payload_clean_negative_over_threshold_count": 0,
        "aligned_payload_attacked_negative_over_threshold_count": 0,
    }


def _update_method_safety_state(
    method_safety_state: dict[str, Any],
    event_record: dict[str, Any],
    threshold_index: dict[str, Any],
) -> None:
    sample_role = str(event_record.get("sample_role"))
    split_name = str(event_record.get("split"))
    if sample_role not in {"clean_negative", "attacked_negative"}:
        return
    if _aligned_payload_decision_value(event_record, threshold_index) > 0.0:
        if sample_role == "clean_negative":
            method_safety_state[
                "aligned_payload_clean_negative_over_threshold_count"
            ] += 1
        else:
            method_safety_state[
                "aligned_payload_attacked_negative_over_threshold_count"
            ] += 1
    if (
        split_name == "calibration"
        and _record_sync_rescue_applied(event_record)
        and _resolved_decision_value(event_record, threshold_index) > 0.0
    ):
        method_safety_state["negative_rescue_over_threshold_count"] += 1


def _finalize_method_safety_state(method_safety_state: dict[str, Any]) -> dict[str, Any]:
    negative_rescue_count = int(
        method_safety_state.get("negative_rescue_over_threshold_count", 0)
    )
    return {
        **method_safety_state,
        "aligned_payload_negative_safety_status": (
            "PASS" if negative_rescue_count == 0 else "FAIL"
        ),
    }


def _record_sync_confident(event_record: dict[str, Any]) -> bool:
    mechanism_trace = event_record.get("mechanism_trace", {})
    if isinstance(mechanism_trace, dict) and "sync_confident" in mechanism_trace:
        return bool(mechanism_trace.get("sync_confident"))
    return bool(event_record.get("sync_confident"))


def _record_sync_rescue_applied(event_record: dict[str, Any]) -> bool:
    mechanism_trace = event_record.get("mechanism_trace", {})
    if isinstance(mechanism_trace, dict) and "sync_rescue_applied" in mechanism_trace:
        return bool(mechanism_trace.get("sync_rescue_applied"))
    return bool(event_record.get("sync_rescue_applied"))


def _aligned_payload_decision_value(
    event_record: dict[str, Any],
    threshold_index: dict[str, Any],
) -> float:
    threshold_value = _resolve_threshold_value(event_record, threshold_index)
    if threshold_value is None:
        return 0.0
    mechanism_trace = event_record.get("mechanism_trace", {})
    if not isinstance(mechanism_trace, dict):
        return 0.0
    aligned_payload_score = _safe_float(mechanism_trace.get("S_payload_aligned"))
    if aligned_payload_score is None:
        return 0.0
    return 1.0 if float(aligned_payload_score) >= float(threshold_value) else 0.0


def _update_selection_group_state(
    group_state: dict[str, Any],
    event_record: dict[str, Any],
    threshold_index: dict[str, Any],
) -> None:
    group_state["decision_sum"] += _resolved_decision_value(
        event_record,
        threshold_index,
    )
    group_state["decision_count"] += 1
    if _resolve_threshold_value(event_record, threshold_index) is not None:
        group_state["aligned_payload_decision_sum"] += _aligned_payload_decision_value(
            event_record,
            threshold_index,
        )
        group_state["aligned_payload_decision_count"] += 1
    group_state["sync_rescue_applied_sum"] += 1.0 if _record_sync_rescue_applied(
        event_record
    ) else 0.0
    group_state["sync_rescue_applied_count"] += 1

    quality_metrics = event_record.get("quality_metrics", {})
    if not isinstance(quality_metrics, dict):
        quality_metrics = {}
    _update_selection_mean_state(
        group_state["quality_psnr_state"],
        quality_metrics.get("watermarked_video_psnr"),
    )
    _update_selection_mean_state(
        group_state["quality_ssim_state"],
        quality_metrics.get("watermarked_video_ssim"),
    )


def _build_selection_mean_state(*, allow_positive_infinity: bool = False) -> dict[str, Any]:
    return {
        "sum": 0.0,
        "count": 0,
        "positive_infinity_present": False,
        "allow_positive_infinity": allow_positive_infinity,
    }


def _update_selection_mean_state(mean_state: dict[str, Any], field_value: Any) -> None:
    numeric_value = _safe_float(field_value)
    if numeric_value is None:
        return
    if math.isfinite(numeric_value):
        mean_state["sum"] += numeric_value
        mean_state["count"] += 1
        return
    if (
        bool(mean_state.get("allow_positive_infinity"))
        and math.isinf(numeric_value)
        and numeric_value > 0
    ):
        mean_state["positive_infinity_present"] = True


def _finalize_selection_mean_state(mean_state: dict[str, Any]) -> float | None:
    if int(mean_state.get("count", 0)) < 1:
        if bool(mean_state.get("positive_infinity_present")):
            return math.inf
        return None
    if bool(mean_state.get("positive_infinity_present")):
        return math.inf
    return round(float(mean_state["sum"]) / int(mean_state["count"]), 6)


def _selection_group_decision_rate(group_state: dict[str, Any] | None) -> float | None:
    if not isinstance(group_state, dict):
        return None
    decision_count = int(group_state.get("decision_count", 0))
    if decision_count < 1:
        return None
    return round(float(group_state["decision_sum"]) / decision_count, 6)


def _selection_group_rate(
    group_state: dict[str, Any] | None,
    *,
    sum_field_name: str,
    count_field_name: str,
) -> float | None:
    if not isinstance(group_state, dict):
        return None
    decision_count = int(group_state.get(count_field_name, 0))
    if decision_count < 1:
        return None
    return round(float(group_state.get(sum_field_name, 0.0)) / decision_count, 6)


def _build_selection_audit_lookup(
    grouped_metrics: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    audit_lookup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for group_key, group_state in grouped_metrics.items():
        method_variant, attack_name, sample_role = group_key
        audit_lookup[group_key] = {
            "run_id": group_state.get("run_id"),
            "construction_phase": group_state.get("construction_phase"),
            "method_variant": method_variant,
            "attack_name": attack_name,
            "sample_role": sample_role,
            "clean_negative_FPR": _selection_group_decision_rate(
                grouped_metrics.get((method_variant, attack_name, "clean_negative"))
            ),
            "attacked_negative_FPR": _selection_group_decision_rate(
                grouped_metrics.get((method_variant, attack_name, "attacked_negative"))
            ),
            "clean_positive_TPR": _selection_group_decision_rate(
                grouped_metrics.get(
                    (method_variant, attack_name, "watermarked_positive")
                )
            ),
            "attacked_positive_TPR": _selection_group_decision_rate(
                grouped_metrics.get((method_variant, attack_name, "attacked_positive"))
            ),
            "aligned_payload_clean_negative_FPR": _selection_group_rate(
                grouped_metrics.get((method_variant, attack_name, "clean_negative")),
                sum_field_name="aligned_payload_decision_sum",
                count_field_name="aligned_payload_decision_count",
            ),
            "aligned_payload_attacked_negative_FPR": _selection_group_rate(
                grouped_metrics.get((method_variant, attack_name, "attacked_negative")),
                sum_field_name="aligned_payload_decision_sum",
                count_field_name="aligned_payload_decision_count",
            ),
            "aligned_payload_clean_positive_TPR": _selection_group_rate(
                grouped_metrics.get(
                    (method_variant, attack_name, "watermarked_positive")
                ),
                sum_field_name="aligned_payload_decision_sum",
                count_field_name="aligned_payload_decision_count",
            ),
            "aligned_payload_attacked_positive_TPR": _selection_group_rate(
                grouped_metrics.get((method_variant, attack_name, "attacked_positive")),
                sum_field_name="aligned_payload_decision_sum",
                count_field_name="aligned_payload_decision_count",
            ),
            "sync_rescue_applied_clean_negative_rate": _selection_group_rate(
                grouped_metrics.get((method_variant, attack_name, "clean_negative")),
                sum_field_name="sync_rescue_applied_sum",
                count_field_name="sync_rescue_applied_count",
            ),
            "sync_rescue_applied_attacked_negative_rate": _selection_group_rate(
                grouped_metrics.get((method_variant, attack_name, "attacked_negative")),
                sum_field_name="sync_rescue_applied_sum",
                count_field_name="sync_rescue_applied_count",
            ),
            "sync_rescue_applied_clean_positive_rate": _selection_group_rate(
                grouped_metrics.get(
                    (method_variant, attack_name, "watermarked_positive")
                ),
                sum_field_name="sync_rescue_applied_sum",
                count_field_name="sync_rescue_applied_count",
            ),
            "sync_rescue_applied_attacked_positive_rate": _selection_group_rate(
                grouped_metrics.get((method_variant, attack_name, "attacked_positive")),
                sum_field_name="sync_rescue_applied_sum",
                count_field_name="sync_rescue_applied_count",
            ),
            "quality_psnr_mean": _finalize_selection_mean_state(
                group_state["quality_psnr_state"]
            ),
            "quality_ssim_mean": _finalize_selection_mean_state(
                group_state["quality_ssim_state"]
            ),
        }
    return audit_lookup


def _build_sync_stage_signature(event_record: dict[str, Any]) -> tuple[int, str, float, float]:
    return (
        int(event_record.get("tubelet_length", 1)),
        json.dumps(
            _resolve_spatial_patch_size(event_record),
            ensure_ascii=False,
        ),
        round(float(_resolve_projection_support_weight(event_record) or 0.0), 6),
        round(float(_resolve_embedding_margin(event_record) or DEFAULT_EMBEDDING_MARGIN), 6),
    )


def _build_tubelet_only_calibration_grid_rows(
    audit_lookup: dict[tuple[str, str, str], dict[str, Any]],
    candidate_variants: set[str],
    representative_records: dict[str, dict[str, Any]],
    mechanism_config: dict[str, Any],
) -> list[dict[str, Any]]:
    required_attacks = _read_string_list(mechanism_config, "required_mechanism_attacks")
    rows: list[dict[str, Any]] = []
    for method_variant in sorted(candidate_variants):
        representative_record = representative_records.get(method_variant)
        if representative_record is None:
            continue
        no_attack_negative_row = audit_lookup.get((method_variant, "no_attack", "clean_negative"), {})
        no_attack_positive_row = audit_lookup.get((method_variant, "no_attack", "watermarked_positive"), {})
        temporal_crop_row = audit_lookup.get((method_variant, "temporal_crop", "attacked_positive"), {})
        frame_dropping_row = audit_lookup.get((method_variant, "frame_dropping", "attacked_positive"), {})
        local_clip_row = audit_lookup.get((method_variant, "local_clip", "attacked_positive"), {})
        attacked_negative_rates = [
            _safe_float(
                audit_lookup.get((method_variant, attack_name, "attacked_negative"), {}).get(
                    "attacked_negative_FPR"
                )
            )
            for attack_name in required_attacks
            if attack_name != "no_attack"
        ]
        max_attacked_negative_fpr = _max_numeric_value(attacked_negative_rates)
        temporal_positive_rates = [
            _safe_float(temporal_crop_row.get("attacked_positive_TPR")),
            _safe_float(frame_dropping_row.get("attacked_positive_TPR")),
            _safe_float(local_clip_row.get("attacked_positive_TPR")),
        ]
        clean_negative_fpr = _safe_float(no_attack_negative_row.get("clean_negative_FPR"))
        no_attack_clean_positive_tpr = _safe_float(
            no_attack_positive_row.get("clean_positive_TPR")
        )
        quality_psnr_mean = _safe_float(no_attack_positive_row.get("quality_psnr_mean"))
        quality_ssim_mean = _safe_float(no_attack_positive_row.get("quality_ssim_mean"))
        candidate_eligible = _is_tubelet_only_candidate_eligible(
            clean_negative_fpr,
            no_attack_clean_positive_tpr,
            max_attacked_negative_fpr,
            quality_psnr_mean,
            quality_ssim_mean,
            mechanism_config,
        )
        anchor_semantics = build_anchor_selection_assessment(
            absolute_tprs={
                "temporal_crop": _safe_float(temporal_crop_row.get("attacked_positive_TPR")),
                "local_clip": _safe_float(local_clip_row.get("attacked_positive_TPR")),
            },
            candidate_eligible=candidate_eligible,
            max_attacked_negative_fpr=max_attacked_negative_fpr,
            mechanism_config=mechanism_config,
            anchor_compatible=True,
        )
        rows.append(
            {
                "selection_scope": "tubelet_only",
                "method_variant": method_variant,
                "base_method_variant": str(
                    representative_record.get(
                        "base_method_variant",
                        representative_record.get("method_variant"),
                    )
                ),
                "tubelet_length": int(representative_record.get("tubelet_length", 1)),
                "spatial_patch_size": json.dumps(
                    _resolve_spatial_patch_size(representative_record),
                    ensure_ascii=False,
                ),
                "embedding_projection_support_weight": _resolve_projection_support_weight(
                    representative_record,
                ),
                "embedding_margin": _resolve_embedding_margin(representative_record),
                "fusion_rule": None,
                "lambda_sync": None,
                "sync_search_radius": None,
                "min_sync_positive_margin": None,
                "min_sync_alignment_coverage_ratio": None,
                "min_sync_alignment_matched_count": None,
                "no_attack_clean_negative_fpr": clean_negative_fpr,
                "no_attack_clean_positive_tpr": no_attack_clean_positive_tpr,
                "max_attacked_negative_fpr": max_attacked_negative_fpr,
                "temporal_crop_attacked_positive_tpr": _safe_float(
                    temporal_crop_row.get("attacked_positive_TPR")
                ),
                "frame_dropping_attacked_positive_tpr": _safe_float(
                    frame_dropping_row.get("attacked_positive_TPR")
                ),
                "local_clip_attacked_positive_tpr": _safe_float(
                    local_clip_row.get("attacked_positive_TPR")
                ),
                "mean_temporal_attacked_positive_tpr": _mean_numeric_values(
                    temporal_positive_rates
                ),
                "quality_psnr_mean": quality_psnr_mean,
                "quality_ssim_mean": quality_ssim_mean,
                "temporal_crop_sync_gain": None,
                "frame_dropping_sync_gain": None,
                "local_clip_sync_gain": None,
                "mean_temporal_sync_gain": None,
                "temporal_crop_absolute_tpr": anchor_semantics["temporal_crop_absolute_tpr"],
                "local_clip_absolute_tpr": anchor_semantics["local_clip_absolute_tpr"],
                "temporal_crop_anchor_headroom": anchor_semantics[
                    "temporal_crop_anchor_headroom"
                ],
                "local_clip_anchor_headroom": anchor_semantics[
                    "local_clip_anchor_headroom"
                ],
                "temporal_crop_saturated_anchor": anchor_semantics[
                    "temporal_crop_saturated_anchor"
                ],
                "local_clip_saturated_anchor": anchor_semantics[
                    "local_clip_saturated_anchor"
                ],
                "absolute_rescue_status": anchor_semantics["absolute_rescue_status"],
                "incremental_gain_status": None,
                "negative_leakage_status": anchor_semantics["negative_leakage_status"],
                "sync_rescue_decision": None,
                "sync_leakage_decision": None,
                "candidate_selection_status": anchor_semantics[
                    "candidate_selection_status"
                ],
                "fpr_controlled": _is_fpr_controlled(
                    clean_negative_fpr,
                    max_attacked_negative_fpr,
                    mechanism_config,
                ),
                "quality_not_collapsed": _is_quality_not_collapsed(
                    quality_psnr_mean,
                    quality_ssim_mean,
                    mechanism_config,
                ),
                "candidate_eligible": candidate_eligible,
                "selection_score": _selection_score(
                    no_attack_clean_positive_tpr,
                    _mean_numeric_values(temporal_positive_rates),
                    max_attacked_negative_fpr,
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            _anchor_candidate_status_rank(str(row.get("candidate_selection_status") or "")),
            0 if bool(row.get("fpr_controlled")) else 1,
            -float(row.get("selection_score") or 0.0),
            -float(_anchor_headroom_score(row) or 0.0),
            int(row.get("tubelet_length") or 1),
        )
    )
    return rows


def _build_tubelet_sync_calibration_grid_rows(
    audit_lookup: dict[tuple[str, str, str], dict[str, Any]],
    candidate_variants: set[str],
    representative_records: dict[str, dict[str, Any]],
    sync_confident_attacked_negative_counts: dict[str, int],
    method_safety_metrics: dict[str, dict[str, Any]],
    mechanism_config: dict[str, Any],
    *,
    selected_candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    required_attacks = _read_string_list(mechanism_config, "required_mechanism_attacks")
    selected_spatial_patch_size = list(
        selected_candidate["tubelet_partition"]["spatial_patch_size"]
    )
    selected_support_weight = round(
        float(
            selected_candidate["score_calibration"][
                "embedding_projection_support_weight"
            ]
        ),
        6,
    )
    selected_embedding_margin = round(
        float(selected_candidate.get("embedding_margin", DEFAULT_EMBEDDING_MARGIN)),
        6,
    )
    selected_tubelet_length = int(selected_candidate["tubelet_length"])
    tubelet_only_metrics = selected_candidate["metrics"]
    rows: list[dict[str, Any]] = []
    for method_variant in sorted(candidate_variants):
        representative_record = representative_records.get(method_variant)
        if representative_record is None:
            continue
        spatial_patch_size = _resolve_spatial_patch_size(representative_record)
        support_weight = _resolve_projection_support_weight(representative_record)
        embedding_margin = _resolve_embedding_margin(representative_record)
        if int(representative_record.get("tubelet_length", 1)) != selected_tubelet_length:
            continue
        if list(spatial_patch_size) != selected_spatial_patch_size:
            continue
        if support_weight != selected_support_weight:
            continue
        if round(float(embedding_margin), 6) != selected_embedding_margin:
            continue

        no_attack_negative_row = audit_lookup.get((method_variant, "no_attack", "clean_negative"), {})
        no_attack_positive_row = audit_lookup.get((method_variant, "no_attack", "watermarked_positive"), {})
        temporal_crop_row = audit_lookup.get((method_variant, "temporal_crop", "attacked_positive"), {})
        frame_dropping_row = audit_lookup.get((method_variant, "frame_dropping", "attacked_positive"), {})
        local_clip_row = audit_lookup.get((method_variant, "local_clip", "attacked_positive"), {})
        attacked_negative_rates = [
            _safe_float(
                audit_lookup.get((method_variant, attack_name, "attacked_negative"), {}).get(
                    "attacked_negative_FPR"
                )
            )
            for attack_name in required_attacks
            if attack_name != "no_attack"
        ]
        max_attacked_negative_fpr = _max_numeric_value(attacked_negative_rates)
        aligned_payload_attacked_negative_rates = [
            _safe_float(
                audit_lookup.get((method_variant, attack_name, "attacked_negative"), {}).get(
                    "aligned_payload_attacked_negative_FPR"
                )
            )
            for attack_name in required_attacks
            if attack_name != "no_attack"
        ]
        sync_rescue_attacked_negative_rates = [
            _safe_float(
                audit_lookup.get((method_variant, attack_name, "attacked_negative"), {}).get(
                    "sync_rescue_applied_attacked_negative_rate"
                )
            )
            for attack_name in required_attacks
            if attack_name != "no_attack"
        ]
        temporal_crop_positive_tpr = _safe_float(
            temporal_crop_row.get("attacked_positive_TPR")
        )
        frame_dropping_positive_tpr = _safe_float(
            frame_dropping_row.get("attacked_positive_TPR")
        )
        local_clip_positive_tpr = _safe_float(local_clip_row.get("attacked_positive_TPR"))
        temporal_positive_rates = [
            temporal_crop_positive_tpr,
            frame_dropping_positive_tpr,
            local_clip_positive_tpr,
        ]
        fusion_rule = _resolve_fusion_rule(representative_record)
        lambda_sync = _resolve_lambda_sync(representative_record)
        sync_search_radius = _resolve_sync_search_radius(representative_record)
        sync_confidence_config = _resolve_sync_confidence_config(representative_record)
        temporal_crop_sync_gain = _difference(
            temporal_crop_positive_tpr,
            _safe_float(tubelet_only_metrics.get("temporal_crop_attacked_positive_tpr")),
        )
        frame_dropping_sync_gain = _difference(
            frame_dropping_positive_tpr,
            _safe_float(tubelet_only_metrics.get("frame_dropping_attacked_positive_tpr")),
        )
        local_clip_sync_gain = _difference(
            local_clip_positive_tpr,
            _safe_float(tubelet_only_metrics.get("local_clip_attacked_positive_tpr")),
        )
        mean_temporal_sync_gain = _mean_numeric_values(
            [
                temporal_crop_sync_gain,
                frame_dropping_sync_gain,
                local_clip_sync_gain,
            ]
        )
        quality_psnr_mean = _safe_float(no_attack_positive_row.get("quality_psnr_mean"))
        quality_ssim_mean = _safe_float(no_attack_positive_row.get("quality_ssim_mean"))
        clean_negative_fpr = _safe_float(no_attack_negative_row.get("clean_negative_FPR"))
        no_attack_clean_positive_tpr = _safe_float(
            no_attack_positive_row.get("clean_positive_TPR")
        )
        sync_confident_attacked_negative_count = int(
            sync_confident_attacked_negative_counts.get(method_variant, 0)
        )
        method_safety = method_safety_metrics.get(method_variant, {})
        aligned_payload_clean_negative_fpr = _safe_float(
            no_attack_negative_row.get("aligned_payload_clean_negative_FPR")
        )
        aligned_payload_attacked_negative_fpr = _max_numeric_value(
            aligned_payload_attacked_negative_rates
        )
        aligned_payload_positive_tpr = _safe_float(
            no_attack_positive_row.get("aligned_payload_clean_positive_TPR")
        )
        aligned_payload_temporal_crop_tpr = _safe_float(
            temporal_crop_row.get("aligned_payload_attacked_positive_TPR")
        )
        aligned_payload_local_clip_tpr = _safe_float(
            local_clip_row.get("aligned_payload_attacked_positive_TPR")
        )
        sync_rescue_applied_positive_rate = _mean_numeric_values(
            [
                _safe_float(
                    no_attack_positive_row.get(
                        "sync_rescue_applied_clean_positive_rate"
                    )
                ),
                _safe_float(
                    temporal_crop_row.get(
                        "sync_rescue_applied_attacked_positive_rate"
                    )
                ),
                _safe_float(
                    local_clip_row.get("sync_rescue_applied_attacked_positive_rate")
                ),
            ]
        )
        sync_rescue_applied_attacked_negative_rate = _max_numeric_value(
            sync_rescue_attacked_negative_rates
        )
        negative_rescue_over_threshold_count = int(
            method_safety.get("negative_rescue_over_threshold_count", 0)
        )
        aligned_payload_negative_safety_status = str(
            method_safety.get("aligned_payload_negative_safety_status", "PASS")
        )
        aligned_payload_clean_negative_over_threshold_count = int(
            method_safety.get("aligned_payload_clean_negative_over_threshold_count", 0)
        )
        aligned_payload_attacked_negative_over_threshold_count = int(
            method_safety.get("aligned_payload_attacked_negative_over_threshold_count", 0)
        )
        sync_semantics = build_sync_gain_assessment(
            absolute_tprs={
                "temporal_crop": temporal_crop_positive_tpr,
                "local_clip": local_clip_positive_tpr,
            },
            sync_gains={
                "temporal_crop": temporal_crop_sync_gain,
                "local_clip": local_clip_sync_gain,
            },
            mean_temporal_sync_gain=mean_temporal_sync_gain,
            clean_negative_fpr=clean_negative_fpr,
            max_attacked_negative_fpr=max_attacked_negative_fpr,
            mechanism_config=mechanism_config,
        )
        rows.append(
            {
                "selection_scope": "tubelet_sync",
                "method_variant": method_variant,
                "base_method_variant": str(
                    representative_record.get(
                        "base_method_variant",
                        representative_record.get("method_variant"),
                    )
                ),
                "tubelet_length": int(representative_record.get("tubelet_length", 1)),
                "spatial_patch_size": json.dumps(spatial_patch_size, ensure_ascii=False),
                "embedding_projection_support_weight": support_weight,
                "embedding_margin": embedding_margin,
                "fusion_rule": fusion_rule,
                "lambda_sync": lambda_sync,
                "sync_search_radius": sync_search_radius,
                "min_sync_positive_margin": sync_confidence_config[
                    "min_sync_positive_margin"
                ],
                "min_sync_alignment_coverage_ratio": sync_confidence_config[
                    "min_sync_alignment_coverage_ratio"
                ],
                "min_sync_alignment_matched_count": sync_confidence_config[
                    "min_sync_alignment_matched_count"
                ],
                "min_sync_candidate_score": sync_confidence_config[
                    "min_sync_candidate_score"
                ],
                "sync_confidence_gate_rule": sync_confidence_config[
                    "sync_confidence_gate_rule"
                ],
                "min_payload_rescue_gain": sync_confidence_config[
                    "min_payload_rescue_gain"
                ],
                "min_aligned_payload_score": sync_confidence_config[
                    "min_aligned_payload_score"
                ],
                "no_attack_clean_negative_fpr": clean_negative_fpr,
                "no_attack_clean_positive_tpr": no_attack_clean_positive_tpr,
                "max_attacked_negative_fpr": max_attacked_negative_fpr,
                "aligned_payload_clean_negative_fpr": aligned_payload_clean_negative_fpr,
                "aligned_payload_attacked_negative_fpr": (
                    aligned_payload_attacked_negative_fpr
                ),
                "aligned_payload_positive_tpr": aligned_payload_positive_tpr,
                "aligned_payload_temporal_crop_tpr": aligned_payload_temporal_crop_tpr,
                "aligned_payload_local_clip_tpr": aligned_payload_local_clip_tpr,
                "sync_rescue_applied_positive_rate": sync_rescue_applied_positive_rate,
                "sync_rescue_applied_attacked_negative_rate": (
                    sync_rescue_applied_attacked_negative_rate
                ),
                "negative_rescue_over_threshold_count": (
                    negative_rescue_over_threshold_count
                ),
                "aligned_payload_negative_safety_status": (
                    aligned_payload_negative_safety_status
                ),
                "aligned_payload_clean_negative_over_threshold_count": (
                    aligned_payload_clean_negative_over_threshold_count
                ),
                "aligned_payload_attacked_negative_over_threshold_count": (
                    aligned_payload_attacked_negative_over_threshold_count
                ),
                "temporal_crop_attacked_positive_tpr": temporal_crop_positive_tpr,
                "frame_dropping_attacked_positive_tpr": frame_dropping_positive_tpr,
                "local_clip_attacked_positive_tpr": local_clip_positive_tpr,
                "mean_temporal_attacked_positive_tpr": _mean_numeric_values(
                    temporal_positive_rates
                ),
                "quality_psnr_mean": quality_psnr_mean,
                "quality_ssim_mean": quality_ssim_mean,
                "temporal_crop_sync_gain": temporal_crop_sync_gain,
                "frame_dropping_sync_gain": frame_dropping_sync_gain,
                "local_clip_sync_gain": local_clip_sync_gain,
                "mean_temporal_sync_gain": mean_temporal_sync_gain,
                "sync_confident_attacked_negative_count": (
                    sync_confident_attacked_negative_count
                ),
                "temporal_crop_absolute_tpr": temporal_crop_positive_tpr,
                "local_clip_absolute_tpr": local_clip_positive_tpr,
                "temporal_crop_anchor_headroom": _attack_headroom(
                    _safe_float(tubelet_only_metrics.get("temporal_crop_attacked_positive_tpr")),
                ),
                "local_clip_anchor_headroom": _attack_headroom(
                    _safe_float(tubelet_only_metrics.get("local_clip_attacked_positive_tpr")),
                ),
                "temporal_crop_saturated_anchor": _is_saturated_attack(
                    _safe_float(tubelet_only_metrics.get("temporal_crop_attacked_positive_tpr")),
                ),
                "local_clip_saturated_anchor": _is_saturated_attack(
                    _safe_float(tubelet_only_metrics.get("local_clip_attacked_positive_tpr")),
                ),
                "absolute_rescue_status": sync_semantics["absolute_rescue_status"],
                "incremental_gain_status": sync_semantics["incremental_gain_status"],
                "negative_leakage_status": sync_semantics["negative_leakage_status"],
                "sync_rescue_decision": sync_semantics["sync_rescue_decision"],
                "sync_leakage_decision": sync_semantics["sync_leakage_decision"],
                "candidate_selection_status": sync_semantics["candidate_selection_status"],
                "fpr_controlled": _is_fpr_controlled(
                    clean_negative_fpr,
                    max_attacked_negative_fpr,
                    mechanism_config,
                ),
                "quality_not_collapsed": _is_quality_not_collapsed(
                    quality_psnr_mean,
                    quality_ssim_mean,
                    mechanism_config,
                ),
                "candidate_eligible": _is_tubelet_sync_candidate_eligible(
                    clean_negative_fpr,
                    no_attack_clean_positive_tpr,
                    max_attacked_negative_fpr,
                    quality_psnr_mean,
                    quality_ssim_mean,
                    temporal_crop_sync_gain,
                    local_clip_sync_gain,
                    mean_temporal_sync_gain,
                    aligned_payload_negative_safety_status,
                    mechanism_config,
                ),
                "selection_score": _selection_score(
                    no_attack_clean_positive_tpr,
                    mean_temporal_sync_gain,
                    max_attacked_negative_fpr,
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            0 if bool(row.get("candidate_eligible")) else 1,
            0 if bool(row.get("fpr_controlled")) else 1,
            _sync_candidate_status_rank(str(row.get("candidate_selection_status") or "")),
            -float(row.get("selection_score") or 0.0),
            float(row.get("lambda_sync") or 0.0),
            int(row.get("sync_search_radius") or 0),
            str(row.get("fusion_rule") or ""),
        )
    )
    return rows


def _select_tubelet_only_candidate(
    calibration_rows: list[dict[str, Any]],
    mechanism_config: dict[str, Any],
    grid_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not calibration_rows:
        raise ValueError("calibration_rows must not be empty")
    fixed_anchor_config = _resolve_fixed_tubelet_only_anchor_config(grid_config)
    if fixed_anchor_config is not None:
        selected_row = _select_fixed_tubelet_only_anchor_row(
            calibration_rows,
            fixed_anchor_config,
        )
    elif _resolve_anchor_selection_policy(grid_config) == "sync_rescuable_anchor":
        selected_row = _select_sync_rescuable_tubelet_only_anchor_row(
            calibration_rows,
            grid_config,
        )
    else:
        selected_row = calibration_rows[0]
    candidate_eligible = bool(selected_row.get("candidate_eligible"))
    return {
        "candidate_status": _resolve_tubelet_only_candidate_status(selected_row),
        "candidate_eligible": candidate_eligible,
        "fpr_controlled": bool(selected_row.get("fpr_controlled")),
        "quality_not_collapsed": bool(selected_row.get("quality_not_collapsed")),
        "candidate_selection_status": selected_row["candidate_selection_status"],
        "absolute_rescue_status": selected_row["absolute_rescue_status"],
        "negative_leakage_status": selected_row["negative_leakage_status"],
        "method_variant": selected_row["method_variant"],
        "base_method_variant": selected_row["base_method_variant"],
        "tubelet_length": int(selected_row["tubelet_length"]),
        "tubelet_partition": {
            "spatial_patch_size": json.loads(str(selected_row["spatial_patch_size"])),
        },
        "embedding_margin": float(selected_row["embedding_margin"]),
        "score_calibration": {
            "embedding_projection_support_weight": float(
                selected_row["embedding_projection_support_weight"]
            )
        },
        "metrics": {
            "no_attack_clean_negative_fpr": selected_row[
                "no_attack_clean_negative_fpr"
            ],
            "no_attack_clean_positive_tpr": selected_row[
                "no_attack_clean_positive_tpr"
            ],
            "max_attacked_negative_fpr": selected_row[
                "max_attacked_negative_fpr"
            ],
            "temporal_crop_absolute_tpr": selected_row[
                "temporal_crop_absolute_tpr"
            ],
            "local_clip_absolute_tpr": selected_row[
                "local_clip_absolute_tpr"
            ],
            "temporal_crop_anchor_headroom": selected_row[
                "temporal_crop_anchor_headroom"
            ],
            "local_clip_anchor_headroom": selected_row[
                "local_clip_anchor_headroom"
            ],
            "temporal_crop_attacked_positive_tpr": selected_row[
                "temporal_crop_attacked_positive_tpr"
            ],
            "frame_dropping_attacked_positive_tpr": selected_row[
                "frame_dropping_attacked_positive_tpr"
            ],
            "local_clip_attacked_positive_tpr": selected_row[
                "local_clip_attacked_positive_tpr"
            ],
        },
        "selection_gate": {
            "max_clean_negative_fpr": mechanism_config.get("max_clean_negative_fpr"),
            "max_attacked_negative_fpr": mechanism_config.get(
                "max_attacked_negative_fpr"
            ),
            "min_no_attack_clean_positive_tpr": mechanism_config.get(
                "min_no_attack_clean_positive_tpr"
            ),
        },
    }


def _resolve_tubelet_only_candidate_status(selected_row: dict[str, Any]) -> str:
    if bool(selected_row.get("candidate_eligible")):
        return "eligible_candidate_selected"
    if bool(selected_row.get("fpr_controlled")):
        return "fpr_controlled_best_effort_candidate_selected"
    return "best_effort_candidate_selected"


def _resolve_anchor_selection_policy(grid_config: dict[str, Any] | None) -> str:
    """解析受治理的 anchor 选择策略。

    Args:
        grid_config: calibration grid 配置。

    Returns:
        anchor_selection_policy 字符串；未配置时返回空字符串。
    """
    if not isinstance(grid_config, dict):
        return ""
    return str(grid_config.get("anchor_selection_policy", "")).strip()


def _select_sync_rescuable_tubelet_only_anchor_row(
    calibration_rows: list[dict[str, Any]],
    grid_config: dict[str, Any] | None,
) -> dict[str, Any]:
    """选择适合后续 sync rescue 的 tubelet-only anchor。

    该函数属于项目特定写法。它不改变 threshold 校准规则, 也不读取 test split,
    只是在 dev / calibration 诊断结果中避免选择已经过强、sync headroom 过小的 anchor。

    Args:
        calibration_rows: tubelet-only 候选表。
        grid_config: calibration grid 配置。

    Returns:
        最适合进入 sync 搜索的 anchor 行。
    """
    policy_config = _resolve_sync_rescuable_anchor_policy_config(grid_config)
    filtered_rows = [
        row
        for row in calibration_rows
        if _tubelet_only_row_matches_sync_rescuable_policy(row, policy_config)
    ]
    candidate_rows = filtered_rows if filtered_rows else list(calibration_rows)
    candidate_rows.sort(
        key=lambda row: (
            0 if bool(row.get("candidate_eligible")) else 1,
            0 if bool(row.get("fpr_controlled")) else 1,
            _anchor_candidate_status_rank(str(row.get("candidate_selection_status") or "")),
            _distance_from_target(
                _safe_float(row.get("no_attack_clean_positive_tpr")),
                policy_config["target_no_attack_clean_positive_tpr"],
            ),
            -float(_anchor_headroom_score(row) or 0.0),
            float(row.get("embedding_projection_support_weight") or 0.0),
            float(row.get("embedding_margin") or DEFAULT_EMBEDDING_MARGIN),
            str(row.get("spatial_patch_size") or ""),
        )
    )
    return candidate_rows[0]


def _resolve_sync_rescuable_anchor_policy_config(
    grid_config: dict[str, Any] | None,
) -> dict[str, float]:
    """读取 sync-rescuable anchor 选择参数。

    Args:
        grid_config: calibration grid 配置。

    Returns:
        已补齐默认值的策略配置。
    """
    raw_config: dict[str, Any] = {}
    if isinstance(grid_config, dict) and isinstance(
        grid_config.get("sync_rescuable_anchor_selection"),
        dict,
    ):
        raw_config = grid_config["sync_rescuable_anchor_selection"]
    return {
        "min_no_attack_clean_positive_tpr": _safe_float(
            raw_config.get("min_no_attack_clean_positive_tpr")
        )
        or 0.5,
        "max_no_attack_clean_positive_tpr": _safe_float(
            raw_config.get("max_no_attack_clean_positive_tpr")
        )
        or 0.85,
        "target_no_attack_clean_positive_tpr": _safe_float(
            raw_config.get("target_no_attack_clean_positive_tpr")
        )
        or 0.6,
        "min_temporal_crop_anchor_headroom": _safe_float(
            raw_config.get("min_temporal_crop_anchor_headroom")
        )
        or 0.35,
        "min_local_clip_anchor_headroom": _safe_float(
            raw_config.get("min_local_clip_anchor_headroom")
        )
        or 0.35,
    }


def _tubelet_only_row_matches_sync_rescuable_policy(
    row: dict[str, Any],
    policy_config: dict[str, float],
) -> bool:
    """判断 anchor 行是否保留足够 sync rescue 空间。"""
    if not bool(row.get("candidate_eligible")):
        return False
    if not bool(row.get("fpr_controlled")):
        return False
    no_attack_tpr = _safe_float(row.get("no_attack_clean_positive_tpr"))
    temporal_headroom = _safe_float(row.get("temporal_crop_anchor_headroom"))
    local_clip_headroom = _safe_float(row.get("local_clip_anchor_headroom"))
    if no_attack_tpr is None or temporal_headroom is None or local_clip_headroom is None:
        return False
    return (
        policy_config["min_no_attack_clean_positive_tpr"]
        <= no_attack_tpr
        <= policy_config["max_no_attack_clean_positive_tpr"]
        and temporal_headroom >= policy_config["min_temporal_crop_anchor_headroom"]
        and local_clip_headroom >= policy_config["min_local_clip_anchor_headroom"]
    )


def _distance_from_target(value: float | None, target_value: float) -> float:
    """计算数值到目标值的距离, None 会被视为不可取的大距离。"""
    if value is None:
        return 1_000_000.0
    return abs(float(value) - float(target_value))


def _select_tubelet_sync_candidate(
    calibration_rows: list[dict[str, Any]],
    mechanism_config: dict[str, Any],
) -> dict[str, Any] | None:
    if not calibration_rows:
        raise ValueError("tubelet_sync calibration rows must not be empty")
    eligible_rows = [row for row in calibration_rows if bool(row.get("candidate_eligible"))]
    if not eligible_rows:
        return None
    selected_row = eligible_rows[0]
    parsed_payload = _parse_tubelet_sync_variant_name(
        str(selected_row.get("method_variant", ""))
    )
    resolved_sync_search_radius = selected_row.get("sync_search_radius")
    if not isinstance(resolved_sync_search_radius, int):
        parsed_sync_search_radius = parsed_payload.get("sync_search_radius")
        resolved_sync_search_radius = (
            int(parsed_sync_search_radius)
            if isinstance(parsed_sync_search_radius, int)
            else 0
        )
    resolved_min_sync_positive_margin = selected_row.get("min_sync_positive_margin")
    if not isinstance(resolved_min_sync_positive_margin, (int, float)):
        parsed_min_sync_positive_margin = parsed_payload.get("min_sync_positive_margin")
        resolved_min_sync_positive_margin = (
            float(parsed_min_sync_positive_margin)
            if isinstance(parsed_min_sync_positive_margin, (int, float))
            else 0.0
        )
    resolved_min_sync_alignment_coverage_ratio = selected_row.get(
        "min_sync_alignment_coverage_ratio"
    )
    if not isinstance(resolved_min_sync_alignment_coverage_ratio, (int, float)):
        parsed_min_sync_alignment_coverage_ratio = parsed_payload.get(
            "min_sync_alignment_coverage_ratio"
        )
        resolved_min_sync_alignment_coverage_ratio = (
            float(parsed_min_sync_alignment_coverage_ratio)
            if isinstance(parsed_min_sync_alignment_coverage_ratio, (int, float))
            else 0.5
        )
    resolved_min_sync_alignment_matched_count = selected_row.get(
        "min_sync_alignment_matched_count"
    )
    if not isinstance(resolved_min_sync_alignment_matched_count, int):
        parsed_min_sync_alignment_matched_count = parsed_payload.get(
            "min_sync_alignment_matched_count"
        )
        resolved_min_sync_alignment_matched_count = (
            int(parsed_min_sync_alignment_matched_count)
            if isinstance(parsed_min_sync_alignment_matched_count, int)
            else 1
        )
    resolved_min_sync_candidate_score = selected_row.get("min_sync_candidate_score")
    if not isinstance(resolved_min_sync_candidate_score, (int, float)):
        parsed_min_sync_candidate_score = parsed_payload.get("min_sync_candidate_score")
        resolved_min_sync_candidate_score = (
            float(parsed_min_sync_candidate_score)
            if isinstance(parsed_min_sync_candidate_score, (int, float))
            else 0.0
        )
    resolved_sync_confidence_gate_rule = selected_row.get("sync_confidence_gate_rule")
    if not isinstance(resolved_sync_confidence_gate_rule, str):
        parsed_sync_confidence_gate_rule = parsed_payload.get(
            "sync_confidence_gate_rule"
        )
        resolved_sync_confidence_gate_rule = (
            str(parsed_sync_confidence_gate_rule)
            if isinstance(parsed_sync_confidence_gate_rule, str)
            else "candidate_score_gate"
        )
    resolved_min_payload_rescue_gain = selected_row.get("min_payload_rescue_gain")
    if not isinstance(resolved_min_payload_rescue_gain, (int, float)):
        parsed_min_payload_rescue_gain = parsed_payload.get("min_payload_rescue_gain")
        resolved_min_payload_rescue_gain = (
            float(parsed_min_payload_rescue_gain)
            if isinstance(parsed_min_payload_rescue_gain, (int, float))
            else 0.01
        )
    resolved_min_aligned_payload_score = selected_row.get("min_aligned_payload_score")
    if not isinstance(resolved_min_aligned_payload_score, (int, float)):
        parsed_min_aligned_payload_score = parsed_payload.get(
            "min_aligned_payload_score"
        )
        resolved_min_aligned_payload_score = (
            float(parsed_min_aligned_payload_score)
            if isinstance(parsed_min_aligned_payload_score, (int, float))
            else 0.1
        )
    return {
        "candidate_status": (
            "sync_gain_candidate_selected"
            if bool(selected_row.get("candidate_eligible"))
            else "sync_gain_candidate_selected_best_effort"
        ),
        "method_variant": selected_row["method_variant"],
        "base_method_variant": selected_row["base_method_variant"],
        "tubelet_length": int(selected_row["tubelet_length"]),
        "tubelet_partition": {
            "spatial_patch_size": json.loads(str(selected_row["spatial_patch_size"])),
        },
        "embedding_margin": float(selected_row["embedding_margin"]),
        "score_calibration": {
            "embedding_projection_support_weight": float(
                selected_row["embedding_projection_support_weight"]
            )
        },
        "fusion_rule": str(selected_row["fusion_rule"]),
        "lambda_sync": float(selected_row["lambda_sync"]),
        "sync_search": {
            "offset_search_min": -resolved_sync_search_radius,
            "offset_search_max": resolved_sync_search_radius,
            "min_sync_positive_margin": float(
                resolved_min_sync_positive_margin
            ),
            "min_sync_alignment_coverage_ratio": float(
                resolved_min_sync_alignment_coverage_ratio
            ),
            "min_sync_alignment_matched_count": int(
                resolved_min_sync_alignment_matched_count
            ),
            "min_sync_candidate_score": float(resolved_min_sync_candidate_score),
            "sync_confidence_gate_rule": str(resolved_sync_confidence_gate_rule),
            "min_payload_rescue_gain": float(resolved_min_payload_rescue_gain),
            "min_aligned_payload_score": float(resolved_min_aligned_payload_score),
        },
        "metrics": {
            "no_attack_clean_negative_fpr": selected_row[
                "no_attack_clean_negative_fpr"
            ],
            "no_attack_clean_positive_tpr": selected_row[
                "no_attack_clean_positive_tpr"
            ],
            "max_attacked_negative_fpr": selected_row[
                "max_attacked_negative_fpr"
            ],
            "temporal_crop_attacked_positive_tpr": selected_row[
                "temporal_crop_attacked_positive_tpr"
            ],
            "frame_dropping_attacked_positive_tpr": selected_row[
                "frame_dropping_attacked_positive_tpr"
            ],
            "local_clip_attacked_positive_tpr": selected_row[
                "local_clip_attacked_positive_tpr"
            ],
            "quality_psnr_mean": selected_row["quality_psnr_mean"],
            "quality_ssim_mean": selected_row["quality_ssim_mean"],
            "temporal_crop_sync_gain": selected_row["temporal_crop_sync_gain"],
            "frame_dropping_sync_gain": selected_row[
                "frame_dropping_sync_gain"
            ],
            "local_clip_sync_gain": selected_row["local_clip_sync_gain"],
            "mean_temporal_sync_gain": selected_row["mean_temporal_sync_gain"],
            "temporal_crop_absolute_tpr": selected_row["temporal_crop_absolute_tpr"],
            "local_clip_absolute_tpr": selected_row["local_clip_absolute_tpr"],
            "temporal_crop_anchor_headroom": selected_row[
                "temporal_crop_anchor_headroom"
            ],
            "local_clip_anchor_headroom": selected_row[
                "local_clip_anchor_headroom"
            ],
            "temporal_crop_saturated_anchor": selected_row[
                "temporal_crop_saturated_anchor"
            ],
            "local_clip_saturated_anchor": selected_row[
                "local_clip_saturated_anchor"
            ],
        },
        "absolute_rescue_status": selected_row["absolute_rescue_status"],
        "incremental_gain_status": selected_row["incremental_gain_status"],
        "negative_leakage_status": selected_row["negative_leakage_status"],
        "sync_rescue_decision": selected_row["sync_rescue_decision"],
        "sync_leakage_decision": selected_row["sync_leakage_decision"],
        "candidate_selection_status": selected_row["candidate_selection_status"],
        "selection_gate": {
            "max_clean_negative_fpr": mechanism_config.get("max_clean_negative_fpr"),
            "max_attacked_negative_fpr": mechanism_config.get(
                "max_attacked_negative_fpr"
            ),
            "min_no_attack_clean_positive_tpr": mechanism_config.get(
                "min_no_attack_clean_positive_tpr"
            ),
            "min_tubelet_sync_gain_over_tubelet_only_temporal": mechanism_config.get(
                "min_tubelet_sync_gain_over_tubelet_only_temporal"
            ),
            "require_quality_not_collapsed": mechanism_config.get(
                "require_quality_not_collapsed"
            ),
            "min_watermarked_video_psnr": mechanism_config.get(
                "min_watermarked_video_psnr"
            ),
            "min_watermarked_video_ssim": mechanism_config.get(
                "min_watermarked_video_ssim"
            ),
        },
    }


def _build_sync_stage_blocking_details(
    observed_sync_signatures: set[tuple[int, str, float, float]],
    selected_candidate: dict[str, Any],
) -> dict[str, Any]:
    selected_signature = {
        "tubelet_length": int(selected_candidate["tubelet_length"]),
        "spatial_patch_size": list(
            selected_candidate["tubelet_partition"]["spatial_patch_size"]
        ),
        "embedding_projection_support_weight": round(
            float(
                selected_candidate["score_calibration"][
                    "embedding_projection_support_weight"
                ]
            ),
            6,
        ),
        "embedding_margin": round(
            float(selected_candidate.get("embedding_margin", DEFAULT_EMBEDDING_MARGIN)),
            6,
        ),
    }
    normalized_signatures = [
        {
            "tubelet_length": signature[0],
            "spatial_patch_size": json.loads(signature[1]),
            "embedding_projection_support_weight": signature[2],
            "embedding_margin": signature[3],
        }
        for signature in sorted(observed_sync_signatures)
    ]
    matching_signature_count = sum(
        1
        for signature in normalized_signatures
        if int(signature["tubelet_length"]) == int(selected_signature["tubelet_length"])
        and list(signature["spatial_patch_size"]) == list(selected_signature["spatial_patch_size"])
        and round(float(signature["embedding_projection_support_weight"]), 6)
        == round(float(selected_signature["embedding_projection_support_weight"]), 6)
        and round(float(signature["embedding_margin"]), 6)
        == round(float(selected_signature["embedding_margin"]), 6)
    )
    return {
        "selected_anchor_signature": selected_signature,
        "observed_sync_stage_signature_count": len(normalized_signatures),
        "observed_sync_stage_signatures": normalized_signatures,
        "matching_sync_stage_signature_count": matching_signature_count,
    }


def _resolve_fixed_tubelet_only_anchor_config(
    grid_config: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """读取受治理的固定 anchor 配置, 用于避免 selector 误选已饱和 anchor.

    该函数属于项目特定写法. 它只影响 dev / calibration 阶段的候选选择,
    不改变阈值校准规则, 也不读取 test split.
    """
    if not isinstance(grid_config, dict):
        return None
    selection_policy = str(grid_config.get("anchor_selection_policy", "")).strip()
    fixed_anchor = grid_config.get("fixed_tubelet_only_anchor")
    if fixed_anchor is None and selection_policy != "fixed_unsaturated_anchor":
        return None
    if not isinstance(fixed_anchor, dict):
        raise ValueError("fixed_tubelet_only_anchor must be a dictionary when configured")
    return fixed_anchor


def _select_fixed_tubelet_only_anchor_row(
    calibration_rows: list[dict[str, Any]],
    fixed_anchor_config: dict[str, Any],
) -> dict[str, Any]:
    """从候选表中选择与固定 anchor 配置完全匹配的行.

    这里采用精确匹配而不是近邻匹配, 目的是让 notebook 多次运行时能够复现
    同一个未饱和 anchor, 从而把运行预算集中到 sync 参数验证上.
    """
    for candidate_row in calibration_rows:
        if _tubelet_only_row_matches_fixed_anchor(candidate_row, fixed_anchor_config):
            return candidate_row
    available_anchor_summaries = [
        {
            "method_variant": row.get("method_variant"),
            "tubelet_length": row.get("tubelet_length"),
            "spatial_patch_size": row.get("spatial_patch_size"),
            "embedding_projection_support_weight": row.get(
                "embedding_projection_support_weight"
            ),
            "embedding_margin": row.get("embedding_margin"),
        }
        for row in calibration_rows[:20]
    ]
    raise ValueError(
        "fixed_tubelet_only_anchor did not match any generated tubelet-only row; "
        f"fixed_anchor={fixed_anchor_config}; "
        f"available_anchor_preview={available_anchor_summaries}"
    )


def _tubelet_only_row_matches_fixed_anchor(
    candidate_row: dict[str, Any],
    fixed_anchor_config: dict[str, Any],
) -> bool:
    expected_method_variant = fixed_anchor_config.get("method_variant")
    if isinstance(expected_method_variant, str) and expected_method_variant:
        return str(candidate_row.get("method_variant")) == expected_method_variant

    expected_tubelet_length = fixed_anchor_config.get("tubelet_length")
    expected_spatial_patch_size = fixed_anchor_config.get("spatial_patch_size")
    expected_support_weight = fixed_anchor_config.get(
        "embedding_projection_support_weight"
    )
    expected_embedding_margin = fixed_anchor_config.get("embedding_margin")

    if expected_tubelet_length is not None and int(candidate_row["tubelet_length"]) != int(
        expected_tubelet_length
    ):
        return False
    if expected_spatial_patch_size is not None:
        try:
            row_spatial_patch_size = json.loads(str(candidate_row["spatial_patch_size"]))
        except json.JSONDecodeError:
            return False
        if list(row_spatial_patch_size) != list(expected_spatial_patch_size):
            return False
    if expected_support_weight is not None and not _numeric_values_match(
        candidate_row.get("embedding_projection_support_weight"),
        expected_support_weight,
    ):
        return False
    if expected_embedding_margin is not None and not _numeric_values_match(
        candidate_row.get("embedding_margin"),
        expected_embedding_margin,
    ):
        return False
    return True


def _numeric_values_match(left_value: Any, right_value: Any) -> bool:
    left_float = _safe_float(left_value)
    right_float = _safe_float(right_value)
    if left_float is None or right_float is None:
        return False
    return abs(float(left_float) - float(right_float)) <= 1e-6


def _build_tubelet_sync_scan_seed(
    selected_candidate: dict[str, Any],
    grid_config: dict[str, Any],
) -> dict[str, Any]:
    grid = grid_config.get("grid", {})
    if not isinstance(grid, dict):
        raise TypeError("grid must be a dictionary")
    selected_candidate_sync_defaults = _resolve_selected_candidate_sync_defaults(
        selected_candidate
    )
    return {
        "base_method_variant": "tubelet_sync",
        "recommended_method_variant": "tubelet_sync_real_video_vae_candidate",
        "seed_method_config": {
            "tubelet_length": int(selected_candidate["tubelet_length"]),
            "embedding_margin": round(
                float(selected_candidate.get("embedding_margin", DEFAULT_EMBEDDING_MARGIN)),
                6,
            ),
            "tubelet_partition": {
                "spatial_patch_size": list(
                    selected_candidate["tubelet_partition"]["spatial_patch_size"]
                ),
            },
            "score_calibration": {
                "embedding_projection_support_weight": selected_candidate[
                    "score_calibration"
                ]["embedding_projection_support_weight"]
            },
        },
        "parameter_scan": {
            "fusion_rule": _read_optional_grid_string_list(
                grid,
                "fusion_rule",
                [selected_candidate_sync_defaults["fusion_rule"]],
            ),
            "lambda_sync": _read_optional_grid_numeric_list(
                grid,
                "lambda_sync",
                [selected_candidate_sync_defaults["lambda_sync"]],
            ),
            "sync_search_radius": _read_optional_grid_integer_list(
                grid,
                "sync_search_radius",
                [selected_candidate_sync_defaults["sync_search_radius"]],
            ),
            "min_sync_positive_margin": _read_optional_grid_numeric_list(
                grid,
                "min_sync_positive_margin",
                [selected_candidate_sync_defaults["min_sync_positive_margin"]],
            ),
            "min_sync_alignment_coverage_ratio": _read_optional_grid_numeric_list(
                grid,
                "min_sync_alignment_coverage_ratio",
                [selected_candidate_sync_defaults["min_sync_alignment_coverage_ratio"]],
            ),
            "min_sync_alignment_matched_count": _read_optional_grid_integer_list(
                grid,
                "min_sync_alignment_matched_count",
                [selected_candidate_sync_defaults["min_sync_alignment_matched_count"]],
            ),
            "min_sync_candidate_score": _read_optional_grid_numeric_list(
                grid,
                "min_sync_candidate_score",
                [selected_candidate_sync_defaults["min_sync_candidate_score"]],
            ),
            "sync_confidence_gate_rule": _read_optional_grid_string_list(
                grid,
                "sync_confidence_gate_rule",
                [selected_candidate_sync_defaults["sync_confidence_gate_rule"]],
            ),
            "min_payload_rescue_gain": _read_optional_grid_numeric_alias_list(
                grid,
                ("min_aligned_rescue_gain", "min_payload_rescue_gain"),
                [selected_candidate_sync_defaults["min_payload_rescue_gain"]],
            ),
            "min_aligned_payload_score": _read_optional_grid_numeric_alias_list(
                grid,
                ("min_aligned_score_gate", "min_aligned_payload_score"),
                [selected_candidate_sync_defaults["min_aligned_payload_score"]],
            ),
        },
        "rationale": [
            "reuse_tubelet_only_candidate_for_no_attack_recovery",
            "start_with_low_lambda_sync_to_reduce_negative_sync_leakage",
            "shrink_offset_search_radius_before_increasing_sync_weight",
        ],
    }


def _is_tubelet_only_candidate_eligible(
    clean_negative_fpr: float | None,
    no_attack_clean_positive_tpr: float | None,
    max_attacked_negative_fpr: float | None,
    quality_psnr_mean: float | None,
    quality_ssim_mean: float | None,
    mechanism_config: dict[str, Any],
) -> bool:
    min_clean_positive_tpr = _safe_float(
        mechanism_config.get("min_no_attack_clean_positive_tpr")
    )
    if not _is_fpr_controlled(
        clean_negative_fpr,
        max_attacked_negative_fpr,
        mechanism_config,
    ):
        return False
    if (
        min_clean_positive_tpr is not None
        and (
            no_attack_clean_positive_tpr is None
            or no_attack_clean_positive_tpr < min_clean_positive_tpr
        )
    ):
        return False
    return _is_quality_not_collapsed(
        quality_psnr_mean,
        quality_ssim_mean,
        mechanism_config,
    )


def _is_tubelet_sync_candidate_eligible(
    clean_negative_fpr: float | None,
    no_attack_clean_positive_tpr: float | None,
    max_attacked_negative_fpr: float | None,
    quality_psnr_mean: float | None,
    quality_ssim_mean: float | None,
    temporal_crop_sync_gain: float | None,
    local_clip_sync_gain: float | None,
    mean_temporal_sync_gain: float | None,
    aligned_payload_negative_safety_status: str,
    mechanism_config: dict[str, Any],
) -> bool:
    if not _is_tubelet_only_candidate_eligible(
        clean_negative_fpr,
        no_attack_clean_positive_tpr,
        max_attacked_negative_fpr,
        quality_psnr_mean,
        quality_ssim_mean,
        mechanism_config,
    ):
        return False
    if str(aligned_payload_negative_safety_status) != "PASS":
        return False
    sync_semantics = build_sync_gain_assessment(
        absolute_tprs={
            "temporal_crop": None,
            "local_clip": None,
        },
        sync_gains={
            "temporal_crop": temporal_crop_sync_gain,
            "local_clip": local_clip_sync_gain,
        },
        mean_temporal_sync_gain=mean_temporal_sync_gain,
        clean_negative_fpr=clean_negative_fpr,
        max_attacked_negative_fpr=max_attacked_negative_fpr,
        mechanism_config=mechanism_config,
    )
    return sync_semantics["candidate_selection_status"] == "eligible"


def _attack_headroom(attack_positive_tpr: float | None) -> float | None:
    if attack_positive_tpr is None:
        return None
    return round(max(0.0, 1.0 - float(attack_positive_tpr)), 6)


def _is_saturated_attack(attack_positive_tpr: float | None) -> bool:
    if attack_positive_tpr is None:
        return False
    return float(attack_positive_tpr) >= 1.0


def _sync_candidate_status_rank(candidate_selection_status: str) -> int:
    return {
        "eligible": 0,
        "rescue_with_leakage": 1,
        "saturated_anchor_no_increment": 2,
        "insufficient_signal": 3,
        "anchor_incompatible": 4,
    }.get(candidate_selection_status, 5)


def _anchor_candidate_status_rank(candidate_selection_status: str) -> int:
    return {
        "strong_anchor_with_headroom": 0,
        "strong_anchor_saturated": 1,
        "weak_anchor_with_headroom": 2,
        "weak_anchor_incompatible": 3,
    }.get(candidate_selection_status, 4)


def _anchor_headroom_score(row: dict[str, Any]) -> float | None:
    return _mean_numeric_values(
        [
            _safe_float(row.get("temporal_crop_anchor_headroom")),
            _safe_float(row.get("local_clip_anchor_headroom")),
        ]
    )


def _is_quality_not_collapsed(
    quality_psnr_mean: float | None,
    quality_ssim_mean: float | None,
    mechanism_config: dict[str, Any],
) -> bool:
    if not bool(mechanism_config.get("require_quality_not_collapsed", False)):
        return True
    min_psnr = _safe_float(mechanism_config.get("min_watermarked_video_psnr"))
    min_ssim = _safe_float(mechanism_config.get("min_watermarked_video_ssim"))
    if min_psnr is not None and (quality_psnr_mean is None or quality_psnr_mean < min_psnr):
        return False
    if min_ssim is not None and (quality_ssim_mean is None or quality_ssim_mean < min_ssim):
        return False
    return True


def _resolve_fusion_rule(event_record: dict[str, Any]) -> str | None:
    mechanism_trace = event_record.get("mechanism_trace", {})
    field_value = mechanism_trace.get("fusion_rule")
    if isinstance(field_value, str) and field_value:
        return field_value
    return _parse_tubelet_sync_variant_name(str(event_record.get("method_variant", ""))).get(
        "fusion_rule"
    )


def _resolve_lambda_sync(event_record: dict[str, Any]) -> float | None:
    mechanism_trace = event_record.get("mechanism_trace", {})
    field_value = mechanism_trace.get("lambda_sync")
    if isinstance(field_value, (int, float)):
        return round(float(field_value), 6)
    parsed_payload = _parse_tubelet_sync_variant_name(
        str(event_record.get("method_variant", ""))
    )
    lambda_sync = parsed_payload.get("lambda_sync")
    if not isinstance(lambda_sync, (int, float)):
        return None
    return round(float(lambda_sync), 6)


def _resolve_sync_search_radius(event_record: dict[str, Any]) -> int | None:
    parsed_payload = _parse_tubelet_sync_variant_name(
        str(event_record.get("method_variant", ""))
    )
    sync_search_radius = parsed_payload.get("sync_search_radius")
    if isinstance(sync_search_radius, int):
        return sync_search_radius
    return None


def _parse_tubelet_sync_variant_name(method_variant: str) -> dict[str, Any]:
    if not method_variant.startswith("tubelet_sync_cal_"):
        return {}
    variant_tokens = method_variant.split("_")
    parsed_payload: dict[str, Any] = {}
    for token in variant_tokens:
        if token.startswith("sr") and token[2:].isdigit():
            parsed_payload["sync_search_radius"] = int(token[2:])
        elif token.startswith("ls") and token[2:].isdigit():
            parsed_payload["lambda_sync"] = round(int(token[2:]) / 1000.0, 6)
        elif token.startswith("mg") and token[2:].isdigit():
            parsed_payload["min_sync_positive_margin"] = round(
                int(token[2:]) / 1000.0,
                6,
            )
        elif token.startswith("cv") and token[2:].isdigit():
            parsed_payload["min_sync_alignment_coverage_ratio"] = round(
                int(token[2:]) / 1000.0,
                6,
            )
        elif token.startswith("mc") and token[2:].isdigit():
            parsed_payload["min_sync_alignment_matched_count"] = int(token[2:])
        elif token.startswith("cs") and token[2:].isdigit():
            parsed_payload["min_sync_candidate_score"] = round(
                int(token[2:]) / 1000.0,
                6,
            )
        elif token == "grcscore":
            parsed_payload["sync_confidence_gate_rule"] = "candidate_score_gate"
        elif token == "grapsafe":
            parsed_payload["sync_confidence_gate_rule"] = "aligned_payload_safety_gate"
        elif token.startswith("rg") and token[2:].isdigit():
            parsed_payload["min_payload_rescue_gain"] = round(
                int(token[2:]) / 1000.0,
                6,
            )
        elif token.startswith("as") and token[2:].isdigit():
            parsed_payload["min_aligned_payload_score"] = round(
                int(token[2:]) / 1000.0,
                6,
            )
        elif token.startswith("fr"):
            fusion_rule_token = token[2:]
            if fusion_rule_token == "sync":
                continue
            fusion_rule_map = {
                "sync_rescue": "sync_rescue_fusion",
                "cal_sync": "calibrated_tubelet_sync",
            }
            parsed_payload["fusion_rule"] = fusion_rule_map.get(
                fusion_rule_token,
                fusion_rule_token,
            )
    return parsed_payload

def _resolve_selected_candidate_sync_defaults(
    selected_candidate: dict[str, Any],
) -> dict[str, Any]:
    sync_search = selected_candidate.get("sync_search", {})
    if not isinstance(sync_search, dict):
        sync_search = {}

    fusion_rule = selected_candidate.get("fusion_rule")
    if isinstance(fusion_rule, str) and fusion_rule:
        default_fusion_rule = fusion_rule
    else:
        default_fusion_rule = "sync_rescue_fusion"

    lambda_sync = selected_candidate.get("lambda_sync", 0.0)
    default_lambda_sync = (
        round(float(lambda_sync), 6)
        if isinstance(lambda_sync, (int, float))
        else 0.0
    )

    offset_search_min = sync_search.get("offset_search_min")
    offset_search_max = sync_search.get("offset_search_max")
    default_sync_search_radius = 0
    if isinstance(offset_search_min, int) and isinstance(offset_search_max, int):
        default_sync_search_radius = max(
            abs(int(offset_search_min)),
            abs(int(offset_search_max)),
        )

    min_sync_positive_margin = sync_search.get("min_sync_positive_margin", 0.0)
    default_min_sync_positive_margin = (
        round(float(min_sync_positive_margin), 6)
        if isinstance(min_sync_positive_margin, (int, float))
        else 0.0
    )
    min_sync_alignment_coverage_ratio = sync_search.get(
        "min_sync_alignment_coverage_ratio",
        0.5,
    )
    default_min_sync_alignment_coverage_ratio = (
        round(float(min_sync_alignment_coverage_ratio), 6)
        if isinstance(min_sync_alignment_coverage_ratio, (int, float))
        else 0.5
    )
    min_sync_alignment_matched_count = sync_search.get(
        "min_sync_alignment_matched_count",
        1,
    )
    default_min_sync_alignment_matched_count = (
        int(min_sync_alignment_matched_count)
        if isinstance(min_sync_alignment_matched_count, int)
        else 1
    )
    min_sync_candidate_score = sync_search.get("min_sync_candidate_score", 0.0)
    default_min_sync_candidate_score = (
        round(float(min_sync_candidate_score), 6)
        if isinstance(min_sync_candidate_score, (int, float))
        else 0.0
    )
    sync_confidence_gate_rule = sync_search.get(
        "sync_confidence_gate_rule",
        "candidate_score_gate",
    )
    default_sync_confidence_gate_rule = (
        str(sync_confidence_gate_rule)
        if isinstance(sync_confidence_gate_rule, str) and sync_confidence_gate_rule
        else "candidate_score_gate"
    )
    min_payload_rescue_gain = sync_search.get("min_payload_rescue_gain", 0.01)
    default_min_payload_rescue_gain = (
        round(float(min_payload_rescue_gain), 6)
        if isinstance(min_payload_rescue_gain, (int, float))
        else 0.01
    )
    min_aligned_payload_score = sync_search.get("min_aligned_payload_score", 0.1)
    default_min_aligned_payload_score = (
        round(float(min_aligned_payload_score), 6)
        if isinstance(min_aligned_payload_score, (int, float))
        else 0.1
    )
    return {
        "fusion_rule": default_fusion_rule,
        "lambda_sync": default_lambda_sync,
        "sync_search_radius": default_sync_search_radius,
        "min_sync_positive_margin": default_min_sync_positive_margin,
        "min_sync_alignment_coverage_ratio": default_min_sync_alignment_coverage_ratio,
        "min_sync_alignment_matched_count": default_min_sync_alignment_matched_count,
        "min_sync_candidate_score": default_min_sync_candidate_score,
        "sync_confidence_gate_rule": default_sync_confidence_gate_rule,
        "min_payload_rescue_gain": default_min_payload_rescue_gain,
        "min_aligned_payload_score": default_min_aligned_payload_score,
    }


def _find_variant_record(
    event_score_records: list[dict[str, Any]],
    method_variant: str,
) -> dict[str, Any] | None:
    for record in event_score_records:
        if str(record.get("method_variant")) == method_variant:
            return record
    return None


def _resolve_projection_support_weight(event_record: dict[str, Any]) -> float:
    mechanism_trace = event_record.get("mechanism_trace", {})
    if not isinstance(mechanism_trace, dict):
        mechanism_trace = {}
    field_value = mechanism_trace.get("embedding_projection_support_weight")
    if not isinstance(field_value, (int, float)):
        parsed_value = _parse_projection_support_weight_from_variant_name(
            str(event_record.get("method_variant", ""))
        )
        if parsed_value is not None:
            return parsed_value
        return 0.45
    return round(float(field_value), 6)


def _resolve_embedding_margin(event_record: dict[str, Any]) -> float:
    mechanism_trace = event_record.get("mechanism_trace", {})
    if not isinstance(mechanism_trace, dict):
        mechanism_trace = {}
    field_value = mechanism_trace.get("embedding_margin")
    if isinstance(field_value, (int, float)) and float(field_value) > 0.0:
        return round(float(field_value), 6)
    parsed_value = _parse_embedding_margin_from_variant_name(
        str(event_record.get("method_variant", ""))
    )
    if parsed_value is not None:
        return parsed_value
    return round(float(DEFAULT_EMBEDDING_MARGIN), 6)


def _resolve_spatial_patch_size(event_record: dict[str, Any]) -> list[int]:
    """解析候选记录使用的空间 patch 尺寸.

    通用写法是直接读取结构化 trace 字段. 本项目 calibration 结果已经出现
    过 `method_variant` 的 `sp08x08` 语义 token 与
    `mechanism_trace.spatial_patch_size` 不一致的历史记录. 因此这里采用项目
    特定的保守策略: 只要 method variant 名称包含明确的 `spHxW` token, 就
    优先使用名称中的语义配置; 当名称缺少该 token 时, 才回退到 trace 字段.
    这样可以避免 selector 把未饱和 anchor 错误降级为默认 `[4, 4]`.
    """
    parsed_value = _parse_spatial_patch_size_from_variant_name(
        str(event_record.get("method_variant", ""))
    )
    if parsed_value is not None:
        return parsed_value
    mechanism_trace = event_record.get("mechanism_trace", {})
    if isinstance(mechanism_trace, dict):
        field_value = mechanism_trace.get("spatial_patch_size")
        if (
            isinstance(field_value, list)
            and len(field_value) == 2
            and all(isinstance(size, int) and size > 0 for size in field_value)
        ):
            return [int(field_value[0]), int(field_value[1])]
    return [4, 4]


def _parse_spatial_patch_size_from_variant_name(
    method_variant: str,
) -> list[int] | None:
    variant_tokens = method_variant.split("_")
    for token in variant_tokens:
        if not token.startswith("sp") or "x" not in token:
            continue
        patch_payload = token[2:]
        height_text, _, width_text = patch_payload.partition("x")
        if height_text.isdigit() and width_text.isdigit():
            return [int(height_text), int(width_text)]
    return None


def _parse_projection_support_weight_from_variant_name(
    method_variant: str,
) -> float | None:
    variant_tokens = method_variant.split("_")
    for token in variant_tokens:
        if token.startswith("w") and token[1:].isdigit():
            return round(int(token[1:]) / 100.0, 6)
    return None


def _parse_embedding_margin_from_variant_name(
    method_variant: str,
) -> float | None:
    variant_tokens = method_variant.split("_")
    for token in variant_tokens:
        if token.startswith("em") and token[2:].isdigit():
            return round(int(token[2:]) / 1000.0, 6)
    return None


def _resolve_sync_confidence_config(
    event_record: dict[str, Any],
) -> dict[str, float | int | str]:
    mechanism_trace = event_record.get("mechanism_trace", {})
    if not isinstance(mechanism_trace, dict):
        mechanism_trace = {}
    parsed_payload = _parse_tubelet_sync_variant_name(
        str(event_record.get("method_variant", ""))
    )
    min_margin = _resolve_numeric_sync_confidence_value(
        mechanism_trace,
        parsed_payload,
        trace_field_name="sync_confidence_min_margin",
        parsed_field_name="min_sync_positive_margin",
        default_value=0.0,
    )
    min_coverage_ratio = _resolve_numeric_sync_confidence_value(
        mechanism_trace,
        parsed_payload,
        trace_field_name="sync_confidence_min_coverage_ratio",
        parsed_field_name="min_sync_alignment_coverage_ratio",
        default_value=0.5,
    )
    min_matched_count = _resolve_integer_sync_confidence_value(
        mechanism_trace,
        parsed_payload,
        trace_field_name="sync_confidence_min_matched_count",
        parsed_field_name="min_sync_alignment_matched_count",
        default_value=1,
    )
    min_candidate_score = _resolve_numeric_sync_confidence_value(
        mechanism_trace,
        parsed_payload,
        trace_field_name="sync_confidence_min_candidate_score",
        parsed_field_name="min_sync_candidate_score",
        default_value=0.0,
    )
    gate_rule = _resolve_string_sync_confidence_value(
        mechanism_trace,
        parsed_payload,
        trace_field_name="sync_confidence_gate_rule",
        parsed_field_name="sync_confidence_gate_rule",
        default_value="candidate_score_gate",
    )
    min_payload_rescue_gain = _resolve_numeric_sync_confidence_value(
        mechanism_trace,
        parsed_payload,
        trace_field_name="sync_confidence_min_payload_rescue_gain",
        parsed_field_name="min_payload_rescue_gain",
        default_value=0.01,
    )
    min_aligned_payload_score = _resolve_numeric_sync_confidence_value(
        mechanism_trace,
        parsed_payload,
        trace_field_name="sync_confidence_min_aligned_payload_score",
        parsed_field_name="min_aligned_payload_score",
        default_value=0.1,
    )
    return {
        "min_sync_positive_margin": min_margin,
        "min_sync_alignment_coverage_ratio": min_coverage_ratio,
        "min_sync_alignment_matched_count": min_matched_count,
        "min_sync_candidate_score": min_candidate_score,
        "sync_confidence_gate_rule": gate_rule,
        "min_payload_rescue_gain": min_payload_rescue_gain,
        "min_aligned_payload_score": min_aligned_payload_score,
    }


def _resolve_string_sync_confidence_value(
    mechanism_trace: dict[str, Any],
    parsed_payload: dict[str, Any],
    *,
    trace_field_name: str,
    parsed_field_name: str,
    default_value: str,
) -> str:
    field_value = mechanism_trace.get(trace_field_name)
    if isinstance(field_value, str) and field_value:
        return str(field_value)
    parsed_value = parsed_payload.get(parsed_field_name)
    if isinstance(parsed_value, str) and parsed_value:
        return str(parsed_value)
    return str(default_value)


def _resolve_numeric_sync_confidence_value(
    mechanism_trace: dict[str, Any],
    parsed_payload: dict[str, Any],
    *,
    trace_field_name: str,
    parsed_field_name: str,
    default_value: float,
) -> float:
    field_value = mechanism_trace.get(trace_field_name)
    if isinstance(field_value, (int, float)):
        return round(float(field_value), 6)
    parsed_value = parsed_payload.get(parsed_field_name)
    if isinstance(parsed_value, (int, float)):
        return round(float(parsed_value), 6)
    return round(float(default_value), 6)


def _resolve_integer_sync_confidence_value(
    mechanism_trace: dict[str, Any],
    parsed_payload: dict[str, Any],
    *,
    trace_field_name: str,
    parsed_field_name: str,
    default_value: int,
) -> int:
    field_value = mechanism_trace.get(trace_field_name)
    if isinstance(field_value, int):
        return int(field_value)
    parsed_value = parsed_payload.get(parsed_field_name)
    if isinstance(parsed_value, int):
        return int(parsed_value)
    return int(default_value)


def _is_fpr_controlled(
    clean_negative_fpr: float | None,
    attacked_negative_fpr: float | None,
    mechanism_config: dict[str, Any],
) -> bool:
    max_clean_negative_fpr = _safe_float(mechanism_config.get("max_clean_negative_fpr"))
    max_attacked_negative_fpr = _safe_float(
        mechanism_config.get("max_attacked_negative_fpr")
    )
    if clean_negative_fpr is None or attacked_negative_fpr is None:
        return False
    if max_clean_negative_fpr is not None and clean_negative_fpr > max_clean_negative_fpr:
        return False
    if (
        max_attacked_negative_fpr is not None
        and attacked_negative_fpr > max_attacked_negative_fpr
    ):
        return False
    return True


def _selection_score(
    no_attack_clean_positive_tpr: float | None,
    mean_temporal_attacked_positive_tpr: float | None,
    max_attacked_negative_fpr: float | None,
) -> float:
    clean_positive = 0.0 if no_attack_clean_positive_tpr is None else float(no_attack_clean_positive_tpr)
    temporal_positive = 0.0 if mean_temporal_attacked_positive_tpr is None else float(mean_temporal_attacked_positive_tpr)
    attacked_negative_penalty = 0.0 if max_attacked_negative_fpr is None else float(max_attacked_negative_fpr)
    return round(clean_positive + (0.25 * temporal_positive) - attacked_negative_penalty, 6)


def _build_top_candidate_rows(
    calibration_rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    resolved_limit = max(1, int(limit))
    return [dict(row) for row in calibration_rows[:resolved_limit]]


def _build_parameter_interval_summary(
    calibration_rows: list[dict[str, Any]],
    field_names: list[str],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for field_name in field_names:
        field_values = [row.get(field_name) for row in calibration_rows if row.get(field_name) is not None]
        if not field_values:
            summary[field_name] = None
            continue
        if all(isinstance(field_value, (int, float)) for field_value in field_values):
            normalized_values = sorted({round(float(field_value), 6) for field_value in field_values})
            summary[field_name] = {
                "min": normalized_values[0],
                "max": normalized_values[-1],
                "unique_count": len(normalized_values),
                "unique_values": normalized_values,
            }
            continue
        normalized_values = sorted({str(field_value) for field_value in field_values})
        summary[field_name] = {
            "unique_count": len(normalized_values),
            "unique_values": normalized_values,
        }
    return summary


def _write_grid_csv(file_path: Path, rows: list[dict[str, Any]]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CALIBRATION_GRID_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_text_report(
    file_path: Path,
    candidate_payload: dict[str, Any],
    calibration_rows: list[dict[str, Any]],
) -> None:
    selected_candidate = candidate_payload["selected_tubelet_only_candidate"]
    selected_tubelet_sync_candidate = candidate_payload["selected_tubelet_sync_candidate"]
    interval_summary = candidate_payload.get("parameter_interval_summary", {})
    lines = [
        "# Stage2 Mechanism Calibration Report",
        "",
        "## Selection Scope",
        f"- selection_scope: {candidate_payload.get('selection_scope')}",
        f"- allowed_splits: {', '.join(candidate_payload['allowed_splits'])}",
        f"- forbidden_splits: {', '.join(candidate_payload['forbidden_splits'])}",
        f"- observed_forbidden_splits: {', '.join(candidate_payload['observed_forbidden_splits']) or 'none'}",
        "",
        "## Candidate Rows",
        f"- candidate_row_count: {len(calibration_rows)}",
    ]
    if selected_candidate is not None:
        lines.extend(
            [
                "",
                "## Selected Tubelet-only Candidate",
                f"- candidate_status: {selected_candidate['candidate_status']}",
                f"- candidate_eligible: {selected_candidate.get('candidate_eligible')}",
                f"- fpr_controlled: {selected_candidate.get('fpr_controlled')}",
                f"- method_variant: {selected_candidate['method_variant']}",
                f"- tubelet_length: {selected_candidate['tubelet_length']}",
                f"- spatial_patch_size: {selected_candidate['tubelet_partition']['spatial_patch_size']}",
                f"- no_attack_clean_positive_tpr: {selected_candidate['metrics']['no_attack_clean_positive_tpr']}",
                f"- max_attacked_negative_fpr: {selected_candidate['metrics']['max_attacked_negative_fpr']}",
                f"- parameter_interval_summary: {interval_summary.get('tubelet_only')}",
            ]
        )
    if candidate_payload.get("selection_completion_status") != "complete":
        lines.extend(
            [
                "",
                "## Selection Completion",
                f"- selection_completion_status: {candidate_payload.get('selection_completion_status')}",
                f"- selection_blocking_reason: {candidate_payload.get('selection_blocking_reason')}",
                f"- selection_blocking_details: {candidate_payload.get('selection_blocking_details')}",
            ]
        )
    if selected_tubelet_sync_candidate is not None:
        lines.extend(
            [
                "",
                "## Selected Tubelet-sync Candidate",
                f"- candidate_status: {selected_tubelet_sync_candidate['candidate_status']}",
                f"- candidate_selection_status: {selected_tubelet_sync_candidate['candidate_selection_status']}",
                f"- absolute_rescue_status: {selected_tubelet_sync_candidate['absolute_rescue_status']}",
                f"- incremental_gain_status: {selected_tubelet_sync_candidate['incremental_gain_status']}",
                f"- negative_leakage_status: {selected_tubelet_sync_candidate['negative_leakage_status']}",
                f"- sync_rescue_decision: {selected_tubelet_sync_candidate['sync_rescue_decision']}",
                f"- sync_leakage_decision: {selected_tubelet_sync_candidate['sync_leakage_decision']}",
                f"- method_variant: {selected_tubelet_sync_candidate['method_variant']}",
                f"- fusion_rule: {selected_tubelet_sync_candidate['fusion_rule']}",
                f"- lambda_sync: {selected_tubelet_sync_candidate['lambda_sync']}",
                f"- sync_search: {selected_tubelet_sync_candidate['sync_search']}",
                f"- temporal_crop_sync_gain: {selected_tubelet_sync_candidate['metrics']['temporal_crop_sync_gain']}",
                f"- local_clip_sync_gain: {selected_tubelet_sync_candidate['metrics']['local_clip_sync_gain']}",
                f"- mean_temporal_sync_gain: {selected_tubelet_sync_candidate['metrics']['mean_temporal_sync_gain']}",
                f"- parameter_interval_summary: {interval_summary.get('tubelet_sync')}",
            ]
        )
    if candidate_payload.get("tubelet_sync_scan_seed") is not None:
        lines.extend(
            [
                "",
                "## Tubelet-sync Scan Seed",
                f"- fusion_rule: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['fusion_rule']}",
                f"- lambda_sync: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['lambda_sync']}",
                f"- sync_search_radius: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['sync_search_radius']}",
                f"- min_sync_positive_margin: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['min_sync_positive_margin']}",
                f"- min_sync_alignment_coverage_ratio: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['min_sync_alignment_coverage_ratio']}",
                f"- min_sync_alignment_matched_count: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['min_sync_alignment_matched_count']}",
                f"- min_sync_candidate_score: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['min_sync_candidate_score']}",
            ]
        )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(file_path: Path, payload: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_string_list(payload: dict[str, Any], field_name: str) -> list[str]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"{field_name} must be a non-empty list")
    resolved_values = [str(item) for item in field_value if isinstance(item, str) and item]
    if not resolved_values:
        raise ValueError(f"{field_name} must contain at least one non-empty string")
    return resolved_values


def _read_grid_string_list(payload: dict[str, Any], field_name: str) -> list[str]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [str(item) for item in field_value if isinstance(item, str) and item]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain non-empty strings")
    return resolved_values


def _read_optional_grid_string_list(
    payload: dict[str, Any],
    field_name: str,
    default_values: list[str],
) -> list[str]:
    field_value = payload.get(field_name, default_values)
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [str(item) for item in field_value if isinstance(item, str) and item]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain non-empty strings")
    return resolved_values


def _read_grid_numeric_list(payload: dict[str, Any], field_name: str) -> list[float]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [round(float(item), 6) for item in field_value if isinstance(item, (int, float))]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain numeric values")
    return resolved_values


def _read_grid_integer_list(payload: dict[str, Any], field_name: str) -> list[int]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [int(item) for item in field_value if isinstance(item, int)]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain integer values")
    return resolved_values


def _read_optional_grid_numeric_list(
    payload: dict[str, Any],
    field_name: str,
    default_values: list[float],
) -> list[float]:
    field_value = payload.get(field_name, default_values)
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [round(float(item), 6) for item in field_value if isinstance(item, (int, float))]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain numeric values")
    return resolved_values


def _read_optional_grid_numeric_alias_list(
    payload: dict[str, Any],
    field_names: tuple[str, ...],
    default_values: list[float],
) -> list[float]:
    for field_name in field_names:
        if field_name in payload:
            return _read_optional_grid_numeric_list(payload, field_name, default_values)
    return _read_optional_grid_numeric_list(payload, field_names[0], default_values)


def _read_optional_grid_integer_list(
    payload: dict[str, Any],
    field_name: str,
    default_values: list[int],
) -> list[int]:
    field_value = payload.get(field_name, default_values)
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [int(item) for item in field_value if isinstance(item, int)]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain integer values")
    return resolved_values


def _safe_float(field_value: Any) -> float | None:
    if field_value is None or field_value == "":
        return None
    try:
        return round(float(field_value), 6)
    except (TypeError, ValueError):
        return None


def _mean_numeric_values(values: list[float | None]) -> float | None:
    numeric_values = [float(value) for value in values if value is not None]
    if not numeric_values:
        return None
    return round(sum(numeric_values) / len(numeric_values), 6)


def _max_numeric_value(values: list[float | None]) -> float | None:
    numeric_values = [float(value) for value in values if value is not None]
    if not numeric_values:
        return None
    return round(max(numeric_values), 6)


def _difference(left_value: float | None, right_value: float | None) -> float | None:
    if left_value is None or right_value is None:
        return None
    return round(float(left_value) - float(right_value), 6)


def main(argv: list[str] | None = None) -> int:
    """Run the stage-two mechanism candidate selector CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Select a governed stage-two mechanism calibration candidate.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--grid-config", default=str(DEFAULT_GRID_CONFIG_PATH))
    parser.add_argument("--mechanism-config", default=str(DEFAULT_MECHANISM_CONFIG_PATH))
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--grid-output-path", default=None)
    args = parser.parse_args(argv)
    result = select_stage2_mechanism_candidate(
        run_root=args.run_root,
        grid_config_path=args.grid_config,
        mechanism_config_path=args.mechanism_config,
        output_path=args.output_path,
        report_path=args.report_path,
        grid_output_path=args.grid_output_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

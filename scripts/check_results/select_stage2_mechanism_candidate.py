"""
文件用途：从阶段 2 dev / calibration records 中选择 mechanism calibration 候选并写出受治理输出。
File purpose: Select a stage-two mechanism calibration candidate from dev/calibration records and write governed outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from experiments.real_video_vae_latent_probe.mechanism_audit import (
    build_stage2_mechanism_audit_rows,
)
from main.core.records import RecordWriter
from main.core.registry import load_json_config


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
    "fusion_rule",
    "lambda_sync",
    "sync_search_radius",
    "min_sync_positive_margin",
    "min_sync_alignment_coverage_ratio",
    "min_sync_alignment_matched_count",
    "no_attack_clean_negative_fpr",
    "no_attack_clean_positive_tpr",
    "max_attacked_negative_fpr",
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
    event_score_records = record_writer.read_event_score_records()
    if not event_score_records:
        raise ValueError("event_score_records must not be empty")
    try:
        threshold_records = record_writer.read_threshold_records()
    except FileNotFoundError:
        threshold_records = []

    audit_rows = build_stage2_mechanism_audit_rows(
        event_score_records,
        threshold_records,
        allowed_splits=set(allowed_splits),
    )
    tubelet_only_rows = _build_tubelet_only_calibration_grid_rows(
        audit_rows,
        event_score_records,
        mechanism_config,
    )
    selected_candidate = None
    sync_scan_seed = None
    tubelet_sync_rows: list[dict[str, Any]] = []
    selected_tubelet_sync_candidate = None
    if selection_scope == "tubelet_only":
        selected_candidate = _select_tubelet_only_candidate(
            tubelet_only_rows,
            mechanism_config,
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
            audit_rows,
            event_score_records,
            mechanism_config,
            selected_candidate=selected_candidate,
        )
        selected_tubelet_sync_candidate = _select_tubelet_sync_candidate(
            tubelet_sync_rows,
            mechanism_config,
        )
        calibration_rows = list(tubelet_sync_rows)
    else:
        selected_candidate = _select_tubelet_only_candidate(
            tubelet_only_rows,
            mechanism_config,
        )
        sync_scan_seed = _build_tubelet_sync_scan_seed(
            selected_candidate,
            grid_config,
        )
        tubelet_sync_rows = _build_tubelet_sync_calibration_grid_rows(
            audit_rows,
            event_score_records,
            mechanism_config,
            selected_candidate=selected_candidate,
        )
        selected_tubelet_sync_candidate = _select_tubelet_sync_candidate(
            tubelet_sync_rows,
            mechanism_config,
        )
        calibration_rows = [*tubelet_only_rows, *tubelet_sync_rows]
    observed_splits = sorted({str(record.get("split")) for record in event_score_records})
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


def _build_tubelet_only_calibration_grid_rows(
    audit_rows: list[dict[str, Any]],
    event_score_records: list[dict[str, Any]],
    mechanism_config: dict[str, Any],
) -> list[dict[str, Any]]:
    lookup = {
        (
            str(row.get("method_variant")),
            str(row.get("attack_name")),
            str(row.get("sample_role")),
        ): row
        for row in audit_rows
    }
    required_attacks = _read_string_list(mechanism_config, "required_mechanism_attacks")
    candidate_variants = sorted(
        {
            str(record.get("method_variant"))
            for record in event_score_records
            if str(record.get("base_method_variant", record.get("method_variant")))
            == "tubelet_only"
        }
    )
    rows: list[dict[str, Any]] = []
    for method_variant in candidate_variants:
        representative_record = _find_variant_record(event_score_records, method_variant)
        if representative_record is None:
            continue
        no_attack_negative_row = lookup.get((method_variant, "no_attack", "clean_negative"), {})
        no_attack_positive_row = lookup.get((method_variant, "no_attack", "watermarked_positive"), {})
        temporal_crop_row = lookup.get((method_variant, "temporal_crop", "attacked_positive"), {})
        frame_dropping_row = lookup.get((method_variant, "frame_dropping", "attacked_positive"), {})
        local_clip_row = lookup.get((method_variant, "local_clip", "attacked_positive"), {})
        attacked_negative_rates = [
            _safe_float(
                lookup.get((method_variant, attack_name, "attacked_negative"), {}).get(
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
                    representative_record.get("mechanism_trace", {}).get(
                        "spatial_patch_size",
                        [4, 4],
                    ),
                    ensure_ascii=False,
                ),
                "embedding_projection_support_weight": _resolve_projection_support_weight(
                    representative_record,
                ),
                "fusion_rule": None,
                "lambda_sync": None,
                "sync_search_radius": None,
                "no_attack_clean_negative_fpr": _safe_float(
                    no_attack_negative_row.get("clean_negative_FPR")
                ),
                "no_attack_clean_positive_tpr": _safe_float(
                    no_attack_positive_row.get("clean_positive_TPR")
                ),
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
                "quality_psnr_mean": _safe_float(
                    no_attack_positive_row.get("quality_psnr_mean")
                ),
                "quality_ssim_mean": _safe_float(
                    no_attack_positive_row.get("quality_ssim_mean")
                ),
                "temporal_crop_sync_gain": None,
                "frame_dropping_sync_gain": None,
                "local_clip_sync_gain": None,
                "mean_temporal_sync_gain": None,
                "fpr_controlled": _is_fpr_controlled(
                    _safe_float(no_attack_negative_row.get("clean_negative_FPR")),
                    max_attacked_negative_fpr,
                    mechanism_config,
                ),
                "quality_not_collapsed": _is_quality_not_collapsed(
                    _safe_float(no_attack_positive_row.get("quality_psnr_mean")),
                    _safe_float(no_attack_positive_row.get("quality_ssim_mean")),
                    mechanism_config,
                ),
                "candidate_eligible": _is_tubelet_only_candidate_eligible(
                    _safe_float(no_attack_negative_row.get("clean_negative_FPR")),
                    _safe_float(no_attack_positive_row.get("clean_positive_TPR")),
                    max_attacked_negative_fpr,
                    _safe_float(no_attack_positive_row.get("quality_psnr_mean")),
                    _safe_float(no_attack_positive_row.get("quality_ssim_mean")),
                    mechanism_config,
                ),
                "selection_score": _selection_score(
                    _safe_float(no_attack_positive_row.get("clean_positive_TPR")),
                    _mean_numeric_values(temporal_positive_rates),
                    max_attacked_negative_fpr,
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            0 if bool(row.get("fpr_controlled")) else 1,
            -float(row.get("selection_score") or 0.0),
            int(row.get("tubelet_length") or 1),
        )
    )
    return rows


def _build_tubelet_sync_calibration_grid_rows(
    audit_rows: list[dict[str, Any]],
    event_score_records: list[dict[str, Any]],
    mechanism_config: dict[str, Any],
    *,
    selected_candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    lookup = {
        (
            str(row.get("method_variant")),
            str(row.get("attack_name")),
            str(row.get("sample_role")),
        ): row
        for row in audit_rows
    }
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
    selected_tubelet_length = int(selected_candidate["tubelet_length"])
    tubelet_only_metrics = selected_candidate["metrics"]
    candidate_variants = sorted(
        {
            str(record.get("method_variant"))
            for record in event_score_records
            if str(record.get("base_method_variant", record.get("method_variant")))
            == "tubelet_sync"
        }
    )
    rows: list[dict[str, Any]] = []
    for method_variant in candidate_variants:
        representative_record = _find_variant_record(event_score_records, method_variant)
        if representative_record is None:
            continue
        spatial_patch_size = representative_record.get("mechanism_trace", {}).get(
            "spatial_patch_size",
            [4, 4],
        )
        support_weight = _resolve_projection_support_weight(representative_record)
        if int(representative_record.get("tubelet_length", 1)) != selected_tubelet_length:
            continue
        if list(spatial_patch_size) != selected_spatial_patch_size:
            continue
        if support_weight != selected_support_weight:
            continue

        no_attack_negative_row = lookup.get((method_variant, "no_attack", "clean_negative"), {})
        no_attack_positive_row = lookup.get((method_variant, "no_attack", "watermarked_positive"), {})
        temporal_crop_row = lookup.get((method_variant, "temporal_crop", "attacked_positive"), {})
        frame_dropping_row = lookup.get((method_variant, "frame_dropping", "attacked_positive"), {})
        local_clip_row = lookup.get((method_variant, "local_clip", "attacked_positive"), {})
        attacked_negative_rates = [
            _safe_float(
                lookup.get((method_variant, attack_name, "attacked_negative"), {}).get(
                    "attacked_negative_FPR"
                )
            )
            for attack_name in required_attacks
            if attack_name != "no_attack"
        ]
        max_attacked_negative_fpr = _max_numeric_value(attacked_negative_rates)
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
                "no_attack_clean_negative_fpr": clean_negative_fpr,
                "no_attack_clean_positive_tpr": no_attack_clean_positive_tpr,
                "max_attacked_negative_fpr": max_attacked_negative_fpr,
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
) -> dict[str, Any]:
    if not calibration_rows:
        raise ValueError("calibration_rows must not be empty")
    selected_row = calibration_rows[0]
    return {
        "candidate_status": (
            "fpr_controlled_candidate_selected"
            if bool(selected_row.get("fpr_controlled"))
            else "best_effort_candidate_selected"
        ),
        "method_variant": selected_row["method_variant"],
        "base_method_variant": selected_row["base_method_variant"],
        "tubelet_length": int(selected_row["tubelet_length"]),
        "tubelet_partition": {
            "spatial_patch_size": json.loads(str(selected_row["spatial_patch_size"])),
        },
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


def _select_tubelet_sync_candidate(
    calibration_rows: list[dict[str, Any]],
    mechanism_config: dict[str, Any],
) -> dict[str, Any]:
    if not calibration_rows:
        raise ValueError("tubelet_sync calibration rows must not be empty")
    selected_row = calibration_rows[0]
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
        },
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
    mechanism_config: dict[str, Any],
) -> bool:
    min_sync_gain = _safe_float(
        mechanism_config.get("min_tubelet_sync_gain_over_tubelet_only_temporal")
    )
    if not _is_tubelet_only_candidate_eligible(
        clean_negative_fpr,
        no_attack_clean_positive_tpr,
        max_attacked_negative_fpr,
        quality_psnr_mean,
        quality_ssim_mean,
        mechanism_config,
    ):
        return False
    if temporal_crop_sync_gain is None or temporal_crop_sync_gain <= 0.0:
        return False
    if local_clip_sync_gain is None or local_clip_sync_gain <= 0.0:
        return False
    if min_sync_gain is not None and (
        mean_temporal_sync_gain is None or mean_temporal_sync_gain < min_sync_gain
    ):
        return False
    return True


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
    return {
        "fusion_rule": default_fusion_rule,
        "lambda_sync": default_lambda_sync,
        "sync_search_radius": default_sync_search_radius,
        "min_sync_positive_margin": default_min_sync_positive_margin,
        "min_sync_alignment_coverage_ratio": default_min_sync_alignment_coverage_ratio,
        "min_sync_alignment_matched_count": default_min_sync_alignment_matched_count,
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


def _parse_projection_support_weight_from_variant_name(
    method_variant: str,
) -> float | None:
    variant_tokens = method_variant.split("_")
    for token in variant_tokens:
        if token.startswith("w") and token[1:].isdigit():
            return round(int(token[1:]) / 100.0, 6)
    return None


def _resolve_sync_confidence_config(event_record: dict[str, Any]) -> dict[str, float | int]:
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
    return {
        "min_sync_positive_margin": min_margin,
        "min_sync_alignment_coverage_ratio": min_coverage_ratio,
        "min_sync_alignment_matched_count": min_matched_count,
    }


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
                f"- method_variant: {selected_candidate['method_variant']}",
                f"- tubelet_length: {selected_candidate['tubelet_length']}",
                f"- spatial_patch_size: {selected_candidate['tubelet_partition']['spatial_patch_size']}",
                f"- no_attack_clean_positive_tpr: {selected_candidate['metrics']['no_attack_clean_positive_tpr']}",
                f"- max_attacked_negative_fpr: {selected_candidate['metrics']['max_attacked_negative_fpr']}",
                f"- parameter_interval_summary: {interval_summary.get('tubelet_only')}",
            ]
        )
    if selected_tubelet_sync_candidate is not None:
        lines.extend(
            [
                "",
                "## Selected Tubelet-sync Candidate",
                f"- candidate_status: {selected_tubelet_sync_candidate['candidate_status']}",
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
    if not isinstance(field_value, (int, float)):
        return None
    return round(float(field_value), 6)


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
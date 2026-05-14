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
    "method_variant",
    "base_method_variant",
    "tubelet_length",
    "spatial_patch_size",
    "embedding_projection_support_weight",
    "no_attack_clean_negative_fpr",
    "no_attack_clean_positive_tpr",
    "max_attacked_negative_fpr",
    "temporal_crop_attacked_positive_tpr",
    "frame_dropping_attacked_positive_tpr",
    "local_clip_attacked_positive_tpr",
    "mean_temporal_attacked_positive_tpr",
    "fpr_controlled",
    "selection_score",
]


def select_stage2_mechanism_candidate(
    *,
    run_root: str | Path,
    grid_config_path: str | Path = DEFAULT_GRID_CONFIG_PATH,
    mechanism_config_path: str | Path = DEFAULT_MECHANISM_CONFIG_PATH,
    output_path: str | Path | None = None,
    report_path: str | Path | None = None,
    grid_output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Select a governed stage-two mechanism calibration candidate.

    Args:
        run_root: Run-root path.
        grid_config_path: Calibration-grid config path.
        mechanism_config_path: Mechanism-gate config path.
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

    record_writer = RecordWriter(run_root_path)
    event_score_records = record_writer.read_event_score_records()
    if not event_score_records:
        raise ValueError("event_score_records must not be empty")

    audit_rows = build_stage2_mechanism_audit_rows(
        event_score_records,
        [],
        allowed_splits=set(allowed_splits),
    )
    calibration_rows = _build_calibration_grid_rows(
        audit_rows,
        event_score_records,
        mechanism_config,
    )
    selected_candidate = _select_tubelet_only_candidate(
        calibration_rows,
        mechanism_config,
    )
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
        "selection_metrics": _read_string_list(grid_config, "selection_metrics"),
        "selected_tubelet_only_candidate": selected_candidate,
        "tubelet_sync_scan_seed": _build_tubelet_sync_scan_seed(
            selected_candidate,
            grid_config,
        ),
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


def _build_calibration_grid_rows(
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
                "fpr_controlled": _is_fpr_controlled(
                    _safe_float(no_attack_negative_row.get("clean_negative_FPR")),
                    max_attacked_negative_fpr,
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


def _build_tubelet_sync_scan_seed(
    selected_candidate: dict[str, Any],
    grid_config: dict[str, Any],
) -> dict[str, Any]:
    grid = grid_config.get("grid", {})
    if not isinstance(grid, dict):
        raise TypeError("grid must be a dictionary")
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
            "fusion_rule": _read_grid_string_list(grid, "fusion_rule"),
            "lambda_sync": _read_grid_numeric_list(grid, "lambda_sync"),
            "sync_search_radius": _read_grid_integer_list(grid, "sync_search_radius"),
        },
        "rationale": [
            "reuse_tubelet_only_candidate_for_no_attack_recovery",
            "start_with_low_lambda_sync_to_reduce_negative_sync_leakage",
            "shrink_offset_search_radius_before_increasing_sync_weight",
        ],
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
    field_value = mechanism_trace.get("embedding_projection_support_weight")
    if not isinstance(field_value, (int, float)):
        return 0.45
    return round(float(field_value), 6)


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
    lines = [
        "# Stage2 Mechanism Calibration Report",
        "",
        "## Selection Scope",
        f"- allowed_splits: {', '.join(candidate_payload['allowed_splits'])}",
        f"- forbidden_splits: {', '.join(candidate_payload['forbidden_splits'])}",
        f"- observed_forbidden_splits: {', '.join(candidate_payload['observed_forbidden_splits']) or 'none'}",
        "",
        "## Selected Tubelet-only Candidate",
        f"- candidate_status: {selected_candidate['candidate_status']}",
        f"- method_variant: {selected_candidate['method_variant']}",
        f"- tubelet_length: {selected_candidate['tubelet_length']}",
        f"- spatial_patch_size: {selected_candidate['tubelet_partition']['spatial_patch_size']}",
        f"- no_attack_clean_positive_tpr: {selected_candidate['metrics']['no_attack_clean_positive_tpr']}",
        f"- max_attacked_negative_fpr: {selected_candidate['metrics']['max_attacked_negative_fpr']}",
        "",
        "## Tubelet-sync Scan Seed",
        f"- fusion_rule: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['fusion_rule']}",
        f"- lambda_sync: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['lambda_sync']}",
        f"- sync_search_radius: {candidate_payload['tubelet_sync_scan_seed']['parameter_scan']['sync_search_radius']}",
        "",
        "## Candidate Rows",
        f"- candidate_row_count: {len(calibration_rows)}",
    ]
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
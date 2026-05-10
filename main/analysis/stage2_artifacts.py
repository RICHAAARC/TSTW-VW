"""
文件用途：从阶段 2 records 重建表格、figure、report 与失败样例索引。
File purpose: Rebuild stage-two tables, figure, report, and failure-gallery artifacts from records.
Module type: General module
"""

from __future__ import annotations

import binascii
import csv
from pathlib import Path
import struct
from typing import Any
import zlib

from main.analysis.failure_case_exporter import export_failure_case_gallery
from main.core.records import RecordWriter
from main.protocol.evaluator import build_ablation_table_rows, build_main_metrics_rows
from main.protocol.stage2_paths import Stage2OutputPaths, build_stage2_output_paths


REAL_VIDEO_ATTACK_BREAKDOWN_COLUMNS = [
    "run_id",
    "construction_phase",
    "method_variant",
    "attack_name",
    "attack_strength",
    "threshold_id",
    "clean_negative_FPR",
    "attacked_negative_FPR",
    "clean_positive_TPR",
    "attacked_positive_TPR",
    "local_clip_TPR",
    "sync_alignment_error_mean",
    "sync_peak_rank_median",
    "positive_count",
    "negative_count",
]
QUALITY_TABLE_COLUMNS = [
    "run_id",
    "construction_phase",
    "method_variant",
    "attack_name",
    "sample_role",
    "video_count",
    "vae_reconstruction_psnr_mean",
    "vae_reconstruction_ssim_mean",
    "watermarked_video_psnr_mean",
    "watermarked_video_ssim_mean",
    "watermarked_video_lpips_mean",
    "quality_failure_count",
    "threshold_id",
]
TEMPORAL_CONSISTENCY_COLUMNS = [
    "run_id",
    "construction_phase",
    "method_variant",
    "attack_name",
    "sample_role",
    "video_count",
    "temporal_consistency_score_mean",
    "flicker_score_mean",
    "motion_consistency_score_mean",
    "temporal_failure_count",
    "threshold_id",
]
STAGE2_GOVERNANCE_SUMMARY_COLUMNS = [
    "run_id",
    "construction_phase",
    "method_variants_summary",
    "attack_names_summary",
    "target_fprs_summary",
    "event_record_count",
    "threshold_record_count",
    "clean_negative_fpr_controlled",
    "attacked_negative_fpr_reported",
    "quality_table_non_empty",
    "quality_metrics_runtime",
    "temporal_table_non_empty",
    "temporal_metrics_runtime",
    "records_to_tables",
    "records_to_report",
    "records_to_failure_gallery",
    "stage2_decision",
    "blocking_reasons",
    "next_allowed_stage",
]
FIGURE_WIDTH = 640
FIGURE_HEIGHT = 360
BACKGROUND_COLOR = (248, 250, 252)
AXIS_COLOR = (15, 23, 42)
PSNR_BAR_COLOR = (14, 116, 144)
TPR_BAR_COLOR = (22, 163, 74)
GRID_COLOR = (203, 213, 225)


class Stage2ArtifactBuilder:
    """功能：构建阶段 2 scaffold 产物。

    Builder for the stage-two scaffold artifacts.

    Args:
        None.

    Returns:
        None.
    """

    def build_artifacts(
        self,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        output_root: str | Path,
    ) -> dict[str, Path]:
        """功能：从 governed records 构建阶段 2 产物。

        Build stage-two artifacts from governed records.

        Args:
            event_score_records: Event score record list.
            threshold_records: Threshold record list.
            output_root: Run root path.

        Returns:
            A dictionary containing artifact paths.
        """
        if not isinstance(event_score_records, list):
            raise TypeError("event_score_records must be a list")
        if not isinstance(threshold_records, list):
            raise TypeError("threshold_records must be a list")
        output_paths = build_stage2_output_paths(output_root)

        main_rows = build_main_metrics_rows(event_score_records, threshold_records)
        ablation_rows = build_ablation_table_rows(event_score_records, threshold_records)
        attack_breakdown_rows = build_real_video_attack_breakdown_rows(
            event_score_records,
            threshold_records,
        )
        quality_rows = build_quality_table_rows(event_score_records)
        temporal_rows = build_temporal_consistency_rows(event_score_records)
        governance_summary_rows = build_stage2_governance_summary_rows(
            event_score_records,
            threshold_records,
            attack_breakdown_rows,
            quality_rows,
            temporal_rows,
        )
        self._write_csv(output_paths.main_tpr_fpr_table_path, list(main_rows[0].keys()) if main_rows else [
            "run_id",
            "method_family",
            "method_variant",
            "base_method_variant",
            "derived_variant",
            "ablation_axis",
            "tubelet_length",
            "target_fpr",
            "threshold_id",
            "split",
            "attack_name",
            "clean_negative_count",
            "attacked_negative_count",
            "watermarked_positive_count",
            "attacked_positive_count",
            "clean_negative_FPR",
            "attacked_negative_FPR",
            "clean_positive_TPR",
            "attacked_positive_TPR"
        ], main_rows)
        self._write_csv(output_paths.ablation_table_path, list(ablation_rows[0].keys()) if ablation_rows else [
            "run_id",
            "method_family",
            "method_variant",
            "base_method_variant",
            "derived_variant",
            "ablation_axis",
            "tubelet_length",
            "enabled_tubelet_evidence",
            "enabled_sync_evidence",
            "enabled_trajectory_evidence",
            "fusion_rule",
            "threshold_id",
            "clean_negative_FPR",
            "attacked_negative_FPR",
            "clean_positive_TPR",
            "attacked_positive_TPR"
        ], ablation_rows)
        self._write_csv(
            output_paths.real_video_attack_breakdown_path,
            REAL_VIDEO_ATTACK_BREAKDOWN_COLUMNS,
            attack_breakdown_rows,
        )
        self._write_csv(output_paths.quality_table_path, QUALITY_TABLE_COLUMNS, quality_rows)
        self._write_csv(
            output_paths.temporal_consistency_table_path,
            TEMPORAL_CONSISTENCY_COLUMNS,
            temporal_rows,
        )
        self._write_csv(
            output_paths.stage2_governance_summary_path,
            STAGE2_GOVERNANCE_SUMMARY_COLUMNS,
            governance_summary_rows,
        )
        self._write_tradeoff_figure(
            output_paths,
            attack_breakdown_rows,
            quality_rows,
        )
        output_paths.report_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.report_path.write_text(
            build_stage2_report_text(
                governance_summary_rows[0],
            ),
            encoding="utf-8",
        )
        export_failure_case_gallery(event_score_records, output_paths.failure_case_gallery_path)
        return {
            "main_tpr_fpr_table_path": output_paths.main_tpr_fpr_table_path,
            "ablation_table_path": output_paths.ablation_table_path,
            "real_video_attack_breakdown_path": output_paths.real_video_attack_breakdown_path,
            "quality_table_path": output_paths.quality_table_path,
            "temporal_consistency_table_path": output_paths.temporal_consistency_table_path,
            "stage2_governance_summary_path": output_paths.stage2_governance_summary_path,
            "quality_robustness_tradeoff_path": output_paths.quality_robustness_tradeoff_path,
            "report_path": output_paths.report_path,
            "failure_case_gallery_path": output_paths.failure_case_gallery_path,
        }

    def rebuild_artifacts(self, output_root: str | Path) -> dict[str, Path]:
        """功能：仅根据 persisted records 与 thresholds 重建阶段 2 产物。

        Rebuild stage-two artifacts from persisted records and thresholds only.

        Args:
            output_root: Run root path.

        Returns:
            A dictionary containing artifact paths.
        """
        record_writer = RecordWriter(output_root)
        return self.build_artifacts(
            record_writer.read_event_score_records(),
            record_writer.read_threshold_records(),
            output_root,
        )

    def _write_csv(
        self,
        file_path: Path,
        field_names: list[str],
        rows: list[dict[str, Any]],
    ) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=field_names)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _write_tradeoff_figure(
        self,
        output_paths: Stage2OutputPaths,
        attack_breakdown_rows: list[dict[str, Any]],
        quality_rows: list[dict[str, Any]],
    ) -> None:
        output_paths.quality_robustness_tradeoff_path.parent.mkdir(parents=True, exist_ok=True)
        method_variants = sorted(
            {row["method_variant"] for row in attack_breakdown_rows} | {row["method_variant"] for row in quality_rows}
        )
        quality_map = {
            row["method_variant"]: float(row["watermarked_video_psnr_mean"] or 0.0)
            for row in quality_rows
            if row["sample_role"] == "attacked_positive"
        }
        robustness_map = {}
        for row in attack_breakdown_rows:
            robustness_map.setdefault(row["method_variant"], []).append(
                float(row["attacked_positive_TPR"] or 0.0)
            )
        pixels = bytearray(BACKGROUND_COLOR * (FIGURE_WIDTH * FIGURE_HEIGHT))
        _draw_rect(pixels, 64, 44, FIGURE_WIDTH - 36, 48, GRID_COLOR)
        _draw_rect(pixels, 64, FIGURE_HEIGHT - 64, FIGURE_WIDTH - 36, FIGURE_HEIGHT - 60, AXIS_COLOR)
        _draw_rect(pixels, 64, 44, 68, FIGURE_HEIGHT - 60, AXIS_COLOR)
        if method_variants:
            max_psnr = max(1.0, max(quality_map.get(variant, 0.0) for variant in method_variants))
            group_width = max(32, (FIGURE_WIDTH - 160) // len(method_variants))
            for variant_index, method_variant in enumerate(method_variants):
                group_left = 88 + variant_index * group_width
                psnr_value = quality_map.get(method_variant, 0.0)
                tpr_values = robustness_map.get(method_variant, [0.0])
                mean_tpr = sum(tpr_values) / len(tpr_values)
                psnr_height = int((FIGURE_HEIGHT - 140) * (psnr_value / max_psnr))
                tpr_height = int((FIGURE_HEIGHT - 140) * mean_tpr)
                bar_width = max(8, group_width // 4)
                _draw_rect(
                    pixels,
                    group_left,
                    FIGURE_HEIGHT - 80 - psnr_height,
                    group_left + bar_width,
                    FIGURE_HEIGHT - 80,
                    PSNR_BAR_COLOR,
                )
                _draw_rect(
                    pixels,
                    group_left + bar_width + 6,
                    FIGURE_HEIGHT - 80 - tpr_height,
                    group_left + 2 * bar_width + 6,
                    FIGURE_HEIGHT - 80,
                    TPR_BAR_COLOR,
                )
        _write_rgb_png(
            output_paths.quality_robustness_tradeoff_path,
            FIGURE_WIDTH,
            FIGURE_HEIGHT,
            pixels,
        )


def build_real_video_attack_breakdown_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    threshold_map = {
        threshold_record["method_variant"]: threshold_record
        for threshold_record in threshold_records
    }
    rows: list[dict[str, Any]] = []
    test_records = [record for record in event_score_records if record["split"] == "test"]
    for method_variant in sorted({record["method_variant"] for record in test_records}):
        variant_records = [record for record in test_records if record["method_variant"] == method_variant]
        threshold_id = threshold_map[method_variant]["threshold_id"]
        for attack_name in sorted({record["attack_name"] for record in variant_records}):
            grouped_records = [record for record in variant_records if record["attack_name"] == attack_name]
            rows.append(
                {
                    "run_id": grouped_records[0]["run_id"],
                    "construction_phase": grouped_records[0]["mechanism_trace"]["construction_phase"],
                    "method_variant": method_variant,
                    "attack_name": attack_name,
                    "attack_strength": _derive_attack_strength(grouped_records[0]["attack_params"]),
                    "threshold_id": threshold_id,
                    "clean_negative_FPR": _rate_for_role(grouped_records, "clean_negative"),
                    "attacked_negative_FPR": _rate_for_role(grouped_records, "attacked_negative"),
                    "clean_positive_TPR": _rate_for_role(grouped_records, "watermarked_positive"),
                    "attacked_positive_TPR": _rate_for_role(grouped_records, "attacked_positive"),
                    "local_clip_TPR": _rate_for_local_clip(grouped_records),
                    "sync_alignment_error_mean": _mean_mechanism_trace_value(
                        grouped_records,
                        "sync_alignment_error",
                    ),
                    "sync_peak_rank_median": _median_mechanism_trace_value(
                        grouped_records,
                        "sync_peak_rank",
                    ),
                    "positive_count": sum(
                        1
                        for record in grouped_records
                        if record["sample_role"].endswith("positive")
                    ),
                    "negative_count": sum(
                        1
                        for record in grouped_records
                        if record["sample_role"].endswith("negative")
                    ),
                }
            )
    return rows


def build_quality_table_rows(
    event_score_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    test_records = [record for record in event_score_records if record["split"] == "test"]
    grouped_keys = sorted(
        {
            (
                record["method_variant"],
                record["attack_name"],
                record["sample_role"],
                record["threshold_id"],
            )
            for record in test_records
        }
    )
    for method_variant, attack_name, sample_role, threshold_id in grouped_keys:
        grouped_records = [
            record
            for record in test_records
            if record["method_variant"] == method_variant
            and record["attack_name"] == attack_name
            and record["sample_role"] == sample_role
            and record["threshold_id"] == threshold_id
        ]
        rows.append(
            {
                "run_id": grouped_records[0]["run_id"],
                "construction_phase": grouped_records[0]["mechanism_trace"]["construction_phase"],
                "method_variant": method_variant,
                "attack_name": attack_name,
                "sample_role": sample_role,
                "video_count": len(grouped_records),
                "vae_reconstruction_psnr_mean": _mean_payload_value(
                    grouped_records,
                    "quality_metrics",
                    "vae_reconstruction_psnr",
                ),
                "vae_reconstruction_ssim_mean": _mean_payload_value(
                    grouped_records,
                    "quality_metrics",
                    "vae_reconstruction_ssim",
                ),
                "watermarked_video_psnr_mean": _mean_payload_value(
                    grouped_records,
                    "quality_metrics",
                    "watermarked_video_psnr",
                ),
                "watermarked_video_ssim_mean": _mean_payload_value(
                    grouped_records,
                    "quality_metrics",
                    "watermarked_video_ssim",
                ),
                "watermarked_video_lpips_mean": _mean_payload_value(
                    grouped_records,
                    "quality_metrics",
                    "watermarked_video_lpips",
                ),
                "quality_failure_count": sum(
                    1
                    for record in grouped_records
                    if record.get("quality_metrics", {}).get("quality_failure_reason") is not None
                ),
                "threshold_id": threshold_id,
            }
        )
    return rows


def build_temporal_consistency_rows(
    event_score_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    test_records = [record for record in event_score_records if record["split"] == "test"]
    grouped_keys = sorted(
        {
            (
                record["method_variant"],
                record["attack_name"],
                record["sample_role"],
                record["threshold_id"],
            )
            for record in test_records
        }
    )
    for method_variant, attack_name, sample_role, threshold_id in grouped_keys:
        grouped_records = [
            record
            for record in test_records
            if record["method_variant"] == method_variant
            and record["attack_name"] == attack_name
            and record["sample_role"] == sample_role
            and record["threshold_id"] == threshold_id
        ]
        rows.append(
            {
                "run_id": grouped_records[0]["run_id"],
                "construction_phase": grouped_records[0]["mechanism_trace"]["construction_phase"],
                "method_variant": method_variant,
                "attack_name": attack_name,
                "sample_role": sample_role,
                "video_count": len(grouped_records),
                "temporal_consistency_score_mean": _mean_payload_value(
                    grouped_records,
                    "temporal_metrics",
                    "temporal_consistency_score",
                ),
                "flicker_score_mean": _mean_payload_value(
                    grouped_records,
                    "temporal_metrics",
                    "flicker_score",
                ),
                "motion_consistency_score_mean": _mean_payload_value(
                    grouped_records,
                    "temporal_metrics",
                    "motion_consistency_score",
                ),
                "temporal_failure_count": sum(
                    1
                    for record in grouped_records
                    if isinstance(record.get("temporal_metrics", {}).get("flicker_score"), (int, float))
                    and float(record["temporal_metrics"]["flicker_score"]) > 0.25
                ),
                "threshold_id": threshold_id,
            }
        )
    return rows


def build_stage2_report_text(governance_summary_row: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# VAE Latent Probe Report",
            "",
            "## Summary",
            f"- construction_phase: {governance_summary_row['construction_phase']}",
            f"- method_variants: {governance_summary_row['method_variants_summary']}",
            f"- attack_names: {governance_summary_row['attack_names_summary']}",
            f"- target_fprs: {governance_summary_row['target_fprs_summary']}",
            f"- event_record_count: {governance_summary_row['event_record_count']}",
            f"- threshold_record_count: {governance_summary_row['threshold_record_count']}",
            "",
            "## Robustness Summary",
            f"- clean_negative_fpr_controlled: {_bool_to_report_value(governance_summary_row['clean_negative_fpr_controlled'])}",
            f"- attacked_negative_fpr_reported: {_bool_to_report_value(governance_summary_row['attacked_negative_fpr_reported'])}",
            "",
            "## Quality Summary",
            f"- quality_table_non_empty: {_bool_to_report_value(governance_summary_row['quality_table_non_empty'])}",
            f"- quality_metrics_runtime: {governance_summary_row['quality_metrics_runtime']}",
            "",
            "## Temporal Consistency Summary",
            f"- temporal_table_non_empty: {_bool_to_report_value(governance_summary_row['temporal_table_non_empty'])}",
            f"- temporal_metrics_runtime: {governance_summary_row['temporal_metrics_runtime']}",
            "",
            "## Rebuildability",
            f"- records_to_tables: {_bool_to_report_value(governance_summary_row['records_to_tables'])}",
            f"- records_to_report: {_bool_to_report_value(governance_summary_row['records_to_report'])}",
            f"- records_to_failure_gallery: {_bool_to_report_value(governance_summary_row['records_to_failure_gallery'])}",
            "",
            "## Decision",
            f"- Stage2Decision: {governance_summary_row['stage2_decision']}",
            f"- BlockingReasons: {governance_summary_row['blocking_reasons']}",
            f"- NextAllowedStage: {governance_summary_row['next_allowed_stage']}",
        ]
    ) + "\n"


def build_stage2_governance_summary_rows(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
    attack_breakdown_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    temporal_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    main_metric_rows = build_main_metrics_rows(event_score_records, threshold_records)
    clean_negative_fpr_controlled = bool(main_metric_rows) and all(
        float(row["clean_negative_FPR"] or 0.0) <= float(row.get("target_fpr", 1.0) or 1.0)
        for row in main_metric_rows
        if row.get("clean_negative_FPR") is not None
    )
    attacked_negative_fpr_reported = bool(attack_breakdown_rows) and all(
        row["attacked_negative_FPR"] is not None for row in attack_breakdown_rows
    )
    quality_table_non_empty = bool(quality_rows)
    temporal_table_non_empty = bool(temporal_rows)
    records_to_tables = bool(event_score_records) and bool(threshold_records)
    records_to_report = records_to_tables
    records_to_failure_gallery = bool(event_score_records)

    structural_failures: list[str] = []
    if not quality_table_non_empty:
        structural_failures.append("quality_table_empty")
    if not temporal_table_non_empty:
        structural_failures.append("temporal_table_empty")
    if not records_to_tables:
        structural_failures.append("records_to_tables_unavailable")
    if not records_to_report:
        structural_failures.append("records_to_report_unavailable")
    if not records_to_failure_gallery:
        structural_failures.append("records_to_failure_gallery_unavailable")

    if structural_failures:
        stage2_decision = "FAIL"
        blocking_reasons = structural_failures
    else:
        stage2_decision = "INCONCLUSIVE"
        blocking_reasons = [
            "video_vae_backend_placeholder",
            "real_video_runtime_not_enabled",
        ]
        if not clean_negative_fpr_controlled:
            blocking_reasons.append("clean_negative_fpr_not_controlled")
        if not attacked_negative_fpr_reported:
            blocking_reasons.append("attacked_negative_fpr_not_reported")

    first_record = event_score_records[0] if event_score_records else threshold_records[0] if threshold_records else {}
    construction_phase = str(
        first_record.get("construction_phase")
        or first_record.get("mechanism_trace", {}).get("construction_phase")
        or "real_video_vae_latent_probe"
    )
    run_id = str(first_record.get("run_id", ""))
    method_variants_summary = ", ".join(
        sorted({str(record["method_variant"]) for record in event_score_records})
    )
    attack_names_summary = ", ".join(
        sorted({str(record["attack_name"]) for record in event_score_records})
    )
    target_fprs_summary = ", ".join(
        str(value)
        for value in sorted({float(record["target_fpr"]) for record in event_score_records})
    )
    return [
        {
            "run_id": run_id,
            "construction_phase": construction_phase,
            "method_variants_summary": method_variants_summary,
            "attack_names_summary": attack_names_summary,
            "target_fprs_summary": target_fprs_summary,
            "event_record_count": len(event_score_records),
            "threshold_record_count": len(threshold_records),
            "clean_negative_fpr_controlled": clean_negative_fpr_controlled,
            "attacked_negative_fpr_reported": attacked_negative_fpr_reported,
            "quality_table_non_empty": quality_table_non_empty,
            "quality_metrics_runtime": "placeholder_tensor_video_metrics",
            "temporal_table_non_empty": temporal_table_non_empty,
            "temporal_metrics_runtime": "placeholder_tensor_video_metrics",
            "records_to_tables": records_to_tables,
            "records_to_report": records_to_report,
            "records_to_failure_gallery": records_to_failure_gallery,
            "stage2_decision": stage2_decision,
            "blocking_reasons": "; ".join(blocking_reasons),
            "next_allowed_stage": "remain_in_real_video_vae_latent_probe",
        }
    ]


def _rate_for_role(records: list[dict[str, Any]], sample_role: str) -> float | None:
    role_records = [record for record in records if record["sample_role"] == sample_role]
    if not role_records:
        return None
    return round(
        sum(1 for record in role_records if bool(record["decision"])) / len(role_records),
        6,
    )


def _rate_for_local_clip(records: list[dict[str, Any]]) -> float | None:
    local_clip_records = [
        record
        for record in records
        if record["attack_name"] == "local_clip"
        and record["sample_role"] == "attacked_positive"
    ]
    if not local_clip_records:
        return None
    return round(
        sum(1 for record in local_clip_records if bool(record["decision"])) / len(local_clip_records),
        6,
    )


def _derive_attack_strength(attack_params: dict[str, Any]) -> str:
    if "clip_length" in attack_params:
        return f"clip_{int(attack_params['clip_length']):02d}"
    if "crf" in attack_params:
        return f"crf_{int(attack_params['crf'])}"
    if "sigma" in attack_params:
        return f"sigma_{float(attack_params['sigma']):.3f}"
    if "scale" in attack_params:
        return f"scale_{float(attack_params['scale']):.2f}"
    if "crop_ratio" in attack_params:
        return f"crop_{float(attack_params['crop_ratio']):.2f}"
    if "speed_ratio" in attack_params:
        return f"speed_{float(attack_params['speed_ratio']):.2f}"
    return "default"


def _mean_mechanism_trace_value(records: list[dict[str, Any]], key: str) -> float | None:
    values = [
        float(record["mechanism_trace"][key])
        for record in records
        if isinstance(record.get("mechanism_trace", {}).get(key), (int, float))
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _median_mechanism_trace_value(records: list[dict[str, Any]], key: str) -> float | None:
    values = sorted(
        float(record["mechanism_trace"][key])
        for record in records
        if isinstance(record.get("mechanism_trace", {}).get(key), (int, float))
    )
    if not values:
        return None
    middle_index = len(values) // 2
    if len(values) % 2 == 1:
        return round(values[middle_index], 6)
    return round((values[middle_index - 1] + values[middle_index]) / 2.0, 6)


def _mean_payload_value(
    records: list[dict[str, Any]],
    payload_name: str,
    field_name: str,
) -> float | None:
    values = [
        float(record[payload_name][field_name])
        for record in records
        if isinstance(record.get(payload_name, {}).get(field_name), (int, float))
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _bool_to_report_value(value: Any) -> str:
    return str(bool(value)).lower()


def _draw_rect(
    pixels: bytearray,
    left: int,
    top: int,
    right: int,
    bottom: int,
    color: tuple[int, int, int],
) -> None:
    clamped_left = max(0, min(FIGURE_WIDTH, int(left)))
    clamped_right = max(0, min(FIGURE_WIDTH, int(right)))
    clamped_top = max(0, min(FIGURE_HEIGHT, int(top)))
    clamped_bottom = max(0, min(FIGURE_HEIGHT, int(bottom)))
    for y in range(clamped_top, clamped_bottom):
        for x in range(clamped_left, clamped_right):
            pixel_offset = ((y * FIGURE_WIDTH) + x) * 3
            pixels[pixel_offset : pixel_offset + 3] = bytes(color)


def _write_rgb_png(
    file_path: Path,
    width: int,
    height: int,
    pixels: bytearray,
) -> None:
    scanlines = bytearray()
    row_size = width * 3
    for row_index in range(height):
        scanlines.append(0)
        start = row_index * row_size
        scanlines.extend(pixels[start : start + row_size])
    file_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _build_png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
        )
        + _build_png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9))
        + _build_png_chunk(b"IEND", b"")
    )


def _build_png_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
    return (
        struct.pack(">I", len(chunk_data))
        + chunk_type
        + chunk_data
        + struct.pack(">I", binascii.crc32(chunk_type + chunk_data) & 0xFFFFFFFF)
    )
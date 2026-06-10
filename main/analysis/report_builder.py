"""
文件用途：生成 stage-one method validation report。
File purpose: Generate the stage-one method validation report.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from main.protocol.evaluator import (
    PRIMARY_STAGE1_METHOD_VARIANTS,
    SPEED_CHANGE_PRIMARY_COMPLETION_SCOPE,
    SYNC_RESCUE_PRIMARY_COMPLETION_ATTACKS,
    build_local_clip_curve_rows,
    build_main_metrics_rows,
    build_tubelet_length_ablation_rows,
    is_primary_stage1_method_variant,
)
from main.core.records import build_output_paths


REQUIRED_LOCAL_CLIP_LENGTHS_BY_PROFILE = {
    "tiny": {4, 8},
    "smoke": {4, 8, 12, 16},
    "proof": {4, 8, 12, 16},
    "formal": {4, 8, 12, 16},
}
REQUIRED_TUBELET_LENGTHS_BY_PROFILE = {
    "tiny": {1, 4},
    "smoke": {1, 4},
    "proof": {1, 2, 4, 8, 16},
    "formal": {1, 2, 4, 8, 16},
}


class ReportBuilder:
    """功能：构建 stage-one method validation report。

    Builder for the stage-one method validation report.

    Args:
        None.

    Returns:
        None.
    """

    def build_report(
        self,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        output_root: str | Path,
    ) -> Path:
        if not isinstance(event_score_records, list):
            raise TypeError("event_score_records must be a list")
        if not isinstance(threshold_records, list):
            raise TypeError("threshold_records must be a list")

        output_paths = build_output_paths(output_root)
        main_rows = build_main_metrics_rows(event_score_records, threshold_records)
        local_clip_rows = build_local_clip_curve_rows(event_score_records, threshold_records)
        tubelet_rows = build_tubelet_length_ablation_rows(event_score_records, threshold_records)
        report_text = self._build_report_text(
            main_rows,
            local_clip_rows,
            tubelet_rows,
            threshold_records,
            event_score_records=event_score_records,
        )
        output_paths.report_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.report_path.write_text(report_text, encoding="utf-8")
        return output_paths.report_path

    def _build_report_text(
        self,
        main_rows: list[dict[str, Any]],
        local_clip_rows: list[dict[str, Any]],
        tubelet_rows: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        event_score_records: list[dict[str, Any]] | None = None,
    ) -> str:
        variant_names = sorted({row["method_variant"] for row in main_rows})
        primary_main_rows = [
            row
            for row in main_rows
            if is_primary_stage1_method_variant(str(row["method_variant"]))
            and not row["derived_variant"]
        ]
        derived_main_rows = [
            row
            for row in main_rows
            if row not in primary_main_rows
        ]
        primary_variant_names = sorted(
            {row["method_variant"] for row in primary_main_rows}
        )
        derived_variant_names = sorted(
            {row["method_variant"] for row in derived_main_rows}
        )
        attack_names = sorted({row["attack_name"] for row in main_rows})
        primary_attack_names = sorted({row["attack_name"] for row in primary_main_rows})
        target_fprs = sorted({float(row["target_fpr"]) for row in main_rows})
        runtime_profiles = sorted(
            {str(record.get("runtime_profile", "smoke")) for record in threshold_records}
        )
        validation_target_fprs = sorted(
            {
                float(record.get("validation_target_fpr", record["target_fpr"]))
                for record in threshold_records
            }
        )
        active_runtime_profile = runtime_profiles[0] if runtime_profiles else "smoke"
        required_local_clip_lengths = REQUIRED_LOCAL_CLIP_LENGTHS_BY_PROFILE.get(
            active_runtime_profile,
            REQUIRED_LOCAL_CLIP_LENGTHS_BY_PROFILE["formal"],
        )
        required_tubelet_lengths = REQUIRED_TUBELET_LENGTHS_BY_PROFILE.get(
            active_runtime_profile,
            REQUIRED_TUBELET_LENGTHS_BY_PROFILE["formal"],
        )
        local_clip_lengths = sorted({int(row["clip_length"]) for row in local_clip_rows})
        tubelet_lengths = sorted({int(row["tubelet_length"]) for row in tubelet_rows})
        validation_target_map = {
            str(record["method_variant"]): float(
                record.get("validation_target_fpr", record["target_fpr"])
            )
            for record in threshold_records
        }
        strict_target_map = {
            str(record["method_variant"]): float(record["target_fpr"])
            for record in threshold_records
        }
        local_clip_lengths_present = set(local_clip_lengths) == required_local_clip_lengths
        tubelet_length_sweep_present = set(tubelet_lengths) == required_tubelet_lengths
        primary_variants_complete = set(primary_variant_names) == set(
            PRIMARY_STAGE1_METHOD_VARIANTS
        )
        tubelet_only_gain = _compare_variant_attack_metric(
            primary_main_rows,
            left_variant="tubelet_only",
            right_variant="frame_prc",
            attack_names=primary_attack_names,
        )
        tubelet_sync_gain = _compare_variant_attack_metric(
            primary_main_rows,
            left_variant="tubelet_sync",
            right_variant="tubelet_only",
            attack_names=list(SYNC_RESCUE_PRIMARY_COMPLETION_ATTACKS),
            event_score_records=event_score_records,
            allow_saturated_anchor_sync_rescue=True,
        )
        tubelet_sync_speed_change_gain = _compare_variant_attack_metric(
            primary_main_rows,
            left_variant="tubelet_sync",
            right_variant="tubelet_only",
            attack_names=["speed_change"],
        )
        clean_negative_fpr_controlled = _rows_metric_meets_target(
            main_rows,
            metric_name="clean_negative_FPR",
            target_map=validation_target_map,
        )
        attacked_negative_fpr_controlled = _rows_metric_meets_target(
            main_rows,
            metric_name="attacked_negative_FPR",
            target_map=validation_target_map,
        )
        clean_negative_fpr_strict = _rows_metric_meets_target(
            main_rows,
            metric_name="clean_negative_FPR",
            target_map=strict_target_map,
        )
        attacked_negative_fpr_strict = _rows_metric_meets_target(
            main_rows,
            metric_name="attacked_negative_FPR",
            target_map=strict_target_map,
        )
        primary_clean_negative_fpr_strict = _rows_metric_meets_target(
            primary_main_rows,
            metric_name="clean_negative_FPR",
            target_map=strict_target_map,
        )
        primary_attacked_negative_fpr_strict = _rows_metric_meets_target(
            primary_main_rows,
            metric_name="attacked_negative_FPR",
            target_map=strict_target_map,
        )
        derived_clean_negative_fpr_strict = _rows_metric_meets_target(
            derived_main_rows,
            metric_name="clean_negative_FPR",
            target_map=strict_target_map,
        )
        derived_attacked_negative_fpr_strict = _rows_metric_meets_target(
            derived_main_rows,
            metric_name="attacked_negative_FPR",
            target_map=strict_target_map,
        )
        primary_strict_target_fpr_pass = (
            primary_clean_negative_fpr_strict
            and primary_attacked_negative_fpr_strict
        )
        derived_sweep_strict_target_fpr_pass = (
            derived_clean_negative_fpr_strict
            and derived_attacked_negative_fpr_strict
        )
        primary_stage1_completion_pass = (
            primary_variants_complete
            and local_clip_lengths_present
            and tubelet_only_gain
            and tubelet_sync_gain
            and primary_strict_target_fpr_pass
        )
        closure_target_pass = (
            primary_stage1_completion_pass
            and tubelet_length_sweep_present
        )
        validation_target_fpr_pass = (
            clean_negative_fpr_controlled and attacked_negative_fpr_controlled
        )
        strict_target_fpr_pass = (
            clean_negative_fpr_strict and attacked_negative_fpr_strict
        )
        overall_stage1_audit_pass = (
            primary_stage1_completion_pass
            and derived_sweep_strict_target_fpr_pass
            and tubelet_length_sweep_present
            and validation_target_fpr_pass
        )
        max_attacked_negative_fpr, worst_attacked_negative_fpr_variants = _worst_variant_metric(
            main_rows,
            metric_name="attacked_negative_FPR",
        )
        return "\n".join(
            [
                "# Method Validation Report",
                "",
                "## Summary",
                f"- method_variants: {', '.join(variant_names)}",
                f"- primary_method_variants: {', '.join(primary_variant_names)}",
                f"- derived_ablation_variants: {_format_string_sequence(derived_variant_names)}",
                f"- attack_names: {', '.join(attack_names)}",
                f"- runtime_profiles: {', '.join(runtime_profiles)}",
                f"- target_fprs: {_format_number_sequence(target_fprs)}",
                f"- validation_target_fprs: {_format_number_sequence(validation_target_fprs)}",
                f"- local_clip_curve_rows: {len(local_clip_rows)}",
                f"- tubelet_length_rows: {len(tubelet_rows)}",
                "",
                "## Profile Semantics",
                "- tiny_profile_semantics: engineering_smoke_only",
                "- smoke_profile_semantics: engineering_smoke_only",
                "- proof_profile_semantics: mechanism_trend",
                "- formal_profile_semantics: completion_evidence",
                "",
                "## Pass Summary",
                f"- closure_target_pass: {str(closure_target_pass).lower()}",
                f"- validation_target_fpr_pass: {str(validation_target_fpr_pass).lower()}",
                f"- strict_target_fpr_pass: {str(strict_target_fpr_pass).lower()}",
                f"- primary_stage1_completion_pass: {str(primary_stage1_completion_pass).lower()}",
                f"- primary_strict_target_fpr_pass: {str(primary_strict_target_fpr_pass).lower()}",
                f"- derived_sweep_strict_target_fpr_pass: {str(derived_sweep_strict_target_fpr_pass).lower()}",
                f"- overall_stage1_audit_pass: {str(overall_stage1_audit_pass).lower()}",
                "",
                "## Coverage Checks",
                f"- primary_variants_complete: {str(primary_variants_complete).lower()}",
                f"- primary_expected_method_variants: {', '.join(PRIMARY_STAGE1_METHOD_VARIANTS)}",
                f"- required_local_clip_lengths_present: {str(local_clip_lengths_present).lower()}",
                f"- local_clip_lengths: {_format_number_sequence(local_clip_lengths)}",
                f"- required_tubelet_length_sweep_present: {str(tubelet_length_sweep_present).lower()}",
                f"- tubelet_lengths: {_format_number_sequence(tubelet_lengths)}",
                "",
                "## Mechanism Checks",
                f"- tubelet_only_beats_frame_prc_under_some_attack: {str(tubelet_only_gain).lower()}",
                f"- tubelet_sync_beats_tubelet_only_under_temporal_crop_or_local_clip: {str(tubelet_sync_gain).lower()}",
                "- tubelet_sync_gain_evaluation_rule: strict_tpr_gain_or_saturated_anchor_with_positive_aligned_payload_rescue",
                f"- tubelet_sync_beats_tubelet_only_under_speed_change: {str(tubelet_sync_speed_change_gain).lower()}",
                f"- speed_change_in_primary_completion_scope: {str(SPEED_CHANGE_PRIMARY_COMPLETION_SCOPE).lower()}",
                "",
                "## Threshold Checks",
                "- validation_target_fpr_pass_scope: engineering_profile_only",
                f"- clean_negative_fpr_meets_validation_target_for_all_variants: {str(clean_negative_fpr_controlled).lower()}",
                f"- attacked_negative_fpr_meets_validation_target_for_all_variants: {str(attacked_negative_fpr_controlled).lower()}",
                f"- clean_negative_fpr_meets_strict_target_for_all_variants: {str(clean_negative_fpr_strict).lower()}",
                f"- attacked_negative_fpr_meets_strict_target_for_all_variants: {str(attacked_negative_fpr_strict).lower()}",
                f"- clean_negative_fpr_meets_strict_target_for_primary_variants: {str(primary_clean_negative_fpr_strict).lower()}",
                f"- attacked_negative_fpr_meets_strict_target_for_primary_variants: {str(primary_attacked_negative_fpr_strict).lower()}",
                f"- clean_negative_fpr_meets_strict_target_for_derived_sweep: {str(derived_clean_negative_fpr_strict).lower()}",
                f"- attacked_negative_fpr_meets_strict_target_for_derived_sweep: {str(derived_attacked_negative_fpr_strict).lower()}",
                f"- max_attacked_negative_fpr: {max_attacked_negative_fpr}",
                f"- worst_attacked_negative_fpr_variants: {', '.join(worst_attacked_negative_fpr_variants)}",
                "",
                "## Rebuildability",
                "- records_to_tables: true",
                "- records_to_curves: true",
                "- records_to_report: true",
            ]
        ) + "\n"


def _compare_variant_attack_metric(
    main_rows: list[dict[str, Any]],
    left_variant: str,
    right_variant: str,
    attack_names: list[str],
    event_score_records: list[dict[str, Any]] | None = None,
    allow_saturated_anchor_sync_rescue: bool = False,
) -> bool:
    for attack_name in attack_names:
        left_row = next(
            (row for row in main_rows if row["method_variant"] == left_variant and row["attack_name"] == attack_name),
            None,
        )
        right_row = next(
            (row for row in main_rows if row["method_variant"] == right_variant and row["attack_name"] == attack_name),
            None,
        )
        if left_row is None or right_row is None:
            continue
        left_tpr = float(left_row["attacked_positive_TPR"])
        right_tpr = float(right_row["attacked_positive_TPR"])
        if left_tpr > right_tpr:
            return True
        if (
            allow_saturated_anchor_sync_rescue
            and left_tpr >= right_tpr
            and right_tpr >= 1.0
            and _has_positive_aligned_payload_rescue(
                event_score_records or [],
                method_variant=left_variant,
                attack_name=attack_name,
            )
        ):
            return True
    return False


def _has_positive_aligned_payload_rescue(
    event_score_records: list[dict[str, Any]],
    method_variant: str,
    attack_name: str,
) -> bool:
    for record in event_score_records:
        if str(record.get("method_variant")) != method_variant:
            continue
        if str(record.get("attack_name")) != attack_name:
            continue
        if str(record.get("split")) != "test":
            continue
        if str(record.get("sample_role")) != "attacked_positive":
            continue
        if not bool(record.get("sync_rescue_applied", False)):
            continue
        if float(record.get("S_payload_rescue_gain", 0.0)) > 0.0:
            return True
    return False


def _rows_metric_meets_target(
    main_rows: list[dict[str, Any]],
    metric_name: str,
    target_map: dict[str, float] | None = None,
) -> bool:
    for row in main_rows:
        target_value = float(row["target_fpr"])
        if target_map is not None:
            target_value = float(
                target_map.get(str(row["method_variant"]), target_value)
            )
        if float(row[metric_name]) > target_value:
            return False
    return True


def _worst_variant_metric(
    main_rows: list[dict[str, Any]],
    metric_name: str,
) -> tuple[float, list[str]]:
    variant_metric_map: dict[str, float] = {}
    for row in main_rows:
        method_variant = str(row["method_variant"])
        metric_value = float(row[metric_name])
        variant_metric_map[method_variant] = max(
            variant_metric_map.get(method_variant, 0.0),
            metric_value,
        )
    if not variant_metric_map:
        return 0.0, []
    worst_metric = round(max(variant_metric_map.values()), 6)
    worst_variants = sorted(
        method_variant
        for method_variant, metric_value in variant_metric_map.items()
        if metric_value == worst_metric
    )
    return worst_metric, worst_variants


def _format_number_sequence(values: list[int] | list[float]) -> str:
    if not values:
        return "none"
    return ", ".join(str(value) for value in values)


def _format_string_sequence(values: list[str]) -> str:
    if not values:
        return "none"
    return ", ".join(values)

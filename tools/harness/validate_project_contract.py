"""
文件用途：提供项目契约与阈值协议配置的校验逻辑。
File purpose: Provide reusable validators for the project contract and threshold protocol skeleton.
Module type: General module
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from main.attacks.temporal import (
    ATTACK_MATRIX_NAME as TEMPORAL_ATTACK_MATRIX_NAME,
    SUPPORTED_TEMPORAL_ATTACK_NAMES,
)
from main.backends.synthetic_video_latent import (
    DEFAULT_LATENT_GENERATION_SEED,
    DEFAULT_LATENT_SHAPE,
    DEFAULT_RUNTIME_PROFILE,
    FORMAL_LATENT_SHAPE,
    PROOF_LATENT_SHAPE,
    TINY_LATENT_SHAPE,
    LATENT_BACKEND_NAME as SYNTHETIC_VIDEO_LATENT_BACKEND_NAME,
    LATENT_DISTRIBUTION as SYNTHETIC_VIDEO_LATENT_DISTRIBUTION,
    LATENT_STORAGE as SYNTHETIC_VIDEO_LATENT_STORAGE,
)
from main.methods.temporal_tubelet_watermark.synthetic_tubelet_sync_contract import (
    METHOD_FAMILY as SYNTHETIC_TUBELET_SYNC_METHOD_FAMILY,
    METHOD_STATUS as SYNTHETIC_TUBELET_SYNC_METHOD_STATUS,
    SUPPORTED_METHOD_VARIANTS as SYNTHETIC_TUBELET_SYNC_METHOD_VARIANTS,
    TARGET_CONSTRUCTION_PHASE as SYNTHETIC_TUBELET_SYNC_TARGET_PHASE,
    build_reserved_method_support_matrix,
)


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SAMPLE_ROLES = {
    "clean_negative",
    "attacked_negative",
    "watermarked_positive",
    "attacked_positive",
}
REQUIRED_SPLITS = {"dev", "calibration", "test"}
REQUIRED_METHOD_OBJECTS = {
    "temporal_synchronized_tubelet_code",
    "flow_matching_trajectory_statistic",
    "fixed_low_fpr_calibrated_detector",
}
REQUIRED_EVIDENCE_NAMES = {
    "tubelet_evidence",
    "sync_evidence",
    "trajectory_evidence",
    "final_evidence",
}
REQUIRED_PROTOCOL_RUNTIME_OBJECTS = {
    "latent_backend",
    "watermark_method",
    "evidence_extractor",
    "protocol_runner",
    "threshold_calibrator",
    "record_writer",
    "ablation_runner",
    "table_builder",
    "manifest_builder",
}
REQUIRED_SUPPORTED_METHOD_VARIANTS = set(SYNTHETIC_TUBELET_SYNC_METHOD_VARIANTS)
REQUIRED_GOVERNANCE_LAYER_PATHS = {
    "tools/harness",
    ".codex",
    "tests",
}
REQUIRED_PROTOCOL_CORE_CANDIDATE_PATHS = {
    "main/core",
    "main/protocol",
    "main/analysis",
}
REQUIRED_METHOD_CORE_CANDIDATE_PATHS = {"main/methods"}
REQUIRED_FORBIDDEN_RUNTIME_IMPORTS = {"tools.harness", "tests"}
REQUIRED_MINIMAL_DEMO_EXCLUDED_PATHS = {
    "tools/harness",
    ".codex",
    "docs/builds",
    "audit_reports",
    "tests",
}
REQUIRED_OUTPUT_LAYOUT = {
    "event_scores_path": "records/event_scores.jsonl",
    "thresholds_path": "thresholds/thresholds.json",
    "run_manifest_path": "artifacts/run_manifest.json",
    "main_metrics_path": "tables/main_tpr_fpr_table.csv",
    "ablation_table_path": "tables/ablation_table.csv",
    "local_clip_curve_path": "tables/local_clip_curve.csv",
    "temporal_attack_curve_path": "tables/temporal_attack_curve.csv",
    "tubelet_length_ablation_path": "tables/tubelet_length_ablation.csv",
    "sync_peak_examples_path": "figures/sync_peak_examples.png",
    "report_path": "reports/method_validation_report.md",
}
REQUIRED_EVENT_SCORE_FIELDS = {
    "run_id",
    "event_id",
    "sample_id",
    "split",
    "sample_role",
    "method_family",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "attack_name",
    "attack_params",
    "target_fpr",
    "threshold_id",
    "input_artifact_trace",
    "latent_backend_name",
    "latent_backend_status",
    "latent_tensor_digest_random",
    "latent_generation_seed_random",
    "evidence_scores",
    "disabled_evidence",
    "decision",
    "failure_reason",
    "mechanism_trace",
    "placeholder_fields",
    "random_fields",
}
REQUIRED_MECHANISM_TRACE_FIELDS = {
    "construction_phase",
    "latent_backend_name",
    "reference_latent_shape",
    "latent_shape",
    "latent_artifact_relpath",
    "latent_artifact_digest",
    "tubelet_length",
    "spatial_patch_size",
    "partition_digest",
    "embedding_rule",
    "embedding_margin",
    "mean_projection_before",
    "mean_projection_after",
    "mean_embedding_delta_norm",
    "codebook_digest",
    "sync_code_digest",
    "payload_digest",
    "sync_search_enabled",
    "sync_estimated_offset",
    "sync_ground_truth_offset",
    "sync_alignment_error",
    "sync_peak_rank",
    "sync_search_space_size",
    "sync_search_space_digest",
    "clip_length",
}
REQUIRED_EVENT_SCORE_EVIDENCE_FIELDS = {
    "S_tubelet",
    "S_sync",
    "S_traj",
    "S_final",
}
REQUIRED_INPUT_ARTIFACT_TRACE_FIELDS = {
    "artifact_kind",
    "backend_name",
    "backend_status",
    "artifact_digest",
    "generation_seed_random",
}
REQUIRED_EVENT_SCORE_NULL_ENCODING_FIELDS = {
    "threshold_id",
    "failure_reason",
    "S_tubelet",
    "S_sync",
    "S_traj",
}
REQUIRED_THRESHOLD_RECORD_FIELDS = {
    "threshold_id",
    "run_id",
    "method_family",
    "method_variant",
    "score_name",
    "target_fpr",
    "calibration_split",
    "calibration_negative_roles",
    "threshold_value",
    "threshold_quantile",
    "num_calibration_negatives",
    "threshold_source_record_digest",
    "fusion_rule",
    "created_at",
}
REQUIRED_MANIFEST_FIELDS = {
    "run_id",
    "created_at",
    "construction_phase",
    "protocol_name",
    "method_config_digest",
    "protocol_config_digest",
    "attack_matrix_digest",
    "ablation_config_digest",
    "records_digest",
    "thresholds_digest",
    "tables_digest",
    "figures_digest",
    "placeholder_fields",
    "random_fields",
}
REQUIRED_MAIN_METRICS_COLUMNS = {
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
    "attacked_positive_TPR",
}
REQUIRED_ABLATION_TABLE_COLUMNS = {
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
    "attacked_positive_TPR",
}
REQUIRED_LOCAL_CLIP_CURVE_COLUMNS = {
    "run_id",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "clip_length",
    "local_clip_TPR",
    "local_clip_FPR",
    "positive_count",
    "negative_count",
    "threshold_id",
}
REQUIRED_TEMPORAL_ATTACK_CURVE_COLUMNS = {
    "run_id",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "attack_name",
    "attack_strength",
    "sample_role",
    "TPR",
    "FPR",
    "count",
    "threshold_id",
}
REQUIRED_TUBELET_LENGTH_ABLATION_COLUMNS = {
    "run_id",
    "method_variant",
    "base_method_variant",
    "derived_variant",
    "ablation_axis",
    "tubelet_length",
    "attack_name",
    "attacked_positive_TPR",
    "attacked_negative_FPR",
    "sync_alignment_error_mean",
    "sync_peak_rank_median",
}
REQUIRED_ABLATION_METHOD_VARIANTS = {
    "empty_watermark_method_placeholder",
    "random_score_detector_random",
}
REQUIRED_ATTACK_PLACEHOLDER_FIELDS = {
    "attack_name_placeholder",
    "attack_params_placeholder",
}
REQUIRED_STAGE_ONE_OUTPUT_TABLES = {
    "main_tpr_fpr_table.csv",
    "ablation_table.csv",
    "local_clip_curve.csv",
    "temporal_attack_curve.csv",
    "tubelet_length_ablation.csv",
}


def load_json_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON configuration file using only the Python standard library.

    Args:
        path: Target JSON configuration file path.

    Returns:
        Parsed dictionary content.

    Raises:
        FileNotFoundError: Raised when the file does not exist.
        json.JSONDecodeError: Raised when the file is not valid JSON.
    """
    file_path = Path(path)
    return json.loads(file_path.read_text(encoding="utf-8"))


def validate_project_contract_data(data: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the `project_contract.json` data structure.

    Args:
        data: Parsed project contract data.

    Returns:
        A list of contract validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "project_stage",
                "reason": "project_stage_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("construction_phase") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "construction_phase",
                "reason": "construction_phase_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if not REQUIRED_SAMPLE_ROLES.issubset(set(data.get("sample_roles", []))):
        violations.append(
            {
                "field": "sample_roles",
                "reason": "missing_required_sample_roles",
            }
        )

    if not REQUIRED_SPLITS.issubset(set(data.get("splits", []))):
        violations.append(
            {
                "field": "splits",
                "reason": "missing_required_splits",
            }
        )

    if not REQUIRED_METHOD_OBJECTS.issubset(set(data.get("method_objects", []))):
        violations.append(
            {
                "field": "method_objects",
                "reason": "missing_required_method_objects",
            }
        )

    if not REQUIRED_EVIDENCE_NAMES.issubset(set(data.get("evidence_names", []))):
        violations.append(
            {
                "field": "evidence_names",
                "reason": "missing_required_evidence_names",
            }
        )

    if not REQUIRED_PROTOCOL_RUNTIME_OBJECTS.issubset(
        set(data.get("protocol_runtime_objects", []))
    ):
        violations.append(
            {
                "field": "protocol_runtime_objects",
                "reason": "missing_required_protocol_runtime_objects",
            }
        )

    if not REQUIRED_SUPPORTED_METHOD_VARIANTS.issubset(
        set(data.get("supported_method_variants", []))
    ):
        violations.append(
            {
                "field": "supported_method_variants",
                "reason": "missing_required_supported_method_variants",
            }
        )

    core_boundary_policy = data.get("core_boundary_policy")
    if not isinstance(core_boundary_policy, dict):
        violations.append(
            {
                "field": "core_boundary_policy",
                "reason": "missing_core_boundary_policy",
            }
        )
        return violations

    if not REQUIRED_GOVERNANCE_LAYER_PATHS.issubset(
        set(core_boundary_policy.get("governance_layer_paths", []))
    ):
        violations.append(
            {
                "field": "core_boundary_policy.governance_layer_paths",
                "reason": "missing_required_governance_layer_paths",
            }
        )

    if not REQUIRED_PROTOCOL_CORE_CANDIDATE_PATHS.issubset(
        set(core_boundary_policy.get("protocol_core_candidate_paths", []))
    ):
        violations.append(
            {
                "field": "core_boundary_policy.protocol_core_candidate_paths",
                "reason": "missing_required_protocol_core_candidate_paths",
            }
        )

    if not REQUIRED_METHOD_CORE_CANDIDATE_PATHS.issubset(
        set(core_boundary_policy.get("method_core_candidate_paths", []))
    ):
        violations.append(
            {
                "field": "core_boundary_policy.method_core_candidate_paths",
                "reason": "missing_required_method_core_candidate_paths",
            }
        )

    if not REQUIRED_FORBIDDEN_RUNTIME_IMPORTS.issubset(
        set(core_boundary_policy.get("forbidden_runtime_imports", []))
    ):
        violations.append(
            {
                "field": "core_boundary_policy.forbidden_runtime_imports",
                "reason": "missing_required_forbidden_runtime_imports",
            }
        )

    if not REQUIRED_MINIMAL_DEMO_EXCLUDED_PATHS.issubset(
        set(core_boundary_policy.get("minimal_demo_excluded_paths", []))
    ):
        violations.append(
            {
                "field": "core_boundary_policy.minimal_demo_excluded_paths",
                "reason": "missing_required_minimal_demo_excluded_paths",
            }
        )

    return violations


def validate_protocol_config_data(data: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the `protocol_skeleton.json` threshold protocol fields.

    Args:
        data: Parsed protocol skeleton data.

    Returns:
        A list of threshold protocol validation violations.
    """
    violations: list[dict[str, str]] = []
    threshold_protocol = data.get("threshold_protocol", {})

    if threshold_protocol.get("calibration_split") != "calibration":
        violations.append(
            {
                "field": "threshold_protocol.calibration_split",
                "reason": "calibration_split_must_equal_calibration",
            }
        )

    if data.get("construction_phase") != "protocol_skeleton":
        violations.append(
            {
                "field": "construction_phase",
                "reason": "construction_phase_must_equal_protocol_skeleton",
            }
        )

    if data.get("protocol_name") != "fixed_low_fpr_calibrated_detection":
        violations.append(
            {
                "field": "protocol_name",
                "reason": "protocol_name_must_equal_fixed_low_fpr_calibrated_detection",
            }
        )

    calibration_negative_roles = set(
        threshold_protocol.get("calibration_negative_roles", [])
    )
    if not {"clean_negative", "attacked_negative"}.issubset(
        calibration_negative_roles
    ):
        violations.append(
            {
                "field": "threshold_protocol.calibration_negative_roles",
                "reason": "missing_required_calibration_negative_roles",
            }
        )

    if threshold_protocol.get("test_threshold_update_allowed") is not False:
        violations.append(
            {
                "field": "threshold_protocol.test_threshold_update_allowed",
                "reason": "test_threshold_updates_must_be_disabled",
            }
        )

    if threshold_protocol.get("score_name") != "S_final":
        violations.append(
            {
                "field": "threshold_protocol.score_name",
                "reason": "score_name_must_equal_s_final",
            }
        )

    if threshold_protocol.get("threshold_quantile_rule") != "upper_tail":
        violations.append(
            {
                "field": "threshold_protocol.threshold_quantile_rule",
                "reason": "threshold_quantile_rule_must_equal_upper_tail",
            }
        )

    if threshold_protocol.get("allow_attack_specific_threshold") is not False:
        violations.append(
            {
                "field": "threshold_protocol.allow_attack_specific_threshold",
                "reason": "attack_specific_thresholds_must_be_disabled",
            }
        )

    return violations


def validate_protocol_artifact_schema_data(data: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the governed stage-one protocol artifact schema.

    Args:
        data: Parsed protocol artifact schema config data.

    Returns:
        A list of protocol artifact schema validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != "synthetic_tubelet_sync_probe":
        violations.append(
            {
                "field": "project_stage",
                "reason": "artifact_schema_stage_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("construction_phase") != "synthetic_tubelet_sync_probe":
        violations.append(
            {
                "field": "construction_phase",
                "reason": "construction_phase_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("protocol_name") != "fixed_low_fpr_calibrated_detection":
        violations.append(
            {
                "field": "protocol_name",
                "reason": "protocol_name_must_equal_fixed_low_fpr_calibrated_detection",
            }
        )

    if data.get("record_schema_name") != "event_score_record":
        violations.append(
            {
                "field": "record_schema_name",
                "reason": "record_schema_name_must_equal_event_score_record",
            }
        )

    if data.get("threshold_schema_name") != "threshold_record":
        violations.append(
            {
                "field": "threshold_schema_name",
                "reason": "threshold_schema_name_must_equal_threshold_record",
            }
        )

    if data.get("manifest_schema_name") != "run_manifest_record":
        violations.append(
            {
                "field": "manifest_schema_name",
                "reason": "manifest_schema_name_must_equal_run_manifest_record",
            }
        )

    output_layout = data.get("output_layout", {})
    for field_name, expected_value in REQUIRED_OUTPUT_LAYOUT.items():
        if output_layout.get(field_name) != expected_value:
            violations.append(
                {
                    "field": f"output_layout.{field_name}",
                    "reason": "unexpected_protocol_artifact_output_path",
                }
            )

    event_score_record = data.get("event_score_record", {})
    if not REQUIRED_EVENT_SCORE_FIELDS.issubset(
        set(event_score_record.get("required_top_level_fields", []))
    ):
        violations.append(
            {
                "field": "event_score_record.required_top_level_fields",
                "reason": "missing_required_event_score_fields",
            }
        )

    if not REQUIRED_EVENT_SCORE_EVIDENCE_FIELDS.issubset(
        set(event_score_record.get("required_evidence_score_fields", []))
    ):
        violations.append(
            {
                "field": "event_score_record.required_evidence_score_fields",
                "reason": "missing_required_evidence_score_fields",
            }
        )

    if not REQUIRED_INPUT_ARTIFACT_TRACE_FIELDS.issubset(
        set(event_score_record.get("required_input_artifact_trace_fields", []))
    ):
        violations.append(
            {
                "field": "event_score_record.required_input_artifact_trace_fields",
                "reason": "missing_required_input_artifact_trace_fields",
            }
        )

    if not REQUIRED_MECHANISM_TRACE_FIELDS.issubset(
        set(event_score_record.get("required_mechanism_trace_fields", []))
    ):
        violations.append(
            {
                "field": "event_score_record.required_mechanism_trace_fields",
                "reason": "missing_required_mechanism_trace_fields",
            }
        )

    if not REQUIRED_EVENT_SCORE_NULL_ENCODING_FIELDS.issubset(
        set(event_score_record.get("required_null_encoding_fields", []))
    ):
        violations.append(
            {
                "field": "event_score_record.required_null_encoding_fields",
                "reason": "missing_required_null_encoding_fields",
            }
        )

    threshold_record = data.get("threshold_record", {})
    if not REQUIRED_THRESHOLD_RECORD_FIELDS.issubset(
        set(threshold_record.get("required_fields", []))
    ):
        violations.append(
            {
                "field": "threshold_record.required_fields",
                "reason": "missing_required_threshold_record_fields",
            }
        )

    run_manifest_record = data.get("run_manifest_record", {})
    if not REQUIRED_MANIFEST_FIELDS.issubset(
        set(run_manifest_record.get("required_fields", []))
    ):
        violations.append(
            {
                "field": "run_manifest_record.required_fields",
                "reason": "missing_required_run_manifest_fields",
            }
        )

    tables = data.get("tables", {})
    if not REQUIRED_MAIN_METRICS_COLUMNS.issubset(
        set(tables.get("main_metrics_columns", []))
    ):
        violations.append(
            {
                "field": "tables.main_metrics_columns",
                "reason": "missing_required_main_metrics_columns",
            }
        )

    if not REQUIRED_ABLATION_TABLE_COLUMNS.issubset(
        set(tables.get("ablation_table_columns", []))
    ):
        violations.append(
            {
                "field": "tables.ablation_table_columns",
                "reason": "missing_required_ablation_table_columns",
            }
        )

    if not REQUIRED_LOCAL_CLIP_CURVE_COLUMNS.issubset(
        set(tables.get("local_clip_curve_columns", []))
    ):
        violations.append(
            {
                "field": "tables.local_clip_curve_columns",
                "reason": "missing_required_local_clip_curve_columns",
            }
        )

    if not REQUIRED_TEMPORAL_ATTACK_CURVE_COLUMNS.issubset(
        set(tables.get("temporal_attack_curve_columns", []))
    ):
        violations.append(
            {
                "field": "tables.temporal_attack_curve_columns",
                "reason": "missing_required_temporal_attack_curve_columns",
            }
        )

    if not REQUIRED_TUBELET_LENGTH_ABLATION_COLUMNS.issubset(
        set(tables.get("tubelet_length_ablation_columns", []))
    ):
        violations.append(
            {
                "field": "tables.tubelet_length_ablation_columns",
                "reason": "missing_required_tubelet_length_ablation_columns",
            }
        )

    return violations


def validate_ablation_placeholder_data(data: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the governed protocol skeleton runtime ablation placeholder config.

    Args:
        data: Parsed ablation placeholder config data.

    Returns:
        A list of ablation placeholder validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != "protocol_skeleton":
        violations.append(
            {
                "field": "project_stage",
                "reason": "ablation_config_stage_must_equal_protocol_skeleton",
            }
        )

    if data.get("construction_phase") != "protocol_skeleton":
        violations.append(
            {
                "field": "construction_phase",
                "reason": "construction_phase_must_equal_protocol_skeleton",
            }
        )

    if data.get("shared_protocol_required") is not True:
        violations.append(
            {
                "field": "shared_protocol_required",
                "reason": "shared_protocol_must_be_required",
            }
        )

    if data.get("shared_attack_matrix_required") is not True:
        violations.append(
            {
                "field": "shared_attack_matrix_required",
                "reason": "shared_attack_matrix_must_be_required",
            }
        )

    variants = data.get("supported_method_variants", [])
    if not REQUIRED_ABLATION_METHOD_VARIANTS.issubset(set(variants)):
        violations.append(
            {
                "field": "supported_method_variants",
                "reason": "missing_required_supported_method_variants",
            }
        )

    if data.get("shared_target_fpr_placeholder") != 0.001:
        violations.append(
            {
                "field": "shared_target_fpr_placeholder",
                "reason": "shared_target_fpr_placeholder_must_equal_point_zero_zero_one",
            }
        )

    if (
        data.get("shared_table_builder_placeholder")
        != "protocol_table_builder_placeholder"
    ):
        violations.append(
            {
                "field": "shared_table_builder_placeholder",
                "reason": "unexpected_shared_table_builder_placeholder",
            }
        )

    return violations


def validate_attack_placeholder_data(data: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the governed protocol skeleton runtime attack placeholder config.

    Args:
        data: Parsed attack placeholder config data.

    Returns:
        A list of attack placeholder validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != "protocol_skeleton":
        violations.append(
            {
                "field": "project_stage",
                "reason": "attack_config_stage_must_equal_protocol_skeleton",
            }
        )

    if data.get("shared_attack_matrix_required") is not True:
        violations.append(
            {
                "field": "shared_attack_matrix_required",
                "reason": "attack_matrix_must_be_shared",
            }
        )

    attack_matrix = data.get("attack_matrix_placeholder", [])
    if not attack_matrix:
        violations.append(
            {
                "field": "attack_matrix_placeholder",
                "reason": "missing_attack_matrix_placeholder_entries",
            }
        )
        return violations

    first_entry = attack_matrix[0]
    if not REQUIRED_ATTACK_PLACEHOLDER_FIELDS.issubset(set(first_entry.keys())):
        violations.append(
            {
                "field": "attack_matrix_placeholder",
                "reason": "missing_required_attack_placeholder_fields",
            }
        )

    if first_entry.get("attack_name_placeholder") != "identity_attack_placeholder":
        violations.append(
            {
                "field": "attack_matrix_placeholder.attack_name_placeholder",
                "reason": "attack_name_placeholder_must_equal_identity_attack_placeholder",
            }
        )

    if not isinstance(first_entry.get("attack_params_placeholder"), dict):
        violations.append(
            {
                "field": "attack_matrix_placeholder.attack_params_placeholder",
                "reason": "attack_params_placeholder_must_be_object",
            }
        )

    return violations


def validate_synthetic_tubelet_sync_protocol_support_data(
    data: dict[str, Any],
) -> list[dict[str, str]]:
    """Validate the reserved protocol config for the synthetic tubelet sync probe.

    Args:
        data: Parsed protocol support config.

    Returns:
        A list of validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "project_stage",
                "reason": "stage_one_support_project_stage_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("target_construction_phase") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "target_construction_phase",
                "reason": "target_construction_phase_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("protocol_name") != "fixed_low_fpr_calibrated_detection":
        violations.append(
            {
                "field": "protocol_name",
                "reason": "stage_one_protocol_name_must_equal_fixed_low_fpr_calibrated_detection",
            }
        )

    if data.get("construction_phase") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "construction_phase",
                "reason": "construction_phase_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if not REQUIRED_SPLITS.issubset(set(data.get("splits", []))):
        violations.append(
            {
                "field": "splits",
                "reason": "missing_required_stage_one_splits",
            }
        )

    if not REQUIRED_SAMPLE_ROLES.issubset(set(data.get("sample_roles", []))):
        violations.append(
            {
                "field": "sample_roles",
                "reason": "missing_required_stage_one_sample_roles",
            }
        )

    threshold_protocol = data.get("threshold_protocol", {})
    if threshold_protocol.get("calibration_split") != "calibration":
        violations.append(
            {
                "field": "threshold_protocol.calibration_split",
                "reason": "calibration_split_must_equal_calibration",
            }
        )
    if threshold_protocol.get("score_name") != "S_final":
        violations.append(
            {
                "field": "threshold_protocol.score_name",
                "reason": "score_name_must_equal_s_final",
            }
        )
    if threshold_protocol.get("threshold_quantile_rule") != "upper_tail":
        violations.append(
            {
                "field": "threshold_protocol.threshold_quantile_rule",
                "reason": "threshold_quantile_rule_must_equal_upper_tail",
            }
        )
    if threshold_protocol.get("test_threshold_update_allowed") is not False:
        violations.append(
            {
                "field": "threshold_protocol.test_threshold_update_allowed",
                "reason": "test_threshold_updates_must_be_disabled",
            }
        )
    if threshold_protocol.get("allow_attack_specific_threshold") is not False:
        violations.append(
            {
                "field": "threshold_protocol.allow_attack_specific_threshold",
                "reason": "attack_specific_thresholds_must_be_disabled",
            }
        )
    if not {"clean_negative", "attacked_negative"}.issubset(
        set(threshold_protocol.get("calibration_negative_roles", []))
    ):
        violations.append(
            {
                "field": "threshold_protocol.calibration_negative_roles",
                "reason": "missing_required_calibration_negative_roles",
            }
        )

    if data.get("latent_backend_name") != SYNTHETIC_VIDEO_LATENT_BACKEND_NAME:
        violations.append(
            {
                "field": "latent_backend_name",
                "reason": "latent_backend_name_must_equal_synthetic_video_latent",
            }
        )

    if data.get("latent_distribution") != SYNTHETIC_VIDEO_LATENT_DISTRIBUTION:
        violations.append(
            {
                "field": "latent_distribution",
                "reason": "latent_distribution_must_equal_standard_normal",
            }
        )

    latent_shape = data.get("latent_shape")
    if not isinstance(latent_shape, dict):
        violations.append(
            {
                "field": "latent_shape",
                "reason": "latent_shape_must_be_object",
            }
        )
    elif latent_shape != DEFAULT_LATENT_SHAPE:
        violations.append(
            {
                "field": "latent_shape",
                "reason": "latent_shape_must_match_stage_one_default",
            }
        )

    if data.get("runtime_profile") != DEFAULT_RUNTIME_PROFILE:
        violations.append(
            {
                "field": "runtime_profile",
                "reason": "runtime_profile_must_equal_smoke",
            }
        )

    formal_latent_shape = data.get("formal_latent_shape")
    if not isinstance(formal_latent_shape, dict):
        violations.append(
            {
                "field": "formal_latent_shape",
                "reason": "formal_latent_shape_must_be_object",
            }
        )
    elif formal_latent_shape != FORMAL_LATENT_SHAPE:
        violations.append(
            {
                "field": "formal_latent_shape",
                "reason": "formal_latent_shape_must_match_stage_one_formal_profile",
            }
        )

    proof_latent_shape = data.get("proof_latent_shape")
    if not isinstance(proof_latent_shape, dict):
        violations.append(
            {
                "field": "proof_latent_shape",
                "reason": "proof_latent_shape_must_be_object",
            }
        )
    elif proof_latent_shape != PROOF_LATENT_SHAPE:
        violations.append(
            {
                "field": "proof_latent_shape",
                "reason": "proof_latent_shape_must_match_stage_one_proof_profile",
            }
        )

    tiny_latent_shape = data.get("tiny_latent_shape")
    if not isinstance(tiny_latent_shape, dict):
        violations.append(
            {
                "field": "tiny_latent_shape",
                "reason": "tiny_latent_shape_must_be_object",
            }
        )
    elif tiny_latent_shape != TINY_LATENT_SHAPE:
        violations.append(
            {
                "field": "tiny_latent_shape",
                "reason": "tiny_latent_shape_must_match_stage_one_tiny_profile",
            }
        )

    if data.get("latent_generation_seed") != DEFAULT_LATENT_GENERATION_SEED:
        violations.append(
            {
                "field": "latent_generation_seed",
                "reason": "latent_generation_seed_must_match_stage_one_default",
            }
        )

    threshold_protocol = data.get("threshold_protocol")
    if not isinstance(threshold_protocol, dict):
        violations.append(
            {
                "field": "threshold_protocol",
                "reason": "threshold_protocol_must_be_object",
            }
        )
    else:
        validation_target_fpr_by_profile = threshold_protocol.get(
            "validation_target_fpr_by_profile"
        )
        if not isinstance(validation_target_fpr_by_profile, dict):
            violations.append(
                {
                    "field": "threshold_protocol.validation_target_fpr_by_profile",
                    "reason": "validation_target_fpr_by_profile_must_be_object",
                }
            )
        sync_guard_band_by_profile = threshold_protocol.get(
            "sync_threshold_guard_band_multiplier_by_profile"
        )
        if not isinstance(sync_guard_band_by_profile, dict):
            violations.append(
                {
                    "field": "threshold_protocol.sync_threshold_guard_band_multiplier_by_profile",
                    "reason": "sync_threshold_guard_band_multiplier_by_profile_must_be_object",
                }
            )
        calibration_negative_min_samples = threshold_protocol.get(
            "calibration_negative_min_samples_per_role_by_profile"
        )
        if not isinstance(calibration_negative_min_samples, dict):
            violations.append(
                {
                    "field": "threshold_protocol.calibration_negative_min_samples_per_role_by_profile",
                    "reason": "calibration_negative_min_samples_per_role_by_profile_must_be_object",
                }
            )
        tubelet_guard_band_by_profile = threshold_protocol.get(
            "tubelet_length_threshold_guard_band_multiplier_by_profile"
        )
        if not isinstance(tubelet_guard_band_by_profile, dict):
            violations.append(
                {
                    "field": "threshold_protocol.tubelet_length_threshold_guard_band_multiplier_by_profile",
                    "reason": "tubelet_length_threshold_guard_band_multiplier_by_profile_must_be_object",
                }
            )

    if data.get("latent_storage") != SYNTHETIC_VIDEO_LATENT_STORAGE:
        violations.append(
            {
                "field": "latent_storage",
                "reason": "latent_storage_must_equal_npy_artifact",
            }
        )

    if data.get("attack_matrix_name") != TEMPORAL_ATTACK_MATRIX_NAME:
        violations.append(
            {
                "field": "attack_matrix_name",
                "reason": "attack_matrix_name_must_equal_temporal_attack_matrix",
            }
        )

    required_method_variants = set(data.get("required_method_variants", []))
    if not set(SYNTHETIC_TUBELET_SYNC_METHOD_VARIANTS).issubset(required_method_variants):
        violations.append(
            {
                "field": "required_method_variants",
                "reason": "missing_required_stage_one_method_variants",
            }
        )

    if data.get("mechanism_trace_required") is not True:
        violations.append(
            {
                "field": "mechanism_trace_required",
                "reason": "mechanism_trace_must_be_required",
            }
        )

    required_output_tables = set(data.get("required_output_tables", []))
    if not REQUIRED_STAGE_ONE_OUTPUT_TABLES.issubset(required_output_tables):
        violations.append(
            {
                "field": "required_output_tables",
                "reason": "missing_required_stage_one_output_tables",
            }
        )

    return violations


def validate_temporal_attack_matrix_support_data(
    data: dict[str, Any],
) -> list[dict[str, str]]:
    """Validate the reserved temporal attack matrix config for the next stage.

    Args:
        data: Parsed temporal attack matrix config.

    Returns:
        A list of validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "project_stage",
                "reason": "temporal_attack_matrix_project_stage_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("target_construction_phase") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "target_construction_phase",
                "reason": "target_construction_phase_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("attack_matrix_name") != TEMPORAL_ATTACK_MATRIX_NAME:
        violations.append(
            {
                "field": "attack_matrix_name",
                "reason": "attack_matrix_name_must_equal_temporal_attack_matrix",
            }
        )

    attacks = data.get("attacks")
    if not isinstance(attacks, list) or not attacks:
        violations.append(
            {
                "field": "attacks",
                "reason": "attacks_must_be_non_empty_list",
            }
        )
        return violations

    attack_names: list[str] = []
    for attack_entry in attacks:
        if not isinstance(attack_entry, dict):
            violations.append(
                {
                    "field": "attacks",
                    "reason": "attack_entries_must_be_objects",
                }
            )
            continue
        attack_name = attack_entry.get("attack_name")
        attack_params = attack_entry.get("attack_params")
        if attack_name not in SUPPORTED_TEMPORAL_ATTACK_NAMES:
            violations.append(
                {
                    "field": "attack_name",
                    "reason": "unsupported_stage_one_attack_name",
                }
            )
            continue
        if not isinstance(attack_params, dict):
            violations.append(
                {
                    "field": "attack_params",
                    "reason": "attack_params_must_be_object",
                }
            )
            continue
        attack_names.append(attack_name)

    if tuple(attack_names) != SUPPORTED_TEMPORAL_ATTACK_NAMES:
        violations.append(
            {
                "field": "attacks",
                "reason": "stage_one_attack_names_must_match_governed_order",
            }
        )

    return violations


def validate_synthetic_tubelet_sync_ablation_support_data(
    data: dict[str, Any],
) -> list[dict[str, str]]:
    """Validate the reserved ablation config for the synthetic tubelet sync probe.

    Args:
        data: Parsed ablation support config.

    Returns:
        A list of validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "project_stage",
                "reason": "stage_one_ablation_project_stage_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("target_construction_phase") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "target_construction_phase",
                "reason": "target_construction_phase_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("ablation_name") != "synthetic_tubelet_sync_ablation":
        violations.append(
            {
                "field": "ablation_name",
                "reason": "ablation_name_must_equal_synthetic_tubelet_sync_ablation",
            }
        )

    if data.get("shared_protocol_name") != "fixed_low_fpr_calibrated_detection":
        violations.append(
            {
                "field": "shared_protocol_name",
                "reason": "shared_protocol_name_must_equal_fixed_low_fpr_calibrated_detection",
            }
        )

    if data.get("shared_attack_matrix_name") != TEMPORAL_ATTACK_MATRIX_NAME:
        violations.append(
            {
                "field": "shared_attack_matrix_name",
                "reason": "shared_attack_matrix_name_must_equal_temporal_attack_matrix",
            }
        )

    if tuple(data.get("method_variants", [])) != SYNTHETIC_TUBELET_SYNC_METHOD_VARIANTS:
        violations.append(
            {
                "field": "method_variants",
                "reason": "method_variants_must_match_stage_one_governed_order",
            }
        )

    if data.get("shared_target_fpr") != 0.001:
        violations.append(
            {
                "field": "shared_target_fpr",
                "reason": "shared_target_fpr_must_equal_point_zero_zero_one",
            }
        )

    if data.get("shared_table_builder_name") != "table_builder":
        violations.append(
            {
                "field": "shared_table_builder_name",
                "reason": "shared_table_builder_name_must_equal_table_builder",
            }
        )

    return violations


def validate_synthetic_tubelet_sync_method_config_data(
    data: dict[str, Any],
) -> list[dict[str, str]]:
    """Validate a reserved method config for the synthetic tubelet sync probe.

    Args:
        data: Parsed method config.

    Returns:
        A list of validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "project_stage",
                "reason": "stage_one_method_project_stage_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("target_construction_phase") != SYNTHETIC_TUBELET_SYNC_TARGET_PHASE:
        violations.append(
            {
                "field": "target_construction_phase",
                "reason": "target_construction_phase_must_equal_synthetic_tubelet_sync_probe",
            }
        )

    if data.get("method_family") != SYNTHETIC_TUBELET_SYNC_METHOD_FAMILY:
        violations.append(
            {
                "field": "method_family",
                "reason": "method_family_must_equal_temporal_tubelet_watermark",
            }
        )

    method_variant = data.get("method_variant")
    if method_variant not in SYNTHETIC_TUBELET_SYNC_METHOD_VARIANTS:
        violations.append(
            {
                "field": "method_variant",
                "reason": "unsupported_stage_one_method_variant",
            }
        )
        return violations

    if data.get("method_status") != SYNTHETIC_TUBELET_SYNC_METHOD_STATUS:
        violations.append(
            {
                "field": "method_status",
                "reason": "method_status_must_equal_formal_synthetic_probe",
            }
        )

    expected_config = build_reserved_method_support_matrix()[method_variant]
    for field_name in (
        "enable_frame_prc",
        "enable_tubelet",
        "enable_sync",
        "enable_trajectory",
        "tubelet_length",
        "fusion_rule",
    ):
        if data.get(field_name) != expected_config[field_name]:
            violations.append(
                {
                    "field": field_name,
                    "reason": f"unexpected_{field_name}_for_{method_variant}",
                }
            )

    return violations


def main(argv: list[str] | None = None) -> None:
    """Run the project contract validator as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    project_contract_path = root / "configs" / "project" / "project_contract.json"
    protocol_path = root / "configs" / "protocol" / "protocol_skeleton.json"
    protocol_artifact_schema_path = (
        root / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    ablation_path = root / "configs" / "ablation" / "ablation_placeholder.json"
    attack_path = root / "configs" / "attacks" / "identity_attack_placeholder.json"
    stage_one_protocol_path = (
        root / "configs" / "protocol" / "synthetic_tubelet_sync_probe.json"
    )
    temporal_attack_matrix_path = (
        root / "configs" / "attacks" / "temporal_attack_matrix.json"
    )
    stage_one_ablation_path = (
        root / "configs" / "ablation" / "synthetic_tubelet_sync_ablation.json"
    )
    stage_one_method_paths = [
        root / "configs" / "method" / "frame_prc.json",
        root / "configs" / "method" / "tubelet_only.json",
        root / "configs" / "method" / "tubelet_sync.json",
    ]

    payload = {
        "project_contract_violations": validate_project_contract_data(
            load_json_config(project_contract_path)
        ),
        "protocol_threshold_violations": validate_protocol_config_data(
            load_json_config(protocol_path)
        ),
        "protocol_artifact_schema_violations": validate_protocol_artifact_schema_data(
            load_json_config(protocol_artifact_schema_path)
        ),
        "ablation_placeholder_violations": validate_ablation_placeholder_data(
            load_json_config(ablation_path)
        ),
        "attack_placeholder_violations": validate_attack_placeholder_data(
            load_json_config(attack_path)
        ),
        "synthetic_tubelet_sync_protocol_support_violations": (
            validate_synthetic_tubelet_sync_protocol_support_data(
                load_json_config(stage_one_protocol_path)
            )
            if stage_one_protocol_path.exists()
            else [{
                "field": "synthetic_tubelet_sync_probe",
                "reason": "missing_stage_one_protocol_support_config",
            }]
        ),
        "temporal_attack_matrix_support_violations": (
            validate_temporal_attack_matrix_support_data(
                load_json_config(temporal_attack_matrix_path)
            )
            if temporal_attack_matrix_path.exists()
            else [{
                "field": "temporal_attack_matrix",
                "reason": "missing_temporal_attack_matrix_support_config",
            }]
        ),
        "synthetic_tubelet_sync_ablation_support_violations": (
            validate_synthetic_tubelet_sync_ablation_support_data(
                load_json_config(stage_one_ablation_path)
            )
            if stage_one_ablation_path.exists()
            else [{
                "field": "synthetic_tubelet_sync_ablation",
                "reason": "missing_stage_one_ablation_support_config",
            }]
        ),
        "synthetic_tubelet_sync_method_support_violations": [
            violation
            for method_path in stage_one_method_paths
            for violation in (
                validate_synthetic_tubelet_sync_method_config_data(
                    load_json_config(method_path)
                )
                if method_path.exists()
                else [{
                    "field": str(method_path.name),
                    "reason": "missing_stage_one_method_support_config",
                }]
            )
        ],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)

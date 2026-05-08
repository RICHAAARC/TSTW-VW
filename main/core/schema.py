"""
文件用途：定义当前 formal probe 阶段所需的枚举、样本结构与记录校验。
File purpose: Define the active formal-probe protocol schema, sample models, and record validators.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SPLIT_ORDER = ("dev", "calibration", "test")
SAMPLE_ROLE_ORDER = (
    "clean_negative",
    "attacked_negative",
    "watermarked_positive",
    "attacked_positive",
)
EVIDENCE_SCORE_ORDER = ("S_tubelet", "S_sync", "S_traj", "S_final")

SPLITS = set(SPLIT_ORDER)
SAMPLE_ROLES = set(SAMPLE_ROLE_ORDER)
NEGATIVE_SAMPLE_ROLES = {"clean_negative", "attacked_negative"}
POSITIVE_SAMPLE_ROLES = {"watermarked_positive", "attacked_positive"}
EVIDENCE_SCORE_NAMES = set(EVIDENCE_SCORE_ORDER)

CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"
PROTOCOL_NAME = "fixed_low_fpr_calibrated_detection"
IDENTITY_ATTACK_NAME = "identity_attack_placeholder"
DEFAULT_LATENT_SHAPE = (16, 4, 32, 32)

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
REQUIRED_INPUT_ARTIFACT_TRACE_FIELDS = {
    "artifact_kind",
    "backend_name",
    "backend_status",
    "artifact_digest",
    "generation_seed_random",
}
REQUIRED_THRESHOLD_FIELDS = {
    "threshold_id",
    "run_id",
    "method_family",
    "method_variant",
    "score_name",
    "target_fpr",
    "validation_target_fpr",
    "runtime_profile",
    "calibration_split",
    "calibration_negative_roles",
    "threshold_value",
    "threshold_quantile",
    "sync_threshold_guard_band_multiplier",
    "tubelet_length_threshold_guard_band_multiplier",
    "applied_threshold_guard_band_multiplier",
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


@dataclass(frozen=True)
class LatentSample:
    """功能：定义当前 formal probe 阶段的 latent 样本结构。

    Latent sample model for the active formal probe stage.

    Args:
        sample_id: Stable sample identifier.
        split: Governed split name.
        sample_role: Governed sample role name.
        latent_shape: Declared latent tensor shape.
        latent_tensor_digest_random: Digest-backed latent identity.
        latent_generation_seed_random: Deterministic latent seed.
        latent_backend_name: Stable latent backend identifier.
        latent_backend_status: Backend scaffold status.
        latent_artifact_relpath: Relative artifact path for the tensor payload.
        latent_artifact_path: Absolute artifact path for runtime-only tensor access.
        latent_artifact_digest: File digest for the tensor artifact.
        mechanism_trace: Trace payload accumulated along the sample lifecycle.
        applied_attack_params: Materialized attack parameters after deterministic selection.

    Returns:
        None.
    """

    sample_id: str
    split: str
    sample_role: str
    latent_shape: tuple[int, int, int, int]
    latent_tensor_digest_random: str
    latent_generation_seed_random: int
    latent_backend_name: str
    latent_backend_status: str
    latent_artifact_relpath: str | None = None
    latent_artifact_path: str | None = None
    latent_artifact_digest: str | None = None
    run_root_path: str | None = None
    mechanism_trace: dict[str, Any] | None = None
    applied_attack_params: dict[str, Any] | None = None


@dataclass(frozen=True)
class DetectionResult:
    """功能：定义受治理检测输出结构。

    Governed detection result model.

    Args:
        evidence_scores: Governed evidence score payload.
        disabled_evidence: Explicitly disabled evidence names.
        decision: Final binary decision.
        failure_reason: Optional failure reason.
        placeholder_fields: Placeholder-governed field names.
        random_fields: Random-trace field names.
        mechanism_trace: Optional detector-side trace payload.

    Returns:
        None.
    """

    evidence_scores: dict[str, float | None]
    disabled_evidence: list[str]
    decision: bool
    failure_reason: str | None
    placeholder_fields: list[str]
    random_fields: list[str]
    mechanism_trace: dict[str, Any] | None = None


def ensure_non_empty_string(field_value: Any, field_name: str) -> None:
    """功能：校验字符串字段非空。

    Validate that a governed string field is non-empty.

    Args:
        field_value: Candidate field value.
        field_name: Field name used in the error message.

    Returns:
        None.
    """
    if not isinstance(field_value, str) or not field_value:
        raise ValueError(f"{field_name} must be a non-empty string")


def build_input_artifact_trace(latent_sample: LatentSample) -> dict[str, Any]:
    """功能：根据输入样本构建长期 artifact trace。

    Build the long-lived input artifact trace for a governed event record.

    Args:
        latent_sample: Input latent sample metadata.

    Returns:
        A governed input artifact trace dictionary.
    """
    if not isinstance(latent_sample, LatentSample):
        raise TypeError("latent_sample must be a LatentSample instance")

    return {
        "artifact_kind": "latent_tensor",
        "backend_name": latent_sample.latent_backend_name,
        "backend_status": latent_sample.latent_backend_status,
        "artifact_digest": (
            latent_sample.latent_artifact_digest
            or latent_sample.latent_tensor_digest_random
        ),
        "generation_seed_random": latent_sample.latent_generation_seed_random,
    }


def validate_input_artifact_trace(input_artifact_trace: dict[str, Any]) -> None:
    """功能：校验长期 input artifact trace 结构。

    Validate the governed input artifact trace payload.

    Args:
        input_artifact_trace: Candidate input artifact trace payload.

    Returns:
        None.
    """
    if not isinstance(input_artifact_trace, dict):
        raise TypeError("input_artifact_trace must be a dictionary")

    missing_fields = REQUIRED_INPUT_ARTIFACT_TRACE_FIELDS.difference(
        input_artifact_trace.keys()
    )
    if missing_fields:
        raise ValueError(
            f"missing input_artifact_trace fields: {sorted(missing_fields)}"
        )

    ensure_non_empty_string(
        input_artifact_trace["artifact_kind"],
        "input_artifact_trace.artifact_kind",
    )
    ensure_non_empty_string(
        input_artifact_trace["backend_name"],
        "input_artifact_trace.backend_name",
    )
    ensure_non_empty_string(
        input_artifact_trace["backend_status"],
        "input_artifact_trace.backend_status",
    )
    ensure_non_empty_string(
        input_artifact_trace["artifact_digest"],
        "input_artifact_trace.artifact_digest",
    )
    if not isinstance(input_artifact_trace["generation_seed_random"], int):
        raise ValueError(
            "input_artifact_trace.generation_seed_random must be an integer"
        )


def ensure_supported_split(split: str) -> None:
    """功能：校验 split 是否属于受治理枚举。

    Validate that a split name belongs to the governed split set.

    Args:
        split: Candidate split name.

    Returns:
        None.

    Raises:
        TypeError: Raised when the split is not a string.
        ValueError: Raised when the split is not governed.
    """
    if not isinstance(split, str):
        # 中文注释：split 必须是字符串，否则后续枚举匹配不可靠。
        raise TypeError("split must be a string")
    if split not in SPLITS:
        # 中文注释：只允许三段式协议中的受治理 split。
        raise ValueError(f"unsupported split: {split}")


def ensure_supported_sample_role(sample_role: str) -> None:
    """功能：校验 sample role 是否属于受治理枚举。

    Validate that a sample role belongs to the governed role set.

    Args:
        sample_role: Candidate sample role name.

    Returns:
        None.

    Raises:
        TypeError: Raised when the role is not a string.
        ValueError: Raised when the role is not governed.
    """
    if not isinstance(sample_role, str):
        # 中文注释：sample role 必须是字符串，否则配置与 records 语义不稳定。
        raise TypeError("sample_role must be a string")
    if sample_role not in SAMPLE_ROLES:
        # 中文注释：只允许四类受治理样本角色。
        raise ValueError(f"unsupported sample_role: {sample_role}")


def build_empty_evidence_scores(final_score: float = 0.0) -> dict[str, float | None]:
    """功能：构建完整但可为空的 evidence score 结构。

    Build a fully enumerated evidence score structure.

    Args:
        final_score: Materialized final score value.

    Returns:
        A governed evidence score dictionary.
    """
    if not isinstance(final_score, (int, float)):
        # 中文注释：最终分数必须可转换为浮点数，否则无法进入后续阈值逻辑。
        raise TypeError("final_score must be numeric")
    return {
        "S_tubelet": None,
        "S_sync": None,
        "S_traj": None,
        "S_final": round(float(final_score), 6),
    }


def validate_evidence_scores(evidence_scores: dict[str, float | None]) -> None:
    """功能：校验 evidence score 字段完整且类型有效。

    Validate that evidence scores contain the governed keys and types.

    Args:
        evidence_scores: Candidate evidence score payload.

    Returns:
        None.

    Raises:
        TypeError: Raised when the payload is not a dictionary.
        ValueError: Raised when required evidence keys are missing.
    """
    if not isinstance(evidence_scores, dict):
        # 中文注释：evidence score 容器必须是字典，便于后续稳定序列化。
        raise TypeError("evidence_scores must be a dictionary")

    missing_fields = EVIDENCE_SCORE_NAMES.difference(evidence_scores.keys())
    if missing_fields:
        # 中文注释：缺失任一 evidence 字段都会破坏 record schema 冻结口径。
        raise ValueError(f"missing evidence score fields: {sorted(missing_fields)}")

    for score_name in EVIDENCE_SCORE_ORDER:
        score_value = evidence_scores[score_name]
        if score_value is not None and not isinstance(score_value, (int, float)):
            # 中文注释：evidence 值只允许浮点数或显式空值编码。
            raise ValueError(f"invalid evidence score value for {score_name}")


def validate_event_score_record(event_score_record: dict[str, Any]) -> None:
    """功能：校验 event-level score record 结构。

    Validate the governed event-level score record schema.

    Args:
        event_score_record: Candidate event score record.

    Returns:
        None.

    Raises:
        TypeError: Raised when the record is not a dictionary.
        ValueError: Raised when required fields are missing or malformed.
    """
    if not isinstance(event_score_record, dict):
        # 中文注释：record 写入前必须保证字典结构完整。
        raise TypeError("event_score_record must be a dictionary")

    missing_fields = REQUIRED_EVENT_SCORE_FIELDS.difference(event_score_record.keys())
    if missing_fields:
        # 中文注释：缺失必填字段会破坏 records schema 可审计性。
        raise ValueError(f"missing event_score_record fields: {sorted(missing_fields)}")

    ensure_supported_split(event_score_record["split"])
    ensure_supported_sample_role(event_score_record["sample_role"])
    ensure_non_empty_string(event_score_record["method_family"], "method_family")
    ensure_non_empty_string(event_score_record["method_variant"], "method_variant")
    ensure_non_empty_string(
        event_score_record["base_method_variant"],
        "base_method_variant",
    )
    if not isinstance(event_score_record["derived_variant"], bool):
        raise ValueError("derived_variant must be a boolean")
    if (
        not isinstance(event_score_record["tubelet_length"], int)
        or event_score_record["tubelet_length"] < 1
    ):
        raise ValueError("tubelet_length must be a positive integer")
    if event_score_record["derived_variant"]:
        if event_score_record["base_method_variant"] == event_score_record["method_variant"]:
            raise ValueError("derived variants must differ from base_method_variant")
        if event_score_record["ablation_axis"] != "tubelet_length":
            raise ValueError("derived variants must declare ablation_axis=tubelet_length")
    else:
        if event_score_record["base_method_variant"] != event_score_record["method_variant"]:
            raise ValueError("non-derived variants must match base_method_variant")
        if event_score_record["ablation_axis"] is not None:
            raise ValueError("non-derived variants must use null ablation_axis")
    validate_evidence_scores(event_score_record["evidence_scores"])
    validate_input_artifact_trace(event_score_record["input_artifact_trace"])

    ensure_non_empty_string(event_score_record["latent_backend_name"], "latent_backend_name")
    ensure_non_empty_string(
        event_score_record["latent_backend_status"],
        "latent_backend_status",
    )
    ensure_non_empty_string(
        event_score_record["latent_tensor_digest_random"],
        "latent_tensor_digest_random",
    )
    if not isinstance(event_score_record["latent_generation_seed_random"], int):
        raise ValueError("latent_generation_seed_random must be an integer")
    if (
        event_score_record["input_artifact_trace"]["backend_name"]
        != event_score_record["latent_backend_name"]
    ):
        raise ValueError(
            "input_artifact_trace.backend_name must equal latent_backend_name"
        )
    if (
        event_score_record["input_artifact_trace"]["backend_status"]
        != event_score_record["latent_backend_status"]
    ):
        raise ValueError(
            "input_artifact_trace.backend_status must equal latent_backend_status"
        )
    if (
        event_score_record["input_artifact_trace"]["artifact_digest"]
        != event_score_record["latent_tensor_digest_random"]
    ):
        raise ValueError(
            "input_artifact_trace.artifact_digest must equal latent_tensor_digest_random"
        )
    if (
        event_score_record["input_artifact_trace"]["generation_seed_random"]
        != event_score_record["latent_generation_seed_random"]
    ):
        raise ValueError(
            "input_artifact_trace.generation_seed_random must equal latent_generation_seed_random"
        )

    if not isinstance(event_score_record["disabled_evidence"], list):
        raise ValueError("disabled_evidence must be a list")
    if not isinstance(event_score_record["mechanism_trace"], dict):
        raise ValueError("mechanism_trace must be a dictionary")
    if not isinstance(event_score_record["placeholder_fields"], list):
        raise ValueError("placeholder_fields must be a list")
    if not isinstance(event_score_record["random_fields"], list):
        raise ValueError("random_fields must be a list")
    if not isinstance(event_score_record["decision"], bool):
        raise ValueError("decision must be a boolean")


def validate_threshold_record(threshold_record: dict[str, Any]) -> None:
    """功能：校验 threshold record 结构。

    Validate the governed threshold record schema.

    Args:
        threshold_record: Candidate threshold record.

    Returns:
        None.

    Raises:
        TypeError: Raised when the record is not a dictionary.
        ValueError: Raised when required fields are missing or malformed.
    """
    if not isinstance(threshold_record, dict):
        raise TypeError("threshold_record must be a dictionary")

    missing_fields = REQUIRED_THRESHOLD_FIELDS.difference(threshold_record.keys())
    if missing_fields:
        raise ValueError(f"missing threshold_record fields: {sorted(missing_fields)}")

    ensure_non_empty_string(threshold_record["method_family"], "method_family")
    ensure_non_empty_string(threshold_record["method_variant"], "method_variant")
    ensure_non_empty_string(threshold_record["runtime_profile"], "runtime_profile")
    ensure_supported_split(threshold_record["calibration_split"])
    if not isinstance(threshold_record["target_fpr"], (int, float)):
        raise ValueError("target_fpr must be numeric")
    if not isinstance(threshold_record["validation_target_fpr"], (int, float)):
        raise ValueError("validation_target_fpr must be numeric")
    if not isinstance(threshold_record["threshold_value"], (int, float)):
        raise ValueError("threshold_value must be numeric")
    if not isinstance(threshold_record["threshold_quantile"], (int, float)):
        raise ValueError("threshold_quantile must be numeric")
    if not isinstance(threshold_record["sync_threshold_guard_band_multiplier"], (int, float)):
        raise ValueError("sync_threshold_guard_band_multiplier must be numeric")
    if not isinstance(
        threshold_record["tubelet_length_threshold_guard_band_multiplier"],
        (int, float),
    ):
        raise ValueError("tubelet_length_threshold_guard_band_multiplier must be numeric")
    if not isinstance(
        threshold_record["applied_threshold_guard_band_multiplier"],
        (int, float),
    ):
        raise ValueError("applied_threshold_guard_band_multiplier must be numeric")
    calibration_negative_roles = threshold_record["calibration_negative_roles"]
    if not isinstance(calibration_negative_roles, list):
        raise ValueError("calibration_negative_roles must be a list")
    if not NEGATIVE_SAMPLE_ROLES.issubset(set(calibration_negative_roles)):
        raise ValueError("threshold_record is missing required calibration negative roles")


def validate_run_manifest_record(run_manifest_record: dict[str, Any]) -> None:
    """功能：校验 run manifest 结构。

    Validate the governed run manifest schema.

    Args:
        run_manifest_record: Candidate run manifest payload.

    Returns:
        None.

    Raises:
        TypeError: Raised when the payload is not a dictionary.
        ValueError: Raised when required fields are missing or malformed.
    """
    if not isinstance(run_manifest_record, dict):
        raise TypeError("run_manifest_record must be a dictionary")

    missing_fields = REQUIRED_MANIFEST_FIELDS.difference(run_manifest_record.keys())
    if missing_fields:
        raise ValueError(f"missing run_manifest_record fields: {sorted(missing_fields)}")

    if run_manifest_record["construction_phase"] != CONSTRUCTION_PHASE:
        raise ValueError(
            "run_manifest_record construction_phase must equal synthetic_tubelet_sync_probe"
        )
    if run_manifest_record["protocol_name"] != PROTOCOL_NAME:
        raise ValueError(
            "run_manifest_record protocol_name must equal fixed_low_fpr_calibrated_detection"
        )
    if not isinstance(run_manifest_record["placeholder_fields"], list):
        raise ValueError("placeholder_fields must be a list")
    if not isinstance(run_manifest_record["random_fields"], list):
        raise ValueError("random_fields must be a list")
    ensure_non_empty_string(run_manifest_record["figures_digest"], "figures_digest")

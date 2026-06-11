"""阶段三 baseline comparison 记录字段契约。"""

from __future__ import annotations

from typing import Any

REQUIRED_BASELINE_RECORD_FIELDS = {
    "workflow_key",
    "run_id",
    "sample_id",
    "split",
    "sample_role",
    "baseline_name",
    "baseline_family",
    "method_name",
    "method_family",
    "payload_length_bits",
    "payload_digest",
    "attack_name",
    "attack_family",
    "attack_config_digest",
    "baseline_score",
    "baseline_raw_detector_output",
    "threshold",
    "target_fpr",
    "decision",
    "bit_accuracy",
    "ber",
    "quality_metrics",
    "temporal_metrics",
    "runtime_metrics",
    "baseline_trace",
    "failure_reason",
}

REQUIRED_BASELINE_TRACE_FIELDS = {
    "source_digest",
    "model_digest",
    "adapter_version",
    "score_mapping_rule",
    "license_status",
}


def validate_baseline_record(record: dict[str, Any]) -> list[dict[str, str]]:
    """校验单条 baseline comparison record 的最小字段完整性。"""
    violations: list[dict[str, str]] = []
    missing_fields = REQUIRED_BASELINE_RECORD_FIELDS - set(record)
    for field_name in sorted(missing_fields):
        violations.append({"field": field_name, "reason": "missing_required_field"})

    if record.get("workflow_key") != "baseline_comparison_gate":
        violations.append({"field": "workflow_key", "reason": "must_equal_baseline_comparison_gate"})

    if record.get("split") not in {"dev", "calibration", "test"}:
        violations.append({"field": "split", "reason": "unsupported_split"})

    if record.get("target_fpr") is not None and not isinstance(record.get("target_fpr"), float):
        violations.append({"field": "target_fpr", "reason": "must_be_float_or_null"})

    baseline_trace = record.get("baseline_trace")
    if not isinstance(baseline_trace, dict):
        violations.append({"field": "baseline_trace", "reason": "must_be_object"})
    else:
        missing_trace_fields = REQUIRED_BASELINE_TRACE_FIELDS - set(baseline_trace)
        for field_name in sorted(missing_trace_fields):
            violations.append(
                {"field": f"baseline_trace.{field_name}", "reason": "missing_required_trace_field"}
            )

    for object_field in (
        "baseline_raw_detector_output",
        "quality_metrics",
        "temporal_metrics",
        "runtime_metrics",
    ):
        if object_field in record and not isinstance(record.get(object_field), dict):
            violations.append({"field": object_field, "reason": "must_be_object"})

    return violations

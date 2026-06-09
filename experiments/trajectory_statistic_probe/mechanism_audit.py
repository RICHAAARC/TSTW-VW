"""
文件用途：构建阶段 3 trajectory statistic probe 的实现与机制审计结论。
File purpose: Build implementation and mechanism-audit decisions for the stage-three trajectory statistic probe.
Module type: General module
"""

from __future__ import annotations

from statistics import mean
from typing import Any


def build_stage3_mechanism_decision(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
    runtime_method_configs: list[dict[str, Any]],
    frozen_baseline_manifest: dict[str, Any] | None = None,
    trajectory_backend_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """功能：构建阶段 3 implementation / mechanism 审计结论。

    Build the stage-three implementation and mechanism-audit decision payload.

    Args:
        event_score_records: Event score records emitted by the runner.
        threshold_records: Threshold records emitted by the runner.
        runtime_method_configs: Runtime method configs used by the runner.
        frozen_baseline_manifest: Optional validated frozen baseline manifest.
        trajectory_backend_config: Optional trajectory backend config.

    Returns:
        A mechanism-decision dictionary.
    """
    method_config_by_variant = {
        method_config["method_variant"]: method_config
        for method_config in runtime_method_configs
    }
    trajectory_enabled_variants = sorted(
        method_variant
        for method_variant, method_config in method_config_by_variant.items()
        if bool(method_config.get("enable_trajectory", False))
    )
    trajectory_disabled_variants = sorted(
        method_variant
        for method_variant, method_config in method_config_by_variant.items()
        if not bool(method_config.get("enable_trajectory", False))
    )
    blocking_reasons: list[str] = []
    if not threshold_records:
        blocking_reasons.append("threshold_records_missing")

    for method_variant in trajectory_enabled_variants:
        variant_records = [
            record
            for record in event_score_records
            if record["method_variant"] == method_variant
        ]
        if not variant_records:
            blocking_reasons.append(f"records_missing:{method_variant}")
            continue
        if any(record["evidence_scores"].get("S_traj") is None for record in variant_records):
            blocking_reasons.append("s_traj_missing_for_trajectory_enabled_variant")
            break
        if any(record["mechanism_trace"].get("trajectory_source_kind") is None for record in variant_records):
            blocking_reasons.append("trajectory_source_kind_missing")
            break
        if any(record["mechanism_trace"].get("trajectory_statistic_kind") is None for record in variant_records):
            blocking_reasons.append("trajectory_statistic_kind_missing")
            break
        if any(record["mechanism_trace"].get("trajectory_time_grid") is None for record in variant_records):
            blocking_reasons.append("trajectory_time_grid_missing")
            break
        if any(
            record["mechanism_trace"].get("trajectory_source_kind")
            == "stage2_frozen_endpoint_replay"
            and not record["mechanism_trace"].get("trajectory_source_provenance_digest")
            for record in variant_records
        ):
            blocking_reasons.append("trajectory_source_provenance_digest_missing")
            break

    for method_variant in trajectory_disabled_variants:
        variant_records = [
            record
            for record in event_score_records
            if record["method_variant"] == method_variant
        ]
        if not variant_records:
            continue
        if any(record["evidence_scores"].get("S_traj") is not None for record in variant_records):
            blocking_reasons.append("s_traj_non_null_for_trajectory_disabled_variant")
            break

    stage2_dependency_status = _resolve_stage2_dependency_status(
        frozen_baseline_manifest
    )
    trajectory_source_kind = _resolve_trajectory_source_kind(
        event_score_records,
        trajectory_backend_config,
    )
    if (
        stage2_dependency_status != "PASSED"
        and frozen_baseline_manifest is not None
    ):
        blocking_reasons.append("stage2_frozen_baseline_manifest_not_passed")

    implementation_decision = "PASS" if not blocking_reasons else "FAIL"
    mechanism_blocking_reasons = _build_mechanism_blocking_reasons(
        stage2_dependency_status,
        trajectory_source_kind,
        implementation_decision,
    )
    formal_trajectory_source_status = _resolve_formal_trajectory_source_status(
        stage2_dependency_status,
        trajectory_source_kind,
    )
    mechanism_decision = (
        "INCONCLUSIVE"
        if implementation_decision == "PASS"
        else "INCONCLUSIVE"
    )
    next_allowed_stage = (
        "trajectory_mechanism_formal_validation"
        if implementation_decision == "PASS"
        and stage2_dependency_status == "PASSED"
        else "finish_stage2_first"
        if implementation_decision == "PASS"
        else "hold_stage3"
    )

    enabled_records = [
        record
        for record in event_score_records
        if record["method_variant"] in trajectory_enabled_variants
        and record["evidence_scores"].get("S_traj") is not None
    ]
    control_values = [
        abs(float(score_value))
        for record in enabled_records
        for score_value in record["mechanism_trace"].get("trajectory_control_scores", {}).values()
    ]
    delta_traj_values = _collect_delta_traj_values(event_score_records)
    runtime_values = [
        float(record["mechanism_trace"]["trajectory_runtime_ms"])
        for record in enabled_records
        if record["mechanism_trace"].get("trajectory_runtime_ms") is not None
    ]

    return {
        "Stage3ImplementationDecision": implementation_decision,
        "Stage3MechanismDecision": mechanism_decision,
        "Stage2DependencyStatus": stage2_dependency_status,
        "BlockingReasons": blocking_reasons,
        "Stage3MechanismBlockingReasons": mechanism_blocking_reasons,
        "trajectory_source_kind": trajectory_source_kind,
        "formal_trajectory_source_status": formal_trajectory_source_status,
        "TrajectoryLeakageSummary": {
            "max_clean_negative_fpr": _max_role_decision_rate(
                event_score_records,
                "clean_negative",
            ),
            "max_attacked_negative_fpr": _max_role_decision_rate(
                event_score_records,
                "attacked_negative",
            ),
        },
        "TrajectoryGainSummary": {
            "max_delta_traj": max(delta_traj_values, default=0.0),
            "mean_delta_traj": round(mean(delta_traj_values), 6)
            if delta_traj_values
            else 0.0,
        },
        "TrajectoryCorrelationSummary": {
            "mean_abs_control_score": round(mean(control_values), 6)
            if control_values
            else 0.0,
            "trajectory_enabled_variant_count": len(trajectory_enabled_variants),
        },
        "TrajectoryControlSummary": {
            "control_score_count": len(control_values),
            "max_abs_control_score": max(control_values, default=0.0),
        },
        "TrajectoryRuntimeOverheadSummary": {
            "mean_trajectory_runtime_ms": round(mean(runtime_values), 6)
            if runtime_values
            else 0.0,
            "runtime_record_count": len(runtime_values),
        },
        "NextAllowedStageByTrajectory": next_allowed_stage,
    }


def _resolve_stage2_dependency_status(
    frozen_baseline_manifest: dict[str, Any] | None,
) -> str:
    if frozen_baseline_manifest is None:
        return "NOT_PASSED"
    if frozen_baseline_manifest.get("Stage2DependencyStatus") == "PASSED":
        return "PASSED"
    return "NOT_PASSED"


def _resolve_trajectory_source_kind(
    event_score_records: list[dict[str, Any]],
    trajectory_backend_config: dict[str, Any] | None,
) -> str | None:
    if trajectory_backend_config is not None:
        source_kind = trajectory_backend_config.get("trajectory_source_kind")
        if isinstance(source_kind, str) and source_kind:
            return source_kind
    for record in event_score_records:
        source_kind = record.get("mechanism_trace", {}).get("trajectory_source_kind")
        if isinstance(source_kind, str) and source_kind:
            return source_kind
    return None


def _build_mechanism_blocking_reasons(
    stage2_dependency_status: str,
    trajectory_source_kind: str | None,
    implementation_decision: str,
) -> list[str]:
    blocking_reasons: list[str] = []
    if implementation_decision != "PASS":
        blocking_reasons.append("implementation_not_passed")
    if stage2_dependency_status != "PASSED":
        blocking_reasons.append("stage2_dependency_not_passed")
    if trajectory_source_kind is None:
        blocking_reasons.append("formal_trajectory_source_missing")
    if trajectory_source_kind == "latent_interpolation_surrogate":
        blocking_reasons.append("surrogate_source_not_sufficient")
    if (
        stage2_dependency_status == "PASSED"
        and trajectory_source_kind == "stage2_frozen_endpoint_replay"
    ):
        blocking_reasons.append("formal_source_candidate_requires_mechanism_validation")
    return blocking_reasons


def _resolve_formal_trajectory_source_status(
    stage2_dependency_status: str,
    trajectory_source_kind: str | None,
) -> str:
    if trajectory_source_kind == "stage2_frozen_endpoint_replay":
        return (
            "candidate_ready"
            if stage2_dependency_status == "PASSED"
            else "candidate_blocked_by_stage2_dependency"
        )
    if trajectory_source_kind is None:
        return "missing"
    return "not_formal_source"


def _collect_delta_traj_values(event_score_records: list[dict[str, Any]]) -> list[float]:
    deltas: list[float] = []
    comparisons = (
        ("tubelet_traj", "tubelet_only"),
        ("tubelet_sync_trajectory_fusion", "tubelet_sync"),
    )
    test_records = [record for record in event_score_records if record["split"] == "test"]
    for method_variant, base_method_variant in comparisons:
        method_records = [
            record for record in test_records if record["method_variant"] == method_variant
        ]
        base_records = [
            record
            for record in test_records
            if record["method_variant"] == base_method_variant
        ]
        for attack_name in sorted({record["attack_name"] for record in method_records}):
            method_positive_records = [
                record
                for record in method_records
                if record["attack_name"] == attack_name
                and record["sample_role"] == "attacked_positive"
            ]
            base_positive_records = [
                record
                for record in base_records
                if record["attack_name"] == attack_name
                and record["sample_role"] == "attacked_positive"
            ]
            if not method_positive_records or not base_positive_records:
                continue
            deltas.append(
                round(
                    _decision_rate(method_positive_records)
                    - _decision_rate(base_positive_records),
                    6,
                )
            )
    return deltas


def _max_role_decision_rate(
    event_score_records: list[dict[str, Any]],
    sample_role: str,
) -> float:
    grouped_records = [
        record
        for record in event_score_records
        if record["sample_role"] == sample_role and record["split"] == "test"
    ]
    if not grouped_records:
        return 0.0
    rates = []
    for method_variant in sorted({record["method_variant"] for record in grouped_records}):
        method_records = [
            record
            for record in grouped_records
            if record["method_variant"] == method_variant
        ]
        rates.append(_decision_rate(method_records))
    return max(rates, default=0.0)


def _decision_rate(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    return round(sum(1 for record in records if record["decision"]) / len(records), 6)

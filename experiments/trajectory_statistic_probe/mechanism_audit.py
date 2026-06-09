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
    main_trajectory_values = [
        abs(float(record["evidence_scores"]["S_traj"]))
        for record in enabled_records
        if record["evidence_scores"].get("S_traj") is not None
    ]
    delta_traj_values = _collect_delta_traj_values(event_score_records)
    runtime_values = [
        float(record["mechanism_trace"]["trajectory_runtime_ms"])
        for record in enabled_records
        if record["mechanism_trace"].get("trajectory_runtime_ms") is not None
    ]
    leakage_summary = {
        "max_clean_negative_fpr": _max_role_decision_rate(
            event_score_records,
            "clean_negative",
        ),
        "max_attacked_negative_fpr": _max_role_decision_rate(
            event_score_records,
            "attacked_negative",
        ),
        "max_negative_leakage_increase_over_baseline": (
            _max_negative_leakage_increase_over_baseline(event_score_records)
        ),
    }
    gain_summary = {
        "max_delta_traj": max(delta_traj_values, default=0.0),
        "mean_delta_traj": round(mean(delta_traj_values), 6)
        if delta_traj_values
        else 0.0,
    }
    control_summary = {
        "control_score_count": len(control_values),
        "max_abs_control_score": max(control_values, default=0.0),
        "mean_abs_control_score": round(mean(control_values), 6)
        if control_values
        else 0.0,
        "mean_abs_main_trajectory_score": round(mean(main_trajectory_values), 6)
        if main_trajectory_values
        else 0.0,
    }
    control_summary["control_suppression_ratio"] = _safe_ratio(
        float(control_summary["mean_abs_control_score"]),
        float(control_summary["mean_abs_main_trajectory_score"]),
    )
    runtime_summary = {
        "mean_trajectory_runtime_ms": round(mean(runtime_values), 6)
        if runtime_values
        else 0.0,
        "runtime_record_count": len(runtime_values),
    }
    target_fpr = _resolve_target_fpr(threshold_records)
    mechanism_gate_summary = _build_mechanism_gate_summary(
        leakage_summary,
        gain_summary,
        control_summary,
        runtime_summary,
        target_fpr,
        len(enabled_records),
        _resolve_runtime_profiles(threshold_records),
        trajectory_backend_config,
    )
    implementation_decision = "PASS" if not blocking_reasons else "FAIL"
    mechanism_blocking_reasons = _build_mechanism_blocking_reasons(
        stage2_dependency_status,
        trajectory_source_kind,
        implementation_decision,
        mechanism_gate_summary,
    )
    formal_trajectory_source_status = _resolve_formal_trajectory_source_status(
        stage2_dependency_status,
        trajectory_source_kind,
    )
    mechanism_decision = (
        "PASS"
        if implementation_decision == "PASS"
        and not mechanism_blocking_reasons
        else "INCONCLUSIVE"
    )
    next_allowed_stage = (
        "trajectory_aware_sampling_probe"
        if mechanism_decision == "PASS"
        else "trajectory_formal_gpu_validation"
        if implementation_decision == "PASS"
        and stage2_dependency_status == "PASSED"
        and all(
            gate == "PASS"
            for gate_name, gate in mechanism_gate_summary.items()
            if gate_name != "trajectory_formal_runtime_profile_gate"
        )
        else "trajectory_mechanism_formal_validation"
        if implementation_decision == "PASS"
        and stage2_dependency_status == "PASSED"
        else "finish_stage2_first"
        if implementation_decision == "PASS"
        else "hold_stage3"
    )

    return {
        "Stage3ImplementationDecision": implementation_decision,
        "Stage3MechanismDecision": mechanism_decision,
        "Stage2DependencyStatus": stage2_dependency_status,
        "BlockingReasons": blocking_reasons,
        "Stage3MechanismBlockingReasons": mechanism_blocking_reasons,
        "trajectory_source_kind": trajectory_source_kind,
        "formal_trajectory_source_status": formal_trajectory_source_status,
        "TrajectoryMechanismGateSummary": mechanism_gate_summary,
        "TrajectoryLeakageSummary": leakage_summary,
        "TrajectoryGainSummary": gain_summary,
        "TrajectoryCorrelationSummary": {
            "mean_abs_control_score": round(mean(control_values), 6)
            if control_values
            else 0.0,
            "trajectory_enabled_variant_count": len(trajectory_enabled_variants),
        },
        "TrajectoryControlSummary": control_summary,
        "TrajectoryRuntimeOverheadSummary": runtime_summary,
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
    mechanism_gate_summary: dict[str, Any],
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
        if mechanism_gate_summary.get("trajectory_gain_gate") != "PASS":
            blocking_reasons.append("trajectory_gain_not_positive")
        if mechanism_gate_summary.get("trajectory_negative_leakage_gate") != "PASS":
            blocking_reasons.append("trajectory_negative_leakage_above_target")
        if mechanism_gate_summary.get("trajectory_control_gate") != "PASS":
            blocking_reasons.append("trajectory_control_not_suppressed")
        if mechanism_gate_summary.get("trajectory_runtime_gate") != "PASS":
            blocking_reasons.append("trajectory_runtime_overhead_not_bounded")
        if mechanism_gate_summary.get("trajectory_formal_runtime_profile_gate") != "PASS":
            blocking_reasons.append("trajectory_formal_runtime_profile_required")
        if any(gate != "PASS" for gate in mechanism_gate_summary.values()):
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


def _build_mechanism_gate_summary(
    leakage_summary: dict[str, float],
    gain_summary: dict[str, float],
    control_summary: dict[str, float | int],
    runtime_summary: dict[str, float | int],
    target_fpr: float,
    enabled_record_count: int,
    runtime_profiles: set[str],
    trajectory_backend_config: dict[str, Any] | None,
) -> dict[str, str]:
    """功能：把阶段 3 机制审计摘要转换为显式 gate 结果。

    该函数属于项目特定写法, 用于把 trajectory evidence 是否可支撑机制结论拆分为可审计
    的 gain、negative leakage、control 和 runtime 四类 gate。通用工程可复用的部分是:
    不直接用单个总分判定机制成立, 而是把每类失败原因保留为独立字段。
    """
    runtime_limit_ms = 100.0
    max_control_suppression_ratio = 0.9
    if trajectory_backend_config is not None:
        configured_limit = trajectory_backend_config.get("max_trajectory_runtime_ms")
        if isinstance(configured_limit, (int, float)) and configured_limit > 0:
            runtime_limit_ms = float(configured_limit)
        configured_control_ratio = trajectory_backend_config.get(
            "max_control_suppression_ratio"
        )
        if (
            isinstance(configured_control_ratio, (int, float))
            and configured_control_ratio > 0
        ):
            max_control_suppression_ratio = float(configured_control_ratio)

    max_delta_traj = float(gain_summary.get("max_delta_traj", 0.0))
    runtime_record_count = int(runtime_summary.get("runtime_record_count", 0))
    mean_runtime_ms = float(runtime_summary.get("mean_trajectory_runtime_ms", 0.0))
    formal_runtime_profiles = {
        "formal",
        "l4_formal",
        "a100_80g_formal",
        "a100_80g_paper_main",
    }
    return {
        "trajectory_gain_gate": "PASS" if max_delta_traj > 0.0 else "FAIL",
        "trajectory_negative_leakage_gate": (
            "PASS"
            if float(
                leakage_summary.get("max_negative_leakage_increase_over_baseline", 0.0)
            )
            <= target_fpr
            else "FAIL"
        ),
        "trajectory_control_gate": (
            "PASS"
            if max_delta_traj > 0.0
            and int(control_summary.get("control_score_count", 0)) > 0
            and float(control_summary.get("control_suppression_ratio", 1.0))
            <= max_control_suppression_ratio
            else "FAIL"
        ),
        "trajectory_runtime_gate": (
            "PASS"
            if enabled_record_count > 0
            and runtime_record_count == enabled_record_count
            and mean_runtime_ms <= runtime_limit_ms
            else "FAIL"
        ),
        "trajectory_formal_runtime_profile_gate": (
            "PASS"
            if runtime_profiles
            and runtime_profiles.issubset(formal_runtime_profiles)
            else "FAIL"
        ),
    }


def _resolve_target_fpr(threshold_records: list[dict[str, Any]]) -> float:
    target_values = [
        float(record["target_fpr"])
        for record in threshold_records
        if isinstance(record.get("target_fpr"), (int, float))
    ]
    return min(target_values) if target_values else 0.001


def _resolve_runtime_profiles(threshold_records: list[dict[str, Any]]) -> set[str]:
    return {
        str(record["runtime_profile"])
        for record in threshold_records
        if isinstance(record.get("runtime_profile"), str)
        and record["runtime_profile"]
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 1.0
    return round(numerator / denominator, 6)


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


def _max_negative_leakage_increase_over_baseline(
    event_score_records: list[dict[str, Any]],
) -> float:
    """功能：计算 trajectory-enabled variant 相对 frozen baseline 增加的负样本泄漏。

    该函数修复的工程问题是: 阶段 3 只能对 trajectory 分支新增的 leakage 负责, 不能把
    frozen `tubelet_sync` baseline 在 smoke replay 中已经存在的负样本命中误记为 trajectory
    source 失败。通用写法是把机制分支的安全性定义为“相对基线不恶化”。
    """
    comparisons = (
        ("tubelet_traj", "tubelet_only"),
        ("tubelet_sync_trajectory_fusion", "tubelet_sync"),
        ("traj_only", None),
    )
    increases: list[float] = []
    test_records = [record for record in event_score_records if record["split"] == "test"]
    for method_variant, base_method_variant in comparisons:
        method_records = [
            record
            for record in test_records
            if record["method_variant"] == method_variant
            and record["sample_role"] in {"clean_negative", "attacked_negative"}
        ]
        if not method_records:
            continue
        method_rate = _decision_rate(method_records)
        if base_method_variant is None:
            base_rate = 0.0
        else:
            base_records = [
                record
                for record in test_records
                if record["method_variant"] == base_method_variant
                and record["sample_role"] in {"clean_negative", "attacked_negative"}
            ]
            base_rate = _decision_rate(base_records)
        increases.append(round(method_rate - base_rate, 6))
    return max(increases, default=0.0)


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

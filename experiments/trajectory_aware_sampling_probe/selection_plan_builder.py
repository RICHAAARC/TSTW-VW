"""
文件用途: 构建 trajectory-aware sampling probe 的最小记录选择计划。
Module type: General module
"""

from __future__ import annotations

from typing import Any

from experiments.trajectory_aware_sampling_probe.readiness_audit import (
    build_trajectory_aware_sampling_readiness_decision,
)
from main.core.digest import compute_object_digest

TRAJECTORY_ENABLED_METHOD_VARIANTS = frozenset(
    {
        "traj_only",
        "tubelet_traj",
        "tubelet_sync_trajectory_fusion",
    }
)
DEFAULT_SELECTED_RECORD_LIMIT = 8


def build_record_digest_selection_plan(
    event_score_records: list[dict[str, Any]],
    trajectory_mechanism_decision: dict[str, Any],
    sampling_probe_config: dict[str, Any],
    *,
    selected_record_limit: int | None = None,
) -> dict[str, Any]:
    """功能: 从阶段 3 records 构建只含摘要的 sampling 选择计划。

    该函数属于项目特定的 transition scaffold。它只读取阶段 3 已冻结的 records 和机制决策,
    生成可审计的 record digest 清单, 不调用真实生成模型, 不写出视频, 不执行 watermark 嵌入或检测。
    在其他项目中可复用的部分是: 先复用上游 readiness gate, 再把候选样本压缩成 digest + 少量排序字段,
    从而让下一阶段可以复现选择依据, 同时避免把当前 scaffold 误扩展为真实运行后端。
    """
    readiness_decision = build_trajectory_aware_sampling_readiness_decision(
        trajectory_mechanism_decision,
        sampling_probe_config,
    )
    limit = _resolve_selected_record_limit(selected_record_limit)
    selected_policy_kind = str(
        readiness_decision.get("selected_sampling_policy_kind", "")
    ).strip()
    allowed_policy_kinds = _as_string_list(
        readiness_decision.get("allowed_sampling_policy_kinds", [])
    )

    if readiness_decision.get("SamplingReadinessDecision") != "PASS":
        return _build_blocked_plan(
            readiness_decision,
            selected_policy_kind,
            allowed_policy_kinds,
            event_score_records,
        )

    policy_sections = {
        policy_kind: _build_policy_section(event_score_records, policy_kind, limit)
        for policy_kind in allowed_policy_kinds
    }
    selected_records = policy_sections.get(selected_policy_kind, {}).get(
        "selected_records",
        [],
    )
    blocking_reasons: list[str] = []
    if not selected_records:
        blocking_reasons.append("no_records_selected_for_policy")

    plan_payload: dict[str, Any] = {
        "selection_output_kind": "record_digest_selection_plan",
        "SamplingSelectionPlanDecision": "PASS" if not blocking_reasons else "INCONCLUSIVE",
        "SamplingSelectionBlockingReasons": blocking_reasons,
        "SamplingReadinessDecision": readiness_decision["SamplingReadinessDecision"],
        "selected_sampling_policy_kind": selected_policy_kind,
        "allowed_sampling_policy_kinds": allowed_policy_kinds,
        "selected_record_count": len(selected_records),
        "selected_records": selected_records,
        "policy_sections": policy_sections,
        "source_record_count": len(event_score_records),
        "upstream_trajectory_decision_digest": readiness_decision[
            "upstream_trajectory_decision_digest"
        ],
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "requires_real_gpu_validation": False,
    }
    plan_payload["selection_plan_digest"] = compute_object_digest(
        _without_digest(plan_payload, "selection_plan_digest")
    )
    return plan_payload


def _build_blocked_plan(
    readiness_decision: dict[str, Any],
    selected_policy_kind: str,
    allowed_policy_kinds: list[str],
    event_score_records: list[dict[str, Any]],
) -> dict[str, Any]:
    blocking_reasons = _as_string_list(
        readiness_decision.get("TrajectoryAwareSamplingBlockingReasons", [])
    )
    plan_payload: dict[str, Any] = {
        "selection_output_kind": "record_digest_selection_plan",
        "SamplingSelectionPlanDecision": "INCONCLUSIVE",
        "SamplingSelectionBlockingReasons": blocking_reasons,
        "SamplingReadinessDecision": readiness_decision.get("SamplingReadinessDecision"),
        "selected_sampling_policy_kind": selected_policy_kind,
        "allowed_sampling_policy_kinds": allowed_policy_kinds,
        "selected_record_count": 0,
        "selected_records": [],
        "policy_sections": {},
        "source_record_count": len(event_score_records),
        "upstream_trajectory_decision_digest": readiness_decision.get(
            "upstream_trajectory_decision_digest"
        ),
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "requires_real_gpu_validation": False,
    }
    plan_payload["selection_plan_digest"] = compute_object_digest(
        _without_digest(plan_payload, "selection_plan_digest")
    )
    return plan_payload


def _build_policy_section(
    event_score_records: list[dict[str, Any]],
    policy_kind: str,
    limit: int,
) -> dict[str, Any]:
    if policy_kind == "trajectory_ranked_replay":
        candidates = _build_trajectory_ranked_candidates(event_score_records)
    elif policy_kind == "control_balanced_replay":
        candidates = _build_control_balanced_candidates(event_score_records)
    else:
        candidates = []
    selected_records = candidates[:limit]
    return {
        "sampling_policy_kind": policy_kind,
        "candidate_record_count": len(candidates),
        "selected_record_count": len(selected_records),
        "selected_records": selected_records,
    }


def _build_trajectory_ranked_candidates(
    event_score_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = [
        _summarize_record(record, "trajectory_ranked_replay")
        for record in event_score_records
        if _is_trajectory_ranked_candidate(record)
    ]
    if not candidates:
        candidates = [
            _summarize_record(record, "trajectory_ranked_replay")
            for record in event_score_records
            if _as_number(record.get("evidence_scores", {}).get("S_traj")) is not None
        ]
    return sorted(
        candidates,
        key=lambda candidate: (
            -float(candidate["trajectory_rank_score"]),
            str(candidate["method_variant"]),
            str(candidate["attack_name"]),
            str(candidate["sample_id"]),
            str(candidate["event_id"]),
        ),
    )


def _build_control_balanced_candidates(
    event_score_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates = [
        _summarize_record(record, "control_balanced_replay")
        for record in event_score_records
        if isinstance(
            record.get("mechanism_trace", {}).get("trajectory_control_scores"),
            dict,
        )
    ]
    grouped_candidates: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        grouped_candidates.setdefault(str(candidate["sample_role"]), []).append(candidate)

    balanced_records: list[dict[str, Any]] = []
    for sample_role in sorted(grouped_candidates):
        role_candidates = sorted(
            grouped_candidates[sample_role],
            key=lambda candidate: (
                -float(candidate["control_abs_max"]),
                str(candidate["method_variant"]),
                str(candidate["attack_name"]),
                str(candidate["sample_id"]),
                str(candidate["event_id"]),
            ),
        )
        balanced_records.extend(role_candidates)
    return balanced_records


def _is_trajectory_ranked_candidate(record: dict[str, Any]) -> bool:
    return (
        record.get("split") == "test"
        and record.get("sample_role") == "attacked_positive"
        and record.get("method_variant") in TRAJECTORY_ENABLED_METHOD_VARIANTS
        and _as_number(record.get("evidence_scores", {}).get("S_traj")) is not None
    )


def _summarize_record(record: dict[str, Any], policy_kind: str) -> dict[str, Any]:
    evidence_scores = record.get("evidence_scores", {})
    mechanism_trace = record.get("mechanism_trace", {})
    s_traj = _as_number(evidence_scores.get("S_traj")) or 0.0
    s_final = _as_number(evidence_scores.get("S_final")) or 0.0
    control_scores = mechanism_trace.get("trajectory_control_scores")
    control_abs_max = _max_abs_control_score(control_scores)
    trajectory_runtime_ms = _as_number(mechanism_trace.get("trajectory_runtime_ms"))
    summary = {
        "record_digest": _compute_record_selection_digest(record),
        "event_id": str(record.get("event_id", "")),
        "sample_id": str(record.get("sample_id", "")),
        "split": str(record.get("split", "")),
        "sample_role": str(record.get("sample_role", "")),
        "method_variant": str(record.get("method_variant", "")),
        "attack_name": str(record.get("attack_name", "")),
        "selection_policy_kind": policy_kind,
        "S_traj": round(s_traj, 6),
        "S_final": round(s_final, 6),
        "trajectory_rank_score": round(s_traj + max(s_final, 0.0), 6),
        "control_abs_max": round(control_abs_max, 6),
        "trajectory_runtime_ms": round(trajectory_runtime_ms, 6)
        if trajectory_runtime_ms is not None
        else None,
    }
    return summary


def _compute_record_selection_digest(record: dict[str, Any]) -> str:
    digest_payload = {
        "event_id": record.get("event_id"),
        "sample_id": record.get("sample_id"),
        "split": record.get("split"),
        "sample_role": record.get("sample_role"),
        "method_variant": record.get("method_variant"),
        "attack_name": record.get("attack_name"),
        "evidence_scores": record.get("evidence_scores", {}),
        "trajectory_control_scores": record.get("mechanism_trace", {}).get(
            "trajectory_control_scores"
        ),
        "trajectory_runtime_ms": record.get("mechanism_trace", {}).get(
            "trajectory_runtime_ms"
        ),
    }
    return compute_object_digest(digest_payload)


def _max_abs_control_score(control_scores: Any) -> float:
    if not isinstance(control_scores, dict):
        return 0.0
    numeric_values = [
        abs(float(value))
        for value in control_scores.values()
        if isinstance(value, (int, float))
    ]
    return max(numeric_values, default=0.0)


def _resolve_selected_record_limit(selected_record_limit: int | None) -> int:
    if selected_record_limit is None:
        return DEFAULT_SELECTED_RECORD_LIMIT
    return max(1, int(selected_record_limit))


def _as_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _without_digest(payload: dict[str, Any], digest_field_name: str) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key != digest_field_name
    }

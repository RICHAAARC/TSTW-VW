"""
文件用途：提供阶段 2 mechanism rescue、leakage 与 anchor 语义的共享判定辅助函数。
File purpose: Provide shared helpers for stage-two mechanism rescue, leakage, and anchor semantics.
Module type: General module
"""

from __future__ import annotations

from typing import Any


DEFAULT_REQUIRED_SYNC_GAIN_ATTACKS = ("temporal_crop", "local_clip")
ALL_REQUIRED_TEMPORAL_ATTACKS_POLICY = "all_required_temporal_attacks"
ANY_REQUIRED_TEMPORAL_ATTACK_POLICY = "any_required_temporal_attack"
ANY_OF_KEY_ATTACKS_PLUS_MEAN_FLOOR_POLICY = "any_of_key_attacks_plus_mean_floor"


def build_anchor_selection_assessment(
    *,
    absolute_tprs: dict[str, float | None],
    candidate_eligible: bool,
    max_attacked_negative_fpr: float | None,
    mechanism_config: dict[str, Any],
    anchor_compatible: bool,
) -> dict[str, Any]:
    """功能：构建 tubelet-only anchor 的 headroom 与兼容性语义摘要。

    Build the semantic summary used to score tubelet-only anchors.

    Args:
        absolute_tprs: Absolute attacked-positive TPRs keyed by attack name.
        candidate_eligible: Whether the anchor satisfies the governed tubelet-only gate.
        max_attacked_negative_fpr: Maximum attacked negative FPR for the anchor.
        mechanism_config: Mechanism gate configuration.
        anchor_compatible: Whether downstream sync variants are compatible with the anchor.

    Returns:
        A dictionary containing headroom scores and anchor status fields.
    """
    required_attacks = resolve_required_sync_gain_attacks(
        mechanism_config,
        available_attacks=list(absolute_tprs.keys()),
    )
    temporal_crop_absolute_tpr = _safe_float(absolute_tprs.get("temporal_crop"))
    local_clip_absolute_tpr = _safe_float(absolute_tprs.get("local_clip"))
    temporal_crop_anchor_headroom = compute_attack_headroom(
        temporal_crop_absolute_tpr,
        mechanism_config,
    )
    local_clip_anchor_headroom = compute_attack_headroom(
        local_clip_absolute_tpr,
        mechanism_config,
    )
    required_headrooms = [
        compute_attack_headroom(_safe_float(absolute_tprs.get(attack_name)), mechanism_config)
        for attack_name in required_attacks
    ]
    temporal_headrooms = [
        compute_attack_headroom(_safe_float(absolute_tprs.get(attack_name)), mechanism_config)
        for attack_name in ("temporal_crop", "frame_dropping", "local_clip")
    ]
    rescue_headroom_score = _mean_numeric_values(required_headrooms)
    sync_headroom_score = _mean_numeric_values(temporal_headrooms)
    anchor_sync_compatibility_score = 1.0 if anchor_compatible else 0.0
    negative_margin_score = _negative_margin_score(
        max_attacked_negative_fpr,
        mechanism_config,
    )
    absolute_rescue_status = _classify_absolute_rescue_status(
        absolute_tprs,
        mechanism_config,
        required_attacks,
    )
    negative_leakage_status = classify_negative_leakage_status(
        clean_negative_fpr=None,
        max_attacked_negative_fpr=max_attacked_negative_fpr,
        mechanism_config=mechanism_config,
    )
    if not anchor_compatible:
        anchor_selection_status = "weak_anchor_incompatible"
    elif rescue_headroom_score is not None and rescue_headroom_score > 0.0:
        anchor_selection_status = (
            "strong_anchor_with_headroom"
            if candidate_eligible
            else "weak_anchor_with_headroom"
        )
    else:
        anchor_selection_status = (
            "strong_anchor_saturated"
            if candidate_eligible
            else "weak_anchor_incompatible"
        )
    return {
        "temporal_crop_absolute_tpr": temporal_crop_absolute_tpr,
        "local_clip_absolute_tpr": local_clip_absolute_tpr,
        "temporal_crop_anchor_headroom": temporal_crop_anchor_headroom,
        "local_clip_anchor_headroom": local_clip_anchor_headroom,
        "temporal_crop_saturated_anchor": is_saturated_attack(
            temporal_crop_absolute_tpr,
            mechanism_config,
        ),
        "local_clip_saturated_anchor": is_saturated_attack(
            local_clip_absolute_tpr,
            mechanism_config,
        ),
        "sync_headroom_score": sync_headroom_score,
        "rescue_headroom_score": rescue_headroom_score,
        "anchor_sync_compatibility_score": anchor_sync_compatibility_score,
        "negative_margin_score": negative_margin_score,
        "absolute_rescue_status": absolute_rescue_status,
        "negative_leakage_status": negative_leakage_status,
        "anchor_selection_status": anchor_selection_status,
        "candidate_selection_status": anchor_selection_status,
    }


def build_sync_gain_assessment(
    *,
    absolute_tprs: dict[str, float | None],
    sync_gains: dict[str, float | None],
    mean_temporal_sync_gain: float | None,
    clean_negative_fpr: float | None,
    max_attacked_negative_fpr: float | None,
    mechanism_config: dict[str, Any],
    anchor_compatible: bool = True,
) -> dict[str, Any]:
    """功能：构建 tubelet-sync 候选的 rescue 与 leakage 语义摘要。

    Build the semantic summary used to classify a tubelet-sync candidate.

    Args:
        absolute_tprs: Absolute attacked-positive TPRs keyed by attack name.
        sync_gains: Incremental sync gains keyed by attack name.
        mean_temporal_sync_gain: Mean temporal sync gain across temporal attacks.
        clean_negative_fpr: Clean negative FPR under no attack.
        max_attacked_negative_fpr: Maximum attacked negative FPR across governed attacks.
        mechanism_config: Mechanism gate configuration.
        anchor_compatible: Whether the selected anchor is compatible with the sync scan.

    Returns:
        A dictionary containing sync rescue, leakage, and candidate-selection states.
    """
    required_attacks = resolve_required_sync_gain_attacks(
        mechanism_config,
        available_attacks=list({*absolute_tprs.keys(), *sync_gains.keys()}),
    )
    min_required_attack_count = resolve_min_required_sync_gain_attack_count(
        mechanism_config,
        len(required_attacks),
    )
    positive_gain_attacks = [
        attack_name
        for attack_name in required_attacks
        if _safe_float(sync_gains.get(attack_name)) is not None
        and float(sync_gains[attack_name]) > 0.0
    ]
    saturated_anchor_attacks = [
        attack_name
        for attack_name in required_attacks
        if is_saturated_attack(_safe_float(absolute_tprs.get(attack_name)), mechanism_config)
    ]
    absolute_rescue_status = _classify_absolute_rescue_status(
        absolute_tprs,
        mechanism_config,
        required_attacks,
    )
    available_required_attacks = [
        attack_name
        for attack_name in required_attacks
        if attack_name in absolute_tprs or attack_name in sync_gains
    ]
    if len(positive_gain_attacks) >= min_required_attack_count:
        incremental_gain_status = "positive_gain"
    elif available_required_attacks and all(
        attack_name in saturated_anchor_attacks
        for attack_name in available_required_attacks
    ):
        incremental_gain_status = "saturated_no_gain"
    elif any(
        _safe_float(sync_gains.get(attack_name)) is not None
        and float(sync_gains[attack_name]) < 0.0
        for attack_name in available_required_attacks
    ):
        incremental_gain_status = "negative_gain"
    else:
        incremental_gain_status = "no_gain"

    min_mean_temporal_sync_gain = resolve_min_mean_temporal_sync_gain(mechanism_config)
    mean_floor_satisfied = (
        min_mean_temporal_sync_gain is None
        or (
            mean_temporal_sync_gain is not None
            and float(mean_temporal_sync_gain) >= float(min_mean_temporal_sync_gain)
        )
    )
    has_absolute_rescue = absolute_rescue_status != "no_absolute_rescue"
    if len(available_required_attacks) < min_required_attack_count:
        sync_rescue_decision = "INCONCLUSIVE"
    elif len(positive_gain_attacks) >= min_required_attack_count and mean_floor_satisfied:
        sync_rescue_decision = "PASS"
    elif incremental_gain_status == "saturated_no_gain" and has_absolute_rescue:
        sync_rescue_decision = "PASS"
    else:
        sync_rescue_decision = "FAIL"

    negative_leakage_status = classify_negative_leakage_status(
        clean_negative_fpr=clean_negative_fpr,
        max_attacked_negative_fpr=max_attacked_negative_fpr,
        mechanism_config=mechanism_config,
    )
    sync_leakage_decision = {
        "controlled": "PASS",
        "leakage_risk": "RISK",
        "leakage_exceeded": "FAIL",
    }[negative_leakage_status]

    if not anchor_compatible:
        candidate_selection_status = "anchor_incompatible"
    elif incremental_gain_status == "saturated_no_gain":
        candidate_selection_status = "saturated_anchor_no_increment"
    elif sync_rescue_decision == "PASS" and sync_leakage_decision == "PASS":
        candidate_selection_status = "eligible"
    elif sync_rescue_decision == "PASS":
        candidate_selection_status = "rescue_with_leakage"
    else:
        candidate_selection_status = "insufficient_signal"

    return {
        "sync_gain_policy": resolve_sync_gain_policy(mechanism_config),
        "required_sync_gain_attacks": required_attacks,
        "min_required_sync_gain_attack_count": min_required_attack_count,
        "positive_gain_attacks": positive_gain_attacks,
        "positive_gain_attack_count": len(positive_gain_attacks),
        "saturated_anchor_attacks": saturated_anchor_attacks,
        "absolute_rescue_status": absolute_rescue_status,
        "incremental_gain_status": incremental_gain_status,
        "negative_leakage_status": negative_leakage_status,
        "sync_rescue_decision": sync_rescue_decision,
        "sync_leakage_decision": sync_leakage_decision,
        "candidate_selection_status": candidate_selection_status,
        "min_mean_temporal_sync_gain": min_mean_temporal_sync_gain,
    }


def classify_negative_leakage_status(
    *,
    clean_negative_fpr: float | None,
    max_attacked_negative_fpr: float | None,
    mechanism_config: dict[str, Any],
) -> str:
    """功能：将负样本泄漏划分为受控、风险或超限。

    Classify negative leakage as controlled, at risk, or exceeded.

    Args:
        clean_negative_fpr: Clean negative FPR.
        max_attacked_negative_fpr: Maximum attacked negative FPR.
        mechanism_config: Mechanism gate configuration.

    Returns:
        A negative leakage status string.
    """
    max_clean_negative_fpr = _safe_float(mechanism_config.get("max_clean_negative_fpr"))
    max_attacked_fpr = _safe_float(mechanism_config.get("max_attacked_negative_fpr"))
    leakage_exceeded_multiplier = _safe_float(
        mechanism_config.get("leakage_exceeded_multiplier")
    )
    if leakage_exceeded_multiplier is None or leakage_exceeded_multiplier < 1.0:
        leakage_exceeded_multiplier = 2.0
    clean_failure = (
        max_clean_negative_fpr is not None
        and clean_negative_fpr is not None
        and float(clean_negative_fpr) > float(max_clean_negative_fpr)
    )
    attacked_failure = (
        max_attacked_fpr is not None
        and max_attacked_negative_fpr is not None
        and float(max_attacked_negative_fpr) > float(max_attacked_fpr)
    )
    if not clean_failure and not attacked_failure:
        return "controlled"
    if clean_failure:
        return "leakage_exceeded"
    if (
        max_attacked_fpr is not None
        and max_attacked_negative_fpr is not None
        and float(max_attacked_negative_fpr)
        > float(max_attacked_fpr) * float(leakage_exceeded_multiplier)
    ):
        return "leakage_exceeded"
    return "leakage_risk"


def compute_attack_headroom(
    attack_positive_tpr: float | None,
    mechanism_config: dict[str, Any],
) -> float | None:
    """Return remaining attack headroom before the configured saturation threshold."""
    if attack_positive_tpr is None:
        return None
    saturation_threshold = resolve_saturation_threshold(mechanism_config)
    return round(max(0.0, float(saturation_threshold) - float(attack_positive_tpr)), 6)


def is_saturated_attack(
    attack_positive_tpr: float | None,
    mechanism_config: dict[str, Any],
) -> bool:
    """Return whether an attack TPR reaches the configured saturation threshold."""
    if attack_positive_tpr is None:
        return False
    return float(attack_positive_tpr) >= float(resolve_saturation_threshold(mechanism_config))


def resolve_min_mean_temporal_sync_gain(mechanism_config: dict[str, Any]) -> float | None:
    """Return the configured mean temporal sync-gain floor."""
    configured_value = _safe_float(mechanism_config.get("min_mean_temporal_sync_gain"))
    if configured_value is not None:
        return configured_value
    return _safe_float(
        mechanism_config.get("min_tubelet_sync_gain_over_tubelet_only_temporal")
    )


def resolve_min_required_sync_gain_attack_count(
    mechanism_config: dict[str, Any],
    required_attack_count: int,
) -> int:
    """Return the configured minimum count of required attacks with positive sync gain."""
    configured_value = mechanism_config.get("min_required_sync_gain_attack_count")
    if isinstance(configured_value, int) and configured_value > 0:
        return min(required_attack_count, configured_value)
    if resolve_sync_gain_policy(mechanism_config) == ALL_REQUIRED_TEMPORAL_ATTACKS_POLICY:
        return required_attack_count
    return 1 if required_attack_count > 0 else 0


def resolve_required_sync_gain_attacks(
    mechanism_config: dict[str, Any],
    *,
    available_attacks: list[str] | None = None,
) -> list[str]:
    """Return the required attacks used by the sync gain policy."""
    configured_value = mechanism_config.get("required_sync_gain_attacks")
    if isinstance(configured_value, list):
        resolved_attacks = [
            str(attack_name)
            for attack_name in configured_value
            if isinstance(attack_name, str) and attack_name
        ]
        if resolved_attacks:
            return resolved_attacks
    fallback_attacks = list(DEFAULT_REQUIRED_SYNC_GAIN_ATTACKS)
    if available_attacks is None:
        return fallback_attacks
    filtered_attacks = [
        attack_name
        for attack_name in fallback_attacks
        if attack_name in set(available_attacks)
    ]
    return filtered_attacks or list(available_attacks)


def resolve_saturation_threshold(mechanism_config: dict[str, Any]) -> float:
    """Return the configured anchor saturation threshold."""
    configured_value = _safe_float(mechanism_config.get("sync_gain_saturation_threshold"))
    if configured_value is None:
        return 1.0
    return float(configured_value)


def resolve_sync_gain_policy(mechanism_config: dict[str, Any]) -> str:
    """Return the configured sync gain policy name."""
    configured_policy = str(
        mechanism_config.get("sync_gain_policy", ALL_REQUIRED_TEMPORAL_ATTACKS_POLICY)
    ).strip()
    if configured_policy in {
        ALL_REQUIRED_TEMPORAL_ATTACKS_POLICY,
        ANY_REQUIRED_TEMPORAL_ATTACK_POLICY,
        ANY_OF_KEY_ATTACKS_PLUS_MEAN_FLOOR_POLICY,
    }:
        return configured_policy
    return ALL_REQUIRED_TEMPORAL_ATTACKS_POLICY


def _classify_absolute_rescue_status(
    absolute_tprs: dict[str, float | None],
    mechanism_config: dict[str, Any],
    required_attacks: list[str],
) -> str:
    absolute_success_threshold = _safe_float(
        mechanism_config.get("absolute_rescue_tpr_threshold")
    )
    if absolute_success_threshold is None:
        absolute_success_threshold = resolve_saturation_threshold(mechanism_config)
    successful_attacks = [
        attack_name
        for attack_name in required_attacks
        if _safe_float(absolute_tprs.get(attack_name)) is not None
        and float(absolute_tprs[attack_name]) >= float(absolute_success_threshold)
    ]
    if not successful_attacks:
        return "no_absolute_rescue"
    if len(successful_attacks) == 1:
        return f"{successful_attacks[0]}_absolute_success"
    return "multi_attack_absolute_success"


def _mean_numeric_values(values: list[float | None]) -> float | None:
    numeric_values = [float(value) for value in values if value is not None]
    if not numeric_values:
        return None
    return round(sum(numeric_values) / len(numeric_values), 6)


def _negative_margin_score(
    max_attacked_negative_fpr: float | None,
    mechanism_config: dict[str, Any],
) -> float:
    max_allowed_attacked_negative_fpr = _safe_float(
        mechanism_config.get("max_attacked_negative_fpr")
    )
    if (
        max_allowed_attacked_negative_fpr is None
        or max_allowed_attacked_negative_fpr <= 0.0
        or max_attacked_negative_fpr is None
    ):
        return 0.0
    if float(max_attacked_negative_fpr) >= float(max_allowed_attacked_negative_fpr):
        return 0.0
    return round(
        (
            float(max_allowed_attacked_negative_fpr)
            - float(max_attacked_negative_fpr)
        )
        / float(max_allowed_attacked_negative_fpr),
        6,
    )


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
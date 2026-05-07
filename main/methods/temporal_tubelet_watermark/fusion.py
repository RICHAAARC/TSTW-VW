"""
文件用途：提供阶段 0 方法骨架的 fusion 规则。
File purpose: Provide stage-0 scaffold fusion rules.
Module type: General module
"""

from __future__ import annotations

from collections.abc import Callable


EVIDENCE_ENABLEMENT_ORDER = ("tubelet", "sync", "trajectory")


def build_disabled_evidence(enabled_evidence: dict[str, bool]) -> list[str]:
    """功能：根据 evidence 开关生成禁用列表。

    Build the disabled evidence list from an enablement mapping.

    Args:
        enabled_evidence: Evidence enablement mapping.

    Returns:
        A stable list of disabled evidence names.
    """
    if not isinstance(enabled_evidence, dict):
        raise TypeError("enabled_evidence must be a dictionary")
    disabled_evidence = [
        evidence_name
        for evidence_name in EVIDENCE_ENABLEMENT_ORDER
        if not bool(enabled_evidence.get(evidence_name, False))
    ]
    return disabled_evidence


def constant_zero_fusion_placeholder(evidence_scores: dict[str, float | None]) -> float:
    """功能：返回常数零分数的 placeholder fusion。

    Return a constant-zero final score for the placeholder method.

    Args:
        evidence_scores: Governed evidence score payload.

    Returns:
        The placeholder final score.
    """
    if not isinstance(evidence_scores, dict):
        raise TypeError("evidence_scores must be a dictionary")
    return 0.0


def random_score_linear_fusion_random(evidence_scores: dict[str, float | None]) -> float:
    """功能：对可用 evidence 分数做简单平均。

    Compute a simple average over available evidence scores.

    Args:
        evidence_scores: Governed evidence score payload.

    Returns:
        The averaged final score.
    """
    if not isinstance(evidence_scores, dict):
        raise TypeError("evidence_scores must be a dictionary")
    available_scores = [
        float(evidence_scores[score_name])
        for score_name in ("S_tubelet", "S_sync", "S_traj")
        if evidence_scores.get(score_name) is not None
    ]
    if not available_scores:
        # 中文注释：当没有有效 evidence 时，阶段 0 仍需返回稳定分数而非抛弃字段。
        return 0.0
    return round(sum(available_scores) / len(available_scores), 6)


def tubelet_score_only(evidence_scores: dict[str, float | None]) -> float:
    """功能：返回 tubelet 分支分数作为最终分数。

    Return the tubelet score as the governed final score.

    Args:
        evidence_scores: Governed evidence score payload.

    Returns:
        The tubelet-only final score.
    """
    if not isinstance(evidence_scores, dict):
        raise TypeError("evidence_scores must be a dictionary")
    tubelet_score = evidence_scores.get("S_tubelet")
    if tubelet_score is None:
        return 0.0
    return round(float(tubelet_score), 6)


def calibrated_tubelet_sync(evidence_scores: dict[str, float | None]) -> float:
    """功能：融合 tubelet 与 sync 分支分数。

    Fuse the tubelet and synchronization scores for the formal synthetic probe.

    Args:
        evidence_scores: Governed evidence score payload.

    Returns:
        The fused final score.
    """
    if not isinstance(evidence_scores, dict):
        raise TypeError("evidence_scores must be a dictionary")
    tubelet_score = evidence_scores.get("S_tubelet")
    sync_score = evidence_scores.get("S_sync")
    if tubelet_score is None and sync_score is None:
        return 0.0
    if tubelet_score is None:
        return round(float(sync_score), 6)
    if sync_score is None or float(sync_score) <= 0.0:
        return round(float(tubelet_score), 6)
    return round((0.65 * float(tubelet_score)) + (0.35 * float(sync_score)), 6)


def get_fusion_rule(fusion_rule: str) -> Callable[[dict[str, float | None]], float]:
    """功能：根据配置名解析 fusion 规则。

    Resolve a fusion rule callable from its governed name.

    Args:
        fusion_rule: Governed fusion rule name.

    Returns:
        A callable that computes the final score.
    """
    if not isinstance(fusion_rule, str) or not fusion_rule:
        raise ValueError("fusion_rule must be a non-empty string")
    if fusion_rule == "constant_zero_fusion_placeholder":
        return constant_zero_fusion_placeholder
    if fusion_rule == "random_score_linear_fusion_random":
        return random_score_linear_fusion_random
    if fusion_rule == "tubelet_score_only":
        return tubelet_score_only
    if fusion_rule == "calibrated_tubelet_sync":
        return calibrated_tubelet_sync
    raise ValueError(f"unsupported fusion_rule: {fusion_rule}")
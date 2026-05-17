"""
文件用途：在阈值标定完成后把最终 decision 物化回 governed event score records。
File purpose: Materialize threshold-based final decisions back onto governed event score records.
Module type: General module
"""

from __future__ import annotations

from typing import Any


def materialize_threshold_decisions(
    event_score_records: list[dict[str, Any]],
    threshold_record: dict[str, Any] | None,
    *,
    attach_threshold_id: bool,
) -> list[dict[str, Any]]:
    """功能：基于 threshold record 回填最终 decision。

    Materialize final binary decisions from a governed threshold record.

    Args:
        event_score_records: Candidate governed event score records.
        threshold_record: Threshold record that provides threshold_value and threshold_id.
        attach_threshold_id: Whether the returned records should be stamped with threshold_id.

    Returns:
        A new list of governed event score records with materialized decisions.
    """
    if not isinstance(event_score_records, list):
        raise TypeError("event_score_records must be a list")
    if threshold_record is not None and not isinstance(threshold_record, dict):
        raise TypeError("threshold_record must be a dictionary or None")

    threshold_value = None if threshold_record is None else _safe_float(
        threshold_record.get("threshold_value")
    )
    threshold_id = None
    if attach_threshold_id and isinstance(threshold_record, dict):
        raw_threshold_id = threshold_record.get("threshold_id")
        if isinstance(raw_threshold_id, str) and raw_threshold_id:
            threshold_id = raw_threshold_id

    materialized_records: list[dict[str, Any]] = []
    for event_score_record in event_score_records:
        if not isinstance(event_score_record, dict):
            raise TypeError("each event_score_record must be a dictionary")
        materialized_record = dict(event_score_record)
        if threshold_value is not None:
            materialized_record["decision"] = _threshold_decision(
                event_score_record,
                threshold_value,
            )
        if attach_threshold_id:
            materialized_record["threshold_id"] = threshold_id
        materialized_records.append(materialized_record)
    return materialized_records


def _threshold_decision(event_score_record: dict[str, Any], threshold_value: float) -> bool:
    evidence_scores = event_score_record.get("evidence_scores", {})
    if not isinstance(evidence_scores, dict):
        return False
    final_score = _safe_float(evidence_scores.get("S_final"))
    if final_score is None:
        return False
    return float(final_score) >= float(threshold_value)


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
"""
文件用途：导出阶段 2 scaffold 的失败样例索引。
File purpose: Export the failure-case gallery index for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_failure_case_gallery(
    event_score_records: list[dict[str, Any]],
    output_dir: str | Path,
) -> Path:
    """功能：导出失败样例索引 JSON。

    Export a JSON index for stage-two detection and quality failure cases.

    Args:
        event_score_records: Event score record list.
        output_dir: Failure gallery directory.

    Returns:
        The written index path.
    """
    if not isinstance(event_score_records, list):
        raise TypeError("event_score_records must be a list")
    gallery_dir = Path(output_dir)
    gallery_dir.mkdir(parents=True, exist_ok=True)
    failure_entries: list[dict[str, Any]] = []
    for event_score_record in event_score_records:
        quality_metrics = event_score_record.get("quality_metrics", {})
        temporal_metrics = event_score_record.get("temporal_metrics", {})
        if event_score_record.get("failure_reason") is not None:
            failure_entries.append(
                {
                    "event_id": event_score_record["event_id"],
                    "failure_category": "detector_failure",
                    "failure_reason": event_score_record["failure_reason"],
                }
            )
            continue
        if (
            event_score_record.get("sample_role") == "attacked_positive"
            and not bool(event_score_record.get("decision"))
        ):
            failure_entries.append(
                {
                    "event_id": event_score_record["event_id"],
                    "failure_category": "missed_attacked_positive",
                    "failure_reason": "attacked_positive_false_negative",
                }
            )
        if quality_metrics.get("quality_failure_reason") is not None:
            failure_entries.append(
                {
                    "event_id": event_score_record["event_id"],
                    "failure_category": "quality_failure",
                    "failure_reason": quality_metrics["quality_failure_reason"],
                }
            )
        if isinstance(temporal_metrics.get("flicker_score"), (int, float)) and float(
            temporal_metrics["flicker_score"]
        ) > 0.25:
            failure_entries.append(
                {
                    "event_id": event_score_record["event_id"],
                    "failure_category": "temporal_failure",
                    "failure_reason": "flicker_score_above_placeholder_threshold",
                }
            )
    index_path = gallery_dir / "index.json"
    index_path.write_text(
        json.dumps(failure_entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index_path
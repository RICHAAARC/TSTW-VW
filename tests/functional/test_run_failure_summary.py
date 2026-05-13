"""
文件用途：验证运行失败摘要脚本对 records、checker 与 timing 失败的汇总行为。
File purpose: Validate run-failure summary behavior across records, checker outputs, and timing failures.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_results.summarize_run_failures import summarize_run_failures


pytestmark = pytest.mark.quick


def test_run_failure_summary_reads_records_checker_and_timing(tmp_path: Path) -> None:
    """Validate failure-summary aggregation across governed artifacts.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    records_path = run_root / "records" / "event_scores.jsonl"
    timing_events_path = run_root / "runtime_profile" / "run_timing_events.jsonl"
    formal_validation_path = run_root / "runtime_profile" / "formal_validation_summary.json"
    output_json = run_root / "runtime_profile" / "run_failure_summary.json"
    output_md = run_root / "runtime_profile" / "run_failure_summary.md"

    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(
        "\n".join(
            [
                json.dumps({"event_id": 1, "failure_reason": "decode_error"}, ensure_ascii=False),
                json.dumps({"event_id": 2, "failure_reason": "decode_error"}, ensure_ascii=False),
                json.dumps({"event_id": 3, "failure_reason": "attack_timeout"}, ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    timing_events_path.parent.mkdir(parents=True, exist_ok=True)
    timing_events_path.write_text(
        json.dumps(
            {
                "event_name": "real_video_vae_latent_runner",
                "status": "failed",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    formal_validation_path.write_text(
        json.dumps(
            {
                "status": False,
                "BlockingReasons": ["missing_temporal_consistency_table"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = summarize_run_failures(
        run_root=run_root,
        output_json=output_json,
        output_md=output_md,
    )

    assert payload["record_failure_count"] == 3
    assert payload["failure_reason_counts"] == {"attack_timeout": 1, "decode_error": 2}
    assert payload["checker_status"] is False
    assert payload["checker_blocking_reasons"] == ["missing_temporal_consistency_table"]
    assert payload["runtime_profile_failures"] == ["real_video_vae_latent_runner"]
    assert payload["dominant_failure_category"] == "checker_blocking_reason"
    assert output_json.exists()
    assert output_md.exists()
    assert "decode_error: 2" in output_md.read_text(encoding="utf-8")

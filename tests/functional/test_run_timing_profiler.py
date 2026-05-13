"""
文件用途：验证运行时间记录器与 timing 汇总脚本的功能合同。
File purpose: Validate the runtime timing recorder and summary-script contracts.
Module type: Functional test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.profile_runtime.profile_run_timing import RunTimingRecorder
from scripts.profile_runtime.summarize_run_timing import summarize_run_timing


pytestmark = pytest.mark.quick


def test_run_timing_recorder_tracks_ok_and_failed_events(tmp_path: Path) -> None:
    """Validate the recorder writes both successful and failed timing events.

    Args:
        tmp_path: Temporary run root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    recorder = RunTimingRecorder(run_root=run_root, run_id="timing_smoke")

    with recorder.event("runtime_preflight", run_mode="formal", runtime_profile="formal"):
        pass

    with pytest.raises(ValueError, match="timing failure"):
        with recorder.event("real_video_vae_latent_runner", run_mode="formal"):
            raise ValueError("timing failure")

    events_path = run_root / "runtime_profile" / "run_timing_events.jsonl"
    output_json = run_root / "runtime_profile" / "run_timing_summary.json"
    output_md = run_root / "runtime_profile" / "run_timing_report.md"
    records = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = summarize_run_timing(
        run_root=run_root,
        events_jsonl=events_path,
        output_json=output_json,
        output_md=output_md,
    )

    assert len(records) == 2
    assert records[0]["status"] == "ok"
    assert records[1]["status"] == "failed"
    assert records[1]["error_type"] == "ValueError"
    assert summary["event_count"] == 2
    assert summary["failed_event_count"] == 1
    assert "runtime_preflight" in summary["events_by_name"]
    assert output_json.exists()
    assert output_md.exists()

"""
文件用途：验证阶段 2 scaffold event records 的扩展字段与产物布局。
File purpose: Validate extended fields and artifact layout for stage-two scaffold event records.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from main.core.records import RecordWriter
from tests.stage2_test_support import run_stage2_tiny


@pytest.mark.smoke
def test_stage2_event_records_include_quality_and_temporal_payloads(tmp_path: Path) -> None:
    """Validate that stage-two event records include quality and temporal payloads.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = run_stage2_tiny(tmp_path)
    record_writer = RecordWriter(output_root)
    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    run_manifest = json.loads(
        (output_root / "artifacts" / "run_manifest.json").read_text(encoding="utf-8")
    )

    assert event_score_records
    assert threshold_records
    assert run_manifest["construction_phase"] == "real_video_vae_latent_probe"
    for event_score_record in event_score_records:
        assert event_score_record["evidence_scores"]["S_traj"] is None
        assert "quality_metrics" in event_score_record
        assert "temporal_metrics" in event_score_record
        assert event_score_record["mechanism_trace"]["construction_phase"] == "real_video_vae_latent_probe"
        assert event_score_record["mechanism_trace"]["encoded_latent_digest"]
        assert event_score_record["mechanism_trace"]["video_source_digest"]
        assert not Path(event_score_record["mechanism_trace"]["video_source_relpath"]).is_absolute()
    assert all(
        threshold_record["threshold_id"].endswith(":real_video_vae_latent_probe")
        for threshold_record in threshold_records
    )

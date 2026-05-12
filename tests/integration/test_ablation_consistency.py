"""
文件用途：验证 active formal stage 的方法变体共享同一 protocol 口径。
File purpose: Validate that the active-stage method variants share one governed protocol.
Module type: General module
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from experiments.synthetic_tubelet_sync_probe.ablation_runner import AblationRunner
from main.core.records import RecordWriter


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.smoke
def test_active_stage_ablation_variants_share_split_and_attack_matrix(tmp_path: Path) -> None:
    """Validate that active-stage method variants share split plan, attack matrix, and target FPR.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2, runtime_profile_override="tiny")
    event_score_records = RecordWriter(output_root).read_event_score_records()

    method_variants = sorted(
        {event_score_record["method_variant"] for event_score_record in event_score_records}
    )
    assert method_variants == [
        "frame_prc",
        "tubelet_only",
        "tubelet_only_lt01",
        "tubelet_sync",
    ]
    derived_records = [
        event_score_record
        for event_score_record in event_score_records
        if event_score_record["method_variant"] == "tubelet_only_lt01"
    ]
    assert derived_records
    assert {record["base_method_variant"] for record in derived_records} == {"tubelet_only"}
    assert {record["derived_variant"] for record in derived_records} == {True}
    assert {record["ablation_axis"] for record in derived_records} == {"tubelet_length"}
    assert {record["tubelet_length"] for record in derived_records} == {1}
    primary_records = [
        event_score_record
        for event_score_record in event_score_records
        if event_score_record["method_variant"] in {"frame_prc", "tubelet_only", "tubelet_sync"}
    ]
    assert all(
        record["base_method_variant"] == record["method_variant"]
        and not record["derived_variant"]
        and record["ablation_axis"] is None
        for record in primary_records
    )
    assert {event_score_record["target_fpr"] for event_score_record in event_score_records} == {0.001}
    assert {event_score_record["attack_name"] for event_score_record in event_score_records} == {
        "frame_dropping",
        "latent_gaussian_noise",
        "local_clip",
        "no_attack",
        "speed_change",
        "temporal_crop",
    }

    variant_plans = {
        method_variant: sorted(
            (
                event_score_record["split"],
                event_score_record["sample_role"],
                event_score_record["sample_id"],
                event_score_record["attack_name"],
            )
            for event_score_record in event_score_records
            if event_score_record["method_variant"] == method_variant
        )
        for method_variant in method_variants
    }
    assert len({tuple(variant_plan) for variant_plan in variant_plans.values()}) == 1

    local_clip_rows = list(
        csv.DictReader(
            RecordWriter(output_root).output_paths.local_clip_curve_path.open(
                encoding="utf-8"
            )
        )
    )
    assert {int(row["clip_length"]) for row in local_clip_rows} == {4, 8}

    tubelet_rows = list(
        csv.DictReader(
            RecordWriter(output_root).output_paths.tubelet_length_ablation_path.open(
                encoding="utf-8"
            )
        )
    )
    assert {int(row["tubelet_length"]) for row in tubelet_rows} == {1, 4}

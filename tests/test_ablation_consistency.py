"""
文件用途：验证 active formal stage 的方法变体共享同一 protocol 口径。
File purpose: Validate that the active-stage method variants share one governed protocol.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.core.records import RecordWriter
from main.protocol.ablation_runner import AblationRunner


ROOT = Path(__file__).resolve().parents[1]


def test_active_stage_ablation_variants_share_split_and_attack_matrix(tmp_path: Path) -> None:
    """Validate that active-stage method variants share split plan, attack matrix, and target FPR.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2)
    event_score_records = RecordWriter(output_root).read_event_score_records()

    method_variants = sorted(
        {event_score_record["method_variant"] for event_score_record in event_score_records}
    )
    assert method_variants == [
        "frame_prc",
        "tubelet_only",
        "tubelet_sync",
    ]
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
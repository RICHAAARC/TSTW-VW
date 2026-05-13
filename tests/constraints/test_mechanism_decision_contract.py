"""
文件用途：验证 Stage2MechanismDecision 的门禁语义与字段完整性。
File purpose: Validate the gate semantics and payload structure of Stage2MechanismDecision.
Module type: General module
"""

from __future__ import annotations

import pytest

from experiments.real_video_vae_latent_probe.mechanism_audit import (
    build_stage2_mechanism_decision,
)


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_stage2_mechanism_decision_inconclusive_when_sample_counts_insufficient() -> None:
    """Validate insufficient sample counts yield INCONCLUSIVE rather than FAIL.

    Args:
        None.

    Returns:
        None.
    """
    event_score_records = [
        {
            "run_id": "real_video_vae_latent_probe_formal",
            "split": "test",
            "method_variant": method_variant,
            "attack_name": attack_name,
            "sample_role": sample_role,
            "decision": decision,
            "target_fpr": 0.001,
            "evidence_scores": {"S_tubelet": 0.1, "S_sync": None, "S_traj": None, "S_final": 0.1},
            "quality_metrics": {"watermarked_video_psnr": 24.0, "watermarked_video_ssim": 0.7},
            "temporal_metrics": {"temporal_consistency_score": 0.9, "flicker_score": 0.1},
        }
        for method_variant, attack_name, sample_role, decision in (
            ("frame_prc", "no_attack", "clean_negative", False),
            ("frame_prc", "no_attack", "watermarked_positive", True),
            ("tubelet_only", "no_attack", "clean_negative", False),
            ("tubelet_only", "no_attack", "watermarked_positive", False),
            ("tubelet_sync", "no_attack", "clean_negative", False),
            ("tubelet_sync", "no_attack", "watermarked_positive", False),
        )
    ]
    mechanism_config = {
        "construction_phase": "real_video_vae_latent_probe",
        "minimum_positive_count_per_key": 20,
        "minimum_negative_count_per_key": 20,
        "required_main_variants": ["frame_prc", "tubelet_only", "tubelet_sync"],
        "required_mechanism_attacks": ["no_attack", "local_clip"],
        "max_clean_negative_fpr": 0.05,
        "max_attacked_negative_fpr": 0.1,
        "min_no_attack_clean_positive_tpr": 0.5,
        "min_tubelet_only_gain_over_frame_prc": 0.0,
        "min_tubelet_sync_gain_over_tubelet_only_temporal": 0.1,
        "min_sync_positive_negative_score_gap": 0.05,
        "require_quality_not_collapsed": True,
        "min_watermarked_video_psnr": 20.0,
        "min_watermarked_video_ssim": 0.5,
    }
    governance_summary_row = {
        "real_video_vae_latent_decision": "PASS",
        "next_allowed_stage": "trajectory_statistic_probe",
    }

    result = build_stage2_mechanism_decision(
        event_score_records=event_score_records,
        threshold_records=[],
        mechanism_config=mechanism_config,
        governance_summary_row=governance_summary_row,
        runtime_config={},
        target_fpr=0.001,
    )

    assert result["Stage2ImplementationDecision"] == "PASS"
    assert result["Stage2MechanismDecision"] == "INCONCLUSIVE"
    assert "sample_count_insufficient" in result["Stage2MechanismBlockingReasons"]
    assert result["NextAllowedStageByImplementation"] == "trajectory_statistic_probe"
    assert result["NextAllowedStageByMechanism"] == "remain_in_real_video_vae_latent_probe"
    assert result["RecommendedNextAction"] == "stage2_mechanism_calibration_run"
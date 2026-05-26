"""
文件用途：验证 Stage2MechanismDecision 的门禁语义与字段完整性。
File purpose: Validate the gate semantics and payload structure of Stage2MechanismDecision.
Module type: General module
"""

from __future__ import annotations

import inspect

import pytest

from experiments.real_video_vae_latent_probe.mechanism_audit import (
    build_stage2_mechanism_decision,
)
from scripts.check_results import select_stage2_mechanism_candidate


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


def test_mechanism_decision_blocks_when_any_variant_exceeds_attacked_negative_fpr() -> None:
    """验证 attacked-negative 门禁按最差方法变体计数, 不允许被跨方法均值稀释。"""
    required_variants = ["frame_prc", "tubelet_only", "tubelet_sync"]
    event_score_records = [
        _build_decision_event_record(
            method_variant=method_variant,
            attack_name=attack_name,
            sample_role=sample_role,
            decision=decision,
        )
        for method_variant in required_variants
        for attack_name, sample_role, decision in (
            ("no_attack", "clean_negative", False),
            ("no_attack", "watermarked_positive", True),
            ("local_clip", "attacked_negative", method_variant == "frame_prc"),
            ("local_clip", "attacked_positive", method_variant == "tubelet_sync"),
        )
    ]
    mechanism_config = {
        "construction_phase": "real_video_vae_latent_probe",
        "minimum_positive_count_per_key": 1,
        "minimum_negative_count_per_key": 1,
        "required_main_variants": required_variants,
        "required_mechanism_attacks": ["no_attack", "local_clip"],
        "required_sync_gain_attacks": ["local_clip"],
        "max_clean_negative_fpr": 0.05,
        "max_attacked_negative_fpr": 0.5,
        "min_no_attack_clean_positive_tpr": 0.0,
        "min_mean_temporal_sync_gain": 0.0,
        "require_quality_not_collapsed": False,
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
        runtime_config={
            "quality_metrics": {"enable_lpips": True, "enable_clip_similarity": True},
            "temporal_metrics": {"enable_motion_consistency": True},
        },
        target_fpr=0.001,
    )

    assert result["Stage2MechanismDecision"] == "FAIL"
    assert "attacked_negative_fpr_not_controlled" in result["Stage2MechanismBlockingReasons"]


def test_mechanism_candidate_selector_has_no_local_clip_only_sync_confident_counter() -> None:
    """验证 selector 不再保留只统计 local_clip 的旧 sync_confident 负样本计数器。"""
    selector_source = inspect.getsource(select_stage2_mechanism_candidate)

    assert "_count_local_clip_attacked_negative_sync_confident_records" not in selector_source


def _build_decision_event_record(
    *,
    method_variant: str,
    attack_name: str,
    sample_role: str,
    decision: bool,
) -> dict[str, object]:
    return {
        "run_id": "real_video_vae_latent_probe_formal",
        "split": "test",
        "method_variant": method_variant,
        "attack_name": attack_name,
        "sample_role": sample_role,
        "decision": decision,
        "target_fpr": 0.001,
        "evidence_scores": {
            "S_tubelet": 0.8 if decision else 0.1,
            "S_sync": 0.4 if method_variant == "tubelet_sync" and decision else -0.1,
            "S_traj": None,
            "S_final": 0.8 if decision else 0.1,
        },
        "quality_metrics": {
            "watermarked_video_psnr": 24.0,
            "watermarked_video_ssim": 0.7,
            "watermarked_video_lpips": 0.1,
            "clip_similarity_score": 0.9,
        },
        "temporal_metrics": {
            "temporal_consistency_score": 0.9,
            "flicker_score": 0.1,
            "motion_consistency_score": 0.8,
        },
    }

"""
File purpose: Validate sync-rescue fusion semantics for the synthetic tubelet probe.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

from main.attacks.temporal import TemporalAttackPlaceholder
from main.backends.synthetic_video_latent import SyntheticVideoLatentPlaceholder
from main.methods.temporal_tubelet_watermark.fusion import sync_rescue_fusion
from main.methods.temporal_tubelet_watermark.method_placeholder import build_method_from_config


TUBELET_ONLY_CONFIG = {
    "method_family": "temporal_tubelet_watermark",
    "method_variant": "tubelet_only",
    "method_status": "formal_synthetic_probe",
    "enable_frame_prc": False,
    "enable_tubelet": True,
    "enable_sync": False,
    "enable_trajectory": False,
    "tubelet_length": 4,
    "score_calibration": {
        "embedding_projection_support_weight": 0.45,
    },
    "fusion_rule": "tubelet_score_only",
}

TUBELET_SYNC_CONFIG = {
    "method_family": "temporal_tubelet_watermark",
    "method_variant": "tubelet_sync",
    "method_status": "formal_synthetic_probe",
    "enable_frame_prc": False,
    "enable_tubelet": True,
    "enable_sync": True,
    "enable_trajectory": False,
    "tubelet_length": 4,
    "score_calibration": {
        "embedding_projection_support_weight": 0.45,
    },
    "sync_search": {
        "offset_search_min": -16,
        "offset_search_max": 16,
        "enable_scale_search": True,
        "scale_candidates": [0.8, 1.0, 1.25],
        "scale_search_snap_radius": 3,
    },
    "lambda_sync": 0.1,
    "fusion_rule": "sync_rescue_fusion",
}


@pytest.mark.unit
def test_sync_rescue_gain_is_non_negative_on_temporal_crop(tmp_path: Path) -> None:
    cropped_sample = _build_sync_embedded_crop(tmp_path)
    detection_result = build_method_from_config(TUBELET_SYNC_CONFIG).detect(
        cropped_sample,
        threshold_record=None,
    )

    mechanism_trace = detection_result.mechanism_trace
    assert mechanism_trace["S_payload_rescue_gain"] >= 0.0
    assert detection_result.evidence_scores["S_final"] >= detection_result.evidence_scores["S_tubelet"]


@pytest.mark.unit
def test_unreliable_sync_does_not_lower_unaligned_payload_score() -> None:
    evidence_scores = {
        "S_tubelet": 0.42,
        "S_sync": 0.0,
        "S_traj": None,
        "S_final": 0.0,
    }

    assert (
        sync_rescue_fusion(
            evidence_scores,
            payload_rescue_gain=0.25,
            lambda_sync=0.1,
            gate_sync=False,
        )
        == 0.42
    )
    assert (
        sync_rescue_fusion(
            evidence_scores,
            payload_rescue_gain=-0.25,
            lambda_sync=0.1,
            gate_sync=True,
        )
        == 0.42
    )


@pytest.mark.unit
def test_reliable_offset_alignment_can_create_payload_rescue_gain(tmp_path: Path) -> None:
    cropped_sample = _build_sync_embedded_crop(tmp_path)
    sync_result = build_method_from_config(TUBELET_SYNC_CONFIG).detect(
        cropped_sample,
        threshold_record=None,
    )
    mechanism_trace = sync_result.mechanism_trace

    assert mechanism_trace["sync_estimated_offset"] == -8
    assert mechanism_trace["sync_ground_truth_offset"] == -8
    assert mechanism_trace["sync_peak_rank"] == 1
    assert mechanism_trace["S_payload_aligned"] > mechanism_trace["S_payload_unaligned"]
    assert mechanism_trace["S_payload_rescue_gain"] > 0.0
    assert mechanism_trace["sync_rescue_applied"] is True
    assert sync_result.evidence_scores["S_final"] > mechanism_trace["S_payload_unaligned"]


@pytest.mark.unit
def test_unaligned_payload_matches_tubelet_only_on_same_sample(tmp_path: Path) -> None:
    cropped_sample = _build_sync_embedded_crop(tmp_path)
    sync_result = build_method_from_config(TUBELET_SYNC_CONFIG).detect(
        cropped_sample,
        threshold_record=None,
    )
    tubelet_only_result = build_method_from_config(TUBELET_ONLY_CONFIG).detect(
        cropped_sample,
        threshold_record=None,
    )

    assert sync_result.mechanism_trace["S_payload_unaligned"] == tubelet_only_result.evidence_scores["S_tubelet"]
    assert sync_result.evidence_scores["S_tubelet"] == tubelet_only_result.evidence_scores["S_tubelet"]


def _build_sync_embedded_crop(tmp_path: Path):
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)
    base_sample = backend.build_sample(
        "sample_test_watermarked_positive_000001",
        "test",
        "watermarked_positive",
    )
    watermarked_sample = build_method_from_config(TUBELET_SYNC_CONFIG).embed(base_sample, {})
    return TemporalAttackPlaceholder(
        "temporal_crop",
        {"crop_start_candidates": [8], "crop_length": 20},
    ).apply(watermarked_sample)

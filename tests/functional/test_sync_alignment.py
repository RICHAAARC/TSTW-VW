"""
文件用途：验证 stage-one offset search synchronization 的最小语义。
File purpose: Validate the minimal semantics of stage-one offset-search synchronization.
Module type: General module
"""

from __future__ import annotations

from dataclasses import replace

import pytest

pytestmark = pytest.mark.quick

from pathlib import Path

from main.attacks.temporal import TemporalAttackPlaceholder
from experiments.synthetic_tubelet_sync_probe.synthetic_video_latent import (
    SyntheticVideoLatentPlaceholder,
)
from main.methods.temporal_tubelet_watermark.method import build_method_from_config
from main.methods.temporal_tubelet_watermark.synchronization import search_best_offset


TUBELET_ONLY_CONFIG = {
    "method_family": "temporal_tubelet_watermark",
    "method_variant": "tubelet_only",
    "method_status": "formal_synthetic_probe",
    "enable_frame_prc": False,
    "enable_tubelet": True,
    "enable_sync": False,
    "enable_trajectory": False,
    "tubelet_length": 4,
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


def test_sync_alignment_recovers_temporal_crop_offset(tmp_path: Path) -> None:
    """Validate that tubelet-sync recovers the governed crop offset.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)
    base_sample = backend.build_sample(
        "sample_test_watermarked_positive_000001",
        "test",
        "watermarked_positive",
    )
    watermark_method = build_method_from_config(TUBELET_SYNC_CONFIG)
    watermarked_sample = watermark_method.embed(base_sample, {})
    temporal_crop = TemporalAttackPlaceholder(
        "temporal_crop",
        {"crop_start_candidates": [8], "crop_length": 20},
    )
    cropped_sample = temporal_crop.apply(watermarked_sample)
    detection_result = watermark_method.detect(cropped_sample, threshold_record=None)

    assert detection_result.mechanism_trace["sync_search_enabled"] is True
    assert detection_result.mechanism_trace["sync_estimated_offset"] == -8
    assert detection_result.mechanism_trace["sync_ground_truth_offset"] == -8
    assert detection_result.mechanism_trace["sync_alignment_error"] == 0
    assert detection_result.mechanism_trace["sync_peak_rank"] == 1


def test_tubelet_only_does_not_emit_fake_sync_trace(tmp_path: Path) -> None:
    """Validate that `tubelet_only` keeps sync diagnostics disabled.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)
    base_sample = backend.build_sample(
        "sample_test_watermarked_positive_000002",
        "test",
        "watermarked_positive",
    )
    watermark_method = build_method_from_config(TUBELET_ONLY_CONFIG)
    watermarked_sample = watermark_method.embed(base_sample, {})
    temporal_crop = TemporalAttackPlaceholder(
        "temporal_crop",
        {"crop_start_candidates": [8], "crop_length": 20},
    )
    cropped_sample = temporal_crop.apply(watermarked_sample)
    detection_result = watermark_method.detect(cropped_sample, threshold_record=None)

    assert detection_result.mechanism_trace["sync_search_enabled"] is False
    assert detection_result.mechanism_trace["sync_estimated_offset"] is None
    assert detection_result.mechanism_trace["sync_alignment_error"] is None


def test_negative_sample_uses_same_sync_search_configuration(tmp_path: Path) -> None:
    """Validate that sync search is not disabled only for negative samples.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)
    negative_sample = backend.build_sample(
        "sample_test_clean_negative_000001",
        "test",
        "clean_negative",
    )
    temporal_crop = TemporalAttackPlaceholder(
        "temporal_crop",
        {"crop_start_candidates": [8], "crop_length": 20},
    )
    cropped_negative = temporal_crop.apply(negative_sample)
    watermark_method = build_method_from_config(TUBELET_SYNC_CONFIG)
    detection_result = watermark_method.detect(cropped_negative, threshold_record=None)

    assert detection_result.mechanism_trace["sync_search_enabled"] is True
    assert detection_result.mechanism_trace["sync_ground_truth_offset"] == -8


def test_sync_alignment_expands_offset_range_for_short_local_clip(tmp_path: Path) -> None:
    """Validate short local clips can search the full observable negative offset range.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder(latent_shape=(32, 4, 16, 16))
    backend.set_output_root(tmp_path)
    base_sample = backend.build_sample(
        "sample_test_watermarked_positive_local_clip_000001",
        "test",
        "watermarked_positive",
    )
    local_clip_config = {
        **TUBELET_SYNC_CONFIG,
        "sync_search": {
            **TUBELET_SYNC_CONFIG["sync_search"],
            "offset_search_min": -8,
            "offset_search_max": 8,
            "enable_scale_search": False,
        },
    }
    watermark_method = build_method_from_config(local_clip_config)
    watermarked_sample = watermark_method.embed(base_sample, {})
    seeded_sample = replace(
        watermarked_sample,
        latent_generation_seed_random=42,
    )
    local_clip = TemporalAttackPlaceholder("local_clip", {"clip_length": 4})
    clipped_sample = local_clip.apply(seeded_sample)

    assert clipped_sample.applied_attack_params["ground_truth_offset"] == -24

    detection_result = watermark_method.detect(clipped_sample, threshold_record=None)

    assert detection_result.mechanism_trace["sync_estimated_offset"] == -24
    assert detection_result.mechanism_trace["sync_ground_truth_offset"] == -24
    assert detection_result.mechanism_trace["sync_alignment_error"] == 0
    assert detection_result.mechanism_trace["sync_peak_rank"] == 1


def test_sync_search_range_does_not_expand_from_ground_truth() -> None:
    """Validate that ground truth is diagnostic-only and does not widen the search range.

    Args:
        None.

    Returns:
        None.
    """
    sync_result = search_best_offset(
        temporal_scores={0: 0.5, 4: 0.25},
        sync_codes={0: 1, 4: -1, 8: 1},
        offset_search_min=-2,
        offset_search_max=2,
        ground_truth_offset=-8,
    )

    assert sync_result["sync_search_space_size"] == 5
    assert sync_result["sync_peak_rank"] is None
    assert sync_result["sync_alignment_error"] == abs(
        sync_result["sync_estimated_offset"] - (-8)
    )


def test_short_local_clip_coverage_penalty_does_not_double_scale_payload_scores(
    tmp_path: Path,
) -> None:
    """Validate short local clips keep coverage penalty in alignment scoring only.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder(latent_shape=(32, 4, 16, 16))
    backend.set_output_root(tmp_path)
    base_sample = backend.build_sample(
        "sample_test_watermarked_positive_local_clip_penalty_000001",
        "test",
        "watermarked_positive",
    )
    local_clip_config = {
        **TUBELET_SYNC_CONFIG,
        "sync_search": {
            **TUBELET_SYNC_CONFIG["sync_search"],
            "offset_search_min": -8,
            "offset_search_max": 8,
            "enable_scale_search": False,
        },
    }
    penalty_disabled_config = {
        **local_clip_config,
        "sync_search": {
            **local_clip_config["sync_search"],
            "coverage_penalty_enabled": False,
        },
    }
    watermarked_sample = build_method_from_config(local_clip_config).embed(base_sample, {})
    seeded_sample = replace(
        watermarked_sample,
        latent_generation_seed_random=42,
    )
    local_clip = TemporalAttackPlaceholder("local_clip", {"clip_length": 4})
    clipped_sample = local_clip.apply(seeded_sample)

    penalty_enabled_result = build_method_from_config(local_clip_config).detect(
        clipped_sample,
        threshold_record=None,
    )
    penalty_disabled_result = build_method_from_config(penalty_disabled_config).detect(
        clipped_sample,
        threshold_record=None,
    )

    enabled_trace = penalty_enabled_result.mechanism_trace
    disabled_trace = penalty_disabled_result.mechanism_trace

    assert enabled_trace["sync_estimated_offset"] == -24
    assert disabled_trace["sync_estimated_offset"] == -24
    assert enabled_trace["sync_candidate_score_penalized"] < enabled_trace["sync_candidate_score_raw"]
    assert disabled_trace["sync_candidate_score_penalized"] == disabled_trace["sync_candidate_score_raw"]
    assert penalty_enabled_result.evidence_scores["S_tubelet"] == penalty_disabled_result.evidence_scores["S_tubelet"]
    assert enabled_trace["S_payload_aligned"] == disabled_trace["S_payload_aligned"]
    assert enabled_trace["S_payload_rescue_gain"] == disabled_trace["S_payload_rescue_gain"]

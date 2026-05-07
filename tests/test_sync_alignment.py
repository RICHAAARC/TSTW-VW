"""
文件用途：验证 stage-one offset search synchronization 的最小语义。
File purpose: Validate the minimal semantics of stage-one offset-search synchronization.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.attacks.temporal import TemporalAttackPlaceholder
from main.backends.synthetic_video_latent import SyntheticVideoLatentPlaceholder
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
    "fusion_rule": "calibrated_tubelet_sync",
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
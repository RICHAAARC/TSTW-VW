"""
File purpose: Validate sync-rescue fusion semantics for the synthetic tubelet probe.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

from main.attacks.temporal import TemporalAttackPlaceholder
from experiments.synthetic_tubelet_sync_probe.synthetic_video_latent import (
    SyntheticVideoLatentPlaceholder,
)
from main.core.tensor_artifact import read_float_tensor_npy
from main.methods.temporal_tubelet_watermark.codebook import (
    build_codebook_config,
    build_tubelet_codebook,
)
from main.methods.temporal_tubelet_watermark.embedding import (
    build_partition_config_from_method_config,
)
from main.methods.temporal_tubelet_watermark.evidence import SyntheticProbeEvidenceExtractor
from main.methods.temporal_tubelet_watermark.fusion import sync_rescue_fusion
from main.methods.temporal_tubelet_watermark.method import build_method_from_config
from main.methods.temporal_tubelet_watermark.tubelet_partition import (
    build_tubelet_descriptors,
    dot_tubelet_direction,
)


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
def test_positive_sync_score_is_gated_with_rescue() -> None:
    evidence_scores = {
        "S_tubelet": 0.42,
        "S_sync": 0.8,
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
            payload_rescue_gain=0.25,
            lambda_sync=0.1,
            gate_sync=True,
        )
        == 0.75
    )


@pytest.mark.unit
def test_positive_tubelet_score_is_coverage_penalized_for_partial_clip() -> None:
    extractor = SyntheticProbeEvidenceExtractor(
        method_variant="tubelet_only",
        method_config=TUBELET_ONLY_CONFIG,
        enabled_evidence={"tubelet": True, "sync": False, "trajectory": False},
        fusion_rule="tubelet_score_only",
    )

    saturated_partial_score = extractor._build_tubelet_score(
        [1.0],
        embedding_support=0.0,
        attack_strength=0.0,
        coverage_ratio=0.125,
    )
    full_coverage_score = extractor._build_tubelet_score(
        [1.0],
        embedding_support=0.0,
        attack_strength=0.0,
        coverage_ratio=1.0,
    )

    assert saturated_partial_score == 0.125
    assert full_coverage_score == 1.0


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
    assert mechanism_trace["sync_confident"] is True
    assert mechanism_trace["sync_alignment_coverage_ratio"] >= 0.5
    assert mechanism_trace["sync_candidate_score_penalized"] <= mechanism_trace["sync_candidate_score_raw"]
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


@pytest.mark.unit
def test_aligned_payload_uses_payload_code_not_sync_code(tmp_path: Path) -> None:
    cropped_sample = _build_sync_embedded_crop(tmp_path)
    sync_result = build_method_from_config(TUBELET_SYNC_CONFIG).detect(
        cropped_sample,
        threshold_record=None,
    )
    mechanism_trace = sync_result.mechanism_trace
    pure_payload_score, sync_coupled_payload_score = _rebuild_aligned_payload_scores(
        cropped_sample,
        int(mechanism_trace["sync_estimated_offset"]),
    )

    assert mechanism_trace["S_payload_aligned"] == pure_payload_score
    assert mechanism_trace["S_payload_aligned"] != sync_coupled_payload_score
    assert sync_result.evidence_scores["S_sync"] == mechanism_trace["S_sync_positive_margin"]
    assert mechanism_trace["S_payload_rescue_gain"] == round(
        max(
            0.0,
            mechanism_trace["S_payload_aligned"] - mechanism_trace["S_payload_unaligned"],
        ),
        6,
    )


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


def _rebuild_aligned_payload_scores(cropped_sample, estimated_offset: int) -> tuple[float, float]:
    tensor_artifact = read_float_tensor_npy(cropped_sample.latent_artifact_path)
    partition_config = build_partition_config_from_method_config(TUBELET_SYNC_CONFIG)
    observed_descriptors = build_tubelet_descriptors(
        cropped_sample.latent_shape,
        partition_config,
    )
    reference_shape = tuple(cropped_sample.mechanism_trace["reference_latent_shape"])
    reference_descriptors = build_tubelet_descriptors(reference_shape, partition_config)
    reference_descriptor_map = {
        (
            descriptor.frame_start,
            descriptor.height_start,
            descriptor.width_start,
        ): descriptor
        for descriptor in reference_descriptors
    }
    codebook = build_tubelet_codebook(
        cropped_sample.sample_id,
        reference_descriptors,
        len(reference_descriptors[0].flat_indices),
        build_codebook_config(),
        enable_sync=True,
    )
    pure_payload_projections: list[float] = []
    sync_coupled_projections: list[float] = []
    for observed_descriptor in observed_descriptors:
        reference_descriptor = reference_descriptor_map.get(
            (
                observed_descriptor.frame_start - estimated_offset,
                observed_descriptor.height_start,
                observed_descriptor.width_start,
            )
        )
        if reference_descriptor is None:
            continue
        direction = codebook.directions[reference_descriptor.tubelet_index]
        raw_projection = _dot_observed_tubelet_direction(
            tensor_artifact,
            observed_descriptor,
            direction,
        )
        payload_code = codebook.payload_codes[reference_descriptor.tubelet_index]
        sync_code = codebook.sync_codes.get(reference_descriptor.frame_start, 1)
        pure_payload_projections.append(_clip_score(payload_code * raw_projection))
        sync_coupled_projections.append(
            _clip_score(payload_code * sync_code * raw_projection)
        )
    embedding_support = max(
        0.0,
        min(
            1.0,
            float(cropped_sample.mechanism_trace["mean_projection_after"])
            - float(cropped_sample.mechanism_trace["mean_projection_before"]),
        ),
    )
    coverage_ratio = len(pure_payload_projections) / max(len(reference_descriptor_map), 1)
    return (
        _score_payload_projections(pure_payload_projections, embedding_support, coverage_ratio),
        _score_payload_projections(sync_coupled_projections, embedding_support, coverage_ratio),
    )


def _dot_observed_tubelet_direction(
    tensor_artifact,
    descriptor,
    direction: tuple[float, ...],
) -> float:
    if len(descriptor.flat_indices) == len(direction):
        return dot_tubelet_direction(tensor_artifact, descriptor, direction)
    return sum(
        float(tensor_artifact.values[flat_index]) * float(direction_value)
        for flat_index, direction_value in zip(
            descriptor.flat_indices,
            direction[: len(descriptor.flat_indices)],
        )
    )


def _score_payload_projections(
    projections: list[float],
    embedding_support: float,
    coverage_ratio: float,
) -> float:
    base_score = sum(projections) / len(projections)
    support_score = embedding_support * 0.45
    if base_score > 0.0:
        base_score *= coverage_ratio
    if support_score > 0.0:
        support_score *= coverage_ratio
    return _clip_score(base_score + support_score)


def _clip_score(score: float) -> float:
    return round(max(-1.0, min(1.0, score)), 6)

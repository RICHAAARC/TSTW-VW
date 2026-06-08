"""
File purpose: Validate sync-rescue fusion semantics for the synthetic tubelet probe.
Module type: General module
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

from main.attacks.temporal import TemporalAttackPlaceholder
from experiments.synthetic_tubelet_sync_probe.synthetic_video_latent import (
    SyntheticVideoLatentPlaceholder,
)
from main.core.schema import LatentSample
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
def test_partial_clip_tubelet_score_penalizes_unaligned_positive_support() -> None:
    extractor = SyntheticProbeEvidenceExtractor(
        method_variant="tubelet_only",
        method_config=TUBELET_ONLY_CONFIG,
        enabled_evidence={"tubelet": True, "sync": False, "trajectory": False},
        fusion_rule="tubelet_score_only",
    )

    penalized_partial_score = extractor._build_tubelet_score(
        [1.0],
        embedding_support=0.0,
        attack_strength=0.0,
        coverage_ratio=0.125,
        apply_coverage_penalty=True,
    )
    unpenalized_partial_score = extractor._build_tubelet_score(
        [1.0],
        embedding_support=0.0,
        attack_strength=0.0,
        coverage_ratio=0.125,
        apply_coverage_penalty=False,
    )
    full_coverage_score = extractor._build_tubelet_score(
        [1.0],
        embedding_support=0.0,
        attack_strength=0.0,
        coverage_ratio=1.0,
        apply_coverage_penalty=True,
    )

    assert penalized_partial_score == 0.125
    assert unpenalized_partial_score == 1.0
    assert full_coverage_score == 1.0


@pytest.mark.unit
def test_sync_candidate_surface_compares_penalized_and_raw_rankings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate sync candidate surface exposes ranking-rule differences.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    local_clip_config = copy.deepcopy(TUBELET_SYNC_CONFIG)
    local_clip_config["sync_search"] = {
        **local_clip_config["sync_search"],
        "min_sync_alignment_coverage_ratio": 0.25,
        "min_sync_alignment_matched_count": 1,
    }

    extractor = SyntheticProbeEvidenceExtractor(
        method_variant="tubelet_sync",
        method_config=local_clip_config,
        enabled_evidence={"tubelet": True, "sync": True, "trajectory": False},
        fusion_rule="sync_rescue_fusion",
    )
    sample = LatentSample(
        sample_id="sample_test_surface_000001",
        split="test",
        sample_role="attacked_positive",
        latent_shape=(8, 4, 4, 4),
        latent_tensor_digest_random="digest_surface",
        latent_generation_seed_random=11,
        latent_backend_name="synthetic_backend",
        latent_backend_status="ok",
        latent_artifact_relpath="artifacts/latents/sample.npy",
        latent_artifact_path="artifacts/latents/sample.npy",
        mechanism_trace={
            "reference_latent_shape": [8, 4, 4, 4],
            "sync_ground_truth_offset": -2,
        },
        applied_attack_params={"clip_length": 4},
    )

    monkeypatch.setattr(
        "main.methods.temporal_tubelet_watermark.evidence.read_float_tensor_npy",
        lambda _: object(),
    )
    monkeypatch.setattr(
        "main.methods.temporal_tubelet_watermark.evidence.build_tubelet_descriptors",
        lambda latent_shape, partition_config: [
            {
                "latent_shape": latent_shape,
                "partition_config": partition_config,
            }
        ],
    )
    monkeypatch.setattr(
        extractor,
        "_build_payload_coded_projections",
        lambda sample, tensor_artifact, descriptors, partition_config: (
            [0.25],
            object(),
            {(0, 0, 0): object()},
            {
                "reference_latent_shape": [8, 4, 4, 4],
                "tubelet_projection_coverage_ratio": 1.0,
            },
        ),
    )
    monkeypatch.setattr(
        extractor,
        "_build_alignment_candidate_scores",
        lambda descriptors, tensor_artifact, reference_descriptor_map, codebook, sample: (
            {
                (0, 1.0): 0.4,
                (-2, 1.0): 0.5,
                (2, 1.0): 0.39,
            },
            {
                (0, 1.0): {
                    "sync_alignment_matched_count": 4,
                    "sync_alignment_candidate_count": 8,
                    "sync_alignment_coverage_ratio": 0.5,
                    "sync_candidate_score_raw": 0.4,
                    "sync_candidate_score_penalized": 0.4,
                    "sync_candidate_score_hybrid": 0.4,
                },
                (-2, 1.0): {
                    "sync_alignment_matched_count": 2,
                    "sync_alignment_candidate_count": 8,
                    "sync_alignment_coverage_ratio": 0.25,
                    "sync_candidate_score_raw": 0.5,
                    "sync_candidate_score_penalized": 0.25,
                    "sync_candidate_score_hybrid": 0.5,
                },
                (2, 1.0): {
                    "sync_alignment_matched_count": 6,
                    "sync_alignment_candidate_count": 8,
                    "sync_alignment_coverage_ratio": 0.75,
                    "sync_candidate_score_raw": 0.39,
                    "sync_candidate_score_penalized": 0.39,
                    "sync_candidate_score_hybrid": 0.39,
                },
            },
            "hybrid_prior",
        ),
    )

    candidate_surface = extractor.build_sync_candidate_surface(sample)
    candidate_rows = candidate_surface["candidate_rows"]
    penalized_winner = candidate_surface["ranking_summaries"]["penalized_prior"]["winner"]
    hybrid_winner = candidate_surface["ranking_summaries"]["hybrid_prior"]["winner"]
    raw_winner = candidate_surface["ranking_summaries"]["raw_prior"]["winner"]
    ground_truth_row = candidate_surface["ground_truth_candidate"]

    assert candidate_surface["search_score_rule"] == "hybrid_prior"
    assert candidate_surface["sync_result"]["sync_estimated_offset"] == -2
    assert penalized_winner["offset_candidate"] == 0
    assert hybrid_winner["offset_candidate"] == -2
    assert raw_winner["offset_candidate"] == -2
    assert ground_truth_row["offset_candidate"] == -2
    assert candidate_surface["ranking_summaries"]["penalized_prior"]["ground_truth_rank"] == 3
    assert candidate_surface["ranking_summaries"]["hybrid_prior"]["ground_truth_rank"] == 1
    assert candidate_surface["ranking_summaries"]["raw_prior"]["ground_truth_rank"] == 1
    assert any(bool(row["selected_penalized_prior"]) for row in candidate_rows)
    assert any(bool(row["selected_hybrid_prior"]) for row in candidate_rows)
    assert any(bool(row["selected_raw_prior"]) for row in candidate_rows)
    assert any(bool(row["is_current_selected_candidate"]) for row in candidate_rows)


@pytest.mark.unit
def test_local_clip_sync_search_defaults_to_hybrid_no_prior_runtime_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate local-clip sync search removes center bias in runtime selection.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    local_clip_config = copy.deepcopy(TUBELET_SYNC_CONFIG)
    local_clip_config["sync_search"] = {
        **local_clip_config["sync_search"],
        "min_sync_alignment_coverage_ratio": 0.25,
        "min_sync_alignment_matched_count": 1,
    }

    extractor = SyntheticProbeEvidenceExtractor(
        method_variant="tubelet_sync",
        method_config=local_clip_config,
        enabled_evidence={"tubelet": True, "sync": True, "trajectory": False},
        fusion_rule="sync_rescue_fusion",
    )
    sample = LatentSample(
        sample_id="sample_test_surface_no_prior_000001",
        split="test",
        sample_role="attacked_positive",
        latent_shape=(8, 4, 4, 4),
        latent_tensor_digest_random="digest_surface_no_prior",
        latent_generation_seed_random=11,
        latent_backend_name="synthetic_backend",
        latent_backend_status="ok",
        latent_artifact_relpath="artifacts/latents/sample.npy",
        latent_artifact_path="artifacts/latents/sample.npy",
        mechanism_trace={
            "reference_latent_shape": [8, 4, 4, 4],
            "sync_ground_truth_offset": -2,
        },
        applied_attack_params={"clip_length": 4},
    )

    assert extractor._resolve_sync_search_score_rule(sample) == "hybrid_no_prior"

    monkeypatch.setattr(
        "main.methods.temporal_tubelet_watermark.evidence.read_float_tensor_npy",
        lambda _: object(),
    )
    monkeypatch.setattr(
        "main.methods.temporal_tubelet_watermark.evidence.build_tubelet_descriptors",
        lambda latent_shape, partition_config: [
            {
                "latent_shape": latent_shape,
                "partition_config": partition_config,
            }
        ],
    )
    monkeypatch.setattr(
        extractor,
        "_build_payload_coded_projections",
        lambda sample, tensor_artifact, descriptors, partition_config: (
            [0.25],
            object(),
            {(0, 0, 0): object()},
            {
                "reference_latent_shape": [8, 4, 4, 4],
                "tubelet_projection_coverage_ratio": 1.0,
            },
        ),
    )
    monkeypatch.setattr(
        extractor,
        "_build_alignment_candidate_scores",
        lambda descriptors, tensor_artifact, reference_descriptor_map, codebook, sample: (
            {
                (0, 1.0): 0.5,
                (-2, 1.0): 0.5,
                (2, 1.0): 0.4,
            },
            {
                (0, 1.0): {
                    "sync_alignment_matched_count": 4,
                    "sync_alignment_candidate_count": 8,
                    "sync_alignment_coverage_ratio": 0.5,
                    "sync_candidate_score_raw": 0.5,
                    "sync_candidate_score_penalized": 0.5,
                    "sync_candidate_score_hybrid": 0.5,
                },
                (-2, 1.0): {
                    "sync_alignment_matched_count": 2,
                    "sync_alignment_candidate_count": 8,
                    "sync_alignment_coverage_ratio": 0.25,
                    "sync_candidate_score_raw": 0.5,
                    "sync_candidate_score_penalized": 0.25,
                    "sync_candidate_score_hybrid": 0.5,
                },
                (2, 1.0): {
                    "sync_alignment_matched_count": 6,
                    "sync_alignment_candidate_count": 8,
                    "sync_alignment_coverage_ratio": 0.75,
                    "sync_candidate_score_raw": 0.4,
                    "sync_candidate_score_penalized": 0.4,
                    "sync_candidate_score_hybrid": 0.4,
                },
            },
            "hybrid_no_prior",
        ),
    )

    candidate_surface = extractor.build_sync_candidate_surface(sample)

    assert candidate_surface["search_score_rule"] == "hybrid_no_prior"
    assert candidate_surface["sync_result"]["sync_estimated_offset"] == -2
    assert (
        candidate_surface["ranking_summaries"]["hybrid_prior"]["winner"]["offset_candidate"]
        == 0
    )
    assert (
        candidate_surface["ranking_summaries"]["hybrid_no_prior"]["winner"]["offset_candidate"]
        == -2
    )


@pytest.mark.unit
def test_sync_confidence_can_gate_on_minimum_candidate_score() -> None:
    """Validate sync confidence can require a minimum selected candidate score.

    Args:
        None.

    Returns:
        None.
    """
    gated_config = copy.deepcopy(TUBELET_SYNC_CONFIG)
    gated_config["sync_search"] = {
        **gated_config["sync_search"],
        "min_sync_positive_margin": 0.12,
        "min_sync_alignment_coverage_ratio": 0.25,
        "min_sync_alignment_matched_count": 3,
        "min_sync_candidate_score": 0.55,
    }

    extractor = SyntheticProbeEvidenceExtractor(
        method_variant="tubelet_sync",
        method_config=gated_config,
        enabled_evidence={"tubelet": True, "sync": True, "trajectory": False},
        fusion_rule="sync_rescue_fusion",
    )

    leaking_like_trace = extractor._build_sync_confidence_trace(
        {
            "sync_search_score_rule": "hybrid_no_prior",
            "S_sync_positive_margin": 0.233373,
            "sync_alignment_coverage_ratio": 0.375,
            "sync_alignment_matched_count": 6,
            "sync_candidate_score_hybrid": 0.532451,
        }
    )
    rescued_positive_trace = extractor._build_sync_confidence_trace(
        {
            "sync_search_score_rule": "hybrid_no_prior",
            "S_sync_positive_margin": 0.139795,
            "sync_alignment_coverage_ratio": 0.25,
            "sync_alignment_matched_count": 4,
            "sync_candidate_score_hybrid": 0.639795,
        }
    )

    assert leaking_like_trace["sync_confident"] is False
    assert (
        leaking_like_trace["sync_confidence_failure_reason"]
        == "sync_candidate_score_below_gate"
    )
    assert leaking_like_trace["sync_confidence_min_candidate_score"] == 0.55
    assert leaking_like_trace["sync_confidence_score_field"] == "sync_candidate_score_hybrid"
    assert rescued_positive_trace["sync_confident"] is True


@pytest.mark.unit
def test_aligned_payload_safety_gate_checks_payload_and_coverage() -> None:
    """验证 aligned payload gate 同时约束 payload 增益和对齐覆盖。"""
    gated_config = copy.deepcopy(TUBELET_SYNC_CONFIG)
    gated_config["sync_search"] = {
        **gated_config["sync_search"],
        "sync_confidence_gate_rule": "aligned_payload_safety_gate",
        "min_payload_rescue_gain": 0.02,
        "min_aligned_payload_score": 0.1,
        "min_sync_alignment_coverage_ratio": 0.125,
        "min_sync_alignment_matched_count": 64,
    }

    extractor = SyntheticProbeEvidenceExtractor(
        method_variant="tubelet_sync",
        method_config=gated_config,
        enabled_evidence={"tubelet": True, "sync": True, "trajectory": False},
        fusion_rule="sync_rescue_fusion",
    )
    sync_result = {
        "sync_alignment_coverage_ratio": 0.125,
        "sync_alignment_matched_count": 64,
    }

    low_gain_trace = extractor._build_sync_confidence_trace_for_gate_rule(
        sync_result=sync_result,
        S_payload_aligned=0.11,
        S_payload_rescue_gain=0.01,
    )
    low_score_trace = extractor._build_sync_confidence_trace_for_gate_rule(
        sync_result=sync_result,
        S_payload_aligned=0.09,
        S_payload_rescue_gain=0.03,
    )
    low_coverage_trace = extractor._build_sync_confidence_trace_for_gate_rule(
        sync_result={
            "sync_alignment_coverage_ratio": 0.0625,
            "sync_alignment_matched_count": 64,
        },
        S_payload_aligned=0.11,
        S_payload_rescue_gain=0.03,
    )
    passing_trace = extractor._build_sync_confidence_trace_for_gate_rule(
        sync_result=sync_result,
        S_payload_aligned=0.11,
        S_payload_rescue_gain=0.03,
    )

    assert low_gain_trace["sync_confident"] is False
    assert "payload_rescue_gain_below_gate" in str(
        low_gain_trace["sync_confidence_failure_reason"]
    )
    assert low_score_trace["sync_confident"] is False
    assert "aligned_payload_score_below_gate" in str(
        low_score_trace["sync_confidence_failure_reason"]
    )
    assert low_coverage_trace["sync_confident"] is False
    assert "sync_coverage_below_gate" in str(
        low_coverage_trace["sync_confidence_failure_reason"]
    )
    assert passing_trace["sync_confident"] is True
    assert passing_trace["sync_confidence_gate_rule"] == "aligned_payload_safety_gate"
    assert passing_trace["sync_confidence_score_field"] == "S_payload_aligned"


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
def test_low_confidence_sync_blocks_positive_sync_bonus_on_detect_path(tmp_path: Path) -> None:
    """Validate observable sync gate blocks both rescue gain and positive sync bonus.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    low_confidence_config = copy.deepcopy(TUBELET_SYNC_CONFIG)
    low_confidence_config["sync_search"]["min_sync_alignment_matched_count"] = 999

    cropped_sample = _build_sync_embedded_crop(tmp_path)
    detection_result = build_method_from_config(low_confidence_config).detect(
        cropped_sample,
        threshold_record=None,
    )
    mechanism_trace = detection_result.mechanism_trace

    assert detection_result.evidence_scores["S_sync"] > 0.0
    assert mechanism_trace["S_payload_rescue_gain"] > 0.0
    assert mechanism_trace["sync_confident"] is False
    assert "sync_matched_count_below_gate" in str(
        mechanism_trace["sync_confidence_failure_reason"]
    )
    assert mechanism_trace["sync_rescue_applied"] is False
    assert detection_result.evidence_scores["S_final"] == mechanism_trace["S_payload_unaligned"]


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
    (
        pure_payload_penalized_score,
        pure_payload_unpenalized_score,
        sync_coupled_payload_score,
    ) = _rebuild_aligned_payload_scores(
        cropped_sample,
        int(mechanism_trace["sync_estimated_offset"]),
    )

    assert mechanism_trace["S_payload_aligned"] == pure_payload_penalized_score
    assert pure_payload_penalized_score < pure_payload_unpenalized_score
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
        _score_payload_projections(
            pure_payload_projections,
            embedding_support,
            coverage_ratio,
            apply_coverage_penalty=True,
        ),
        _score_payload_projections(
            pure_payload_projections,
            embedding_support,
            coverage_ratio,
            apply_coverage_penalty=False,
        ),
        _score_payload_projections(
            sync_coupled_projections,
            embedding_support,
            coverage_ratio,
            apply_coverage_penalty=True,
        ),
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
    *,
    apply_coverage_penalty: bool,
) -> float:
    base_score = sum(projections) / len(projections)
    if apply_coverage_penalty and base_score > 0.0:
        base_score *= max(0.0, min(1.0, coverage_ratio))
    support_score = embedding_support * 0.45
    return _clip_score(base_score + support_score)


def _clip_score(score: float) -> float:
    return round(max(-1.0, min(1.0, score)), 6)

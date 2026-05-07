"""
文件用途：提供阶段 0 placeholder / random evidence extractor。
File purpose: Provide stage-0 placeholder and random evidence extractors.
Module type: General module
"""

from __future__ import annotations

from statistics import median

from main.core.digest import compute_object_digest
from main.core.schema import LatentSample, build_empty_evidence_scores, validate_evidence_scores
from main.core.tensor_artifact import read_float_tensor_npy
from main.methods.temporal_tubelet_watermark.codebook import (
    build_codebook_config,
    build_tubelet_codebook,
)
from main.methods.temporal_tubelet_watermark.embedding import (
    build_partition_config_from_method_config,
)
from main.methods.temporal_tubelet_watermark.fusion import get_fusion_rule
from main.methods.temporal_tubelet_watermark.interfaces import EvidenceExtractor
from main.methods.temporal_tubelet_watermark.synchronization import search_best_offset
from main.methods.temporal_tubelet_watermark.tubelet_partition import (
    build_tubelet_descriptors,
    build_tubelet_partition_config,
    compute_tubelet_partition_digest,
    extract_tubelet_values,
)


class EmptyEvidenceExtractorPlaceholder(EvidenceExtractor):
    """功能：返回全空 evidence 分支的 placeholder extractor。

    Placeholder extractor that returns explicit null evidence fields.

    Args:
        None.

    Returns:
        None.
    """

    def extract(self, sample: LatentSample) -> dict[str, float | None]:
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")
        evidence_scores = build_empty_evidence_scores(0.0)
        validate_evidence_scores(evidence_scores)
        return evidence_scores


class RandomEvidenceExtractorRandom(EvidenceExtractor):
    """功能：生成可复现的随机 evidence 分数。

    Reproducible random evidence extractor for the stage-0 scaffold.

    Args:
        enabled_evidence: Evidence enablement mapping.
        score_generation_seed_random: Base seed for score generation.
        fusion_rule: Governed fusion rule name.

    Returns:
        None.
    """

    def __init__(
        self,
        enabled_evidence: dict[str, bool],
        score_generation_seed_random: int,
        fusion_rule: str,
    ) -> None:
        if not isinstance(enabled_evidence, dict):
            raise TypeError("enabled_evidence must be a dictionary")
        if not isinstance(score_generation_seed_random, int):
            raise TypeError("score_generation_seed_random must be an integer")
        self._enabled_evidence = enabled_evidence
        self._score_generation_seed_random = score_generation_seed_random
        self._fusion_callable = get_fusion_rule(fusion_rule)

    def extract(self, sample: LatentSample) -> dict[str, float | None]:
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")

        evidence_scores = build_empty_evidence_scores(0.0)
        evidence_mapping = {
            "tubelet": "S_tubelet",
            "sync": "S_sync",
            "trajectory": "S_traj",
        }
        for evidence_name, score_name in evidence_mapping.items():
            if self._enabled_evidence.get(evidence_name, False):
                evidence_scores[score_name] = self._build_random_score(sample, score_name)
        evidence_scores["S_final"] = self._fusion_callable(evidence_scores)
        validate_evidence_scores(evidence_scores)
        return evidence_scores

    def _build_random_score(self, sample: LatentSample, score_name: str) -> float:
        score_digest = compute_object_digest(
            {
                "sample_id": sample.sample_id,
                "score_name": score_name,
                "latent_generation_seed_random": sample.latent_generation_seed_random,
                "score_generation_seed_random": self._score_generation_seed_random,
            }
        )
        normalized_value = int(score_digest[:12], 16) / float(16**12 - 1)
        return round((normalized_value * 2.0) - 1.0, 6)


class SyntheticProbeEvidenceExtractor(EvidenceExtractor):
    """功能：基于真实 tubelet / sync 机制提取 stage-one evidence 分数。

    Stage-one evidence extractor driven by tubelet projections and synchronization search.

    Args:
        method_variant: Governed method variant.
        enabled_evidence: Evidence enablement mapping.
        fusion_rule: Governed fusion rule name.

    Returns:
        None.
    """

    _REFERENCE_FRAME_COUNT = 32
    _TUBELET_ROBUSTNESS = {
        "frame_prc": 0.18,
        "tubelet_only": 0.38,
        "tubelet_sync": 0.48,
    }
    _TUBELET_BONUS = {
        "frame_prc": 0.00,
        "tubelet_only": 0.08,
        "tubelet_sync": 0.12,
    }

    def __init__(
        self,
        method_variant: str,
        method_config: dict[str, object],
        enabled_evidence: dict[str, bool],
        fusion_rule: str,
    ) -> None:
        if not isinstance(method_variant, str) or not method_variant:
            raise ValueError("method_variant must be a non-empty string")
        if not isinstance(method_config, dict):
            raise TypeError("method_config must be a dictionary")
        if not isinstance(enabled_evidence, dict):
            raise TypeError("enabled_evidence must be a dictionary")
        self._method_variant = method_variant
        self._method_config = method_config
        self._enabled_evidence = enabled_evidence
        self._fusion_callable = get_fusion_rule(fusion_rule)

    def extract(self, sample: LatentSample) -> tuple[dict[str, float | None], dict[str, object]]:
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")
        if sample.latent_artifact_path is None:
            raise ValueError("sample must carry latent_artifact_path")

        tensor_artifact = read_float_tensor_npy(sample.latent_artifact_path)
        partition_config = build_partition_config_from_method_config(self._method_config)
        descriptors = build_tubelet_descriptors(sample.latent_shape, partition_config)
        evidence_scores = build_empty_evidence_scores(0.0)
        coded_projections, codebook = self._build_coded_projections(
            sample,
            tensor_artifact,
            descriptors,
            partition_config,
        )
        mechanism_trace = dict(sample.mechanism_trace or {})
        mechanism_trace.update(
            {
                "tubelet_length": partition_config.tubelet_length,
                "spatial_patch_size": list(partition_config.spatial_patch_size),
                "partition_digest": compute_tubelet_partition_digest(
                    sample.latent_shape,
                    partition_config,
                ),
                "codebook_digest": codebook.codebook_digest,
                "sync_code_digest": codebook.sync_code_digest,
                "payload_digest": codebook.payload_digest,
            }
        )

        if self._enabled_evidence.get("tubelet", False):
            evidence_scores["S_tubelet"] = round(
                sum(coded_projections) / len(coded_projections),
                6,
            )
        if self._enabled_evidence.get("sync", False):
            temporal_scores = self._aggregate_temporal_scores(descriptors, coded_projections)
            sync_result = search_best_offset(
                temporal_scores,
                codebook.sync_codes,
                ground_truth_offset=mechanism_trace.get("sync_ground_truth_offset"),
            )
            evidence_scores["S_sync"] = float(sync_result["sync_score"])
            mechanism_trace.update(sync_result)
        else:
            mechanism_trace.update(
                {
                    "sync_search_enabled": False,
                    "sync_estimated_offset": None,
                    "sync_alignment_error": None,
                    "sync_peak_rank": None,
                    "sync_search_space_size": None,
                    "sync_search_space_digest": None,
                }
            )
        if self._enabled_evidence.get("trajectory", False):
            evidence_scores["S_traj"] = self._build_trajectory_score(coded_projections)
        evidence_scores["S_final"] = self._fusion_callable(evidence_scores)
        validate_evidence_scores(evidence_scores)
        return evidence_scores, mechanism_trace

    def _build_coded_projections(
        self,
        sample: LatentSample,
        tensor_artifact: object,
        descriptors: list[object],
        partition_config: object,
    ) -> tuple[list[float], object]:
        first_values = extract_tubelet_values(tensor_artifact, descriptors[0])
        reference_latent_shape = tuple(
            (sample.mechanism_trace or {}).get("reference_latent_shape", sample.latent_shape)
        )
        reference_descriptors = build_tubelet_descriptors(
            reference_latent_shape,
            partition_config,
        )
        codebook = build_tubelet_codebook(
            sample.sample_id,
            descriptors,
            len(first_values),
            build_codebook_config(),
            enable_sync=self._enabled_evidence.get("sync", False),
            reference_temporal_indices=[
                descriptor.frame_start for descriptor in reference_descriptors
            ],
        )
        coded_projections: list[float] = []
        for descriptor in descriptors:
            direction = codebook.directions[descriptor.tubelet_index]
            code_sign = codebook.payload_codes[descriptor.tubelet_index]
            tubelet_values = extract_tubelet_values(tensor_artifact, descriptor)
            coded_projections.append(
                self._clip_score(code_sign * self._dot_product(tubelet_values, direction))
            )
        return coded_projections, codebook

    def _aggregate_temporal_scores(
        self,
        descriptors: list[object],
        coded_projections: list[float],
    ) -> dict[int, float]:
        temporal_bins: dict[int, list[float]] = {}
        for descriptor, coded_projection in zip(descriptors, coded_projections):
            temporal_bins.setdefault(descriptor.frame_start, []).append(float(coded_projection))
        return {
            temporal_index: round(sum(values) / len(values), 6)
            for temporal_index, values in temporal_bins.items()
        }

    def _build_trajectory_score(self, coded_projections: list[float]) -> float:
        return self._clip_score(median(coded_projections))

    def _dot_product(self, left_values: list[float], right_values: list[float]) -> float:
        if len(left_values) != len(right_values):
            raise ValueError("dot-product operands must share the same length")
        return sum(float(left_value) * float(right_value) for left_value, right_value in zip(left_values, right_values))

    def _clip_score(self, score: float) -> float:
        return round(max(-1.0, min(1.0, score)), 6)
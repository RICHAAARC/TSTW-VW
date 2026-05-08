"""
文件用途：提供阶段 0 placeholder / random evidence extractor。
File purpose: Provide stage-0 placeholder and random evidence extractors.
Module type: General module
"""

from __future__ import annotations

import math
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
from main.methods.temporal_tubelet_watermark.synchronization import build_offset_search_result
from main.methods.temporal_tubelet_watermark.tubelet_partition import (
    build_tubelet_descriptors,
    compute_tubelet_partition_digest,
    dot_tubelet_direction,
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
        (
            payload_coded_projections,
            combined_coded_projections,
            codebook,
            reference_descriptor_map,
        ) = self._build_payload_coded_projections(
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
        embedding_support = self._resolve_embedding_support(sample)
        attack_strength = self._resolve_attack_strength(sample)

        aligned_tubelet_projections = combined_coded_projections
        if self._enabled_evidence.get("sync", False):
            offset_scores = self._build_offset_candidate_scores(
                descriptors,
                tensor_artifact,
                reference_descriptor_map,
                codebook,
            )
            sync_result = build_offset_search_result(
                offset_scores,
                ground_truth_offset=mechanism_trace.get("sync_ground_truth_offset"),
            )
            mechanism_trace.update(sync_result)
            evidence_scores["S_sync"] = self._build_sync_support_score(
                float(sync_result["sync_score"]),
                embedding_support,
                attack_strength,
            )
            aligned_tubelet_projections = self._align_tubelet_projections(
                descriptors,
                tensor_artifact,
                reference_descriptor_map,
                codebook,
                int(sync_result["sync_estimated_offset"]),
            )
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
        if self._enabled_evidence.get("tubelet", False):
            evidence_scores["S_tubelet"] = self._build_tubelet_score(
                aligned_tubelet_projections,
                embedding_support,
                attack_strength,
            )
        if self._enabled_evidence.get("trajectory", False):
            evidence_scores["S_traj"] = self._build_trajectory_score(
                aligned_tubelet_projections
            )
        evidence_scores["S_final"] = self._fusion_callable(evidence_scores)
        validate_evidence_scores(evidence_scores)
        return evidence_scores, mechanism_trace

    def _build_payload_coded_projections(
        self,
        sample: LatentSample,
        tensor_artifact: object,
        descriptors: list[object],
        partition_config: object,
    ) -> tuple[list[float], list[float], object, dict[tuple[int, int, int], object]]:
        reference_latent_shape = tuple(
            (sample.mechanism_trace or {}).get("reference_latent_shape", sample.latent_shape)
        )
        reference_descriptors = build_tubelet_descriptors(
            reference_latent_shape,
            partition_config,
        )
        reference_descriptor_map = self._build_reference_descriptor_map(reference_descriptors)
        codebook = build_tubelet_codebook(
            sample.sample_id,
            reference_descriptors,
            len(reference_descriptors[0].flat_indices),
            build_codebook_config(),
            enable_sync=self._enabled_evidence.get("sync", False),
        )
        payload_coded_projections: list[float] = []
        combined_coded_projections: list[float] = []
        for descriptor in descriptors:
            reference_descriptor = self._resolve_reference_descriptor(
                reference_descriptor_map,
                descriptor,
                estimated_offset=0,
            )
            if reference_descriptor is None:
                continue
            direction = codebook.directions[reference_descriptor.tubelet_index]
            raw_projection = self._dot_observed_tubelet_direction(
                tensor_artifact,
                descriptor,
                direction,
            )
            if raw_projection is None:
                continue
            payload_coded_projections.append(
                self._clip_score(
                    codebook.payload_codes[reference_descriptor.tubelet_index]
                    * raw_projection
                )
            )
            combined_coded_projections.append(
                self._clip_score(
                    codebook.combined_codes[reference_descriptor.tubelet_index]
                    * raw_projection
                )
            )
        if not payload_coded_projections or not combined_coded_projections:
            raise ValueError("projection extraction produced no valid tubelets")
        return (
            payload_coded_projections,
            combined_coded_projections,
            codebook,
            reference_descriptor_map,
        )

    def _build_reference_descriptor_map(
        self,
        reference_descriptors: list[object],
    ) -> dict[tuple[int, int, int], object]:
        return {
            (
                int(descriptor.frame_start),
                int(descriptor.height_start),
                int(descriptor.width_start),
            ): descriptor
            for descriptor in reference_descriptors
        }

    def _resolve_reference_descriptor(
        self,
        reference_descriptor_map: dict[tuple[int, int, int], object],
        descriptor: object,
        estimated_offset: int,
    ) -> object | None:
        reference_frame_start = int(descriptor.frame_start) - int(estimated_offset)
        return reference_descriptor_map.get(
            (
                reference_frame_start,
                int(descriptor.height_start),
                int(descriptor.width_start),
            )
        )

    def _build_offset_candidate_scores(
        self,
        descriptors: list[object],
        tensor_artifact: object,
        reference_descriptor_map: dict[tuple[int, int, int], object],
        codebook: object,
    ) -> dict[int, float]:
        offset_scores: dict[int, float] = {}
        for offset_candidate in range(-16, 17):
            candidate_payload_projections: list[float] = []
            candidate_sync_products: list[float] = []
            for descriptor in descriptors:
                reference_descriptor = self._resolve_reference_descriptor(
                    reference_descriptor_map,
                    descriptor,
                    offset_candidate,
                )
                if reference_descriptor is None:
                    continue
                direction = codebook.directions[reference_descriptor.tubelet_index]
                raw_projection = self._dot_observed_tubelet_direction(
                    tensor_artifact,
                    descriptor,
                    direction,
                )
                if raw_projection is None:
                    continue
                payload_projection = self._clip_score(
                    codebook.payload_codes[reference_descriptor.tubelet_index]
                    * raw_projection
                )
                sync_code = codebook.sync_codes.get(reference_descriptor.frame_start, 0)
                candidate_payload_projections.append(payload_projection)
                candidate_sync_products.append(float(payload_projection) * float(sync_code))
            if not candidate_sync_products:
                offset_scores[offset_candidate] = -1.0
                continue
            temporal_support = sum(candidate_sync_products) / len(candidate_sync_products)
            projection_support = sum(candidate_payload_projections) / len(
                candidate_payload_projections
            )
            offset_scores[offset_candidate] = round(
                temporal_support + (0.1 * projection_support),
                6,
            )
        return offset_scores

    def _build_trajectory_score(self, coded_projections: list[float]) -> float:
        return self._clip_score(median(coded_projections))

    def _resolve_embedding_support(self, sample: LatentSample) -> float:
        mechanism_trace = sample.mechanism_trace or {}
        projection_before = mechanism_trace.get("mean_projection_before")
        projection_after = mechanism_trace.get("mean_projection_after")
        if projection_before is None or projection_after is None:
            return 0.0
        return max(
            0.0,
            min(1.0, float(projection_after) - float(projection_before)),
        )

    def _resolve_attack_strength(self, sample: LatentSample) -> float:
        applied_attack_params = sample.applied_attack_params or {}
        original_frame_count = applied_attack_params.get("original_frame_count")
        observed_frame_count = applied_attack_params.get("observed_frame_count")
        if (
            not isinstance(original_frame_count, int)
            or original_frame_count < 1
            or not isinstance(observed_frame_count, int)
            or observed_frame_count < 0
        ):
            return 0.0
        return max(
            0.0,
            min(1.0, 1.0 - (float(observed_frame_count) / float(original_frame_count))),
        )

    def _build_tubelet_score(
        self,
        aligned_tubelet_projections: list[float],
        embedding_support: float,
        attack_strength: float,
    ) -> float:
        del attack_strength
        base_score = sum(aligned_tubelet_projections) / len(aligned_tubelet_projections)
        projection_support_weight = self._resolve_score_calibration_value(
            "embedding_projection_support_weight",
        )
        return self._clip_score(
            base_score + (float(embedding_support) * projection_support_weight)
        )

    def _resolve_score_calibration_value(self, field_name: str) -> float:
        score_calibration = self._method_config.get("score_calibration", {})
        if not isinstance(score_calibration, dict):
            return 0.0
        field_value = score_calibration.get(field_name, 0.0)
        if not isinstance(field_value, (int, float)):
            return 0.0
        return float(field_value)

    def _build_sync_support_score(
        self,
        raw_sync_score: float,
        embedding_support: float,
        attack_strength: float,
    ) -> float | None:
        if embedding_support <= 0.0 or attack_strength <= 0.0:
            return 0.0
        normalized_sync_score = math.tanh((float(raw_sync_score) - 2.0) / 2.0)
        bounded_sync_score = max(0.0, min(1.0, normalized_sync_score))
        return round(
            bounded_sync_score * embedding_support * (0.5 + (0.5 * attack_strength)),
            6,
        )

    def _align_tubelet_projections(
        self,
        descriptors: list[object],
        tensor_artifact: object,
        reference_descriptor_map: dict[tuple[int, int, int], object],
        codebook: object,
        estimated_offset: int,
    ) -> list[float]:
        aligned_projections: list[float] = []
        for descriptor in descriptors:
            reference_descriptor = self._resolve_reference_descriptor(
                reference_descriptor_map,
                descriptor,
                estimated_offset,
            )
            if reference_descriptor is None:
                continue
            direction = codebook.directions[reference_descriptor.tubelet_index]
            raw_projection = self._dot_observed_tubelet_direction(
                tensor_artifact,
                descriptor,
                direction,
            )
            if raw_projection is None:
                continue
            aligned_projections.append(
                self._clip_score(
                    codebook.combined_codes[reference_descriptor.tubelet_index]
                    * raw_projection
                )
            )
        if not aligned_projections:
            return [-1.0]
        return aligned_projections

    def _dot_observed_tubelet_direction(
        self,
        tensor_artifact: object,
        descriptor: object,
        direction: tuple[float, ...],
    ) -> float | None:
        if len(descriptor.flat_indices) == len(direction):
            return dot_tubelet_direction(tensor_artifact, descriptor, direction)
        if len(descriptor.flat_indices) > len(direction):
            return None
        return sum(
            float(tensor_artifact.values[flat_index]) * float(direction_value)
            for flat_index, direction_value in zip(
                descriptor.flat_indices,
                direction[: len(descriptor.flat_indices)],
            )
        )

    def _clip_score(self, score: float) -> float:
        return round(max(-1.0, min(1.0, score)), 6)
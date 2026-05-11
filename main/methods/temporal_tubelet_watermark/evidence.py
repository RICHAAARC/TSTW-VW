"""
File purpose: legacy placeholder/random extractor plus stage-one synthetic probe extractor.
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
from main.methods.temporal_tubelet_watermark.fusion import get_fusion_rule, sync_rescue_fusion
from main.methods.temporal_tubelet_watermark.interfaces import EvidenceExtractor
from main.methods.temporal_tubelet_watermark.synchronization import (
    build_offset_scale_search_result,
    build_offset_search_result,
)
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

    Reproducible random evidence extractor for the protocol skeleton runtime scaffold.

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
        self._fusion_rule = fusion_rule
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

        S_payload_unaligned = self._build_tubelet_score(
            payload_coded_projections,
            embedding_support,
            attack_strength,
        )
        S_payload_aligned = S_payload_unaligned
        S_payload_rescue_gain = 0.0
        sync_rescue_applied = False
        trajectory_projections = payload_coded_projections
        if self._enabled_evidence.get("sync", False):
            alignment_scores = self._build_alignment_candidate_scores(
                descriptors,
                tensor_artifact,
                reference_descriptor_map,
                codebook,
                sample,
            )
            sync_result = self._build_sync_search_result(
                alignment_scores,
                mechanism_trace,
                sample,
            )
            mechanism_trace.update(sync_result)
            evidence_scores["S_sync"] = self._build_sync_support_score(
                float(sync_result["S_sync_positive_margin"]),
            )
            aligned_tubelet_projections = self._align_tubelet_projections(
                descriptors,
                tensor_artifact,
                reference_descriptor_map,
                codebook,
                int(sync_result["sync_estimated_offset"]),
                float(sync_result["sync_estimated_scale"]),
            )
            trajectory_projections = aligned_tubelet_projections
            S_payload_aligned = self._build_tubelet_score(
                aligned_tubelet_projections,
                embedding_support,
                attack_strength,
            )
            S_payload_rescue_gain = round(
                max(0.0, S_payload_aligned - S_payload_unaligned),
                6,
            )
            sync_rescue_applied = bool(float(evidence_scores["S_sync"] or 0.0) > 0.0)
        else:
            mechanism_trace.update(
                {
                    "sync_search_enabled": False,
                    "sync_estimated_offset": None,
                    "sync_ground_truth_offset": mechanism_trace.get(
                        "sync_ground_truth_offset"
                    ),
                    "sync_alignment_error": None,
                    "sync_peak_rank": None,
                    "sync_search_space_size": None,
                    "sync_search_space_digest": None,
                    "sync_estimated_scale": None,
                    "sync_ground_truth_scale": self._resolve_ground_truth_scale(sample),
                    "sync_scale_error": None,
                    "sync_alignment_mode": None,
                    "S_sync_peak_best": None,
                    "S_sync_peak_second_or_median": None,
                    "S_sync_peak_margin": None,
                    "S_sync_positive_margin": None,
                }
            )
        if self._enabled_evidence.get("tubelet", False):
            evidence_scores["S_tubelet"] = S_payload_unaligned
        if self._enabled_evidence.get("trajectory", False):
            evidence_scores["S_traj"] = self._build_trajectory_score(
                trajectory_projections
            )
        if self._fusion_rule == "sync_rescue_fusion":
            evidence_scores["S_final"] = sync_rescue_fusion(
                evidence_scores,
                payload_rescue_gain=S_payload_rescue_gain,
                lambda_sync=self._resolve_lambda_sync(),
                gate_sync=sync_rescue_applied,
            )
        else:
            evidence_scores["S_final"] = self._fusion_callable(evidence_scores)
        mechanism_trace.update(
            {
                "S_payload_unaligned": S_payload_unaligned,
                "S_payload_aligned": S_payload_aligned,
                "S_payload_rescue_gain": S_payload_rescue_gain,
                "sync_rescue_applied": sync_rescue_applied,
                "fusion_rule": self._fusion_rule,
                "lambda_sync": self._resolve_lambda_sync(),
            }
        )
        validate_evidence_scores(evidence_scores)
        return evidence_scores, mechanism_trace

    def _build_payload_coded_projections(
        self,
        sample: LatentSample,
        tensor_artifact: object,
        descriptors: list[object],
        partition_config: object,
    ) -> tuple[list[float], object, dict[tuple[int, int, int], object]]:
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
        for descriptor in descriptors:
            reference_descriptor = self._resolve_reference_descriptor(
                reference_descriptor_map,
                descriptor,
                estimated_offset=0,
                estimated_scale=1.0,
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
        if not payload_coded_projections:
            raise ValueError("projection extraction produced no valid tubelets")
        return (
            payload_coded_projections,
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
        estimated_scale: float = 1.0,
    ) -> object | None:
        reference_frame_start = int(round(int(descriptor.frame_start) * float(estimated_scale))) - int(
            estimated_offset
        )
        spatial_key = (
            int(descriptor.height_start),
            int(descriptor.width_start),
        )
        exact_key = (
            reference_frame_start,
            spatial_key[0],
            spatial_key[1],
        )
        exact_descriptor = reference_descriptor_map.get(exact_key)
        if exact_descriptor is not None or abs(float(estimated_scale) - 1.0) <= 1e-9:
            return exact_descriptor

        for frame_delta in range(1, self._resolve_scale_search_snap_radius() + 1):
            for candidate_frame_start in (
                reference_frame_start - frame_delta,
                reference_frame_start + frame_delta,
            ):
                candidate_descriptor = reference_descriptor_map.get(
                    (
                        candidate_frame_start,
                        spatial_key[0],
                        spatial_key[1],
                    )
                )
                if candidate_descriptor is not None:
                    return candidate_descriptor
        return None

    def _build_alignment_candidate_scores(
        self,
        descriptors: list[object],
        tensor_artifact: object,
        reference_descriptor_map: dict[tuple[int, int, int], object],
        codebook: object,
        sample: LatentSample,
    ) -> dict[tuple[int, float], float]:
        alignment_scores: dict[tuple[int, float], float] = {}
        for offset_candidate in self._resolve_offset_candidates():
            for scale_candidate in self._resolve_scale_candidates(sample):
                alignment_scores[(offset_candidate, scale_candidate)] = (
                    self._score_alignment_candidate(
                        descriptors,
                        tensor_artifact,
                        reference_descriptor_map,
                        codebook,
                        offset_candidate,
                        scale_candidate,
                    )
                )
        return alignment_scores

    def _score_alignment_candidate(
        self,
        descriptors: list[object],
        tensor_artifact: object,
        reference_descriptor_map: dict[tuple[int, int, int], object],
        codebook: object,
        offset_candidate: int,
        scale_candidate: float,
    ) -> float:
        candidate_payload_projections: list[float] = []
        for descriptor in descriptors:
            reference_descriptor = self._resolve_reference_descriptor(
                reference_descriptor_map,
                descriptor,
                offset_candidate,
                scale_candidate,
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
            candidate_payload_projections.append(payload_projection)
        if not candidate_payload_projections:
            return -1.0
        projection_support = sum(candidate_payload_projections) / len(
            candidate_payload_projections
        )
        return round(projection_support, 6)

    def _build_sync_search_result(
        self,
        alignment_scores: dict[tuple[int, float], float],
        mechanism_trace: dict[str, object],
        sample: LatentSample,
    ) -> dict[str, float | int | str | None | bool]:
        ground_truth_offset = mechanism_trace.get("sync_ground_truth_offset")
        resolved_ground_truth_offset = (
            int(ground_truth_offset) if isinstance(ground_truth_offset, int) else None
        )
        ground_truth_scale = self._resolve_ground_truth_scale_from_trace(mechanism_trace)
        if self._scale_search_enabled(sample):
            return build_offset_scale_search_result(
                alignment_scores,
                ground_truth_offset=resolved_ground_truth_offset,
                ground_truth_scale=ground_truth_scale,
            )

        offset_scores = {
            int(offset_candidate): float(candidate_score)
            for (offset_candidate, scale_candidate), candidate_score in alignment_scores.items()
            if abs(float(scale_candidate) - 1.0) <= 1e-9
        }
        return build_offset_search_result(
            offset_scores,
            ground_truth_offset=resolved_ground_truth_offset,
        )

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
        sync_positive_margin: float,
    ) -> float | None:
        return self._clip_score(max(0.0, float(sync_positive_margin)))

    def _align_tubelet_projections(
        self,
        descriptors: list[object],
        tensor_artifact: object,
        reference_descriptor_map: dict[tuple[int, int, int], object],
        codebook: object,
        estimated_offset: int,
        estimated_scale: float,
    ) -> list[float]:
        aligned_projections: list[float] = []
        for descriptor in descriptors:
            reference_descriptor = self._resolve_reference_descriptor(
                reference_descriptor_map,
                descriptor,
                estimated_offset,
                estimated_scale,
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
                    codebook.payload_codes[reference_descriptor.tubelet_index]
                    * raw_projection
                )
            )
        if not aligned_projections:
            return [-1.0]
        return aligned_projections

    def _resolve_offset_candidates(self) -> list[int]:
        sync_search_config = self._resolve_sync_search_config()
        offset_min = int(sync_search_config.get("offset_search_min", -16))
        offset_max = int(sync_search_config.get("offset_search_max", 16))
        if offset_min > offset_max:
            raise ValueError("sync_search offset_search_min must not exceed offset_search_max")
        return list(range(offset_min, offset_max + 1))

    def _resolve_scale_candidates(self, sample: LatentSample | None = None) -> list[float]:
        if not self._scale_search_enabled(sample):
            return [1.0]
        sync_search_config = self._resolve_sync_search_config()
        scale_candidates = sync_search_config.get("scale_candidates", [1.0])
        if not isinstance(scale_candidates, list) or not scale_candidates:
            raise ValueError("sync_search scale_candidates must be a non-empty list")
        normalized_candidates = sorted(
            {
                round(float(scale_candidate), 6)
                for scale_candidate in scale_candidates
                if isinstance(scale_candidate, (int, float))
                and float(scale_candidate) > 0.0
            }
        )
        if 1.0 not in normalized_candidates:
            normalized_candidates.append(1.0)
            normalized_candidates.sort()
        if not normalized_candidates:
            raise ValueError("sync_search scale_candidates must contain positive numbers")
        return normalized_candidates

    def _scale_search_enabled(self, sample: LatentSample | None = None) -> bool:
        sync_search_config = self._resolve_sync_search_config()
        if not bool(sync_search_config.get("enable_scale_search", False)):
            return False
        if sample is None:
            return True
        attack_params = sample.applied_attack_params or {}
        return "speed_ratio" in attack_params

    def _resolve_sync_search_config(self) -> dict[str, object]:
        sync_search_config = self._method_config.get("sync_search", {})
        if not isinstance(sync_search_config, dict):
            return {}
        return sync_search_config

    def _resolve_scale_search_snap_radius(self) -> int:
        sync_search_config = self._resolve_sync_search_config()
        snap_radius = sync_search_config.get("scale_search_snap_radius", 3)
        if not isinstance(snap_radius, int) or snap_radius < 0:
            return 3
        return snap_radius

    def _resolve_ground_truth_scale(self, sample: LatentSample) -> float | None:
        mechanism_trace = sample.mechanism_trace or {}
        return self._resolve_ground_truth_scale_from_trace(mechanism_trace)

    def _resolve_ground_truth_scale_from_trace(
        self,
        mechanism_trace: dict[str, object],
    ) -> float | None:
        if "sync_ground_truth_scale" not in mechanism_trace:
            return 1.0
        ground_truth_scale = mechanism_trace.get("sync_ground_truth_scale")
        if isinstance(ground_truth_scale, (int, float)):
            return round(float(ground_truth_scale), 6)
        return None

    def _resolve_lambda_sync(self) -> float:
        lambda_sync = self._method_config.get("lambda_sync", 0.1)
        if not isinstance(lambda_sync, (int, float)):
            return 0.1
        return round(float(lambda_sync), 6)

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

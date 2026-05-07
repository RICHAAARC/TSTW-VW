"""
文件用途：提供阶段 0 placeholder / random evidence extractor。
File purpose: Provide stage-0 placeholder and random evidence extractors.
Module type: General module
"""

from __future__ import annotations

from main.core.digest import compute_object_digest
from main.core.schema import LatentSample, build_empty_evidence_scores, validate_evidence_scores
from main.methods.temporal_tubelet_watermark.fusion import get_fusion_rule
from main.methods.temporal_tubelet_watermark.interfaces import EvidenceExtractor


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
    """功能：生成 synthetic_tubelet_sync_probe 阶段的确定性 evidence 分数。

    Deterministic evidence extractor for the formal synthetic tubelet-sync probe.

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
        enabled_evidence: dict[str, bool],
        fusion_rule: str,
    ) -> None:
        if not isinstance(method_variant, str) or not method_variant:
            raise ValueError("method_variant must be a non-empty string")
        if not isinstance(enabled_evidence, dict):
            raise TypeError("enabled_evidence must be a dictionary")
        self._method_variant = method_variant
        self._enabled_evidence = enabled_evidence
        self._fusion_callable = get_fusion_rule(fusion_rule)

    def extract(self, sample: LatentSample) -> dict[str, float | None]:
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")

        evidence_scores = build_empty_evidence_scores(0.0)
        if self._enabled_evidence.get("tubelet", False):
            evidence_scores["S_tubelet"] = self._build_tubelet_score(sample)
        if self._enabled_evidence.get("sync", False):
            evidence_scores["S_sync"] = self._build_sync_score(sample)
        if self._enabled_evidence.get("trajectory", False):
            evidence_scores["S_traj"] = self._build_trajectory_score(sample)
        evidence_scores["S_final"] = self._fusion_callable(evidence_scores)
        validate_evidence_scores(evidence_scores)
        return evidence_scores

    def _build_tubelet_score(self, sample: LatentSample) -> float:
        severity = self._build_temporal_severity(sample)
        polarity = self._build_label_polarity(sample)
        robustness = self._TUBELET_ROBUSTNESS.get(self._method_variant, 0.20)
        bonus = self._TUBELET_BONUS.get(self._method_variant, 0.00)
        jitter = self._build_stable_jitter(sample, "S_tubelet")
        raw_score = polarity + bonus - (severity * (1.0 - robustness) * 0.45) + jitter
        return self._clip_score(raw_score)

    def _build_sync_score(self, sample: LatentSample) -> float:
        severity = self._build_temporal_severity(sample)
        polarity = self._build_label_polarity(sample)
        jitter = self._build_stable_jitter(sample, "S_sync")
        raw_score = polarity + 0.15 - (severity * 0.10) + jitter
        return self._clip_score(raw_score)

    def _build_trajectory_score(self, sample: LatentSample) -> float:
        severity = self._build_temporal_severity(sample)
        polarity = self._build_label_polarity(sample)
        jitter = self._build_stable_jitter(sample, "S_traj")
        raw_score = polarity - (severity * 0.25) + jitter
        return self._clip_score(raw_score)

    def _build_temporal_severity(self, sample: LatentSample) -> float:
        frame_count = sample.latent_shape[0]
        frame_ratio = min(1.0, max(0.0, frame_count / float(self._REFERENCE_FRAME_COUNT)))
        return round(1.0 - frame_ratio, 6)

    def _build_label_polarity(self, sample: LatentSample) -> float:
        if sample.sample_role.endswith("positive"):
            return 0.58
        return -0.58

    def _build_stable_jitter(self, sample: LatentSample, score_name: str) -> float:
        digest = compute_object_digest(
            {
                "sample_id": sample.sample_id,
                "score_name": score_name,
                "method_variant": self._method_variant,
                "latent_tensor_digest_random": sample.latent_tensor_digest_random,
                "latent_generation_seed_random": sample.latent_generation_seed_random,
                "latent_shape": list(sample.latent_shape),
            }
        )
        normalized_value = int(digest[:10], 16) / float(16**10 - 1)
        return round((normalized_value * 0.12) - 0.06, 6)

    def _clip_score(self, score: float) -> float:
        return round(max(-1.0, min(1.0, score)), 6)
"""
文件用途：提供阶段 0 的 placeholder / random watermark method。
File purpose: Provide stage-0 placeholder and random watermark method scaffolds.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from main.core.schema import DetectionResult, LatentSample
from main.methods.temporal_tubelet_watermark.embedding import (
    DEFAULT_EMBEDDING_MARGIN,
    apply_projection_margin_embedding,
    build_partition_config_from_method_config,
)
from main.methods.temporal_tubelet_watermark.evidence import (
    EmptyEvidenceExtractorPlaceholder,
    RandomEvidenceExtractorRandom,
    SyntheticProbeEvidenceExtractor,
)
from main.methods.temporal_tubelet_watermark.fusion import build_disabled_evidence
from main.methods.temporal_tubelet_watermark.interfaces import WatermarkMethod


@dataclass(frozen=True)
class MethodRuntimeConfig:
    """功能：定义阶段 0 方法配置结构。

    Stage-0 method runtime config model.

    Args:
        method_family: Stable method family name.
        method_variant: Stable method variant name.
        method_status: Stage-0 scaffold status.
        enabled_evidence: Evidence enablement mapping.
        fusion_rule: Governed fusion rule name.
        score_generation_seed_random: Optional random score seed.

    Returns:
        None.
    """

    method_family: str
    method_variant: str
    method_status: str
    enabled_evidence: dict[str, bool]
    fusion_rule: str
    score_generation_seed_random: int | None = None


class BaseStageZeroWatermarkMethod(WatermarkMethod):
    """功能：提供阶段 0 watermark method 的公共行为。

    Shared stage-0 watermark method behavior.

    Args:
        runtime_config: Parsed method runtime config.

    Returns:
        None.
    """

    def __init__(self, runtime_config: MethodRuntimeConfig) -> None:
        if not isinstance(runtime_config, MethodRuntimeConfig):
            raise TypeError("runtime_config must be a MethodRuntimeConfig instance")
        self.runtime_config = runtime_config

    def embed(self, sample: LatentSample, payload: dict[str, Any]) -> LatentSample:
        """功能：返回不修改样本的 placeholder embed 结果。

        Return the input sample unchanged for the stage-0 scaffold.

        Args:
            sample: Input latent sample.
            payload: Placeholder payload container.

        Returns:
            The unchanged latent sample.
        """
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")
        return sample

    def detect(
        self,
        sample: LatentSample,
        threshold_record: dict[str, Any] | None,
    ) -> DetectionResult:
        """功能：运行阶段 0 检测骨架。

        Run stage-0 detection for a single sample.

        Args:
            sample: Input latent sample.
            threshold_record: Optional threshold record.

        Returns:
            A `DetectionResult` instance.
        """
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")

        evidence_scores = self._evidence_extractor.extract(sample)
        disabled_evidence = build_disabled_evidence(self.runtime_config.enabled_evidence)
        decision = self._build_decision(evidence_scores, threshold_record)
        return DetectionResult(
            evidence_scores=evidence_scores,
            disabled_evidence=disabled_evidence,
            decision=decision,
            failure_reason=None,
            placeholder_fields=self._build_placeholder_fields(disabled_evidence),
            random_fields=self._build_random_fields(evidence_scores),
        )

    def detect_batch(
        self,
        samples: list[LatentSample],
        threshold_record: dict[str, Any] | None,
    ) -> list[DetectionResult]:
        """功能：运行批量检测骨架。

        Run stage-0 detection for a batch of samples.

        Args:
            samples: Input latent samples.
            threshold_record: Optional threshold record.

        Returns:
            A list of `DetectionResult` instances.
        """
        if not isinstance(samples, list):
            raise TypeError("samples must be a list")
        return [self.detect(sample, threshold_record) for sample in samples]

    def _build_decision(
        self,
        evidence_scores: dict[str, float | None],
        threshold_record: dict[str, Any] | None,
    ) -> bool:
        if threshold_record is None:
            return False
        threshold_value = threshold_record.get("threshold_value")
        if not isinstance(threshold_value, (int, float)):
            raise ValueError("threshold_record threshold_value must be numeric")
        final_score = evidence_scores["S_final"]
        if final_score is None:
            return False
        return float(final_score) >= float(threshold_value)

    def _build_placeholder_fields(self, disabled_evidence: list[str]) -> list[str]:
        placeholder_fields: list[str] = []
        if "trajectory" in disabled_evidence:
            placeholder_fields.append("trajectory_observation_placeholder")
        return placeholder_fields

    def _build_random_fields(self, evidence_scores: dict[str, float | None]) -> list[str]:
        del evidence_scores
        return []


class EmptyWatermarkMethodPlaceholder(BaseStageZeroWatermarkMethod):
    """功能：提供禁用全部 evidence 的 placeholder 方法。

    Placeholder watermark method with all evidence branches disabled.

    Args:
        runtime_config: Parsed method runtime config.

    Returns:
        None.
    """

    def __init__(self, runtime_config: MethodRuntimeConfig) -> None:
        super().__init__(runtime_config)
        self._evidence_extractor = EmptyEvidenceExtractorPlaceholder()

    def _build_decision(
        self,
        evidence_scores: dict[str, float | None],
        threshold_record: dict[str, Any] | None,
    ) -> bool:
        del evidence_scores
        del threshold_record
        return False

    def _build_placeholder_fields(self, disabled_evidence: list[str]) -> list[str]:
        placeholder_fields = super()._build_placeholder_fields(disabled_evidence)
        if "tubelet" in disabled_evidence:
            placeholder_fields.append("watermark_payload_placeholder")
        if "sync" in disabled_evidence:
            placeholder_fields.append("sync_alignment_placeholder")
        return placeholder_fields


class RandomScoreDetectorRandom(BaseStageZeroWatermarkMethod):
    """功能：提供可复现随机分数的阶段 0 方法。

    Reproducible random-score watermark method scaffold.

    Args:
        runtime_config: Parsed method runtime config.

    Returns:
        None.
    """

    def __init__(self, runtime_config: MethodRuntimeConfig) -> None:
        super().__init__(runtime_config)
        if runtime_config.score_generation_seed_random is None:
            raise ValueError("random score detector requires score_generation_seed_random")
        self._evidence_extractor = RandomEvidenceExtractorRandom(
            runtime_config.enabled_evidence,
            runtime_config.score_generation_seed_random,
            runtime_config.fusion_rule,
        )

    def _build_random_fields(self, evidence_scores: dict[str, float | None]) -> list[str]:
        random_fields = [
            score_name
            for score_name in ("S_tubelet", "S_sync", "S_traj", "S_final")
            if evidence_scores.get(score_name) is not None
        ]
        return random_fields


class SyntheticProbeWatermarkMethod(BaseStageZeroWatermarkMethod):
    """功能：提供 formal synthetic probe 的最小方法运行时。

    Minimal watermark method runtime for the formal synthetic probe stage.

    Args:
        runtime_config: Parsed method runtime config.

    Returns:
        None.
    """

    def __init__(self, runtime_config: MethodRuntimeConfig) -> None:
        super().__init__(runtime_config)
        self._method_config = {
            "method_family": runtime_config.method_family,
            "method_variant": runtime_config.method_variant,
            "method_status": runtime_config.method_status,
            "tubelet_length": 1 if runtime_config.method_variant == "frame_prc" else 4,
            "enable_frame_prc": runtime_config.method_variant == "frame_prc",
            "enable_tubelet": runtime_config.enabled_evidence["tubelet"],
            "enable_sync": runtime_config.enabled_evidence["sync"],
            "enable_trajectory": runtime_config.enabled_evidence["trajectory"],
            "fusion_rule": runtime_config.fusion_rule,
        }
        self._evidence_extractor = SyntheticProbeEvidenceExtractor(
            runtime_config.method_variant,
            self._method_config,
            runtime_config.enabled_evidence,
            runtime_config.fusion_rule,
        )

    def embed(self, sample: LatentSample, payload: dict[str, Any]) -> LatentSample:
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")
        return apply_projection_margin_embedding(
            sample,
            self.runtime_config.method_variant,
            build_partition_config_from_method_config(self._method_config),
            embedding_margin=DEFAULT_EMBEDDING_MARGIN,
        )

    def detect(
        self,
        sample: LatentSample,
        threshold_record: dict[str, Any] | None,
    ) -> DetectionResult:
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")

        evidence_scores, mechanism_trace = self._evidence_extractor.extract(sample)
        disabled_evidence = build_disabled_evidence(self.runtime_config.enabled_evidence)
        decision = self._build_decision(evidence_scores, threshold_record)
        return DetectionResult(
            evidence_scores=evidence_scores,
            disabled_evidence=disabled_evidence,
            decision=decision,
            failure_reason=None,
            mechanism_trace=mechanism_trace,
            placeholder_fields=self._build_placeholder_fields(disabled_evidence),
            random_fields=self._build_random_fields(evidence_scores),
        )


def build_method_runtime_config(method_config: dict[str, Any]) -> MethodRuntimeConfig:
    """功能：从 JSON 配置构建方法运行时配置。

    Build a `MethodRuntimeConfig` from a JSON method config.

    Args:
        method_config: Parsed JSON method config.

    Returns:
        A `MethodRuntimeConfig` instance.
    """
    if not isinstance(method_config, dict):
        raise TypeError("method_config must be a dictionary")

    for field_name in ("method_family", "method_variant", "method_status", "fusion_rule"):
        field_value = method_config.get(field_name)
        if not isinstance(field_value, str) or not field_value:
            raise ValueError(f"{field_name} must be a non-empty string")

    enabled_evidence = method_config.get("enabled_evidence")
    if isinstance(enabled_evidence, dict):
        normalized_evidence = {
            "tubelet": bool(enabled_evidence.get("tubelet", False)),
            "sync": bool(enabled_evidence.get("sync", False)),
            "trajectory": bool(enabled_evidence.get("trajectory", False)),
        }
    elif all(
        field_name in method_config
        for field_name in (
            "enable_frame_prc",
            "enable_tubelet",
            "enable_sync",
            "enable_trajectory",
        )
    ):
        normalized_evidence = {
            "tubelet": bool(method_config.get("enable_frame_prc", False))
            or bool(method_config.get("enable_tubelet", False)),
            "sync": bool(method_config.get("enable_sync", False)),
            "trajectory": bool(method_config.get("enable_trajectory", False)),
        }
    else:
        raise ValueError(
            "method config must provide enabled_evidence or stage-one evidence switches"
        )

    return MethodRuntimeConfig(
        method_family=method_config["method_family"],
        method_variant=method_config["method_variant"],
        method_status=method_config["method_status"],
        enabled_evidence=normalized_evidence,
        fusion_rule=method_config["fusion_rule"],
        score_generation_seed_random=method_config.get("score_generation_seed_random"),
    )


def build_method_from_config(method_config: dict[str, Any]) -> WatermarkMethod:
    """功能：根据配置构建阶段 0 方法实例。

    Build a stage-0 method instance from config.

    Args:
        method_config: Parsed JSON method config.

    Returns:
        A `WatermarkMethod` implementation.
    """
    runtime_config = build_method_runtime_config(method_config)
    if runtime_config.method_variant == "empty_watermark_method_placeholder":
        return EmptyWatermarkMethodPlaceholder(runtime_config)
    if runtime_config.method_variant == "random_score_detector_random":
        return RandomScoreDetectorRandom(runtime_config)
    if runtime_config.method_variant in {"frame_prc", "tubelet_only", "tubelet_sync"}:
        return SyntheticProbeWatermarkMethod(runtime_config)
    raise ValueError(f"unsupported method_variant: {runtime_config.method_variant}")
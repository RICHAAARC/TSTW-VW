"""
文件用途：定义阶段 0 方法骨架接口。
File purpose: Define stage-0 scaffold interfaces for latent backends, evidence extractors, and methods.
Module type: General module
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from main.core.schema import DetectionResult, LatentSample


class LatentBackend(ABC):
    """功能：定义 latent backend 的统一接口。

    Abstract interface for stage-0 latent backends.

    Args:
        None.

    Returns:
        None.
    """

    @abstractmethod
    def build_sample(self, sample_id: str, split: str, sample_role: str) -> LatentSample:
        """Build a latent sample for a governed split and role."""


class EvidenceExtractor(ABC):
    """功能：定义 evidence extractor 的统一接口。

    Abstract interface for stage-0 evidence extractors.

    Args:
        None.

    Returns:
        None.
    """

    @abstractmethod
    def extract(self, sample: LatentSample) -> dict[str, float | None]:
        """Extract governed evidence scores from a latent sample."""


class WatermarkMethod(ABC):
    """功能：定义阶段 0 watermark method 的统一接口。

    Abstract interface for stage-0 watermark methods.

    Args:
        None.

    Returns:
        None.
    """

    @abstractmethod
    def embed(self, sample: LatentSample, payload: dict[str, Any]) -> LatentSample:
        """Embed a placeholder payload into a latent sample."""

    @abstractmethod
    def detect(
        self,
        sample: LatentSample,
        threshold_record: dict[str, Any] | None,
    ) -> DetectionResult:
        """Detect watermark evidence for a latent sample."""

    @abstractmethod
    def detect_batch(
        self,
        samples: list[LatentSample],
        threshold_record: dict[str, Any] | None,
    ) -> list[DetectionResult]:
        """Run detection for a batch of latent samples."""
"""
鏂囦欢鐢ㄩ€旓細瀹氫箟闃舵 0 鏂规硶楠ㄦ灦鎺ュ彛銆?File purpose: Define protocol skeleton runtime scaffold interfaces for latent backends, evidence extractors, and methods.
Module type: General module
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from main.core.schema import DetectionResult, LatentSample


class LatentBackend(ABC):
    """鍔熻兘锛氬畾涔?latent backend 鐨勭粺涓€鎺ュ彛銆?
    Abstract interface for protocol skeleton runtime latent backends.

    Args:
        None.

    Returns:
        None.
    """

    @abstractmethod
    def build_sample(self, sample_id: str, split: str, sample_role: str) -> LatentSample:
        """Build a latent sample for a governed split and role."""


class EvidenceExtractor(ABC):
    """鍔熻兘锛氬畾涔?evidence extractor 鐨勭粺涓€鎺ュ彛銆?
    Abstract interface for protocol skeleton runtime evidence extractors.

    Args:
        None.

    Returns:
        None.
    """

    @abstractmethod
    def extract(self, sample: LatentSample) -> dict[str, float | None]:
        """Extract governed evidence scores from a latent sample."""


class WatermarkMethod(ABC):
    """鍔熻兘锛氬畾涔夐樁娈?0 watermark method 鐨勭粺涓€鎺ュ彛銆?
    Abstract interface for protocol skeleton runtime watermark methods.

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
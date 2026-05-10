"""
文件用途：定义阶段 2 占位 VAE backend 接口。
File purpose: Define the placeholder VAE backend interface for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VAEBackend(ABC):
    """功能：定义阶段 2 VAE backend 的最小接口。

    Minimal interface for stage-two VAE backends.

    Args:
        None.

    Returns:
        None.
    """

    @abstractmethod
    def encode_video(self, video_batch: Any, *, config: dict[str, Any] | None = None) -> Any:
        """Encode a placeholder video batch into placeholder latent data."""

    @abstractmethod
    def decode_video(self, latent_batch: Any, *, config: dict[str, Any] | None = None) -> Any:
        """Decode placeholder latent data into a placeholder video batch."""

    @abstractmethod
    def backend_metadata(self) -> dict[str, Any]:
        """Return the metadata payload for the configured backend."""
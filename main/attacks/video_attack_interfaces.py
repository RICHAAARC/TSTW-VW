"""
文件用途：定义真实视频攻击的基础接口与抽象。
File purpose: Define interfaces and abstractions for real video attacks.
Module type: General module
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class VideoAttackBase(ABC):
    """功能：视频攻击的抽象基类。

    Abstract base class for video attacks.

    Args:
        attack_name: Stable attack name.
        attack_params: Attack parameter payload.

    Returns:
        None.
    """

    def __init__(self, attack_name: str, attack_params: dict[str, Any]) -> None:
        if not isinstance(attack_name, str) or not attack_name:
            raise ValueError("attack_name must be a non-empty string")
        if not isinstance(attack_params, dict):
            raise TypeError("attack_params must be a dictionary")
        self.attack_name = attack_name
        self.attack_params = dict(attack_params)

    @abstractmethod
    def apply_video(
        self,
        input_video_path: str | Path,
        output_video_path: str | Path,
        *,
        fps: int = 8,
        resolution: tuple[int, int] | None = None,
        runtime_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """功能：对视频文件应用攻击。

        Apply the attack to a video file.

        Args:
            input_video_path: Input video file path.
            output_video_path: Output video file path.
            fps: Frame rate.
            resolution: Target resolution as (height, width).
            runtime_config: Optional runtime configuration.

        Returns:
            Attack metadata including digest, codec, container, etc.
        """
        raise NotImplementedError


class FrameAttackBase(ABC):
    """功能：帧级攻击的抽象基类。

    Abstract base class for frame-level attacks.

    Args:
        attack_name: Stable attack name.
        attack_params: Attack parameter payload.

    Returns:
        None.
    """

    def __init__(self, attack_name: str, attack_params: dict[str, Any]) -> None:
        if not isinstance(attack_name, str) or not attack_name:
            raise ValueError("attack_name must be a non-empty string")
        if not isinstance(attack_params, dict):
            raise TypeError("attack_params must be a dictionary")
        self.attack_name = attack_name
        self.attack_params = dict(attack_params)

    @abstractmethod
    def apply_frames(
        self,
        frames: Any,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Any:
        """功能：对帧数组应用攻击。

        Apply the attack to a frame array.

        Args:
            frames: Input frames as [F, H, W, 3] float32 array in [0, 1].
            runtime_config: Optional runtime configuration.

        Returns:
            Attacked frames as [F, H, W, 3] float32 array in [0, 1].
        """
        raise NotImplementedError

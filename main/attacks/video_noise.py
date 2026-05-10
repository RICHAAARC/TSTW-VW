"""
文件用途：实现真实视频噪声攻击（高斯噪声）。
File purpose: Implement real video noise attacks (Gaussian noise).
Module type: General module
"""

from __future__ import annotations

from typing import Any

import numpy as np

from main.attacks.video_attack_interfaces import FrameAttackBase
from main.core.digest import compute_object_digest


class GaussianNoiseVideoAttack(FrameAttackBase):
    """功能：高斯噪声攻击。

    Gaussian noise attack with deterministic seeding.

    Args:
        attack_params: Parameters including sigma, seed_policy.

    Returns:
        None.
    """

    def __init__(self, attack_params: dict[str, Any]) -> None:
        super().__init__("gaussian_noise", attack_params)

    def apply_frames(
        self,
        frames: Any,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Any:
        """功能：应用确定性高斯噪声。

        Apply deterministic Gaussian noise.

        Args:
            frames: Input frames [F, H, W, 3] float32 in [0, 1].
            runtime_config: Optional runtime configuration with seeding info.

        Returns:
            Noisy frames clipped to [0, 1].
        """
        if not isinstance(frames, np.ndarray):
            frames = np.asarray(frames, dtype=np.float32)
        if frames.ndim != 4 or frames.shape[-1] != 3:
            raise ValueError("frames must be [F, H, W, 3]")

        sigma = float(self.attack_params.get("sigma", 0.02))
        if sigma < 0.0:
            raise ValueError("sigma must be non-negative")

        frame_count, height, width = frames.shape[0], frames.shape[1], frames.shape[2]

        # 生成确定性种子
        seed_dict = {
            "attack_name": self.attack_name,
            "attack_params": self.attack_params,
        }
        if runtime_config:
            seed_dict.update(
                {
                    "run_id": runtime_config.get("run_id", "unknown"),
                    "sample_id": runtime_config.get("sample_id", "unknown"),
                }
            )
        seed_hex = compute_object_digest(seed_dict)[:16]
        seed = int(seed_hex, 16) & 0x7FFFFFFF

        # 创建随机数生成器
        rng = np.random.RandomState(seed)

        # 生成噪声
        noise = rng.normal(0.0, sigma, size=(frame_count, height, width, 3))
        noisy_frames = np.clip(frames + noise, 0.0, 1.0)

        return noisy_frames.astype(np.float32)

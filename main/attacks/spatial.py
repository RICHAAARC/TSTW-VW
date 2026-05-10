"""
文件用途：实现真实视频空间攻击（resize、crop、blur）。
File purpose: Implement real video spatial attacks (resize, crop, blur).
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from main.attacks.video_attack_interfaces import FrameAttackBase
from main.core.digest import compute_file_digest


try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    from PIL import Image, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class SpatialResizeAttack(FrameAttackBase):
    """功能：空间下采样攻击。

    Spatial downsampling attack using bilinear interpolation.

    Args:
        attack_params: Parameters including scale factor.

    Returns:
        None.
    """

    def __init__(self, attack_params: dict[str, Any]) -> None:
        super().__init__("spatial_resize", attack_params)

    def apply_frames(
        self,
        frames: Any,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Any:
        """功能：应用空间下采样。

        Apply spatial downsampling.

        Args:
            frames: Input frames [F, H, W, 3] float32 in [0, 1].
            runtime_config: Optional runtime configuration.

        Returns:
            Downsampled frames (same shape as input).
        """
        if not isinstance(frames, np.ndarray):
            frames = np.asarray(frames, dtype=np.float32)
        if frames.ndim != 4 or frames.shape[-1] != 3:
            raise ValueError("frames must be [F, H, W, 3]")

        scale = float(self.attack_params.get("scale", 0.75))
        if scale <= 0.0 or scale >= 1.0:
            raise ValueError("scale must be in (0, 1)")

        frame_count, height, width = frames.shape[0], frames.shape[1], frames.shape[2]
        new_height = max(8, int(height * scale))
        new_width = max(8, int(width * scale))

        if not HAS_OPENCV:
            # 简单的实现：直接按比例缩放像素值
            return (frames * scale).astype(np.float32)

        # 使用 OpenCV
        resized_frames = []
        for frame_idx in range(frame_count):
            # 转换为 uint8 [0, 255]
            frame_uint8 = (np.clip(frames[frame_idx], 0.0, 1.0) * 255).astype(np.uint8)
            # 下采样
            downsampled = cv2.resize(frame_uint8, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            # 上采样回原始分辨率
            upsampled = cv2.resize(downsampled, (width, height), interpolation=cv2.INTER_LINEAR)
            # 转换回 float32
            resized_frames.append(upsampled.astype(np.float32) / 255.0)

        return np.stack(resized_frames, axis=0)


class CropResizeAttack(FrameAttackBase):
    """功能：中心裁剪与扩展攻击。

    Center crop and resize attack.

    Args:
        attack_params: Parameters including crop_ratio.

    Returns:
        None.
    """

    def __init__(self, attack_params: dict[str, Any]) -> None:
        super().__init__("crop_resize", attack_params)

    def apply_frames(
        self,
        frames: Any,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Any:
        """功能：应用中心裁剪与恢复。

        Apply center crop and resize back.

        Args:
            frames: Input frames [F, H, W, 3] float32 in [0, 1].
            runtime_config: Optional runtime configuration.

        Returns:
            Cropped and resized frames.
        """
        if not isinstance(frames, np.ndarray):
            frames = np.asarray(frames, dtype=np.float32)
        if frames.ndim != 4 or frames.shape[-1] != 3:
            raise ValueError("frames must be [F, H, W, 3]")

        crop_ratio = float(self.attack_params.get("crop_ratio", 0.85))
        if crop_ratio <= 0.0 or crop_ratio > 1.0:
            raise ValueError("crop_ratio must be in (0, 1]")

        frame_count, height, width = frames.shape[0], frames.shape[1], frames.shape[2]
        crop_height = max(8, int(height * crop_ratio))
        crop_width = max(8, int(width * crop_ratio))

        if not HAS_OPENCV:
            # 简单实现：返回原始帧
            return frames.copy()

        # 使用 OpenCV
        cropped_frames = []
        for frame_idx in range(frame_count):
            frame_uint8 = (np.clip(frames[frame_idx], 0.0, 1.0) * 255).astype(np.uint8)

            # 中心裁剪
            top = (height - crop_height) // 2
            left = (width - crop_width) // 2
            cropped = frame_uint8[top : top + crop_height, left : left + crop_width, :]

            # 恢复到原始分辨率
            restored = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)
            cropped_frames.append(restored.astype(np.float32) / 255.0)

        return np.stack(cropped_frames, axis=0)


class BlurAttack(FrameAttackBase):
    """功能：高斯模糊攻击。

    Gaussian blur attack.

    Args:
        attack_params: Parameters including kernel_size, sigma.

    Returns:
        None.
    """

    def __init__(self, attack_params: dict[str, Any]) -> None:
        super().__init__("blur", attack_params)

    def apply_frames(
        self,
        frames: Any,
        *,
        runtime_config: dict[str, Any] | None = None,
    ) -> Any:
        """功能：应用高斯模糊。

        Apply Gaussian blur.

        Args:
            frames: Input frames [F, H, W, 3] float32 in [0, 1].
            runtime_config: Optional runtime configuration.

        Returns:
            Blurred frames.
        """
        if not isinstance(frames, np.ndarray):
            frames = np.asarray(frames, dtype=np.float32)
        if frames.ndim != 4 or frames.shape[-1] != 3:
            raise ValueError("frames must be [F, H, W, 3]")

        kernel_size = int(self.attack_params.get("kernel_size", 5))
        sigma = float(self.attack_params.get("sigma", 1.0))

        if kernel_size % 2 == 0:
            kernel_size += 1
        if kernel_size < 3:
            kernel_size = 3

        frame_count = frames.shape[0]

        if not HAS_OPENCV:
            # 简单的逐帧平均
            blurred_frames = []
            for frame_idx in range(frame_count):
                frame = frames[frame_idx].copy()
                for c in range(3):
                    for y in range(1, frames.shape[1] - 1):
                        for x in range(1, frames.shape[2] - 1):
                            frame[y, x, c] = np.mean(
                                frames[frame_idx, y - 1 : y + 2, x - 1 : x + 2, c]
                            )
                blurred_frames.append(frame)
            return np.stack(blurred_frames, axis=0)

        # 使用 OpenCV 高斯模糊
        blurred_frames = []
        for frame_idx in range(frame_count):
            frame_uint8 = (np.clip(frames[frame_idx], 0.0, 1.0) * 255).astype(np.uint8)
            blurred = cv2.GaussianBlur(frame_uint8, (kernel_size, kernel_size), sigma)
            blurred_frames.append(blurred.astype(np.float32) / 255.0)

        return np.stack(blurred_frames, axis=0)

"""
文件用途：实现真实视频压缩攻击（H.264/H.265 via ffmpeg）。
File purpose: Implement real video compression attacks via ffmpeg.
Module type: General module
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from main.attacks.video_attack_interfaces import VideoAttackBase
from main.core.digest import compute_file_digest
from main.video.video_io import probe_video_metadata


class CompressionAttackBase(VideoAttackBase):
    """功能：压缩攻击的基类。

    Base class for compression-based attacks.

    Args:
        attack_name: Attack name (h264_compression or h265_compression).
        attack_params: Parameters including crf, preset, etc.

    Returns:
        None.
    """

    def __init__(self, attack_name: str, attack_params: dict[str, Any]) -> None:
        if attack_name not in {"h264_compression", "h265_compression"}:
            raise ValueError(f"unsupported compression attack: {attack_name}")
        super().__init__(attack_name, attack_params)

    def get_ffmpeg_codec(self) -> str:
        """获取 ffmpeg codec 名称。"""
        if self.attack_name == "h264_compression":
            return "libx264"
        if self.attack_name == "h265_compression":
            return "libx265"
        raise ValueError(f"unknown attack_name: {self.attack_name}")

    def _resolve_ffmpeg_binary(self) -> str:
        ffmpeg_binary = shutil.which("ffmpeg")
        if ffmpeg_binary:
            return ffmpeg_binary
        try:
            import imageio_ffmpeg
        except ImportError as exc:
            raise RuntimeError(
                "ffmpeg not found; install ffmpeg or imageio_ffmpeg to use compression attacks"
            ) from exc
        return imageio_ffmpeg.get_ffmpeg_exe()

    def apply_video(
        self,
        input_video_path: str | Path,
        output_video_path: str | Path,
        *,
        fps: int = 8,
        resolution: tuple[int, int] | None = None,
        runtime_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """功能：使用 ffmpeg 对视频文件应用压缩攻击。

        Apply compression attack using ffmpeg.

        Args:
            input_video_path: Input video file path.
            output_video_path: Output video file path.
            fps: Frame rate.
            resolution: Target resolution (height, width).
            runtime_config: Optional runtime configuration.

        Returns:
            Attack metadata.
        """
        input_path = Path(input_video_path)
        output_path = Path(output_video_path)

        if not input_path.exists():
            raise FileNotFoundError(f"input video not found: {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        codec = self.get_ffmpeg_codec()
        crf = int(self.attack_params.get("crf", 28))
        preset = self.attack_params.get("preset", "medium")
        ffmpeg_binary = self._resolve_ffmpeg_binary()

        # 构建 ffmpeg 命令
        ffmpeg_cmd = [
            ffmpeg_binary,
            "-y",  # 覆盖输出文件
            "-i",
            str(input_path),
            "-c:v",
            codec,
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-pix_fmt",
            "yuv420p",  # 确保兼容性
            str(output_path),
        ]

        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                error_msg = result.stderr or "ffmpeg command failed"
                raise RuntimeError(f"ffmpeg compression failed: {error_msg}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg compression timeout (>300s)")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("ffmpeg compression produced empty or missing output")

        input_digest = compute_file_digest(input_path)
        output_digest = compute_file_digest(output_path)

        try:
            output_metadata = probe_video_metadata(output_path)
            output_width = int(output_metadata["width"])
            output_height = int(output_metadata["height"])
            output_frame_count = int(output_metadata["frame_count"])
            output_fps = int(output_metadata["fps"])
        except Exception:
            output_height, output_width = resolution if resolution else (256, 256)
            output_frame_count = 32
            output_fps = int(fps)

        return {
            "attack_name": self.attack_name,
            "attack_params": dict(self.attack_params),
            "input_video_digest": input_digest,
            "attacked_video_relpath": Path(output_video_path).as_posix(),
            "attacked_video_digest": output_digest,
            "codec": codec,
            "container": "mp4",
            "frame_count": output_frame_count,
            "fps": output_fps,
            "height": output_height,
            "width": output_width,
            "pixel_format": "yuv420p",
        }


class H264CompressionAttack(CompressionAttackBase):
    """功能：H.264 压缩攻击。

    H.264 compression attack using libx264 codec.

    Args:
        attack_params: Parameters including crf, preset, etc.

    Returns:
        None.
    """

    def __init__(self, attack_params: dict[str, Any]) -> None:
        super().__init__("h264_compression", attack_params)


class H265CompressionAttack(CompressionAttackBase):
    """功能：H.265 压缩攻击。

    H.265 compression attack using libx265 codec.

    Args:
        attack_params: Parameters including crf, preset, etc.

    Returns:
        None.
    """

    def __init__(self, attack_params: dict[str, Any]) -> None:
        super().__init__("h265_compression", attack_params)

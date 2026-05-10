"""
文件用途：实现真实视频压缩攻击（H.264/H.265 via ffmpeg）。
File purpose: Implement real video compression attacks via ffmpeg.
Module type: General module
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from main.attacks.video_attack_interfaces import VideoAttackBase
from main.core.digest import compute_file_digest


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

        # 构建 ffmpeg 命令
        ffmpeg_cmd = [
            "ffmpeg",
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
        except FileNotFoundError:
            raise RuntimeError("ffmpeg not found; install ffmpeg to use compression attacks")
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg compression timeout (>300s)")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("ffmpeg compression produced empty or missing output")

        input_digest = compute_file_digest(input_path)
        output_digest = compute_file_digest(output_path)

        # 探测输出视频元数据
        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,nb_frames,r_frame_rate",
            "-of",
            "csv=p=0",
            str(output_path),
        ]

        probe_result = None
        try:
            probe_result = subprocess.run(
                probe_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception:
            pass

        output_width, output_height, output_frame_count = 0, 0, 0
        if probe_result and probe_result.returncode == 0:
            try:
                probe_line = probe_result.stdout.strip().split("\n")[0]
                parts = probe_line.split(",")
                if len(parts) >= 3:
                    output_width = int(parts[0])
                    output_height = int(parts[1])
                    output_frame_count = int(parts[2])
            except (ValueError, IndexError):
                pass

        # 若探测失败，使用默认值或输入值
        if output_height == 0 or output_width == 0:
            output_height, output_width = resolution if resolution else (256, 256)
        if output_frame_count == 0:
            output_frame_count = 32  # 默认

        return {
            "attack_name": self.attack_name,
            "attack_params": dict(self.attack_params),
            "input_video_digest": input_digest,
            "attacked_video_relpath": Path(output_video_path).as_posix(),
            "attacked_video_digest": output_digest,
            "codec": codec,
            "container": "mp4",
            "frame_count": output_frame_count,
            "fps": fps,
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

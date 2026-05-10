"""
文件用途：提供真实视频读写与元数据探测工具。
File purpose: Provide real-video IO and metadata probing helpers.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np

from main.core.digest import compute_file_digest


@dataclass(frozen=True)
class VideoFrames:
    """功能：封装标准化后的视频帧张量与基础元数据。

    Container for normalized video frames and basic metadata.

    Args:
        frames: Video frames in `[F, H, W, 3]`, float32, range `[0, 1]`.
        fps: Frame rate value used for decode/output semantics.

    Returns:
        None.
    """

    frames: np.ndarray
    fps: int


def read_video_frames(video_path: str | Path) -> VideoFrames:
    """功能：读取真实视频并输出标准 float32 RGB 张量。

    Read a real video file and return normalized RGB frame tensors.

    Args:
        video_path: Input video path.

    Returns:
        A `VideoFrames` instance with frames in `[F, H, W, 3]`.

    Raises:
        FileNotFoundError: Raised when the input video file is missing.
        ValueError: Raised when decoded frames are empty or invalid.
    """
    resolved_path = Path(video_path)
    if not resolved_path.exists():
        # 中文注释：formal 路径缺失必须显式失败，避免静默跳过样本。
        raise FileNotFoundError(resolved_path)

    reader = imageio.get_reader(str(resolved_path))
    metadata = reader.get_meta_data() or {}
    fps = int(round(float(metadata.get("fps", 0)))) if metadata.get("fps") else 0
    frame_list: list[np.ndarray] = []
    for frame in reader:
        frame_array = np.asarray(frame)
        if frame_array.ndim != 3 or frame_array.shape[2] != 3:
            # 中文注释：仅支持 RGB 三通道视频输入。
            raise ValueError("video frames must use RGB with 3 channels")
        frame_list.append(frame_array.astype(np.float32) / 255.0)
    reader.close()

    if not frame_list:
        # 中文注释：空视频在协议中不可接受。
        raise ValueError("decoded video has no frames")

    stacked_frames = np.stack(frame_list, axis=0).astype(np.float32)
    return VideoFrames(frames=np.clip(stacked_frames, 0.0, 1.0), fps=max(1, fps))


def write_video_mp4(
    frames: np.ndarray,
    output_path: str | Path,
    fps: int,
    codec: str = "libx264",
    crf: int = 18,
) -> dict[str, Any]:
    """功能：将标准化帧张量写出为 mp4，并返回 artifact 元数据。

    Write normalized frame tensors into mp4 and return artifact metadata.

    Args:
        frames: Video frames in `[F, H, W, 3]`, float32, range `[0, 1]`.
        output_path: Output mp4 path.
        fps: Target frame rate.
        codec: ffmpeg codec name, e.g. `libx264` or `libx265`.
        crf: Constant rate factor for ffmpeg encoding.

    Returns:
        A metadata dictionary for the generated video artifact.

    Raises:
        ValueError: Raised when frame tensors are invalid.
    """
    if not isinstance(frames, np.ndarray):
        raise TypeError("frames must be a numpy ndarray")
    if frames.ndim != 4 or frames.shape[-1] != 3:
        raise ValueError("frames must have shape [F, H, W, 3]")
    if frames.shape[0] < 1:
        raise ValueError("frames must contain at least one frame")
    if not isinstance(fps, int) or fps < 1:
        raise ValueError("fps must be a positive integer")

    normalized_frames = np.clip(frames.astype(np.float32), 0.0, 1.0)
    frame_u8 = np.round(normalized_frames * 255.0).astype(np.uint8)

    destination_path = Path(output_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(
        str(destination_path),
        format="FFMPEG",
        fps=fps,
        codec=codec,
        ffmpeg_params=["-crf", str(int(crf)), "-pix_fmt", "yuv420p"],
    )
    for frame in frame_u8:
        writer.append_data(frame)
    writer.close()

    return {
        "video_relpath": destination_path.as_posix(),
        "video_digest": compute_file_digest(destination_path),
        "frame_count": int(frame_u8.shape[0]),
        "fps": int(fps),
        "height": int(frame_u8.shape[1]),
        "width": int(frame_u8.shape[2]),
        "codec": codec,
        "container": "mp4",
        "pixel_format": "yuv420p",
    }


def probe_video_metadata(video_path: str | Path) -> dict[str, object]:
    """功能：探测视频基础元数据。

    Probe basic metadata for a video file.

    Args:
        video_path: Input video path.

    Returns:
        A metadata dictionary with frame count, fps, and resolution.
    """
    video_frames = read_video_frames(video_path)
    frames = video_frames.frames
    return {
        "frame_count": int(frames.shape[0]),
        "fps": int(video_frames.fps),
        "height": int(frames.shape[1]),
        "width": int(frames.shape[2]),
        "channels": int(frames.shape[3]),
    }

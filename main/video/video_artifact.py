"""
文件用途：提供阶段 2 占位视频 artifact 的读写与摘要工具。
File purpose: Provide IO helpers and digest metadata for stage-two placeholder video artifacts.
Module type: General module
"""

from __future__ import annotations

from array import array
import math
from pathlib import Path
from typing import Any

from main.core.digest import compute_file_digest
from main.core.schema import LatentSample
from main.core.tensor_artifact import read_float_tensor_npy, write_float_tensor_npy


def load_video_artifact(file_path: str | Path) -> Any:
    """功能：读取占位视频 tensor artifact。

    Read a placeholder video tensor artifact.

    Args:
        file_path: Video artifact path.

    Returns:
        The loaded float tensor artifact.
    """
    return read_float_tensor_npy(file_path)


def materialize_video_artifact_from_latent(
    sample: LatentSample,
    output_root: str | Path,
    artifact_relpath: str | Path,
    fps: int,
    codec: str = "tensor_npy",
) -> dict[str, Any]:
    """功能：根据 latent sample 生成占位视频 artifact。

    Materialize a placeholder video artifact from a latent sample.

    Args:
        sample: Input latent sample.
        output_root: Run root path.
        artifact_relpath: Relative artifact path.
        fps: Declared frame rate.
        codec: Artifact codec label.

    Returns:
        Video artifact metadata.
    """
    if not isinstance(sample, LatentSample):
        raise TypeError("sample must be a LatentSample instance")
    if sample.latent_artifact_path is None:
        raise ValueError("sample must carry latent_artifact_path")
    if not isinstance(fps, int) or fps < 1:
        raise ValueError("fps must be a positive integer")

    output_path = Path(output_root) / Path(artifact_relpath)
    if output_path.exists():
        video_digest = compute_file_digest(output_path)
        video_artifact = read_float_tensor_npy(output_path)
        frames, _, height, width = video_artifact.shape
        return {
            "video_relpath": Path(artifact_relpath).as_posix(),
            "video_digest": video_digest,
            "frame_count": frames,
            "fps": fps,
            "height": height,
            "width": width,
            "codec": codec,
            "container": "npy",
        }

    latent_artifact = read_float_tensor_npy(sample.latent_artifact_path)
    frames, channels, height, width = latent_artifact.shape
    spatial_size = height * width
    frame_size = channels * spatial_size
    video_values = array("f")
    for frame_index in range(frames):
        frame_offset = frame_index * frame_size
        for target_channel in range(3):
            source_channel = target_channel % channels
            channel_offset = frame_offset + source_channel * spatial_size
            for spatial_index in range(spatial_size):
                latent_value = float(latent_artifact.values[channel_offset + spatial_index])
                video_values.append((math.tanh(latent_value) + 1.0) / 2.0)
    write_float_tensor_npy(output_path, (frames, 3, height, width), video_values)
    return {
        "video_relpath": Path(artifact_relpath).as_posix(),
        "video_digest": compute_file_digest(output_path),
        "frame_count": frames,
        "fps": fps,
        "height": height,
        "width": width,
        "codec": codec,
        "container": "npy",
    }


def copy_latent_artifact(
    sample: LatentSample,
    output_root: str | Path,
    artifact_relpath: str | Path,
) -> dict[str, str]:
    """功能：复制 latent artifact 到阶段 2 受治理路径。

    Copy a latent artifact into the governed stage-two layout.

    Args:
        sample: Input latent sample.
        output_root: Run root path.
        artifact_relpath: Relative artifact path.

    Returns:
        A dictionary containing the relative path and digest.
    """
    if not isinstance(sample, LatentSample):
        raise TypeError("sample must be a LatentSample instance")
    if sample.latent_artifact_path is None:
        raise ValueError("sample must carry latent_artifact_path")

    output_path = Path(output_root) / Path(artifact_relpath)
    if not output_path.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(Path(sample.latent_artifact_path).read_bytes())
    return {
        "latent_relpath": Path(artifact_relpath).as_posix(),
        "latent_digest": compute_file_digest(output_path),
    }
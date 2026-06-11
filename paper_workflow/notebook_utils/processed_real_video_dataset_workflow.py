"""
File purpose: Provide notebook-specific orchestration for processed real-video dataset builds.
Module type: Notebook workflow helper
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.prepare_datasets.build_processed_real_video_dataset import (
    build_processed_real_video_dataset,
)


def _json_safe(value: Any) -> Any:
    """Convert workflow return values to JSON-serializable values."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def build_processed_dataset_handoff(
    *,
    raw_dataset_download_manifest_path: str | Path | None,
    raw_dataset_key: str,
    raw_archive_path: str | Path | None,
    processed_dataset_root: str | Path,
    processed_dataset_key: str,
    local_workspace_root: str | Path,
    target_frame_count: int = 32,
    target_fps: int = 8,
    target_height: int = 256,
    target_width: int = 256,
    frame_sampling_policy: str = "deterministic_uniform",
    codec: str = "libx264",
    crf: int = 18,
    clip_stride_frames: int | None = None,
    max_samples_per_split: int | None = None,
    registry_path: str | Path | None = None,
    clean_workspace: bool = False,
) -> dict[str, Any]:
    """Build the processed dataset and return the notebook handoff payload."""
    handoff_payload = build_processed_real_video_dataset(
        raw_dataset_download_manifest_path=raw_dataset_download_manifest_path,
        raw_dataset_key=raw_dataset_key,
        raw_archive_path=raw_archive_path,
        processed_dataset_root=processed_dataset_root,
        processed_dataset_key=processed_dataset_key,
        target_frame_count=target_frame_count,
        target_fps=target_fps,
        target_height=target_height,
        target_width=target_width,
        frame_sampling_policy=frame_sampling_policy,
        codec=codec,
        crf=crf,
        clip_stride_frames=clip_stride_frames,
        max_samples_per_split=max_samples_per_split,
        local_workspace_root=local_workspace_root,
        registry_path=registry_path,
        clean_workspace=clean_workspace,
    )
    return _json_safe(handoff_payload)

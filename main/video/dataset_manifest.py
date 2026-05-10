"""
文件用途：提供阶段 2 数据 manifest 的最小加载与摘要工具。
File purpose: Provide minimal loading and summarization helpers for the stage-two dataset manifest.
Module type: General module
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResolvedVideoSample:
    """功能：表示解析后的本地视频样本。

    Resolved local video sample record.

    Args:
        video_source_id: Stable video source identifier.
        split: Governed split name.
        relpath: Relative manifest path.
        resolved_path: Resolved local absolute path.

    Returns:
        None.
    """

    video_source_id: str
    split: str
    relpath: str
    resolved_path: Path


def load_dataset_manifest(path: str | Path) -> dict[str, Any]:
    """功能：加载阶段 2 数据 manifest。

    Load the stage-two dataset manifest.

    Args:
        path: Manifest file path.

    Returns:
        The parsed manifest payload.
    """
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("dataset manifest must define a non-empty samples list")
    seen_source_ids: set[str] = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("dataset manifest samples must be dictionaries")
        video_source_id = sample.get("video_source_id")
        relpath = sample.get("relpath")
        if not isinstance(video_source_id, str) or not video_source_id:
            raise ValueError("video_source_id must be a non-empty string")
        if video_source_id in seen_source_ids:
            raise ValueError("video_source_id values must be unique")
        seen_source_ids.add(video_source_id)
        if not isinstance(relpath, str) or not relpath or Path(relpath).is_absolute():
            raise ValueError("manifest relpath entries must be relative paths")
    return manifest


def summarize_dataset_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """功能：汇总阶段 2 数据 manifest 的 split 与样本数。

    Summarize split-level counts for the stage-two dataset manifest.

    Args:
        manifest: Parsed manifest payload.

    Returns:
        A summary dictionary.
    """
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dictionary")
    samples = manifest.get("samples")
    if not isinstance(samples, list):
        raise ValueError("manifest samples must be a list")
    split_counts: dict[str, int] = {}
    for sample in samples:
        split = str(sample.get("split", "unknown"))
        split_counts[split] = split_counts.get(split, 0) + 1
    return {
        "dataset_name": manifest.get("dataset_name"),
        "dataset_version": manifest.get("dataset_version"),
        "sample_count": len(samples),
        "split_counts": split_counts,
    }


def resolve_manifest_samples(
    manifest: dict[str, Any],
    local_dataset_root: str | Path,
    formal_mode: bool = True,
) -> list[ResolvedVideoSample]:
    """功能：解析并校验 manifest 样本的本地视频路径。

    Resolve and validate local video paths from dataset manifest.

    Args:
        manifest: Parsed dataset manifest payload.
        local_dataset_root: Local dataset root directory.
        formal_mode: Whether to enforce strict file existence checks.

    Returns:
        A list of resolved samples.
    """
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dictionary")
    dataset_root = Path(local_dataset_root)
    if not dataset_root.exists():
        raise FileNotFoundError(dataset_root)

    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("manifest samples must be a non-empty list")

    seen_video_source_ids: set[str] = set()
    split_by_video_source_id: dict[str, str] = {}
    resolved_samples: list[ResolvedVideoSample] = []

    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("manifest samples must be dictionaries")
        video_source_id = str(sample.get("video_source_id", "")).strip()
        split = str(sample.get("split", "")).strip()
        relpath = str(sample.get("relpath", "")).strip()
        if not video_source_id:
            raise ValueError("video_source_id must be a non-empty string")
        if not split:
            raise ValueError("split must be a non-empty string")
        if not relpath:
            raise ValueError("relpath must be a non-empty string")
        if Path(relpath).is_absolute():
            raise ValueError("manifest relpath entries must be relative paths")
        if not relpath.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            raise ValueError("manifest relpath must use a supported video extension")

        existing_split = split_by_video_source_id.get(video_source_id)
        if existing_split is not None and existing_split != split:
            raise ValueError("video_source_id cannot appear across multiple splits")
        split_by_video_source_id[video_source_id] = split
        seen_video_source_ids.add(video_source_id)

        resolved_path = (dataset_root / relpath).resolve()
        try:
            resolved_path.relative_to(dataset_root.resolve())
        except ValueError as error:
            raise ValueError("resolved sample path escapes local_dataset_root") from error

        if formal_mode and not resolved_path.exists():
            raise FileNotFoundError(resolved_path)

        resolved_samples.append(
            ResolvedVideoSample(
                video_source_id=video_source_id,
                split=split,
                relpath=relpath,
                resolved_path=resolved_path,
            )
        )

    split_names = {sample.split for sample in resolved_samples}
    if "calibration" not in split_names or "test" not in split_names:
        raise ValueError("manifest must include both calibration and test splits")

    if len(seen_video_source_ids) != len(resolved_samples):
        raise ValueError("video_source_id values must be unique")

    return resolved_samples
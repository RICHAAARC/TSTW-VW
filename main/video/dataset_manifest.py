"""
文件用途：提供阶段 2 数据 manifest 的最小加载与摘要工具。
File purpose: Provide minimal loading and summarization helpers for the stage-two dataset manifest.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
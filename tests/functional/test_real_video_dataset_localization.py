"""
文件用途：验证阶段 2 本地数据集定位与 manifest 解析。
File purpose: Validate local dataset localization and manifest resolution for stage-two runtime.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

from main.video.dataset_localizer import (
    load_runtime_dataset_config,
    resolve_local_dataset_root,
    resolve_runtime_dataset_manifest_path,
)
from main.video.dataset_manifest import load_dataset_manifest, resolve_manifest_samples


@pytest.mark.unit
def test_dataset_localizer_resolves_runtime_dataset_paths(tmp_path: Path) -> None:
    """Validate local dataset root and manifest are resolved from runtime config.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    dataset_root = tmp_path / "datasets" / "real_video_probe"
    dataset_root.mkdir(parents=True, exist_ok=True)
    manifest_path = dataset_root / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_name": "tiny_dataset",
                "dataset_version": "v1",
                "samples": [
                    {
                        "video_source_id": "rvp_000000",
                        "relpath": "source/rvp_000000.mp4",
                        "split": "dev",
                    },
                    {
                        "video_source_id": "rvp_000001",
                        "relpath": "source/rvp_000001.mp4",
                        "split": "calibration",
                    },
                    {
                        "video_source_id": "rvp_000002",
                        "relpath": "source/rvp_000002.mp4",
                        "split": "test",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (dataset_root / "source").mkdir(parents=True, exist_ok=True)
    (dataset_root / "source" / "rvp_000000.mp4").write_bytes(b"video-dev")
    (dataset_root / "source" / "rvp_000001.mp4").write_bytes(b"video-a")
    (dataset_root / "source" / "rvp_000002.mp4").write_bytes(b"video-b")

    runtime_config_path = tmp_path / "runtime_config.json"
    runtime_config_path.write_text(
        json.dumps(
            {
                "local_dataset_root": str(dataset_root),
                "dataset_manifest_path": str(manifest_path),
                "dataset_key": "tiny_dataset",
                "cache_tar_sha256": "dummy",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    runtime_config = load_runtime_dataset_config(runtime_config_path)
    resolved_root = resolve_local_dataset_root(runtime_config)
    resolved_manifest = resolve_runtime_dataset_manifest_path(runtime_config)

    assert resolved_root == dataset_root
    assert resolved_manifest == manifest_path

    manifest = load_dataset_manifest(resolved_manifest)
    resolved_samples = resolve_manifest_samples(manifest, resolved_root, formal_mode=True)
    assert len(resolved_samples) == 3
    assert {sample.split for sample in resolved_samples} == {"dev", "calibration", "test"}


@pytest.mark.unit
def test_resolve_manifest_samples_requires_governed_dev_split(tmp_path: Path) -> None:
    """Validate the governed manifest requires a dev split.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    dataset_root = tmp_path / "datasets" / "real_video_probe"
    (dataset_root / "source").mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_name": "tiny_dataset",
        "dataset_version": "v1",
        "samples": [
            {
                "video_source_id": "rvp_000010",
                "relpath": "source/rvp_000010.mp4",
                "split": "calibration",
            },
            {
                "video_source_id": "rvp_000011",
                "relpath": "source/rvp_000011.mp4",
                "split": "test",
            },
        ],
    }
    (dataset_root / "source" / "rvp_000010.mp4").write_bytes(b"video-a")
    (dataset_root / "source" / "rvp_000011.mp4").write_bytes(b"video-b")

    with pytest.raises(ValueError, match="dev, calibration, and test"):
        resolve_manifest_samples(manifest, dataset_root, formal_mode=True)


@pytest.mark.unit
def test_resolve_manifest_samples_fails_when_formal_mp4_missing(tmp_path: Path) -> None:
    """Validate formal mode fails when required mp4 files are missing.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    dataset_root = tmp_path / "datasets" / "real_video_probe"
    dataset_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_name": "tiny_dataset",
        "dataset_version": "v1",
        "samples": [
            {
                "video_source_id": "rvp_000009",
                "relpath": "source/rvp_000009.mp4",
                "split": "dev",
            },
            {
                "video_source_id": "rvp_000010",
                "relpath": "source/rvp_000010.mp4",
                "split": "calibration",
            },
            {
                "video_source_id": "rvp_000011",
                "relpath": "source/rvp_000011.mp4",
                "split": "test",
            },
        ],
    }

    with pytest.raises(FileNotFoundError):
        resolve_manifest_samples(manifest, dataset_root, formal_mode=True)

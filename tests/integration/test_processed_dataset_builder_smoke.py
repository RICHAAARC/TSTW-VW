"""
文件用途：验证 processed real-video dataset builder 的最小行为。
File purpose: Validate the minimal behavior of the processed real-video dataset builder.
Module type: General module
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.integration

from main.video.video_io import write_video_mp4
from scripts.prepare_datasets.build_processed_real_video_dataset import (
    build_processed_real_video_dataset,
)


@pytest.mark.smoke
def test_build_processed_real_video_dataset_from_local_video_directory(tmp_path: Path) -> None:
    """Validate the builder materializes governed processed-dataset artifacts.

    Args:
        tmp_path: Temporary repository workspace.

    Returns:
        None.
    """
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("imageio_ffmpeg is unavailable")

    raw_root = tmp_path / "raw_videos"
    raw_root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260511)
    write_video_mp4(
        rng.random((6, 12, 16, 3), dtype=np.float32),
        raw_root / "alpha.mp4",
        fps=8,
        codec="libx264",
        crf=20,
    )
    write_video_mp4(
        rng.random((6, 12, 16, 3), dtype=np.float32),
        raw_root / "beta.mp4",
        fps=8,
        codec="libx264",
        crf=20,
    )

    processed_root = tmp_path / "processed" / "demo_dataset"
    handoff_payload = build_processed_real_video_dataset(
        raw_archive_path=raw_root,
        processed_dataset_root=processed_root,
        processed_dataset_key="demo_dataset",
        target_frame_count=4,
        target_fps=8,
        target_height=8,
        target_width=8,
    )

    manifest_path = Path(handoff_payload["PROCESSED_DATASET_MANIFEST"])
    summary_path = Path(handoff_payload["processed_dataset_summary.json"])
    checks_path = Path(handoff_payload["processed_dataset_checks.json"])
    registry_path = Path(handoff_payload["dataset_registry.json"])

    assert manifest_path.exists()
    assert summary_path.exists()
    assert checks_path.exists()
    assert registry_path.exists()

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    checks_payload = json.loads(checks_path.read_text(encoding="utf-8"))
    registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))

    assert manifest_payload["dataset_key"] == "demo_dataset"
    assert manifest_payload["target_frame_count"] == 4
    assert manifest_payload["target_resolution"] == [8, 8]
    assert len(manifest_payload["samples"]) == 3
    assert {sample["split"] for sample in manifest_payload["samples"]} == {"dev", "calibration", "test"}
    assert all(str(sample["relpath"]).endswith(".mp4") for sample in manifest_payload["samples"])
    assert summary_payload["sample_count"] == 3
    assert summary_payload["split_counts"] == {
        "dev": 1,
        "calibration": 1,
        "test": 1,
    }
    assert checks_payload["status"] is True
    assert checks_payload["required_paths"]["dataset_manifest"] is True
    assert isinstance(registry_payload.get("datasets"), list)
    assert any(
        entry.get("processed_dataset_key") == "demo_dataset"
        for entry in registry_payload["datasets"]
        if isinstance(entry, dict)
    )
"""
文件用途：验证阶段 2 视频 artifact digest 行为。
File purpose: Validate digest behavior for stage-two video artifacts.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.quick

from pathlib import Path

from main.backends.real_video_vae_latent import RealVideoVAELatentBackend


def test_video_artifact_digest_is_stable_and_relative(tmp_path: Path) -> None:
    """Validate that stage-two video artifact digests are stable and relative.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "real_video_digest"
    backend = RealVideoVAELatentBackend(latent_shape=(8, 2, 8, 8), runtime_profile="tiny")
    backend.set_output_root(output_root)

    first_sample = backend.build_sample("rvp_same", "calibration", "clean_negative")
    repeated_sample = backend.build_sample("rvp_same", "calibration", "clean_negative")
    second_sample = backend.build_sample("rvp_other", "calibration", "clean_negative")

    assert first_sample.mechanism_trace["video_source_digest"] == repeated_sample.mechanism_trace["video_source_digest"]
    assert first_sample.mechanism_trace["video_source_digest"] != second_sample.mechanism_trace["video_source_digest"]
    assert not Path(first_sample.mechanism_trace["video_source_relpath"]).is_absolute()

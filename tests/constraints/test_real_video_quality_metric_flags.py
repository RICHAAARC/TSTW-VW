"""
文件用途：验证真实视频质量指标的 governed flags 与 failure reason 行为。
File purpose: Validate governed flags and failure reasons for real-video quality metrics.
Module type: General module
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import main.analysis.real_video_quality_metrics as real_quality_metrics


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_real_video_quality_metrics_disabled_flags_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate disabled LPIPS and CLIP metrics report explicit reasons.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    frames = np.ones((4, 8, 8, 3), dtype=np.float32) * 0.5
    monkeypatch.setattr(
        real_quality_metrics,
        "read_video_frames",
        lambda path: SimpleNamespace(frames=frames),
    )

    payload = real_quality_metrics.build_real_video_quality_metrics_payload(
        "reference.mp4",
        "comparison.mp4",
        runtime_config={
            "quality_metrics": {
                "enable_lpips": False,
                "enable_clip_similarity": False,
            }
        },
    )

    assert payload["watermarked_video_lpips"] is None
    assert payload["lpips_failure_reason"] == "lpips_disabled_by_config"
    assert payload["clip_failure_reason"] == "clip_similarity_disabled_by_config"
    assert "watermarked_video_lpips" in payload["disabled_quality_metrics"]
    assert "clip_similarity" in payload["disabled_quality_metrics"]


def test_real_video_quality_metrics_clip_flag_reports_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate CLIP enablement is auditable even before implementation lands.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    frames = np.ones((4, 8, 8, 3), dtype=np.float32) * 0.5
    monkeypatch.setattr(
        real_quality_metrics,
        "read_video_frames",
        lambda path: SimpleNamespace(frames=frames),
    )

    payload = real_quality_metrics.build_real_video_quality_metrics_payload(
        "reference.mp4",
        "comparison.mp4",
        runtime_config={
            "quality_metrics": {
                "enable_lpips": False,
                "enable_clip_similarity": True,
            }
        },
    )

    assert payload["clip_similarity_score"] is None
    assert payload["clip_failure_reason"] == "clip_similarity_not_implemented"
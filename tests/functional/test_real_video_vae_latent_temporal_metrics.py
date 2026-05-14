"""
文件用途：验证阶段 2 scaffold 时序指标负载。File purpose: Validate temporal-metrics payloads for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import numpy as np

pytestmark = pytest.mark.quick

from pathlib import Path

import main.analysis.real_video_temporal_metrics as real_temporal_metrics
from main.analysis.temporal_metrics import build_temporal_metrics_payload
from main.backends.real_video_vae_latent import RealVideoVAELatentBackend
from main.video.video_artifact import materialize_video_artifact_from_latent


def test_real_video_vae_latent_temporal_metrics_payload_is_materialized(tmp_path: Path) -> None:
    """Validate that stage-two temporal metrics produce governed payload fields.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "real_video_temporal_metrics"
    backend = RealVideoVAELatentBackend(latent_shape=(8, 2, 8, 8), runtime_profile="tiny")
    backend.set_output_root(output_root)
    reference_sample = backend.build_sample("rvp_temporal_ref", "test", "clean_negative")
    comparison_sample = backend.build_sample("rvp_temporal_cmp", "test", "clean_negative")
    reference_meta = materialize_video_artifact_from_latent(
        reference_sample,
        output_root,
        Path("artifacts") / "videos" / "temporal" / "reference.npy",
        fps=8,
    )
    comparison_meta = materialize_video_artifact_from_latent(
        comparison_sample,
        output_root,
        Path("artifacts") / "videos" / "temporal" / "comparison.npy",
        fps=8,
    )
    payload = build_temporal_metrics_payload(
        output_root / reference_meta["video_relpath"],
        output_root / comparison_meta["video_relpath"],
    )

    assert set(payload.keys()) == {
        "temporal_consistency_score",
        "flicker_score",
        "motion_consistency_score",
        "disabled_temporal_metrics",
        "temporal_metrics_runtime",
    }
    assert payload["motion_consistency_score"] is None
    assert "motion_consistency" in payload["disabled_temporal_metrics"]


def test_real_video_temporal_metrics_motion_consistency_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate motion consistency is computed when explicitly enabled.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    reference_frames = np.stack(
        [
            np.full((8, 8, 3), fill_value=value, dtype=np.float32)
            for value in (0.1, 0.2, 0.4, 0.7)
        ],
        axis=0,
    )
    comparison_frames = np.stack(
        [
            np.full((8, 8, 3), fill_value=value, dtype=np.float32)
            for value in (0.1, 0.22, 0.38, 0.68)
        ],
        axis=0,
    )
    frame_lookup = {
        "reference.mp4": SimpleNamespace(frames=reference_frames),
        "comparison.mp4": SimpleNamespace(frames=comparison_frames),
    }
    monkeypatch.setattr(
        real_temporal_metrics,
        "read_video_frames",
        lambda path: frame_lookup[str(path)],
    )

    payload = real_temporal_metrics.build_real_video_temporal_metrics_payload(
        "reference.mp4",
        "comparison.mp4",
        runtime_config={
            "temporal_metrics": {"enable_motion_consistency": True},
        },
    )

    assert payload["motion_consistency_score"] is not None
    assert payload["motion_consistency_score"] >= 0.0
    assert payload["motion_consistency_score"] <= 1.0
    assert payload["motion_consistency_backend"] == "frame_difference_proxy"
    assert payload["motion_consistency_frame_count"] == 4
    assert payload["motion_consistency_normalization_mode"] == "per_transition_max_motion"
    assert payload["disabled_temporal_metrics"] == []
    assert payload["motion_consistency_failure_reason"] is None

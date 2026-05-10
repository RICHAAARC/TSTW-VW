"""
鏂囦欢鐢ㄩ€旓細楠岃瘉闃舵 2 scaffold 鏃跺簭鎸囨爣璐熻浇銆?File purpose: Validate temporal-metrics payloads for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

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
    output_root = tmp_path / "outputs" / "runs" / "stage2_temporal_metrics"
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
    }
    assert payload["motion_consistency_score"] is None
    assert "motion_consistency" in payload["disabled_temporal_metrics"]

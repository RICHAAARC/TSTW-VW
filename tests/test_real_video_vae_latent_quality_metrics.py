"""
鏂囦欢鐢ㄩ€旓細楠岃瘉闃舵 2 scaffold 璐ㄩ噺鎸囨爣璐熻浇銆?File purpose: Validate quality-metrics payloads for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.analysis.quality_metrics import build_quality_metrics_payload
from main.backends.real_video_vae_latent import RealVideoVAELatentBackend
from main.video.video_artifact import materialize_video_artifact_from_latent


def test_real_video_vae_latent_quality_metrics_payload_is_materialized(tmp_path: Path) -> None:
    """Validate that stage-two quality metrics produce governed payload fields.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "stage2_quality_metrics"
    backend = RealVideoVAELatentBackend(latent_shape=(8, 2, 8, 8), runtime_profile="tiny")
    backend.set_output_root(output_root)
    reference_sample = backend.build_sample("rvp_quality_ref", "test", "clean_negative")
    comparison_sample = backend.build_sample("rvp_quality_cmp", "test", "clean_negative")
    reference_meta = materialize_video_artifact_from_latent(
        reference_sample,
        output_root,
        Path("artifacts") / "videos" / "quality" / "reference.npy",
        fps=8,
    )
    comparison_meta = materialize_video_artifact_from_latent(
        comparison_sample,
        output_root,
        Path("artifacts") / "videos" / "quality" / "comparison.npy",
        fps=8,
    )
    payload = build_quality_metrics_payload(
        output_root / reference_meta["video_relpath"],
        output_root / comparison_meta["video_relpath"],
    )

    assert set(payload.keys()) == {
        "vae_reconstruction_psnr",
        "vae_reconstruction_ssim",
        "watermarked_video_psnr",
        "watermarked_video_ssim",
        "watermarked_video_lpips",
        "clip_similarity_score",
        "disabled_quality_metrics",
        "quality_failure_reason",
    }
    assert payload["vae_reconstruction_psnr"] is not None
    assert payload["vae_reconstruction_ssim"] is not None

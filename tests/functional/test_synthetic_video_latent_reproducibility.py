"""
文件用途：验证 synthetic video latent tensor artifact backend 的可复现性。
File purpose: Validate the reproducibility of the synthetic video latent tensor artifact backend.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.quick

import os
from pathlib import Path

from experiments.synthetic_tubelet_sync_probe.synthetic_video_latent import (
    SyntheticVideoLatentPlaceholder,
)


def test_synthetic_video_latent_backend_writes_reproducible_tensor_artifact(
    tmp_path: Path,
) -> None:
    """Validate that identical governed inputs reproduce the same tensor artifact.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)

    first_sample = backend.build_sample(
        "sample_test_watermarked_positive_000001",
        "test",
        "watermarked_positive",
    )
    artifact_path = Path(first_sample.latent_artifact_path or "")
    sentinel_mtime_ns = max(1, artifact_path.stat().st_mtime_ns - 1_000_000_000)
    os.utime(artifact_path, ns=(sentinel_mtime_ns, sentinel_mtime_ns))
    second_sample = backend.build_sample(
        "sample_test_watermarked_positive_000001",
        "test",
        "watermarked_positive",
    )

    assert first_sample.latent_artifact_path is not None
    assert artifact_path.exists()
    assert first_sample.latent_artifact_relpath == second_sample.latent_artifact_relpath
    assert first_sample.latent_artifact_digest == second_sample.latent_artifact_digest
    assert first_sample.latent_tensor_digest_random == second_sample.latent_tensor_digest_random
    assert first_sample.latent_shape == (16, 4, 16, 16)
    assert artifact_path.stat().st_mtime_ns == sentinel_mtime_ns


def test_synthetic_video_latent_backend_separates_sample_identity(tmp_path: Path) -> None:
    """Validate that different governed identities produce different tensor artifacts.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)

    calibration_sample = backend.build_sample(
        "sample_calibration_clean_negative_000001",
        "calibration",
        "clean_negative",
    )
    attacked_sample = backend.build_sample(
        "sample_test_attacked_positive_000001",
        "test",
        "attacked_positive",
    )

    assert calibration_sample.latent_artifact_digest != attacked_sample.latent_artifact_digest
    assert calibration_sample.latent_generation_seed_random != attacked_sample.latent_generation_seed_random
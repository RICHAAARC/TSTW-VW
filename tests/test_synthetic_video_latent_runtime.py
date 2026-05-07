"""
文件用途：验证 synthetic video latent placeholder runtime 的最小运行语义。
File purpose: Validate the minimal runtime behavior of the synthetic video latent placeholder backend.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.backends.synthetic_video_latent import (
    LATENT_BACKEND_NAME,
    SyntheticVideoLatentPlaceholder,
    build_synthetic_video_latent_backend_from_support_config,
)
from main.core.registry import load_json_config


ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_video_latent_backend_builds_reproducible_sample() -> None:
    """Validate that identical inputs produce identical synthetic latent metadata.

    Args:
        None.

    Returns:
        None.
    """
    support_config = load_json_config(
        ROOT / "configs" / "protocol" / "synthetic_tubelet_sync_probe.json"
    )
    backend = build_synthetic_video_latent_backend_from_support_config(support_config)

    first_sample = backend.build_sample(
        "sample_test_watermarked_positive_000001",
        "test",
        "watermarked_positive",
    )
    second_sample = backend.build_sample(
        "sample_test_watermarked_positive_000001",
        "test",
        "watermarked_positive",
    )

    assert first_sample.latent_backend_name == LATENT_BACKEND_NAME
    assert first_sample.latent_backend_status == "placeholder_runtime"
    assert first_sample.latent_shape == (32, 4, 32, 32)
    assert (
        first_sample.latent_generation_seed_random
        == second_sample.latent_generation_seed_random
    )
    assert (
        first_sample.latent_tensor_digest_random
        == second_sample.latent_tensor_digest_random
    )


def test_synthetic_video_latent_backend_separates_split_and_role() -> None:
    """Validate that split and sample role change the derived synthetic latent trace.

    Args:
        None.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()

    calibration_sample = backend.build_sample(
        "sample_shared_000001",
        "calibration",
        "clean_negative",
    )
    test_sample = backend.build_sample(
        "sample_shared_000001",
        "test",
        "watermarked_positive",
    )

    assert calibration_sample.latent_shape == test_sample.latent_shape
    assert (
        calibration_sample.latent_generation_seed_random
        != test_sample.latent_generation_seed_random
    )
    assert (
        calibration_sample.latent_tensor_digest_random
        != test_sample.latent_tensor_digest_random
    )
"""
文件用途：验证 temporal attack placeholder runtime 的最小运行语义。
File purpose: Validate the minimal runtime behavior of the temporal attack placeholder interfaces.
Module type: General module
"""

from __future__ import annotations

import os
from pathlib import Path

from main.attacks.attack_registry import build_attack_registry
from main.backends.synthetic_video_latent import SyntheticVideoLatentPlaceholder
from main.core.registry import load_json_config


ROOT = Path(__file__).resolve().parents[1]


def test_temporal_attack_registry_builds_all_governed_attacks() -> None:
    """Validate that the temporal attack registry materializes all governed attacks.

    Args:
        None.

    Returns:
        None.
    """
    attack_config = load_json_config(
        ROOT / "configs" / "attacks" / "temporal_attack_matrix.json"
    )
    attack_registry = build_attack_registry(attack_config)

    assert [attack.attack_name for attack in attack_registry] == [
        "no_attack",
        "temporal_crop",
        "frame_dropping",
        "speed_change",
        "local_clip",
        "latent_gaussian_noise",
    ]


def test_temporal_attacks_transform_placeholder_sample_metadata() -> None:
    """Validate that governed temporal attacks change artifact shape and digest as expected.

    Args:
        None.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    sample = backend.build_sample(
        "sample_test_attacked_positive_000001",
        "test",
        "attacked_positive",
    )
    attack_registry = build_attack_registry(
        load_json_config(ROOT / "configs" / "attacks" / "temporal_attack_matrix.json")
    )
    attacked_samples = {attack.attack_name: attack.apply(sample) for attack in attack_registry}

    assert attacked_samples["no_attack"] == sample
    assert attacked_samples["temporal_crop"].latent_shape == (
        attacked_samples["temporal_crop"].applied_attack_params["observed_frame_count"],
        4,
        16,
        16,
    )
    assert attacked_samples["frame_dropping"].latent_shape == (
        attacked_samples["frame_dropping"].applied_attack_params["observed_frame_count"],
        4,
        16,
        16,
    )
    assert attacked_samples["speed_change"].latent_shape == (
        attacked_samples["speed_change"].applied_attack_params["observed_frame_count"],
        4,
        16,
        16,
    )
    assert attacked_samples["local_clip"].latent_shape == (
        attacked_samples["local_clip"].applied_attack_params["clip_length"],
        4,
        16,
        16,
    )
    assert attacked_samples["latent_gaussian_noise"].latent_shape == sample.latent_shape
    assert (
        attacked_samples["latent_gaussian_noise"].latent_tensor_digest_random
        != sample.latent_tensor_digest_random
    )
    assert (
        attacked_samples["temporal_crop"].latent_generation_seed_random
        != sample.latent_generation_seed_random
    )


def test_temporal_attack_reuses_existing_artifact(tmp_path: Path) -> None:
    """Validate that repeated governed attacks reuse the existing artifact output.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)
    sample = backend.build_sample(
        "sample_test_attacked_positive_000001",
        "test",
        "attacked_positive",
    )
    temporal_crop = build_attack_registry(
        load_json_config(ROOT / "configs" / "attacks" / "temporal_attack_matrix.json")
    )[1]

    first_attacked_sample = temporal_crop.apply(sample)
    artifact_path = Path(first_attacked_sample.latent_artifact_path or "")
    sentinel_mtime_ns = max(1, artifact_path.stat().st_mtime_ns - 1_000_000_000)
    os.utime(artifact_path, ns=(sentinel_mtime_ns, sentinel_mtime_ns))
    second_attacked_sample = temporal_crop.apply(sample)

    assert first_attacked_sample.latent_artifact_digest == second_attacked_sample.latent_artifact_digest
    assert first_attacked_sample.latent_shape == second_attacked_sample.latent_shape
    assert artifact_path.stat().st_mtime_ns == sentinel_mtime_ns
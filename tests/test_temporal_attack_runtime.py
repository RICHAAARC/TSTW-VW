"""
文件用途：验证 temporal attack placeholder runtime 的最小运行语义。
File purpose: Validate the minimal runtime behavior of the temporal attack placeholder interfaces.
Module type: General module
"""

from __future__ import annotations

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
    """Validate that temporal placeholder attacks change shape and digest as expected.

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
    assert attacked_samples["temporal_crop"].latent_shape == (20, 4, 32, 32)
    assert attacked_samples["frame_dropping"].latent_shape == (24, 4, 32, 32)
    assert attacked_samples["speed_change"].latent_shape == (26, 4, 32, 32)
    assert attacked_samples["local_clip"].latent_shape == (4, 4, 32, 32)
    assert attacked_samples["latent_gaussian_noise"].latent_shape == sample.latent_shape
    assert (
        attacked_samples["latent_gaussian_noise"].latent_tensor_digest_random
        != sample.latent_tensor_digest_random
    )
    assert (
        attacked_samples["temporal_crop"].latent_generation_seed_random
        != sample.latent_generation_seed_random
    )
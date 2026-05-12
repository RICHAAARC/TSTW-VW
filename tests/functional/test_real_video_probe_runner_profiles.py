"""
文件用途：验证 real-video debug profile 的受治理配置解析。
File purpose: Validate governed configuration resolution for the real-video debug profile.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner
from main.attacks.real_video_attack_registry import build_real_video_attack_registry
from main.core.registry import load_json_config


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_debug_real_video_profile_resolves_small_backend_targets_and_single_variant() -> None:
    """Validate the debug profile resolves a small backend target and one method variant.

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    backend_config = load_json_config(
        ROOT / "configs" / "backend" / "real_video_vae_latent.json"
    )
    ablation_config = load_json_config(
        ROOT / "configs" / "ablation" / "real_video_vae_latent_ablation.json"
    )

    resolved_backend_config = runner._resolve_backend_config(
        "debug_real_video",
        backend_config,
    )
    runtime_method_configs = runner._build_runtime_method_configs(
        ablation_config,
        runner._build_method_config_paths(ablation_config),
        "debug_real_video",
        None,
    )

    assert resolved_backend_config["latent_shape"] == {
        "frames": 4,
        "channels": 4,
        "height": 4,
        "width": 4,
    }
    assert resolved_backend_config["target_frame_count"] == 4
    assert resolved_backend_config["target_resolution"] == [16, 16]
    assert [config["method_variant"] for config in runtime_method_configs] == ["frame_prc"]


@pytest.mark.unit
def test_debug_real_video_profile_filters_protocol_scope_and_attacks() -> None:
    """Validate the debug profile keeps a tiny protocol scope and attack set.

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "real_video_vae_latent_probe.json"
    )
    attack_config = load_json_config(
        ROOT / "configs" / "attacks" / "real_video_attack_smoke_matrix.json"
    )
    attack_registry = build_real_video_attack_registry(
        attack_config,
        runtime_kind="tensor_scaffold",
    )
    filtered_attack_registry = runner._filter_attack_registry(
        attack_registry,
        attack_config,
        "debug_real_video",
    )

    assert runner._resolve_samples_per_role(None, protocol_config, "debug_real_video") == 1
    assert runner._resolve_profile_string_list(
        protocol_config.get("splits_by_profile"),
        "debug_real_video",
        protocol_config["splits"],
        "splits_by_profile",
    ) == ["dev", "calibration", "test"]
    assert runner._resolve_profile_string_list(
        protocol_config.get("sample_roles_by_profile"),
        "debug_real_video",
        protocol_config["sample_roles"],
        "sample_roles_by_profile",
    ) == ["clean_negative", "attacked_negative"]
    assert sorted(
        attack_object.attack_name for attack_object in filtered_attack_registry
    ) == ["h264_compression", "no_attack"]


@pytest.mark.unit
def test_runtime_splits_shrink_to_manifest_available_splits() -> None:
    """Validate runner uses only dataset-manifest splits that actually exist.

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "real_video_vae_latent_probe.json"
    )
    dataset_manifest = load_json_config(
        ROOT / "configs" / "data" / "real_video_probe_manifest.json"
    )

    assert runner._resolve_runtime_splits(
        protocol_config,
        "formal",
        dataset_manifest,
    ) == ["calibration", "test"]
"""
文件用途：验证 real-video debug profile 的受治理配置解析。
File purpose: Validate governed configuration resolution for the real-video debug profile.
Module type: General module
"""

from __future__ import annotations

import types
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
def test_runner_allows_method_config_path_overrides(tmp_path: Path) -> None:
    """Validate ablation configs can override method config file paths.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    method_config_path = tmp_path / "custom_method_variant.json"
    method_config_path.write_text("{}\n", encoding="utf-8")

    resolved_paths = runner._build_method_config_paths(
        {
            "method_variants": ["custom_method_variant"],
            "method_config_paths": {
                "custom_method_variant": str(method_config_path),
            },
        }
    )

    assert resolved_paths["custom_method_variant"] == method_config_path


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
def test_real_video_profile_sample_counts_are_explicit_for_governed_profiles() -> None:
    """Validate governed profiles do not rely on runner sample-count fallbacks.

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "real_video_vae_latent_probe.json"
    )

    assert runner._resolve_samples_per_role(None, protocol_config, "tiny") == 1
    assert runner._resolve_samples_per_role(None, protocol_config, "smoke") == 1
    assert runner._resolve_samples_per_role(None, protocol_config, "proof") == 8
    assert runner._resolve_samples_per_role(None, protocol_config, "formal") == 20


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
    ) == ["dev", "calibration", "test"]


@pytest.mark.unit
def test_cached_decoded_video_artifact_reuses_same_latent_across_attack_relpaths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate decoded artifacts are reused for the same latent across attack cases.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    decode_call_count = {"value": 0}
    expected_metadata = {
        "video_relpath": "artifacts/videos/decoded/frame_prc/shared.mp4",
        "video_digest": "decoded-digest",
        "container": "mp4",
        "codec": "libx264",
    }
    sample = types.SimpleNamespace(latent_tensor_digest_random="latent-digest")

    monkeypatch.setattr(runner, "_load_latent_tensor", lambda _sample: "latent-array")

    def _fake_decode(*args, **kwargs):
        del args, kwargs
        decode_call_count["value"] += 1
        return "decoded-video"

    monkeypatch.setattr(runner, "_decode_latent_to_video", _fake_decode)
    monkeypatch.setattr(runner, "_write_video_artifact", lambda *args, **kwargs: dict(expected_metadata))

    cache: dict[tuple[str, str], dict[str, object]] = {}
    first_metadata = runner._cached_decoded_video_artifact(
        cache,
        sample,
        vae_runtime_backend=object(),
        vae_metadata={},
        output_root=ROOT,
        artifact_relpath=Path("artifacts/videos/decoded/frame_prc/attack_a.mp4"),
        fps=8,
        target_resolution=(256, 256),
    )
    second_metadata = runner._cached_decoded_video_artifact(
        cache,
        sample,
        vae_runtime_backend=object(),
        vae_metadata={},
        output_root=ROOT,
        artifact_relpath=Path("artifacts/videos/decoded/frame_prc/attack_b.mp4"),
        fps=8,
        target_resolution=(256, 256),
    )

    assert decode_call_count["value"] == 1
    assert first_metadata == expected_metadata
    assert second_metadata == expected_metadata
"""
文件用途：验证 real-video debug profile 的受治理配置解析。
File purpose: Validate governed configuration resolution for the real-video debug profile.
Module type: General module
"""

from __future__ import annotations

import experiments.real_video_vae_latent_probe.runner as real_video_runner_module

import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.quick

from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner
from main.attacks.real_video_attack_registry import build_real_video_attack_registry
from main.core.registry import load_json_config
from main.protocol.calibrator import ThresholdCalibrator


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
def test_runner_formats_runtime_config_paths_for_repo_and_external_configs(
    tmp_path: Path,
) -> None:
    """Validate runtime-config path serialization keeps repo-relative and external absolute paths.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    repo_config_path = ROOT / "configs" / "protocol" / "real_video_vae_latent_probe.json"
    external_config_path = tmp_path / "external_protocol_config.json"
    external_config_path.write_text("{}\n", encoding="utf-8")

    assert (
        runner._format_runtime_config_path(repo_config_path)
        == "configs/protocol/real_video_vae_latent_probe.json"
    )
    assert runner._format_runtime_config_path(external_config_path) == str(external_config_path)


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
def test_threshold_calibrator_uses_explicit_runtime_profile_override() -> None:
    """Validate threshold calibration honors the active runtime profile override.

    Args:
        None.

    Returns:
        None.
    """
    calibrator = ThresholdCalibrator()
    method_config = load_json_config(ROOT / "configs" / "method" / "frame_prc.json")
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "real_video_vae_latent_probe.json"
    )
    calibration_event_records = [
        {
            "event_id": "frame_prc:sample_calibration_clean_negative_000001:no_attack:default",
            "sample_id": "sample_calibration_clean_negative_000001",
            "split": "calibration",
            "sample_role": "clean_negative",
            "method_variant": "frame_prc",
            "attack_name": "no_attack",
            "evidence_scores": {"S_final": 0.01},
        },
        {
            "event_id": "frame_prc:sample_calibration_attacked_negative_000001:h264_compression:default",
            "sample_id": "sample_calibration_attacked_negative_000001",
            "split": "calibration",
            "sample_role": "attacked_negative",
            "method_variant": "frame_prc",
            "attack_name": "h264_compression",
            "evidence_scores": {"S_final": 0.02},
        },
    ]

    threshold_record = calibrator.calibrate(
        "real_video_probe_threshold_profile_override",
        method_config,
        protocol_config,
        calibration_event_records,
        runtime_profile_override="formal",
    )

    assert threshold_record["runtime_profile"] == "formal"
    assert threshold_record["validation_target_fpr"] == 0.001


@pytest.mark.unit
def test_runner_passes_active_runtime_profile_to_threshold_calibrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the real-video runner forwards its active runtime profile to calibration.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    method_config = load_json_config(ROOT / "configs" / "method" / "frame_prc.json")
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "real_video_vae_latent_probe.json"
    )
    captured_runtime_profile: dict[str, str] = {}
    calibration_records = [
        {
            "event_id": "frame_prc:sample_calibration_clean_negative_000001:no_attack:default",
            "sample_id": "sample_calibration_clean_negative_000001",
            "split": "calibration",
            "sample_role": "clean_negative",
            "method_variant": "frame_prc",
            "attack_name": "no_attack",
            "evidence_scores": {"S_final": 0.01},
        }
    ]

    class _FakeThresholdCalibrator:
        def calibrate(
            self,
            run_id: str,
            method_config: dict[str, object],
            protocol_config: dict[str, object],
            calibration_event_records: list[dict[str, object]],
            runtime_profile_override: str | None = None,
        ) -> dict[str, object]:
            del run_id, method_config, protocol_config, calibration_event_records
            captured_runtime_profile["value"] = str(runtime_profile_override)
            return {
                "threshold_id": "fixed_low_fpr_calibrated_detection:S_final:frame_prc",
                "runtime_profile": str(runtime_profile_override),
            }

    def _fake_run_event_subset(*args: object, **kwargs: object) -> list[dict[str, object]]:
        allowed_splits = kwargs.get("allowed_splits")
        if allowed_splits is None:
            allowed_splits = args[6]
        if allowed_splits == {"calibration"}:
            return calibration_records
        return []

    monkeypatch.setattr(
        real_video_runner_module,
        "build_method_from_config",
        lambda _method_config: object(),
    )
    monkeypatch.setattr(runner, "_run_event_subset", _fake_run_event_subset)
    runner._threshold_calibrator = _FakeThresholdCalibrator()

    _, threshold_record = runner._run_method_variant(
        run_id="real_video_probe_profile_passthrough",
        output_root=ROOT,
        event_plan=[],
        method_config=method_config,
        protocol_config=protocol_config,
        runtime_profile="formal",
        runtime_splits={"dev", "calibration", "test"},
        runtime_sample_roles={
            "clean_negative",
            "attacked_negative",
            "watermarked_positive",
            "attacked_positive",
        },
        latent_backend=object(),
        vae_runtime_backend=object(),
        vae_metadata={},
    )

    assert captured_runtime_profile["value"] == "formal"
    assert threshold_record["runtime_profile"] == "formal"


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


@pytest.mark.unit
def test_split_plan_shard_selection_round_robins_within_split_and_sample_role() -> None:
    """Validate split-plan sharding partitions each split-role stream independently.

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    split_plan = [
        types.SimpleNamespace(split="dev", sample_role="clean_negative", sample_id="cn_00"),
        types.SimpleNamespace(split="dev", sample_role="clean_negative", sample_id="cn_01"),
        types.SimpleNamespace(split="dev", sample_role="attacked_negative", sample_id="an_00"),
        types.SimpleNamespace(split="dev", sample_role="attacked_negative", sample_id="an_01"),
        types.SimpleNamespace(split="test", sample_role="clean_negative", sample_id="tcn_00"),
        types.SimpleNamespace(split="test", sample_role="clean_negative", sample_id="tcn_01"),
    ]

    shard_zero = runner._select_split_plan_shard(split_plan, shard_count=2, shard_index=0)
    shard_one = runner._select_split_plan_shard(split_plan, shard_count=2, shard_index=1)

    assert [entry.sample_id for entry in shard_zero] == ["cn_00", "an_00", "tcn_00"]
    assert [entry.sample_id for entry in shard_one] == ["cn_01", "an_01", "tcn_01"]


@pytest.mark.unit
def test_event_worker_buckets_keep_source_groups_intact() -> None:
    """Validate worker buckets do not split events from the same source identity.

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    event_plan_entries = [
        types.SimpleNamespace(split="dev", sample_role="clean_negative", sample_id="sample_00", attack_name="no_attack"),
        types.SimpleNamespace(split="dev", sample_role="attacked_negative", sample_id="sample_00", attack_name="h264_compression"),
        types.SimpleNamespace(split="dev", sample_role="clean_negative", sample_id="sample_01", attack_name="no_attack"),
        types.SimpleNamespace(split="dev", sample_role="attacked_negative", sample_id="sample_01", attack_name="temporal_crop"),
    ]

    grouped_event_plan = runner._group_event_plan_entries_by_source(event_plan_entries)
    worker_buckets = runner._plan_event_worker_buckets(grouped_event_plan, worker_count=2)

    assert len(worker_buckets) == 2
    assert [entry.sample_id for entry in worker_buckets[0]] == ["sample_00", "sample_00"]
    assert [entry.sample_id for entry in worker_buckets[1]] == ["sample_01", "sample_01"]
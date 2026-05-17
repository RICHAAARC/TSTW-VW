"""
文件用途：验证 real-video debug profile 的受治理配置解析。
File purpose: Validate governed configuration resolution for the real-video debug profile.
Module type: General module
"""

from __future__ import annotations

import experiments.real_video_vae_latent_probe.runner as real_video_runner_module

import types
from pathlib import Path

import numpy as np
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
def test_runner_materializes_post_calibration_decisions_without_calibration_threshold_leakage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate runner stamps dev decisions after calibration without leaking threshold_id into calibration.

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
    dev_records = [
        {
            "split": "dev",
            "sample_role": "watermarked_positive",
            "decision": False,
            "threshold_id": None,
            "evidence_scores": {"S_final": 0.6},
        }
    ]
    calibration_records = [
        {
            "split": "calibration",
            "sample_role": "clean_negative",
            "decision": False,
            "threshold_id": None,
            "evidence_scores": {"S_final": 0.05},
        }
    ]
    test_records = [
        {
            "split": "test",
            "sample_role": "watermarked_positive",
            "decision": True,
            "threshold_id": "fixed_low_fpr_calibrated_detection:S_final:frame_prc:real_video_vae_latent_probe",
            "evidence_scores": {"S_final": 0.6},
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
            del run_id, method_config, protocol_config, calibration_event_records, runtime_profile_override
            return {
                "threshold_id": "fixed_low_fpr_calibrated_detection:S_final:frame_prc",
                "threshold_value": 0.1,
                "runtime_profile": "formal",
            }

    def _fake_run_event_subset(*args: object, **kwargs: object) -> list[dict[str, object]]:
        allowed_splits = kwargs.get("allowed_splits")
        if allowed_splits is None:
            allowed_splits = args[6]
        if allowed_splits == {"dev"}:
            return [dict(record) for record in dev_records]
        if allowed_splits == {"calibration"}:
            return [dict(record) for record in calibration_records]
        return [dict(record) for record in test_records]

    monkeypatch.setattr(
        real_video_runner_module,
        "build_method_from_config",
        lambda _method_config: object(),
    )
    monkeypatch.setattr(runner, "_run_event_subset", _fake_run_event_subset)
    runner._threshold_calibrator = _FakeThresholdCalibrator()

    event_records, threshold_record = runner._run_method_variant(
        run_id="real_video_probe_materialized_decision_run",
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

    dev_positive_record = next(record for record in event_records if record["split"] == "dev")
    calibration_negative_record = next(
        record for record in event_records if record["split"] == "calibration"
    )

    assert threshold_record["threshold_id"].endswith(":real_video_vae_latent_probe")
    assert dev_positive_record["decision"] is True
    assert dev_positive_record["threshold_id"] == threshold_record["threshold_id"]
    assert calibration_negative_record["decision"] is False
    assert calibration_negative_record["threshold_id"] is None


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
def test_cached_attacked_video_artifact_uses_supplied_source_frames(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Validate attacked-video materialization can reuse in-memory source frames.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    source_frames = np.ones((2, 4, 4, 3), dtype=np.float32)
    captured_frames: dict[str, np.ndarray] = {}
    output_root = tmp_path
    artifact_relpath = Path("artifacts/videos/attacked/h264_compression/sample.mp4")

    class _FrameAttack:
        def apply_frames(self, input_frames: np.ndarray, runtime_config: dict[str, object]) -> np.ndarray:
            del runtime_config
            captured_frames["value"] = np.asarray(input_frames, dtype=np.float32)
            return np.asarray(input_frames, dtype=np.float32) * 0.5

    monkeypatch.setattr(
        real_video_runner_module,
        "read_video_frames",
        lambda _video_path: (_ for _ in ()).throw(AssertionError("unexpected source video read")),
    )

    metadata = runner._cached_attacked_video_artifact(
        cache={},
        source_video_metadata={
            "video_digest": "decoded-digest",
            "video_relpath": "artifacts/videos/decoded/frame_prc/source.mp4",
        },
        sample=types.SimpleNamespace(applied_attack_params={"quality": 23}),
        attack_name="h264_compression",
        attack_object=_FrameAttack(),
        output_root=output_root,
        artifact_relpath=artifact_relpath,
        fps=8,
        target_resolution=(4, 4),
        runtime_config={},
        source_video_frames=source_frames,
    )

    assert metadata["video_relpath"] == artifact_relpath.as_posix()
    assert np.array_equal(captured_frames["value"], source_frames)


@pytest.mark.unit
def test_cached_reencoded_latent_artifact_uses_supplied_video_tensor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Validate reencode can reuse in-memory attacked frames.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    expected_video_tensor = np.ones((2, 4, 4, 3), dtype=np.float32)
    captured_video_tensor: dict[str, np.ndarray] = {}

    monkeypatch.setattr(
        runner,
        "_read_video_tensor_from_artifact",
        lambda _artifact_path: (_ for _ in ()).throw(AssertionError("unexpected artifact read")),
    )

    def _fake_encode(video_tensor: np.ndarray, *_args: object) -> np.ndarray:
        captured_video_tensor["value"] = np.asarray(video_tensor, dtype=np.float32)
        return np.ones((2, 4, 4, 4), dtype=np.float32)

    monkeypatch.setattr(runner, "_encode_video_to_latent", _fake_encode)

    metadata = runner._cached_reencoded_latent_artifact(
        cache={},
        video_metadata={"video_digest": "attacked-digest", "video_relpath": "artifacts/videos/attacked/sample.mp4"},
        reference_sample=types.SimpleNamespace(),
        vae_runtime_backend=object(),
        vae_metadata={},
        output_root=tmp_path,
        artifact_relpath=Path("artifacts/latents/reencoded/no_attack/sample.npy"),
        video_tensor=expected_video_tensor,
    )

    assert metadata["latent_relpath"] == "artifacts/latents/reencoded/no_attack/sample.npy"
    assert np.array_equal(captured_video_tensor["value"], expected_video_tensor)


@pytest.mark.unit
def test_load_metric_frame_pair_uses_supplied_frames_without_artifact_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate metric-frame loading short-circuits artifact reads when frames are present.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    reference_frames = np.zeros((2, 4, 4, 3), dtype=np.float32)
    comparison_frames = np.ones((2, 4, 4, 3), dtype=np.float32)

    monkeypatch.setattr(
        runner,
        "_read_video_tensor_from_artifact",
        lambda _artifact_path: (_ for _ in ()).throw(AssertionError("unexpected artifact read")),
    )

    resolved_reference_frames, resolved_comparison_frames = runner._load_metric_frame_pair(
        ROOT / "reference.mp4",
        ROOT / "comparison.mp4",
        reference_frames=reference_frames,
        comparison_frames=comparison_frames,
    )

    assert np.array_equal(resolved_reference_frames, reference_frames)
    assert np.array_equal(resolved_comparison_frames, comparison_frames)


@pytest.mark.unit
def test_quality_metric_policy_can_limit_execution_to_selected_attack_and_role() -> None:
    """Validate quality metrics can be scoped to specific attacks and sample roles.

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    runner._runtime_config_overrides = {
        "quality_metrics": {
            "enabled_attack_names": ["no_attack"],
            "enabled_sample_roles": ["watermarked_positive"],
        }
    }

    assert runner._should_compute_quality_metrics(
        types.SimpleNamespace(attack_name="no_attack", sample_role="watermarked_positive")
    )
    assert not runner._should_compute_quality_metrics(
        types.SimpleNamespace(attack_name="temporal_crop", sample_role="watermarked_positive")
    )
    assert not runner._should_compute_quality_metrics(
        types.SimpleNamespace(attack_name="no_attack", sample_role="attacked_positive")
    )


@pytest.mark.unit
def test_temporal_metric_policy_can_disable_temporal_metrics() -> None:
    """Validate temporal metrics can be fully disabled by runtime policy.

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    runner._runtime_config_overrides = {
        "temporal_metrics": {
            "enable_temporal_metrics": False,
        }
    }

    assert not runner._should_compute_temporal_metrics(
        types.SimpleNamespace(attack_name="no_attack", sample_role="watermarked_positive")
    )

    skipped_payload = runner._build_skipped_temporal_metrics_payload(
        reason="temporal_metrics_skipped_by_runtime_policy"
    )
    assert skipped_payload["temporal_consistency_score"] is None
    assert skipped_payload["flicker_score"] is None
    assert skipped_payload["temporal_failure_reason"] == "temporal_metrics_skipped_by_runtime_policy"


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
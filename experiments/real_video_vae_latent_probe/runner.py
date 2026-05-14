"""
文件用途：运行阶段 2 real-video VAE latent probe 的受治理 runtime 闭环。
File purpose: Run the governed stage-two real-video VAE latent probe runtime.
Module type: General module
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import platform
import sys
import time
from array import array
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.real_video_vae_latent_probe.artifact_builder import (
    RealVideoVaeLatentArtifactBuilder,
)
from experiments.real_video_vae_latent_probe.output_layout import (
    RealVideoVaeLatentOutputPaths,
    build_real_video_vae_latent_output_paths,
)
from main.analysis.real_video_quality_metrics import (
    build_real_video_quality_metrics_payload_from_frames,
)
from main.analysis.real_video_temporal_metrics import (
    build_real_video_temporal_metrics_payload_from_frames,
)
from main.attacks.real_video_attack_registry import build_real_video_attack_registry
from main.backends.real_video_vae_latent import (
    DEFAULT_RUNTIME_PROFILE,
    RealVideoVAELatentBackend,
    build_real_video_vae_latent_backend_from_support_config,
)
from main.core.digest import compute_file_digest, compute_object_digest, compute_path_collection_digest
from main.core.records import RecordWriter
from main.core.registry import load_json_config
from main.core.schema import LatentSample, NEGATIVE_SAMPLE_ROLES, SAMPLE_ROLES, build_input_artifact_trace, validate_event_score_record
from main.core.tensor_artifact import read_float_tensor_npy, write_float_tensor_npy
from main.methods.temporal_tubelet_watermark.method import build_method_from_config
from main.protocol.calibrator import ThresholdCalibrator
from main.protocol.event_builder import EventPlanEntry
from main.protocol.split_builder import build_split_plan
from main.vae.vae_registry import resolve_vae_backend
from main.video.dataset_localizer import resolve_runtime_dataset_manifest_path
from main.video.dataset_manifest import load_dataset_manifest, summarize_dataset_manifest
from main.video.video_io import probe_video_metadata, read_video_frames, write_video_mp4
from main.video.video_artifact import copy_latent_artifact
from scripts.profile_runtime import write_current_runtime_event_tag
from scripts.profile_runtime.profile_run_timing import RunTimingRecorder


SUPPORTED_RUNTIME_PROFILES = (
    "tiny",
    "smoke",
    "debug_real_video",
    "proof",
    "formal",
)
REAL_VIDEO_TEMPORAL_ATTACK_NAMES = {
    "no_attack",
    "temporal_crop",
    "frame_dropping",
    "speed_change",
    "local_clip",
}


@dataclass(frozen=True)
class RealVideoVaeLatentRunResult:
    """功能：定义阶段 2 运行结果载体。

    Stage-two run result payload.

    Args:
        run_id: Stable run identifier.
        output_root: Run root path.
        event_score_records: Persisted event score records.
        threshold_records: Persisted threshold records.
        run_manifest: Persisted run manifest.

    Returns:
        None.
    """

    run_id: str
    output_root: Path
    event_score_records: list[dict[str, Any]]
    threshold_records: list[dict[str, Any]]
    run_manifest: dict[str, Any]


class RealVideoVaeLatentRunner:
    """功能：执行阶段 2 受治理协议闭环。

    Execute the governed stage-two protocol loop.

    Args:
        repository_root: Repository root path.

    Returns:
        None.
    """

    def __init__(self, repository_root: str | Path) -> None:
        self._repository_root = Path(repository_root)
        if not self._repository_root.exists():
            raise FileNotFoundError(self._repository_root)
        self._artifact_builder = RealVideoVaeLatentArtifactBuilder()
        self._threshold_calibrator = ThresholdCalibrator()
        self._runtime_config_overrides: dict[str, Any] = {}
        self._runner_timing_recorder: RunTimingRecorder | None = None
        self._runner_timing_totals: dict[str, float] = {}
        self._runner_timing_counts: dict[str, int] = {}
        self._runner_timing_failures: dict[str, int] = {}
        self._current_runtime_event_tag = "unlabeled"

    def run(
        self,
        output_root: str | Path,
        run_mode: str = "smoke",
        samples_per_role: int | None = None,
        batch_size_frames: int | None = None,
        runtime_profile_override: str | None = None,
        method_variants: list[str] | None = None,
        protocol_config_path: str | Path | None = None,
        backend_config_path: str | Path | None = None,
        attack_matrix_path: str | Path | None = None,
        ablation_config_path: str | Path | None = None,
        dataset_manifest_path: str | Path | None = None,
        runtime_config_path: str | Path | None = None,
    ) -> RealVideoVaeLatentRunResult:
        """功能：运行阶段 2 受治理协议并写出 records、tables 与 manifests。

        Run the governed stage-two protocol and persist its artifacts.

        Args:
            output_root: Run root path.
            run_mode: Runtime mode, one of `smoke` or `formal`.
            samples_per_role: Optional sample count per split-role pair.
            batch_size_frames: Optional VAE frame-batch size override.
            runtime_profile_override: Optional explicit runtime profile.
            method_variants: Optional explicit method-variant allowlist.
            protocol_config_path: Optional protocol config path.
            backend_config_path: Optional backend config path.
            attack_matrix_path: Optional attack config path.
            ablation_config_path: Optional ablation config path.
            dataset_manifest_path: Optional dataset manifest path.
            runtime_config_path: Optional runtime-config override path.

        Returns:
            A `RealVideoVaeLatentRunResult` instance.
        """
        if run_mode not in {"smoke", "formal"}:
            raise ValueError("run_mode must be either smoke or formal")
        runtime_profile = runtime_profile_override or ("formal" if run_mode == "formal" else DEFAULT_RUNTIME_PROFILE)
        if runtime_profile not in SUPPORTED_RUNTIME_PROFILES:
            raise ValueError("unsupported runtime_profile")
        protocol_config_file = self._resolve_config_path(
            protocol_config_path,
            self._repository_root / "configs" / "protocol" / "real_video_vae_latent_probe.json",
        )
        backend_config_file = self._resolve_config_path(
            backend_config_path,
            self._repository_root / "configs" / "backend" / "real_video_vae_latent.json",
        )
        attack_matrix_file = self._resolve_config_path(
            attack_matrix_path,
            self._repository_root / "configs" / "attacks" / (
                "real_video_attack_matrix.json" if run_mode == "formal" else "real_video_attack_smoke_matrix.json"
            ),
        )
        ablation_config_file = self._resolve_config_path(
            ablation_config_path,
            self._repository_root / "configs" / "ablation" / "real_video_vae_latent_ablation.json",
        )
        runtime_config_overrides = self._load_runtime_config(runtime_config_path)
        if batch_size_frames is not None:
            runtime_config_overrides["batch_size_frames"] = int(batch_size_frames)
        if dataset_manifest_path is None and any(
            key in runtime_config_overrides
            for key in ("local_dataset_root", "dataset_manifest_path")
        ):
            dataset_manifest_file = resolve_runtime_dataset_manifest_path(
                runtime_config_overrides
            )
        else:
            dataset_manifest_file = self._resolve_config_path(
                dataset_manifest_path,
                self._repository_root / "configs" / "data" / "real_video_probe_manifest.json",
            )
        protocol_config = load_json_config(protocol_config_file)
        resolved_samples_per_role = self._resolve_samples_per_role(
            samples_per_role,
            protocol_config,
            runtime_profile,
        )
        dataset_manifest = load_dataset_manifest(dataset_manifest_file)
        runtime_splits = set(
            self._resolve_runtime_splits(
                protocol_config,
                runtime_profile,
                dataset_manifest,
            )
        )
        runtime_sample_roles = set(
            self._resolve_profile_string_list(
                protocol_config.get("sample_roles_by_profile"),
                runtime_profile,
                protocol_config.get("sample_roles", list(SAMPLE_ROLES)),
                "sample_roles_by_profile",
            )
        )
        backend_config = self._resolve_backend_config(runtime_profile, load_json_config(backend_config_file))
        attack_config = load_json_config(attack_matrix_file)
        ablation_config = load_json_config(ablation_config_file)
        self._runtime_config_overrides = dict(runtime_config_overrides)
        dataset_summary = summarize_dataset_manifest(dataset_manifest)
        backend_config["dataset_manifest_path"] = str(dataset_manifest_file)
        if "local_dataset_root" in runtime_config_overrides:
            backend_config["local_dataset_root"] = runtime_config_overrides["local_dataset_root"]
        if "local_vae_model_root" in runtime_config_overrides:
            backend_config["vae_model_local_path"] = runtime_config_overrides["local_vae_model_root"]
        elif "vae_model_local_path" in runtime_config_overrides:
            backend_config["vae_model_local_path"] = runtime_config_overrides["vae_model_local_path"]
        if "batch_size_frames" in runtime_config_overrides:
            backend_config["batch_size_frames"] = int(runtime_config_overrides["batch_size_frames"])
        if "frame_sampling_policy" in dataset_manifest:
            backend_config["frame_sampling_policy"] = dataset_manifest["frame_sampling_policy"]
        if "default_frame_count" in dataset_manifest and "target_frame_count" not in backend_config:
            backend_config["target_frame_count"] = int(dataset_manifest["default_frame_count"])
        if "default_resolution" in dataset_manifest and "target_resolution" not in backend_config:
            backend_config["target_resolution"] = dataset_manifest["default_resolution"]
        vae_backend = resolve_vae_backend(backend_config)
        vae_metadata = vae_backend.backend_metadata()
        latent_backend = build_real_video_vae_latent_backend_from_support_config(backend_config)
        output_root_path = Path(output_root)
        output_root_path.mkdir(parents=True, exist_ok=True)
        latent_backend.set_output_root(output_root_path)

        split_plan = build_split_plan(samples_per_role=resolved_samples_per_role)
        attack_registry = build_real_video_attack_registry(
            attack_config,
            runtime_kind=(
                "real_video" if self._video_mp4_runtime_available() else "tensor_scaffold"
            ),
        )
        attack_registry = self._filter_attack_registry(
            attack_registry,
            attack_config,
            runtime_profile,
        )
        event_plan = self._build_event_plan(split_plan, attack_registry)
        method_config_paths = self._build_method_config_paths(ablation_config)
        runtime_method_configs = self._build_runtime_method_configs(
            ablation_config,
            method_config_paths,
            runtime_profile,
            method_variants,
        )
        run_id = output_root_path.name
        self._begin_runner_timing(output_root_path, run_id)
        event_score_records: list[dict[str, Any]] = []
        threshold_records: list[dict[str, Any]] = []
        record_writer = RecordWriter(output_root_path)
        self._reset_incremental_outputs(record_writer)

        try:
            for method_config in runtime_method_configs:
                variant_event_records, threshold_record = self._run_method_variant(
                    run_id=run_id,
                    output_root=output_root_path,
                    event_plan=event_plan,
                    method_config=method_config,
                    protocol_config=protocol_config,
                    runtime_splits=runtime_splits,
                    runtime_sample_roles=runtime_sample_roles,
                    latent_backend=latent_backend,
                    vae_runtime_backend=vae_backend,
                    vae_metadata=vae_metadata,
                )
                event_score_records.extend(variant_event_records)
                threshold_records.append(threshold_record)
        finally:
            self._flush_runner_timing_events()
            self._set_runtime_event_tag("unlabeled")

        record_writer.write_event_score_records(event_score_records)
        record_writer.write_threshold_records(threshold_records)
        artifact_paths = self._artifact_builder.build_artifacts(
            event_score_records,
            threshold_records,
            output_root_path,
        )
        output_paths = build_real_video_vae_latent_output_paths(output_root_path)
        runtime_config_payload = dict(runtime_config_overrides)
        runtime_config_payload.update(
            {
                "run_mode": run_mode,
                "construction_phase": protocol_config["construction_phase"],
                "protocol_config": str(protocol_config_file.relative_to(self._repository_root)).replace("\\", "/"),
                "backend_config": str(backend_config_file.relative_to(self._repository_root)).replace("\\", "/"),
                "attack_matrix_config": str(attack_matrix_file.relative_to(self._repository_root)).replace("\\", "/"),
                "ablation_config": str(ablation_config_file.relative_to(self._repository_root)).replace("\\", "/"),
                "dataset_manifest": str(dataset_manifest_file),
                "dataset_manifest_path": str(dataset_manifest_file),
                "target_fpr": protocol_config["threshold_protocol"]["target_fpr_placeholder"],
                "method_variants": [method_config["method_variant"] for method_config in runtime_method_configs],
            }
        )
        self._write_json(output_paths.runtime_config_path, runtime_config_payload)
        runtime_config_digest = compute_object_digest(runtime_config_payload)
        runtime_manifest = {
            "run_id": run_id,
            "construction_phase": protocol_config["construction_phase"],
            "run_mode": run_mode,
            "runtime_profile": runtime_profile,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "working_directory": str(self._repository_root),
            "notebook_entrypoint_present": all(
                [
                    (
                        self._repository_root
                        / "paper_workflow"
                        / "build_processed_real_video_dataset.ipynb"
                    ).exists(),
                    (
                        self._repository_root
                        / "paper_workflow"
                        / "run_real_video_vae_latent_probe.ipynb"
                    ).exists(),
                ]
            ),
            "dataset_summary": dataset_summary,
            "vae_metadata": vae_metadata,
        }
        runtime_manifest_overrides = runtime_config_overrides.get("runtime_manifest_overrides")
        if runtime_manifest_overrides is None:
            runtime_manifest_overrides = runtime_config_overrides.get(
                "colab_runtime_manifest_overrides"
            )
        if isinstance(runtime_manifest_overrides, dict):
            runtime_manifest.update(runtime_manifest_overrides)
        git_commit = runtime_config_overrides.get("git_commit")
        if isinstance(git_commit, str) and git_commit:
            runtime_manifest["git_commit"] = git_commit
        self._write_json(output_paths.runtime_manifest_path, runtime_manifest)
        artifact_manifest = self._build_artifact_manifest(event_score_records)
        self._write_json(output_paths.artifact_manifest_path, artifact_manifest)
        run_manifest = {
            "run_id": run_id,
            "created_at": threshold_records[0]["created_at"] if threshold_records else "",
            "construction_phase": protocol_config["construction_phase"],
            "protocol_name": protocol_config["protocol_name"],
            "method_config_digest": compute_object_digest(
                [compute_file_digest(method_config_path) for method_config_path in method_config_paths.values()]
            ),
            "protocol_config_digest": compute_file_digest(protocol_config_file),
            "attack_matrix_digest": compute_file_digest(attack_matrix_file),
            "ablation_config_digest": compute_file_digest(ablation_config_file),
            "runtime_config_digest": runtime_config_digest,
            "records_digest": compute_object_digest(event_score_records),
            "thresholds_digest": compute_object_digest(threshold_records),
            "tables_digest": compute_path_collection_digest(output_paths.table_paths()),
            "figures_digest": compute_path_collection_digest(output_paths.figure_paths()),
            "placeholder_fields": [],
            "random_fields": ["latent_generation_seed_random"],
        }
        self._write_json(output_paths.run_manifest_path, run_manifest)
        del artifact_paths
        return RealVideoVaeLatentRunResult(
            run_id=run_id,
            output_root=output_root_path,
            event_score_records=event_score_records,
            threshold_records=threshold_records,
            run_manifest=run_manifest,
        )

    def _begin_runner_timing(self, output_root: Path, run_id: str) -> None:
        self._runner_timing_recorder = RunTimingRecorder(output_root, run_id=run_id)
        self._runner_timing_totals = {}
        self._runner_timing_counts = {}
        self._runner_timing_failures = {}
        self._set_runtime_event_tag("real_video_vae_latent_runner")

    @contextmanager
    def _runner_substage(self, event_name: str, **metadata: Any) -> Iterator[None]:
        if not isinstance(event_name, str) or not event_name:
            raise ValueError("event_name must be a non-empty string")
        previous_event_tag = self._current_runtime_event_tag
        self._set_runtime_event_tag(event_name)
        start_time = time.perf_counter()
        status = "ok"
        try:
            yield
        except Exception:
            status = "failed"
            raise
        finally:
            elapsed_seconds = max(time.perf_counter() - start_time, 0.0)
            self._runner_timing_totals[event_name] = round(
                self._runner_timing_totals.get(event_name, 0.0) + elapsed_seconds,
                6,
            )
            self._runner_timing_counts[event_name] = self._runner_timing_counts.get(event_name, 0) + 1
            if status == "failed":
                self._runner_timing_failures[event_name] = self._runner_timing_failures.get(event_name, 0) + 1
            del metadata
            self._set_runtime_event_tag(previous_event_tag)

    def _flush_runner_timing_events(self) -> None:
        if self._runner_timing_recorder is None:
            return
        for event_name in sorted(self._runner_timing_totals):
            status = "failed" if self._runner_timing_failures.get(event_name, 0) else "ok"
            self._runner_timing_recorder.write_event(
                event_name=event_name,
                start_time=0.0,
                end_time=float(self._runner_timing_totals[event_name]),
                status=status,
                event_group="runner_substage",
                invocation_count=self._runner_timing_counts.get(event_name, 0),
                failure_count=self._runner_timing_failures.get(event_name, 0),
            )

    def _set_runtime_event_tag(self, event_tag: str) -> None:
        self._current_runtime_event_tag = event_tag
        try:
            write_current_runtime_event_tag(
                self._runner_timing_recorder.run_root if self._runner_timing_recorder is not None else self._repository_root,
                event_tag,
            )
        except Exception:
            return

    def _run_method_variant(
        self,
        run_id: str,
        output_root: Path,
        event_plan: list[EventPlanEntry],
        method_config: dict[str, Any],
        protocol_config: dict[str, Any],
        runtime_splits: set[str],
        runtime_sample_roles: set[str],
        latent_backend: RealVideoVAELatentBackend,
        vae_runtime_backend: Any,
        vae_metadata: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        method = build_method_from_config(method_config)
        target_fpr = float(protocol_config["threshold_protocol"]["target_fpr_placeholder"])
        calibration_split = str(
            protocol_config["threshold_protocol"].get("calibration_split", "calibration")
        )
        test_split = str(protocol_config["threshold_protocol"].get("test_split", "test"))
        calibration_negative_roles = set(
            protocol_config["threshold_protocol"].get(
                "calibration_negative_roles",
                list(NEGATIVE_SAMPLE_ROLES),
            )
        )
        allowed_calibration_roles = runtime_sample_roles & calibration_negative_roles
        if not runtime_sample_roles:
            raise ValueError("runtime_sample_roles must contain at least one sample role")
        if not allowed_calibration_roles:
            raise ValueError(
                "runtime_sample_roles must include at least one calibration negative role"
            )
        dev_records = self._run_event_subset(
            run_id,
            output_root,
            event_plan,
            method,
            method_config,
            target_fpr,
            runtime_splits & {"dev"},
            runtime_sample_roles,
            None,
            latent_backend,
            vae_runtime_backend,
            vae_metadata,
        )
        calibration_records = self._run_event_subset(
            run_id,
            output_root,
            event_plan,
            method,
            method_config,
            target_fpr,
            runtime_splits & {calibration_split},
            allowed_calibration_roles,
            None,
            latent_backend,
            vae_runtime_backend,
            vae_metadata,
        )
        threshold_record = self._threshold_calibrator.calibrate(
            run_id,
            method_config,
            protocol_config,
            calibration_records,
        )
        threshold_record = dict(threshold_record)
        threshold_record["threshold_id"] = (
            f"{threshold_record['threshold_id']}:{protocol_config['construction_phase']}"
        )
        threshold_record["construction_phase"] = protocol_config["construction_phase"]
        test_records = self._run_event_subset(
            run_id,
            output_root,
            event_plan,
            method,
            method_config,
            target_fpr,
            runtime_splits & {test_split},
            runtime_sample_roles,
            threshold_record,
            latent_backend,
            vae_runtime_backend,
            vae_metadata,
        )
        return dev_records + calibration_records + test_records, threshold_record

    def _run_event_subset(
        self,
        run_id: str,
        output_root: Path,
        event_plan: list[EventPlanEntry],
        method: Any,
        method_config: dict[str, Any],
        target_fpr: float,
        allowed_splits: set[str],
        allowed_sample_roles: set[str],
        threshold_record: dict[str, Any] | None,
        latent_backend: RealVideoVAELatentBackend,
        vae_runtime_backend: Any,
        vae_metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        event_score_records: list[dict[str, Any]] = []
        source_sample_cache: dict[tuple[str, str, str], Any] = {}
        embedded_sample_cache: dict[tuple[str, str, str, str], Any] = {}
        decoded_video_cache: dict[tuple[str, str], dict[str, Any]] = {}
        attacked_video_cache: dict[tuple[str, str], dict[str, Any]] = {}
        latent_copy_cache: dict[tuple[str, str], dict[str, str]] = {}
        reencoded_cache: dict[tuple[str, str], dict[str, str]] = {}
        output_paths = build_real_video_vae_latent_output_paths(output_root)
        for event_plan_entry in event_plan:
            if event_plan_entry.split not in allowed_splits:
                continue
            if event_plan_entry.sample_role not in allowed_sample_roles:
                continue
            source_sample_id, source_sample_role = self._resolve_source_identity(
                event_plan_entry.sample_id,
                event_plan_entry.sample_role,
            )
            source_key = (event_plan_entry.split, source_sample_role, source_sample_id)
            source_sample = source_sample_cache.get(source_key)
            if source_sample is None:
                with self._runner_substage(
                    "runner_build_source_sample",
                    method_variant=method_config["method_variant"],
                    split=event_plan_entry.split,
                ):
                    source_sample = latent_backend.build_sample(
                        source_sample_id,
                        event_plan_entry.split,
                        source_sample_role,
                    )
                source_sample_cache[source_key] = source_sample

            working_sample = source_sample
            watermarked_latent_metadata: dict[str, str] | None = None
            event_artifact_digest = compute_object_digest(
                {
                    "sample_id": event_plan_entry.sample_id,
                    "sample_role": event_plan_entry.sample_role,
                    "split": event_plan_entry.split,
                    "method_variant": method_config["method_variant"],
                    "attack_name": event_plan_entry.attack_name,
                }
            )[:24]
            decoded_artifact_digest = compute_object_digest(
                {
                    "source_sample_id": source_sample_id,
                    "source_sample_role": source_sample_role,
                    "split": event_plan_entry.split,
                    "method_variant": method_config["method_variant"],
                    "latent_digest": working_sample.latent_tensor_digest_random,
                }
            )[:24]
            embedded_key = (
                event_plan_entry.split,
                source_sample_role,
                source_sample_id,
                method_config["method_variant"],
            )
            if event_plan_entry.sample_role in {"watermarked_positive", "attacked_positive"}:
                working_sample = embedded_sample_cache.get(embedded_key)
                if working_sample is None:
                    with self._runner_substage(
                        "runner_embed_latent",
                        method_variant=method_config["method_variant"],
                        split=event_plan_entry.split,
                    ):
                        working_sample = method.embed(
                            source_sample,
                            {
                                "event_sample_id": event_plan_entry.sample_id,
                                "event_sample_role": event_plan_entry.sample_role,
                            },
                        )
                    embedded_sample_cache[embedded_key] = working_sample
                watermarked_latent_relpath = (
                    Path("artifacts")
                    / "latents"
                    / "watermarked"
                    / method_config["method_variant"]
                    / f"{event_artifact_digest}.npy"
                )
                watermarked_latent_metadata = self._cached_latent_copy(
                    latent_copy_cache,
                    working_sample,
                    output_root,
                    watermarked_latent_relpath,
                )

            video_artifact_suffix = (
                ".mp4"
                if str(source_sample.mechanism_trace.get("video_container")) == "mp4"
                else ".npy"
            )

            decoded_video_relpath = (
                Path("artifacts")
                / "videos"
                / "decoded"
                / method_config["method_variant"]
                / f"{decoded_artifact_digest}{video_artifact_suffix}"
            )
            with self._runner_substage(
                "runner_decode_video",
                method_variant=method_config["method_variant"],
                split=event_plan_entry.split,
            ):
                decoded_video_metadata = self._cached_decoded_video_artifact(
                    decoded_video_cache,
                    working_sample,
                    vae_runtime_backend,
                    vae_metadata,
                    output_root,
                    decoded_video_relpath,
                    int(source_sample.mechanism_trace["video_fps"]),
                    tuple(source_sample.mechanism_trace["video_resolution"]),
                )

            with self._runner_substage(
                "runner_attack_video",
                method_variant=method_config["method_variant"],
                attack_name=event_plan_entry.attack_name,
                split=event_plan_entry.split,
            ):
                materialized_attack_params = self._materialize_attack_params(
                    working_sample,
                    event_plan_entry.attack_object,
                    event_plan_entry.attack_name,
                    event_plan_entry.attack_params,
                )
                attacked_sample = self._build_video_attack_sample(
                    working_sample,
                    event_plan_entry.attack_name,
                    materialized_attack_params,
                )
            attacked_video_relpath = (
                Path("artifacts")
                / "videos"
                / "attacked"
                / event_plan_entry.attack_name
                / f"{event_artifact_digest}{video_artifact_suffix}"
            )
            if event_plan_entry.attack_name == "no_attack":
                attacked_video_metadata = decoded_video_metadata
            else:
                with self._runner_substage(
                    "runner_attack_materialization",
                    method_variant=method_config["method_variant"],
                    attack_name=event_plan_entry.attack_name,
                    split=event_plan_entry.split,
                ):
                    if decoded_video_metadata["container"] == "mp4":
                        attacked_video_metadata = self._cached_attacked_video_artifact(
                            attacked_video_cache,
                            decoded_video_metadata,
                            attacked_sample,
                            event_plan_entry.attack_name,
                            event_plan_entry.attack_object,
                            output_root,
                            attacked_video_relpath,
                            int(source_sample.mechanism_trace["video_fps"]),
                            tuple(source_sample.mechanism_trace["video_resolution"]),
                            {
                                "run_id": run_id,
                                "sample_id": event_plan_entry.sample_id,
                            },
                        )
                    else:
                        attacked_sample = event_plan_entry.attack_object.apply(working_sample)
                        materialized_attack_params = (
                            attacked_sample.applied_attack_params or materialized_attack_params
                        )
                        attacked_video_metadata = self._cached_decoded_video_artifact(
                            decoded_video_cache,
                            attacked_sample,
                            vae_runtime_backend,
                            vae_metadata,
                            output_root,
                            attacked_video_relpath,
                            int(source_sample.mechanism_trace["video_fps"]),
                            tuple(source_sample.mechanism_trace["video_resolution"]),
                        )

            reencoded_latent_relpath = (
                Path("artifacts")
                / "latents"
                / "reencoded"
                / event_plan_entry.attack_name
                / f"{event_artifact_digest}.npy"
            )
            with self._runner_substage(
                "runner_reencode_latent",
                method_variant=method_config["method_variant"],
                attack_name=event_plan_entry.attack_name,
                split=event_plan_entry.split,
            ):
                reencoded_latent_metadata = self._cached_reencoded_latent_artifact(
                    reencoded_cache,
                    attacked_video_metadata,
                    attacked_sample,
                    vae_runtime_backend,
                    vae_metadata,
                    output_root,
                    reencoded_latent_relpath,
                )
            detection_sample = self._build_reencoded_sample(
                attacked_sample,
                reencoded_latent_metadata,
            )
            with self._runner_substage(
                "runner_detect",
                method_variant=method_config["method_variant"],
                attack_name=event_plan_entry.attack_name,
                split=event_plan_entry.split,
            ):
                detection_result = method.detect(detection_sample, threshold_record)
            reference_video_path = output_root / decoded_video_metadata["video_relpath"]
            comparison_video_path = output_root / attacked_video_metadata["video_relpath"]
            with self._runner_substage(
                "runner_load_metric_frames",
                method_variant=method_config["method_variant"],
                attack_name=event_plan_entry.attack_name,
                split=event_plan_entry.split,
            ):
                reference_frames, comparison_frames = self._load_metric_frame_pair(
                    reference_video_path,
                    comparison_video_path,
                )
            with self._runner_substage(
                "runner_quality_metrics",
                method_variant=method_config["method_variant"],
                attack_name=event_plan_entry.attack_name,
                split=event_plan_entry.split,
            ):
                quality_metrics = build_real_video_quality_metrics_payload_from_frames(
                    reference_frames,
                    comparison_frames,
                    runtime_config=dict(self._runtime_config_overrides),
                )
            with self._runner_substage(
                "runner_temporal_metrics",
                method_variant=method_config["method_variant"],
                attack_name=event_plan_entry.attack_name,
                split=event_plan_entry.split,
            ):
                temporal_metrics = build_real_video_temporal_metrics_payload_from_frames(
                    reference_frames,
                    comparison_frames,
                    runtime_config=dict(self._runtime_config_overrides),
                )
            mechanism_trace = dict(detection_sample.mechanism_trace or {})
            mechanism_trace.update(detection_result.mechanism_trace or {})
            mechanism_trace.update(
                {
                    "construction_phase": "real_video_vae_latent_probe",
                    "latent_backend_name": detection_sample.latent_backend_name,
                    "vae_backend_name": vae_metadata["vae_backend_name"],
                    "vae_backend_version": vae_metadata["vae_backend_version"],
                    "vae_config_digest": source_sample.mechanism_trace["vae_config_digest"],
                    "vae_encode_mode": vae_metadata["vae_encode_mode"],
                    "vae_decode_mode": vae_metadata["vae_decode_mode"],
                    "video_source_id": source_sample.mechanism_trace["video_source_id"],
                    "video_source_relpath": source_sample.mechanism_trace["video_source_relpath"],
                    "video_source_digest": source_sample.mechanism_trace["video_source_digest"],
                    "video_frame_count": source_sample.mechanism_trace["video_frame_count"],
                    "video_fps": source_sample.mechanism_trace["video_fps"],
                    "video_resolution": source_sample.mechanism_trace["video_resolution"],
                    "source_video_container": source_sample.mechanism_trace.get("video_container"),
                    "video_runtime_status": (
                        "real_mp4_runtime"
                        if attacked_video_metadata["container"] == "mp4"
                        else source_sample.mechanism_trace.get("video_runtime_status")
                    ),
                    "video_container": attacked_video_metadata["container"],
                    "decoded_video_container": decoded_video_metadata["container"],
                    "attacked_video_container": attacked_video_metadata["container"],
                    "encoded_latent_relpath": source_sample.mechanism_trace["encoded_latent_relpath"],
                    "encoded_latent_digest": source_sample.mechanism_trace["encoded_latent_digest"],
                    "watermarked_latent_relpath": None if watermarked_latent_metadata is None else watermarked_latent_metadata["latent_relpath"],
                    "watermarked_latent_digest": None if watermarked_latent_metadata is None else watermarked_latent_metadata["latent_digest"],
                    "decoded_video_relpath": decoded_video_metadata["video_relpath"],
                    "decoded_video_digest": decoded_video_metadata["video_digest"],
                    "attacked_video_relpath": attacked_video_metadata["video_relpath"],
                    "attacked_video_digest": attacked_video_metadata["video_digest"],
                    "quality_metrics_runtime": quality_metrics.get("quality_metrics_runtime"),
                    "temporal_metrics_runtime": temporal_metrics.get("temporal_metrics_runtime"),
                    "reencode_source": (
                        "attacked_video_mp4"
                        if attacked_video_metadata["container"] == "mp4"
                        else "attacked_video_tensor"
                    ),
                    "codec": attacked_video_metadata.get("codec"),
                    "attack_name": event_plan_entry.attack_name,
                    "reencoded_latent_relpath": reencoded_latent_metadata["latent_relpath"],
                    "reencoded_latent_digest": reencoded_latent_metadata["latent_digest"],
                }
            )
            record_random_fields = list(
                dict.fromkeys(
                    [
                        "latent_generation_seed_random",
                        "latent_tensor_digest_random",
                        *detection_result.random_fields,
                    ]
                )
            )
            base_method_variant = str(
                method_config.get("base_method_variant", method_config["method_variant"])
            )
            derived_variant = base_method_variant != method_config["method_variant"]
            tubelet_length = int(method_config.get("tubelet_length", 1))
            event_score_record = {
                "run_id": run_id,
                "event_id": f"{method_config['method_variant']}:{event_plan_entry.event_id}",
                "sample_id": event_plan_entry.sample_id,
                "split": event_plan_entry.split,
                "sample_role": event_plan_entry.sample_role,
                "method_family": method_config["method_family"],
                "method_variant": method_config["method_variant"],
                "base_method_variant": base_method_variant,
                "derived_variant": derived_variant,
                "ablation_axis": "tubelet_length" if derived_variant else None,
                "tubelet_length": tubelet_length,
                "attack_name": event_plan_entry.attack_name,
                "attack_params": attacked_sample.applied_attack_params or materialized_attack_params,
                "target_fpr": target_fpr,
                "threshold_id": None if threshold_record is None else threshold_record["threshold_id"],
                "input_artifact_trace": build_input_artifact_trace(detection_sample),
                "latent_backend_name": detection_sample.latent_backend_name,
                "latent_backend_status": detection_sample.latent_backend_status,
                "latent_tensor_digest_random": detection_sample.latent_tensor_digest_random,
                "latent_generation_seed_random": detection_sample.latent_generation_seed_random,
                "evidence_scores": detection_result.evidence_scores,
                "disabled_evidence": detection_result.disabled_evidence,
                "decision": detection_result.decision,
                "failure_reason": detection_result.failure_reason,
                "mechanism_trace": mechanism_trace,
                "placeholder_fields": detection_result.placeholder_fields,
                "random_fields": record_random_fields,
                "quality_metrics": quality_metrics,
                "temporal_metrics": temporal_metrics,
            }
            validate_event_score_record(event_score_record)
            event_score_records.append(event_score_record)
        return event_score_records

    def _build_event_plan(self, split_plan: list[Any], attack_registry: list[Any]) -> list[EventPlanEntry]:
        event_plan: list[EventPlanEntry] = []
        for split_plan_entry in split_plan:
            for attack_object in attack_registry:
                attack_cases = self._expand_attack_cases(attack_object)
                for attack_case_id, attack_name, attack_params, attack_case_object in attack_cases:
                    if (
                        split_plan_entry.sample_role in {"clean_negative", "watermarked_positive"}
                        and attack_name != "no_attack"
                    ):
                        continue
                    if (
                        split_plan_entry.sample_role in {"attacked_negative", "attacked_positive"}
                        and attack_name == "no_attack"
                    ):
                        continue
                    event_plan.append(
                        EventPlanEntry(
                            event_id=f"{split_plan_entry.sample_id}:{attack_case_id}",
                            sample_id=split_plan_entry.sample_id,
                            split=split_plan_entry.split,
                            sample_role=split_plan_entry.sample_role,
                            attack_name=attack_name,
                            attack_params=attack_params,
                            attack_object=attack_case_object,
                        )
                    )
        return event_plan

    def _expand_attack_cases(self, attack_object: Any) -> list[tuple[str, str, dict[str, Any], Any]]:
        if getattr(attack_object, "attack_name", None) == "local_clip" and isinstance(
            attack_object.attack_params.get("clip_lengths"),
            list,
        ):
            expanded_cases = []
            for clip_length in attack_object.attack_params["clip_lengths"]:
                fixed_attack_params = {"clip_length": int(clip_length)}
                expanded_cases.append(
                    (
                        f"local_clip_len_{int(clip_length):02d}",
                        "local_clip",
                        fixed_attack_params,
                        type(attack_object)("local_clip", fixed_attack_params),
                    )
                )
            return expanded_cases
        attack_params = dict(getattr(attack_object, "attack_params", {}))
        attack_case_suffix = compute_object_digest(attack_params)[:8] if attack_params else "default"
        return [
            (
                f"{attack_object.attack_name}:{attack_case_suffix}",
                attack_object.attack_name,
                attack_params,
                attack_object,
            )
        ]

    def _cached_decoded_video_artifact(
        self,
        cache: dict[tuple[str, str], dict[str, Any]],
        sample: Any,
        vae_runtime_backend: Any,
        vae_metadata: dict[str, Any],
        output_root: Path,
        artifact_relpath: Path,
        fps: int,
        target_resolution: tuple[int, int],
    ) -> dict[str, Any]:
        cache_key = (
            sample.latent_tensor_digest_random,
            str(fps),
            f"{int(target_resolution[0])}x{int(target_resolution[1])}",
        )
        cached_metadata = cache.get(cache_key)
        if cached_metadata is not None:
            return cached_metadata

        latent_tensor = self._load_latent_tensor(sample)
        decoded_video = self._decode_latent_to_video(
            latent_tensor,
            vae_runtime_backend,
            vae_metadata,
            target_resolution,
        )
        metadata = self._write_video_artifact(
            decoded_video,
            output_root,
            artifact_relpath,
            fps,
        )
        cache[cache_key] = metadata
        return metadata

    def _cached_attacked_video_artifact(
        self,
        cache: dict[tuple[str, str], dict[str, Any]],
        source_video_metadata: dict[str, Any],
        sample: LatentSample,
        attack_name: str,
        attack_object: Any,
        output_root: Path,
        artifact_relpath: Path,
        fps: int,
        target_resolution: tuple[int, int],
        runtime_config: dict[str, Any],
    ) -> dict[str, Any]:
        attack_params_digest = compute_object_digest(sample.applied_attack_params or {})[:12]
        cache_key = (
            source_video_metadata["video_digest"],
            f"{attack_name}:{attack_params_digest}:{artifact_relpath.as_posix()}",
        )
        cached_metadata = cache.get(cache_key)
        if cached_metadata is not None:
            return cached_metadata

        output_path = output_root / artifact_relpath
        input_video_path = output_root / source_video_metadata["video_relpath"]
        if output_path.exists():
            metadata = self._build_video_artifact_metadata_from_path(
                output_path,
                artifact_relpath,
                fps,
            )
            cache[cache_key] = metadata
            return metadata

        codec_hint = None
        if hasattr(attack_object, "apply_video"):
            attack_metadata = attack_object.apply_video(
                input_video_path,
                output_path,
                fps=fps,
                resolution=target_resolution,
                runtime_config=runtime_config,
            )
            codec_hint = attack_metadata.get("codec")
        else:
            input_frames = read_video_frames(input_video_path).frames
            if hasattr(attack_object, "apply_frames"):
                attacked_frames = attack_object.apply_frames(
                    input_frames,
                    runtime_config=runtime_config,
                )
            else:
                attacked_frames = self._apply_temporal_attack_to_frames(
                    input_frames,
                    attack_name,
                    sample.applied_attack_params or {},
                )
            write_video_mp4(
                np.asarray(attacked_frames, dtype=np.float32),
                output_path,
                fps=fps,
                codec="libx264",
                crf=18,
            )
            codec_hint = "libx264"

        metadata = self._build_video_artifact_metadata_from_path(
            output_path,
            artifact_relpath,
            fps,
            codec_hint=codec_hint,
        )
        cache[cache_key] = metadata
        return metadata

    def _cached_reencoded_latent_artifact(
        self,
        cache: dict[tuple[str, str], dict[str, str]],
        video_metadata: dict[str, Any],
        reference_sample: LatentSample,
        vae_runtime_backend: Any,
        vae_metadata: dict[str, Any],
        output_root: Path,
        artifact_relpath: Path,
    ) -> dict[str, str]:
        cache_key = (video_metadata["video_digest"], artifact_relpath.as_posix())
        cached_metadata = cache.get(cache_key)
        if cached_metadata is not None:
            return cached_metadata

        output_path = output_root / artifact_relpath
        if output_path.exists():
            metadata = {
                "latent_relpath": artifact_relpath.as_posix(),
                "latent_digest": compute_file_digest(output_path),
            }
            cache[cache_key] = metadata
            return metadata

        video_tensor = self._read_video_tensor_from_artifact(output_root / video_metadata["video_relpath"])
        reencoded = self._encode_video_to_latent(video_tensor, vae_runtime_backend, vae_metadata)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_float_tensor_npy(
            output_path,
            (
                int(reencoded.shape[0]),
                int(reencoded.shape[1]),
                int(reencoded.shape[2]),
                int(reencoded.shape[3]),
            ),
            array("f", reencoded.reshape(-1).tolist()),
        )
        metadata = {
            "latent_relpath": artifact_relpath.as_posix(),
            "latent_digest": compute_file_digest(output_path),
        }
        cache[cache_key] = metadata
        return metadata

    def _cached_latent_copy(
        self,
        cache: dict[tuple[str, str], dict[str, str]],
        sample: Any,
        output_root: Path,
        artifact_relpath: Path,
    ) -> dict[str, str]:
        cache_key = (sample.latent_tensor_digest_random, artifact_relpath.as_posix())
        cached_metadata = cache.get(cache_key)
        if cached_metadata is not None:
            return cached_metadata
        metadata = copy_latent_artifact(sample, output_root, artifact_relpath)
        cache[cache_key] = metadata
        return metadata

    def _build_reencoded_sample(
        self,
        reference_sample: LatentSample,
        reencoded_latent_metadata: dict[str, str],
    ) -> LatentSample:
        artifact_path = Path(reference_sample.run_root_path) / reencoded_latent_metadata["latent_relpath"]
        artifact = read_float_tensor_npy(artifact_path)
        latent_shape = (
            int(artifact.shape[0]),
            int(artifact.shape[1]),
            int(artifact.shape[2]),
            int(artifact.shape[3]),
        )
        mechanism_trace = dict(reference_sample.mechanism_trace or {})
        mechanism_trace.setdefault("reference_latent_shape", list(reference_sample.latent_shape))
        mechanism_trace.update(
            {
                "latent_shape": list(latent_shape),
                "latent_artifact_relpath": reencoded_latent_metadata["latent_relpath"],
                "latent_artifact_digest": reencoded_latent_metadata["latent_digest"],
            }
        )
        return replace(
            reference_sample,
            latent_shape=latent_shape,
            latent_tensor_digest_random=reencoded_latent_metadata["latent_digest"],
            latent_artifact_relpath=reencoded_latent_metadata["latent_relpath"],
            latent_artifact_path=str(artifact_path),
            latent_artifact_digest=reencoded_latent_metadata["latent_digest"],
            mechanism_trace=mechanism_trace,
        )

    def _load_latent_tensor(self, sample: LatentSample) -> np.ndarray:
        artifact = read_float_tensor_npy(sample.latent_artifact_path)
        return np.asarray(artifact.values, dtype=np.float32).reshape(artifact.shape)

    def _decode_latent_to_video(
        self,
        latent_tensor: np.ndarray,
        vae_runtime_backend: Any,
        vae_metadata: dict[str, Any],
        target_resolution: tuple[int, int],
    ) -> np.ndarray:
        del vae_metadata
        decoded = vae_runtime_backend.decode_video(
            latent_tensor,
            config={"target_resolution": target_resolution},
        )
        if not isinstance(decoded, np.ndarray):
            raise TypeError("decoded video must be a numpy ndarray")
        if decoded.ndim == 4 and decoded.shape[-1] == 3:
            return np.clip(decoded.astype(np.float32), 0.0, 1.0)
        if decoded.ndim == 4 and decoded.shape[1] == 3:
            return np.clip(decoded.astype(np.float32).transpose(0, 2, 3, 1), 0.0, 1.0)
        raise ValueError("decoded video must be shaped as [F, H, W, 3] or [F, 3, H, W]")

    def _write_video_artifact(
        self,
        video_tensor: np.ndarray,
        output_root: Path,
        artifact_relpath: Path,
        fps: int,
    ) -> dict[str, Any]:
        output_path = output_root / artifact_relpath
        if output_path.suffix.lower() == ".mp4":
            if output_path.exists():
                return self._build_video_artifact_metadata_from_path(
                    output_path,
                    artifact_relpath,
                    fps,
                )

            metadata = write_video_mp4(
                np.clip(video_tensor.astype(np.float32), 0.0, 1.0),
                output_path,
                fps=int(fps),
                codec="libx264",
                crf=18,
            )
            metadata["video_relpath"] = artifact_relpath.as_posix()
            metadata["video_digest"] = compute_file_digest(output_path)
            return metadata

        if output_path.exists():
            artifact = read_float_tensor_npy(output_path)
            return {
                "video_relpath": artifact_relpath.as_posix(),
                "video_digest": compute_file_digest(output_path),
                "frame_count": int(artifact.shape[0]),
                "fps": int(fps),
                "height": int(artifact.shape[2]),
                "width": int(artifact.shape[3]),
                "codec": "vae_decode_tensor_npy",
                "container": "npy",
                "pixel_format": "float32_nchw",
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        nchw = np.clip(video_tensor.astype(np.float32), 0.0, 1.0).transpose(0, 3, 1, 2)
        write_float_tensor_npy(
            output_path,
            (
                int(nchw.shape[0]),
                int(nchw.shape[1]),
                int(nchw.shape[2]),
                int(nchw.shape[3]),
            ),
            array("f", nchw.reshape(-1).tolist()),
        )
        return {
            "video_relpath": artifact_relpath.as_posix(),
            "video_digest": compute_file_digest(output_path),
            "frame_count": int(nchw.shape[0]),
            "fps": int(fps),
            "height": int(nchw.shape[2]),
            "width": int(nchw.shape[3]),
            "codec": "vae_decode_tensor_npy",
            "container": "npy",
            "pixel_format": "float32_nchw",
        }

    def _read_video_tensor_from_artifact(self, artifact_path: Path) -> np.ndarray:
        if artifact_path.suffix.lower() == ".mp4":
            return read_video_frames(artifact_path).frames.astype(np.float32)
        artifact = read_float_tensor_npy(artifact_path)
        return np.asarray(artifact.values, dtype=np.float32).reshape(artifact.shape).transpose(0, 2, 3, 1)

    def _load_metric_frame_pair(
        self,
        reference_video_path: Path,
        comparison_video_path: Path,
    ) -> tuple[np.ndarray, np.ndarray]:
        reference_frames = self._read_video_tensor_from_artifact(reference_video_path)
        comparison_frames = self._read_video_tensor_from_artifact(comparison_video_path)
        return reference_frames, comparison_frames

    def _encode_video_to_latent(
        self,
        video_tensor: np.ndarray,
        vae_runtime_backend: Any,
        vae_metadata: dict[str, Any],
    ) -> np.ndarray:
        del vae_metadata
        encoded = vae_runtime_backend.encode_video(video_tensor)
        if not isinstance(encoded, np.ndarray):
            raise TypeError("encoded latent must be a numpy ndarray")
        if encoded.ndim != 4:
            raise ValueError("encoded latent must be a 4D tensor")
        if encoded.shape[-1] == 3:
            encoded = encoded.transpose(0, 3, 1, 2)
        return encoded.astype(np.float32)

    def _video_mp4_runtime_available(self) -> bool:
        return importlib.util.find_spec("imageio_ffmpeg") is not None

    def _build_video_artifact_metadata_from_path(
        self,
        artifact_path: Path,
        artifact_relpath: Path,
        fps: int,
        codec_hint: str | None = None,
    ) -> dict[str, Any]:
        if artifact_path.suffix.lower() == ".mp4":
            metadata = probe_video_metadata(artifact_path)
            return {
                "video_relpath": artifact_relpath.as_posix(),
                "video_digest": compute_file_digest(artifact_path),
                "frame_count": int(metadata["frame_count"]),
                "fps": int(metadata.get("fps", fps) or fps),
                "height": int(metadata["height"]),
                "width": int(metadata["width"]),
                "codec": codec_hint or "libx264",
                "container": "mp4",
                "pixel_format": "yuv420p",
            }

        artifact = read_float_tensor_npy(artifact_path)
        return {
            "video_relpath": artifact_relpath.as_posix(),
            "video_digest": compute_file_digest(artifact_path),
            "frame_count": int(artifact.shape[0]),
            "fps": int(fps),
            "height": int(artifact.shape[2]),
            "width": int(artifact.shape[3]),
            "codec": "vae_decode_tensor_npy",
            "container": "npy",
            "pixel_format": "float32_nchw",
        }

    def _materialize_attack_params(
        self,
        sample: LatentSample,
        attack_object: Any,
        attack_name: str,
        attack_params: dict[str, Any],
    ) -> dict[str, Any]:
        if (
            attack_name in REAL_VIDEO_TEMPORAL_ATTACK_NAMES
            and attack_name != "no_attack"
            and hasattr(attack_object, "_materialize_attack_params")
        ):
            return dict(attack_object._materialize_attack_params(sample))
        return dict(getattr(attack_object, "attack_params", attack_params))

    def _build_video_attack_sample(
        self,
        sample: LatentSample,
        attack_name: str,
        attack_params: dict[str, Any],
    ) -> LatentSample:
        mechanism_trace = dict(sample.mechanism_trace or {})
        mechanism_trace.setdefault("reference_latent_shape", list(sample.latent_shape))
        mechanism_trace.setdefault("latent_shape", list(sample.latent_shape))
        mechanism_trace.setdefault("latent_artifact_relpath", sample.latent_artifact_relpath)
        mechanism_trace.setdefault("latent_artifact_digest", sample.latent_artifact_digest)
        mechanism_trace["attack_name"] = attack_name
        if "ground_truth_offset" in attack_params:
            mechanism_trace["sync_ground_truth_offset"] = attack_params["ground_truth_offset"]
        if "ground_truth_scale" in attack_params:
            mechanism_trace["sync_ground_truth_scale"] = attack_params["ground_truth_scale"]
        if "clip_length" in attack_params:
            mechanism_trace["clip_length"] = attack_params["clip_length"]
        return replace(
            sample,
            mechanism_trace=mechanism_trace,
            applied_attack_params=dict(attack_params),
        )

    def _apply_temporal_attack_to_frames(
        self,
        frames: np.ndarray,
        attack_name: str,
        attack_params: dict[str, Any],
    ) -> np.ndarray:
        if attack_name == "temporal_crop":
            start = int(attack_params["crop_start"])
            stop = start + int(attack_params["crop_length"])
            selected_frames = frames[start:stop]
        elif attack_name == "frame_dropping":
            kept_indices = [int(index) for index in attack_params["kept_frame_indices"]]
            selected_frames = frames[kept_indices]
        elif attack_name == "speed_change":
            observed_frame_count = int(attack_params["observed_frame_count"])
            speed_ratio = float(attack_params["speed_ratio"])
            selected_frames = []
            for observed_index in range(observed_frame_count):
                source_index = min(
                    int(frames.shape[0]) - 1,
                    int(round(observed_index * speed_ratio)),
                )
                selected_frames.append(frames[source_index])
            selected_frames = np.asarray(selected_frames, dtype=np.float32)
        elif attack_name == "local_clip":
            start = int(attack_params["clip_start"])
            stop = start + int(attack_params["clip_length"])
            selected_frames = frames[start:stop]
        else:
            selected_frames = frames

        attacked_frames = np.asarray(selected_frames, dtype=np.float32)
        if attacked_frames.ndim != 4 or attacked_frames.shape[0] < 1:
            attacked_frames = np.asarray(frames[:1], dtype=np.float32)
        return attacked_frames

    def _resolve_source_identity(self, sample_id: str, sample_role: str) -> tuple[str, str]:
        if sample_role == "attacked_negative":
            return sample_id.replace("attacked_negative", "clean_negative"), "clean_negative"
        if sample_role == "attacked_positive":
            return sample_id.replace("attacked_positive", "watermarked_positive"), "watermarked_positive"
        return sample_id, sample_role

    def _resolve_config_path(self, path: str | Path | None, default_path: Path) -> Path:
        resolved_path = default_path if path is None else Path(path)
        if path is not None and not resolved_path.is_absolute():
            repo_relative_path = self._repository_root / resolved_path
            if repo_relative_path.exists():
                resolved_path = repo_relative_path
        if not resolved_path.exists():
            raise FileNotFoundError(resolved_path)
        return resolved_path

    def _load_runtime_config(self, runtime_config_path: str | Path | None) -> dict[str, Any]:
        """Load an optional Colab runtime-config payload.

        Args:
            runtime_config_path: Optional runtime-config JSON path.

        Returns:
            A normalized runtime-config dictionary.
        """
        if runtime_config_path is None:
            return {}
        resolved_path = Path(runtime_config_path)
        if not resolved_path.is_absolute():
            repo_relative_path = self._repository_root / resolved_path
            if repo_relative_path.exists():
                resolved_path = repo_relative_path
        if not resolved_path.exists():
            raise FileNotFoundError(resolved_path)
        runtime_config = load_json_config(resolved_path)
        if not isinstance(runtime_config, dict):
            raise TypeError("runtime_config must be a dictionary")
        return runtime_config

    def _resolve_samples_per_role(
        self,
        samples_per_role: int | None,
        protocol_config: dict[str, Any],
        runtime_profile: str,
    ) -> int:
        if samples_per_role is None:
            profile_samples = protocol_config.get("samples_per_role_by_profile", {})
            resolved_samples_per_role = profile_samples.get(
                runtime_profile,
                1 if runtime_profile in {"tiny", "smoke", "debug_real_video"} else 2,
            )
        else:
            resolved_samples_per_role = samples_per_role
        if not isinstance(resolved_samples_per_role, int) or resolved_samples_per_role < 1:
            raise ValueError("samples_per_role must be a positive integer")
        return int(resolved_samples_per_role)

    def _resolve_profile_string_list(
        self,
        profile_values: Any,
        runtime_profile: str,
        default_values: Any,
        field_name: str,
    ) -> list[str]:
        resolved_values = default_values
        if isinstance(profile_values, dict):
            resolved_values = profile_values.get(runtime_profile, default_values)
        if not isinstance(resolved_values, list) or not resolved_values:
            raise ValueError(f"{field_name} must resolve to a non-empty list")
        normalized_values = [str(value) for value in resolved_values]
        if any(not value for value in normalized_values):
            raise ValueError(f"{field_name} contains an empty value")
        return normalized_values

    def _resolve_runtime_splits(
        self,
        protocol_config: dict[str, Any],
        runtime_profile: str,
        dataset_manifest: dict[str, Any],
    ) -> list[str]:
        configured_splits = self._resolve_profile_string_list(
            protocol_config.get("splits_by_profile"),
            runtime_profile,
            protocol_config.get("splits", ["dev", "calibration", "test"]),
            "splits_by_profile",
        )
        manifest_samples = dataset_manifest.get("samples", [])
        if not isinstance(manifest_samples, list):
            raise ValueError("dataset manifest samples must be a list")
        manifest_splits = {
            str(sample.get("split", "")).strip()
            for sample in manifest_samples
            if isinstance(sample, dict) and str(sample.get("split", "")).strip()
        }
        if not manifest_splits:
            raise ValueError("dataset manifest must contain at least one split")

        resolved_splits = [
            split_name
            for split_name in configured_splits
            if split_name in manifest_splits
        ]
        if not resolved_splits:
            raise ValueError(
                "dataset manifest does not provide any splits required by the runtime profile"
            )
        return resolved_splits

    def _filter_attack_registry(
        self,
        attack_registry: list[Any],
        attack_config: dict[str, Any],
        runtime_profile: str,
    ) -> list[Any]:
        allowed_attack_names = set(
            self._resolve_profile_string_list(
                attack_config.get("attack_names_by_profile"),
                runtime_profile,
                [str(getattr(attack_object, "attack_name", "")) for attack_object in attack_registry],
                "attack_names_by_profile",
            )
        )
        filtered_attack_registry = [
            attack_object
            for attack_object in attack_registry
            if getattr(attack_object, "attack_name", None) in allowed_attack_names
        ]
        if not filtered_attack_registry:
            raise ValueError("runtime_profile attack filter removed all attacks")
        return filtered_attack_registry

    def _resolve_backend_config(self, runtime_profile: str, backend_config: dict[str, Any]) -> dict[str, Any]:
        resolved_backend_config = copy.deepcopy(backend_config)
        resolved_backend_config["runtime_profile"] = runtime_profile
        profile_key = {
            "tiny": "tiny_latent_shape",
            "smoke": "latent_shape",
            "debug_real_video": "debug_real_video_latent_shape",
            "proof": "proof_latent_shape",
            "formal": "formal_latent_shape",
        }[runtime_profile]
        resolved_backend_config["latent_shape"] = backend_config.get(
            profile_key,
            backend_config["latent_shape"],
        )

        profile_override_fields = (
            "vae_backend_name",
            "vae_backend_version",
            "vae_model_local_path",
            "vae_encode_mode",
            "vae_decode_mode",
            "allow_mock_vae_backend",
            "target_frame_count",
            "target_resolution",
        )
        for field_name in profile_override_fields:
            runtime_field_name = f"{runtime_profile}_{field_name}"
            if runtime_field_name in backend_config:
                resolved_backend_config[field_name] = backend_config[runtime_field_name]

        return resolved_backend_config

    def _build_method_config_paths(self, ablation_config: dict[str, Any]) -> dict[str, Path]:
        method_variants = ablation_config.get("method_variants", [])
        if not isinstance(method_variants, list) or not method_variants:
            raise ValueError("ablation method_variants must be a non-empty list")
        return {
            method_variant: self._repository_root / "configs" / "method" / f"{method_variant}.json"
            for method_variant in method_variants
        }

    def _build_runtime_method_configs(
        self,
        ablation_config: dict[str, Any],
        method_config_paths: dict[str, Path],
        runtime_profile: str,
        method_variants: list[str] | None,
    ) -> list[dict[str, Any]]:
        method_configs = {
            method_variant: load_json_config(config_path)
            for method_variant, config_path in method_config_paths.items()
        }
        configured_method_variants = ablation_config.get("method_variants_by_profile", {}).get(
            runtime_profile,
            ablation_config["method_variants"],
        )
        if not isinstance(configured_method_variants, list) or not configured_method_variants:
            raise ValueError("ablation method_variants_by_profile must resolve to a non-empty list")
        runtime_method_configs = [
            dict(method_configs[method_variant])
            for method_variant in configured_method_variants
        ]
        sweep_variant = ablation_config.get("tubelet_length_sweep_variant")
        sweep_lengths = list(ablation_config.get(f"tubelet_length_sweep_{runtime_profile}", []))
        if isinstance(sweep_variant, str) and sweep_variant in method_configs and sweep_lengths:
            base_config = method_configs[sweep_variant]
            default_length = int(base_config["tubelet_length"])
            for tubelet_length in sweep_lengths:
                if int(tubelet_length) == default_length:
                    continue
                derived_method_config = dict(base_config)
                derived_method_config["base_method_variant"] = sweep_variant
                derived_method_config["method_variant"] = f"{sweep_variant}_lt{int(tubelet_length):02d}"
                derived_method_config["tubelet_length"] = int(tubelet_length)
                runtime_method_configs.append(derived_method_config)
        for runtime_method_config in runtime_method_configs:
            runtime_method_config["method_status"] = "formal_real_video_vae_probe_runtime"
            runtime_method_config["target_construction_phase"] = "real_video_vae_latent_probe"
        if method_variants is None:
            return runtime_method_configs
        runtime_map = {
            runtime_method_config["method_variant"]: runtime_method_config
            for runtime_method_config in runtime_method_configs
        }
        return [dict(runtime_map[method_variant]) for method_variant in method_variants]

    def _build_artifact_manifest(self, event_score_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        artifact_entries: dict[tuple[str, str], dict[str, Any]] = {}
        for event_score_record in event_score_records:
            mechanism_trace = event_score_record.get("mechanism_trace", {})
            for relpath_key, digest_key, artifact_kind in (
                ("video_source_relpath", "video_source_digest", "source_video"),
                ("encoded_latent_relpath", "encoded_latent_digest", "encoded_latent"),
                ("watermarked_latent_relpath", "watermarked_latent_digest", "watermarked_latent"),
                ("decoded_video_relpath", "decoded_video_digest", "decoded_video"),
                ("attacked_video_relpath", "attacked_video_digest", "attacked_video"),
                ("reencoded_latent_relpath", "reencoded_latent_digest", "reencoded_latent"),
            ):
                relpath = mechanism_trace.get(relpath_key)
                digest = mechanism_trace.get(digest_key)
                if relpath is None or digest is None:
                    continue
                artifact_entries[(artifact_kind, relpath)] = {
                    "artifact_kind": artifact_kind,
                    "relpath": relpath,
                    "digest": digest,
                }
        return [artifact_entries[key] for key in sorted(artifact_entries.keys())]

    def _reset_incremental_outputs(self, record_writer: RecordWriter) -> None:
        event_scores_path = record_writer.output_paths.event_scores_path
        thresholds_path = record_writer.output_paths.thresholds_path
        event_scores_path.parent.mkdir(parents=True, exist_ok=True)
        thresholds_path.parent.mkdir(parents=True, exist_ok=True)
        if event_scores_path.exists():
            event_scores_path.unlink()
        if thresholds_path.exists():
            thresholds_path.unlink()

    def _write_json(self, file_path: Path, payload: Any) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the governed stage-two real-video VAE latent probe runtime.",
    )
    parser.add_argument("--run-mode", choices=("smoke", "formal"), default="smoke")
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--samples-per-role", type=int, default=None)
    parser.add_argument("--batch-size-frames", type=int, default=None)
    parser.add_argument("--runtime-profile", default=None)
    parser.add_argument("--protocol-config", default=None)
    parser.add_argument("--backend-config", default=None)
    parser.add_argument("--attack-matrix", default=None)
    parser.add_argument("--ablation-config", default=None)
    parser.add_argument("--dataset-manifest", default=None)
    parser.add_argument("--runtime-config", default=None)
    parser.add_argument("--method-variants", nargs="+", default=None)
    args = parser.parse_args(argv)
    RealVideoVaeLatentRunner(ROOT).run(
        output_root=args.run_root,
        run_mode=args.run_mode,
        samples_per_role=args.samples_per_role,
        batch_size_frames=args.batch_size_frames,
        runtime_profile_override=args.runtime_profile,
        method_variants=args.method_variants,
        protocol_config_path=args.protocol_config,
        backend_config_path=args.backend_config,
        attack_matrix_path=args.attack_matrix,
        ablation_config_path=args.ablation_config,
        dataset_manifest_path=args.dataset_manifest,
        runtime_config_path=args.runtime_config,
    )


if __name__ == "__main__":
    main()
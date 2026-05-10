"""
文件用途：运行阶段 2 real-video VAE latent probe 的受治理占位闭环。
File purpose: Run the governed placeholder stage-two real-video VAE latent probe.
Module type: General module
"""

from __future__ import annotations

import argparse
import copy
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main.analysis.quality_metrics import build_quality_metrics_payload
from main.analysis.real_video_vae_latent_artifacts import RealVideoVaeLatentArtifactBuilder
from main.analysis.temporal_metrics import build_temporal_metrics_payload
from main.attacks.real_video_attack_registry import build_real_video_attack_registry
from main.backends.real_video_vae_latent import (
    DEFAULT_RUNTIME_PROFILE,
    RealVideoVAELatentBackend,
    build_real_video_vae_latent_backend_from_support_config,
)
from main.core.digest import compute_file_digest, compute_object_digest, compute_path_collection_digest
from main.core.records import RecordWriter
from main.core.registry import load_json_config
from main.core.schema import NEGATIVE_SAMPLE_ROLES, SAMPLE_ROLES, build_input_artifact_trace, validate_event_score_record
from main.methods.temporal_tubelet_watermark.method_placeholder import build_method_from_config
from main.protocol.calibrator import ThresholdCalibrator
from main.protocol.event_builder import EventPlanEntry
from main.protocol.split_builder import build_split_plan
from main.protocol.real_video_vae_latent_paths import RealVideoVaeLatentOutputPaths, build_real_video_vae_latent_output_paths
from main.vae.vae_registry import resolve_vae_backend
from main.video.dataset_manifest import load_dataset_manifest, summarize_dataset_manifest
from main.video.video_artifact import copy_latent_artifact, materialize_video_artifact_from_latent


SUPPORTED_RUNTIME_PROFILES = ("tiny", "smoke", "proof", "formal")


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
    """功能：执行阶段 2 占位协议闭环。

    Execute the placeholder stage-two governed protocol loop.

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

    def run(
        self,
        output_root: str | Path,
        run_mode: str = "smoke",
        samples_per_role: int | None = None,
        runtime_profile_override: str | None = None,
        method_variants: list[str] | None = None,
        protocol_config_path: str | Path | None = None,
        backend_config_path: str | Path | None = None,
        attack_matrix_path: str | Path | None = None,
        ablation_config_path: str | Path | None = None,
        dataset_manifest_path: str | Path | None = None,
        runtime_config_path: str | Path | None = None,
    ) -> RealVideoVaeLatentRunResult:
        """功能：运行阶段 2 占位协议并写出 records、tables 与 manifests。

        Run the placeholder stage-two protocol and persist its governed artifacts.

        Args:
            output_root: Run root path.
            run_mode: Runtime mode, one of `smoke` or `formal`.
            samples_per_role: Optional sample count per split-role pair.
            runtime_profile_override: Optional explicit runtime profile.
            method_variants: Optional explicit method-variant allowlist.
            protocol_config_path: Optional protocol config path.
            backend_config_path: Optional backend config path.
            attack_matrix_path: Optional attack config path.
            ablation_config_path: Optional ablation config path.
            dataset_manifest_path: Optional dataset manifest path.
            runtime_config_path: Optional Colab runtime-config override path.

        Returns:
            A `RealVideoVaeLatentRunResult` instance.
        """
        if run_mode not in {"smoke", "formal"}:
            raise ValueError("run_mode must be either smoke or formal")
        runtime_profile = runtime_profile_override or ("formal" if run_mode == "formal" else DEFAULT_RUNTIME_PROFILE)
        if runtime_profile not in SUPPORTED_RUNTIME_PROFILES:
            raise ValueError("unsupported runtime_profile")
        resolved_samples_per_role = 1 if samples_per_role is None and runtime_profile in {"tiny", "smoke"} else 2 if samples_per_role is None else int(samples_per_role)
        if resolved_samples_per_role < 1:
            raise ValueError("samples_per_role must be a positive integer")

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
        dataset_manifest_file = self._resolve_config_path(
            dataset_manifest_path,
            self._repository_root / "configs" / "data" / "real_video_probe_manifest.json",
        )

        protocol_config = load_json_config(protocol_config_file)
        backend_config = self._resolve_backend_config(runtime_profile, load_json_config(backend_config_file))
        attack_config = load_json_config(attack_matrix_file)
        ablation_config = load_json_config(ablation_config_file)
        dataset_manifest = load_dataset_manifest(dataset_manifest_file)
        runtime_config_overrides = self._load_runtime_config(runtime_config_path)
        dataset_summary = summarize_dataset_manifest(dataset_manifest)
        backend_config["dataset_manifest_path"] = str(dataset_manifest_file)
        if "local_dataset_root" in runtime_config_overrides:
            backend_config["local_dataset_root"] = runtime_config_overrides["local_dataset_root"]
        if "local_vae_model_root" in runtime_config_overrides:
            backend_config["vae_model_local_path"] = runtime_config_overrides["local_vae_model_root"]
        elif "vae_model_local_path" in runtime_config_overrides:
            backend_config["vae_model_local_path"] = runtime_config_overrides["vae_model_local_path"]
        if "frame_sampling_policy" in dataset_manifest:
            backend_config["frame_sampling_policy"] = dataset_manifest["frame_sampling_policy"]
        if "default_frame_count" in dataset_manifest:
            backend_config["target_frame_count"] = int(dataset_manifest["default_frame_count"])
        if "default_resolution" in dataset_manifest:
            backend_config["target_resolution"] = dataset_manifest["default_resolution"]
        vae_backend = resolve_vae_backend(backend_config)
        vae_metadata = vae_backend.backend_metadata()
        latent_backend = build_real_video_vae_latent_backend_from_support_config(backend_config)
        output_root_path = Path(output_root)
        output_root_path.mkdir(parents=True, exist_ok=True)
        latent_backend.set_output_root(output_root_path)

        split_plan = build_split_plan(samples_per_role=resolved_samples_per_role)
        attack_registry = build_real_video_attack_registry(attack_config)
        event_plan = self._build_event_plan(split_plan, attack_registry)
        method_config_paths = self._build_method_config_paths(ablation_config)
        runtime_method_configs = self._build_runtime_method_configs(
            ablation_config,
            method_config_paths,
            runtime_profile,
            method_variants,
        )
        run_id = output_root_path.name
        event_score_records: list[dict[str, Any]] = []
        threshold_records: list[dict[str, Any]] = []
        record_writer = RecordWriter(output_root_path)
        self._reset_incremental_outputs(record_writer)

        for method_config in runtime_method_configs:
            variant_event_records, threshold_record = self._run_method_variant(
                run_id=run_id,
                output_root=output_root_path,
                event_plan=event_plan,
                method_config=method_config,
                protocol_config=protocol_config,
                latent_backend=latent_backend,
                vae_metadata=vae_metadata,
            )
            event_score_records.extend(variant_event_records)
            threshold_records.append(threshold_record)

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
                "dataset_manifest": str(dataset_manifest_file.relative_to(self._repository_root)).replace("\\", "/"),
                "target_fpr": protocol_config["threshold_protocol"]["target_fpr_placeholder"],
                "method_variants": [method_config["method_variant"] for method_config in runtime_method_configs],
            }
        )
        self._write_json(output_paths.colab_real_video_vae_latent_runtime_config_path, runtime_config_payload)
        runtime_config_digest = compute_object_digest(runtime_config_payload)
        runtime_manifest = {
            "run_id": run_id,
            "construction_phase": protocol_config["construction_phase"],
            "run_mode": run_mode,
            "runtime_profile": runtime_profile,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "working_directory": str(self._repository_root),
            "notebook_entrypoint_present": (
                self._repository_root
                / "paper_workflow"
                / "Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb"
            ).exists(),
            "dataset_summary": dataset_summary,
            "vae_metadata": vae_metadata,
        }
        git_commit = runtime_config_overrides.get("git_commit")
        if isinstance(git_commit, str) and git_commit:
            runtime_manifest["git_commit"] = git_commit
        self._write_json(output_paths.colab_runtime_manifest_path, runtime_manifest)
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
            "placeholder_fields": [
                "video_vae_backend_placeholder",
                "clip_similarity_placeholder",
                "motion_consistency_placeholder",
            ],
            "random_fields": [
                "latent_generation_seed_random",
                "latent_tensor_digest_random",
            ],
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

    def _run_method_variant(
        self,
        run_id: str,
        output_root: Path,
        event_plan: list[EventPlanEntry],
        method_config: dict[str, Any],
        protocol_config: dict[str, Any],
        latent_backend: RealVideoVAELatentBackend,
        vae_metadata: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        method = build_method_from_config(method_config)
        target_fpr = float(protocol_config["threshold_protocol"]["target_fpr_placeholder"])
        dev_records = self._run_event_subset(
            run_id,
            output_root,
            event_plan,
            method,
            method_config,
            target_fpr,
            {"dev"},
            SAMPLE_ROLES,
            None,
            latent_backend,
            vae_metadata,
        )
        calibration_records = self._run_event_subset(
            run_id,
            output_root,
            event_plan,
            method,
            method_config,
            target_fpr,
            {"calibration"},
            NEGATIVE_SAMPLE_ROLES,
            None,
            latent_backend,
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
            {"test"},
            SAMPLE_ROLES,
            threshold_record,
            latent_backend,
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
        vae_metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        event_score_records: list[dict[str, Any]] = []
        source_sample_cache: dict[tuple[str, str, str], Any] = {}
        embedded_sample_cache: dict[tuple[str, str, str, str], Any] = {}
        video_cache: dict[tuple[str, str], dict[str, Any]] = {}
        latent_copy_cache: dict[tuple[str, str], dict[str, str]] = {}
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
            embedded_key = (
                event_plan_entry.split,
                source_sample_role,
                source_sample_id,
                method_config["method_variant"],
            )
            if event_plan_entry.sample_role in {"watermarked_positive", "attacked_positive"}:
                working_sample = embedded_sample_cache.get(embedded_key)
                if working_sample is None:
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

            decoded_video_relpath = (
                Path("artifacts")
                / "videos"
                / "decoded"
                / method_config["method_variant"]
                / f"{event_artifact_digest}.npy"
            )
            decoded_video_metadata = self._cached_video_artifact(
                video_cache,
                working_sample,
                output_root,
                decoded_video_relpath,
                int(source_sample.mechanism_trace["video_fps"]),
            )

            attacked_sample = event_plan_entry.attack_object.apply(working_sample)
            attacked_video_metadata = None
            if event_plan_entry.attack_name != "no_attack":
                attacked_video_relpath = (
                    Path("artifacts")
                    / "videos"
                    / "attacked"
                    / event_plan_entry.attack_name
                    / f"{event_artifact_digest}.npy"
                )
                attacked_video_metadata = self._cached_video_artifact(
                    video_cache,
                    attacked_sample,
                    output_root,
                    attacked_video_relpath,
                    int(source_sample.mechanism_trace["video_fps"]),
                )
            reencoded_latent_relpath = (
                Path("artifacts")
                / "latents"
                / "reencoded"
                / event_plan_entry.attack_name
                / f"{event_artifact_digest}.npy"
            )
            reencoded_latent_metadata = self._cached_latent_copy(
                latent_copy_cache,
                attacked_sample,
                output_root,
                reencoded_latent_relpath,
            )
            detection_result = method.detect(attacked_sample, threshold_record)
            comparison_video_metadata = (
                attacked_video_metadata if attacked_video_metadata is not None else decoded_video_metadata
            )
            reference_video_path = output_root / source_sample.mechanism_trace["video_source_relpath"]
            comparison_video_path = output_root / comparison_video_metadata["video_relpath"]
            quality_metrics = build_quality_metrics_payload(
                reference_video_path,
                comparison_video_path,
            )
            temporal_metrics = build_temporal_metrics_payload(
                reference_video_path,
                comparison_video_path,
            )
            mechanism_trace = dict(attacked_sample.mechanism_trace or {})
            mechanism_trace.update(detection_result.mechanism_trace or {})
            mechanism_trace.update(
                {
                    "construction_phase": "real_video_vae_latent_probe",
                    "latent_backend_name": attacked_sample.latent_backend_name,
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
                    "encoded_latent_relpath": source_sample.mechanism_trace["encoded_latent_relpath"],
                    "encoded_latent_digest": source_sample.mechanism_trace["encoded_latent_digest"],
                    "watermarked_latent_relpath": None if watermarked_latent_metadata is None else watermarked_latent_metadata["latent_relpath"],
                    "watermarked_latent_digest": None if watermarked_latent_metadata is None else watermarked_latent_metadata["latent_digest"],
                    "decoded_video_relpath": decoded_video_metadata["video_relpath"],
                    "decoded_video_digest": decoded_video_metadata["video_digest"],
                    "attacked_video_relpath": None if attacked_video_metadata is None else attacked_video_metadata["video_relpath"],
                    "attacked_video_digest": None if attacked_video_metadata is None else attacked_video_metadata["video_digest"],
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
                "attack_params": attacked_sample.applied_attack_params or event_plan_entry.attack_params,
                "target_fpr": target_fpr,
                "threshold_id": None if threshold_record is None else threshold_record["threshold_id"],
                "input_artifact_trace": build_input_artifact_trace(attacked_sample),
                "latent_backend_name": attacked_sample.latent_backend_name,
                "latent_backend_status": attacked_sample.latent_backend_status,
                "latent_tensor_digest_random": attacked_sample.latent_tensor_digest_random,
                "latent_generation_seed_random": attacked_sample.latent_generation_seed_random,
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

    def _cached_video_artifact(
        self,
        cache: dict[tuple[str, str], dict[str, Any]],
        sample: Any,
        output_root: Path,
        artifact_relpath: Path,
        fps: int,
    ) -> dict[str, Any]:
        cache_key = (sample.latent_tensor_digest_random, artifact_relpath.as_posix())
        cached_metadata = cache.get(cache_key)
        if cached_metadata is not None:
            return cached_metadata
        metadata = materialize_video_artifact_from_latent(sample, output_root, artifact_relpath, fps)
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

    def _resolve_backend_config(self, runtime_profile: str, backend_config: dict[str, Any]) -> dict[str, Any]:
        resolved_backend_config = copy.deepcopy(backend_config)
        resolved_backend_config["runtime_profile"] = runtime_profile
        profile_key = {
            "tiny": "tiny_latent_shape",
            "smoke": "latent_shape",
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
        runtime_method_configs = [
            dict(method_configs[method_variant])
            for method_variant in ablation_config["method_variants"]
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
            runtime_method_config["method_status"] = "formal_real_video_vae_probe_scaffold"
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
        description="Run the governed placeholder stage-two real-video VAE latent probe.",
    )
    parser.add_argument("--run-mode", choices=("smoke", "formal"), default="smoke")
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--samples-per-role", type=int, default=None)
    parser.add_argument("--runtime-profile", default=None)
    parser.add_argument("--protocol-config", default=None)
    parser.add_argument("--backend-config", default=None)
    parser.add_argument("--attack-matrix", default=None)
    parser.add_argument("--ablation-config", default=None)
    parser.add_argument("--dataset-manifest", default=None)
    parser.add_argument("--runtime-config", default=None)
    args = parser.parse_args(argv)
    RealVideoVaeLatentRunner(ROOT).run(
        output_root=args.run_root,
        run_mode=args.run_mode,
        samples_per_role=args.samples_per_role,
        runtime_profile_override=args.runtime_profile,
        protocol_config_path=args.protocol_config,
        backend_config_path=args.backend_config,
        attack_matrix_path=args.attack_matrix,
        ablation_config_path=args.ablation_config,
        dataset_manifest_path=args.dataset_manifest,
        runtime_config_path=args.runtime_config,
    )


if __name__ == "__main__":
    main()
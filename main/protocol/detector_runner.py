"""
文件用途：提供阶段 0 的 protocol runner 骨架。
File purpose: Provide the stage-0 protocol runner scaffold.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

from main.backends.synthetic_latent_backend_random import SyntheticLatentBackendRandom
from main.core.schema import (
    NEGATIVE_SAMPLE_ROLES,
    SAMPLE_ROLES,
    build_input_artifact_trace,
    validate_event_score_record,
)
from main.methods.temporal_tubelet_watermark.method_placeholder import build_method_from_config
from main.protocol.calibrator import ThresholdCalibrator
from main.protocol.event_builder import EventPlanEntry


@dataclass(frozen=True)
class EventSubsetRuntimeProfile:
    """功能：记录单个 split 子集的运行时 profile。

    Runtime profile for one split-scoped event subset.

    Args:
        split: Governed split name.
        event_count: Number of materialized event records.
        source_artifact_seconds: Time spent materializing source artifacts.
        embedded_artifact_seconds: Time spent materializing embedded artifacts.
        attacked_artifact_seconds: Time spent materializing attacked artifacts.
        artifact_generation_seconds: Aggregate artifact-generation time.
        detection_seconds: Time spent in detector execution.
        total_seconds: Total subset runtime.

    Returns:
        None.
    """

    split: str
    event_count: int
    source_artifact_seconds: float
    embedded_artifact_seconds: float
    attacked_artifact_seconds: float
    artifact_generation_seconds: float
    detection_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class MethodVariantRuntimeProfile:
    """功能：记录单个方法变体的运行时 profile。

    Runtime profile for one governed method variant.

    Args:
        method_variant: Governed method variant.
        runtime_profile: Active runtime profile name.
        event_count: Number of materialized event records.
        threshold_calibration_seconds: Time spent in threshold calibration.
        artifact_generation_seconds: Aggregate artifact-generation time.
        detection_seconds: Aggregate detector execution time.
        total_seconds: Total method-variant runtime.
        split_profiles: Ordered split-level runtime profiles.

    Returns:
        None.
    """

    method_variant: str
    runtime_profile: str
    event_count: int
    threshold_calibration_seconds: float
    artifact_generation_seconds: float
    detection_seconds: float
    total_seconds: float
    split_profiles: tuple[EventSubsetRuntimeProfile, ...]


class ProtocolRunner:
    """功能：执行阶段 0 的单方法 protocol runtime。

    Stage-0 single-method protocol runner scaffold.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(
        self,
        latent_backend: Any | None = None,
        method_factory: Callable[[dict[str, Any]], Any] | None = None,
        threshold_calibrator: Any | None = None,
    ) -> None:
        """功能：构建可注入依赖的阶段 0 protocol runner。

        Build a stage-0 protocol runner with injectable backend, method factory,
        and threshold calibrator dependencies.

        Args:
            latent_backend: Optional latent backend implementation.
            method_factory: Optional method factory callable.
            threshold_calibrator: Optional threshold calibrator implementation.

        Returns:
            None.
        """
        resolved_latent_backend = (
            SyntheticLatentBackendRandom() if latent_backend is None else latent_backend
        )
        resolved_method_factory = (
            build_method_from_config if method_factory is None else method_factory
        )
        resolved_threshold_calibrator = (
            ThresholdCalibrator() if threshold_calibrator is None else threshold_calibrator
        )
        if not hasattr(resolved_latent_backend, "build_sample") or not callable(
            resolved_latent_backend.build_sample
        ):
            raise TypeError("latent_backend must provide a callable build_sample")
        if not callable(resolved_method_factory):
            raise TypeError("method_factory must be callable")
        if not hasattr(resolved_threshold_calibrator, "calibrate") or not callable(
            resolved_threshold_calibrator.calibrate
        ):
            raise TypeError(
                "threshold_calibrator must provide a callable calibrate"
            )

        self._latent_backend = resolved_latent_backend
        self._method_factory = resolved_method_factory
        self._threshold_calibrator = resolved_threshold_calibrator

    def run_method_variant(
        self,
        run_id: str,
        event_plan: list[EventPlanEntry],
        method_config: dict[str, Any],
        protocol_config: dict[str, Any],
        output_root: str | Path | None = None,
        return_runtime_profile: bool = False,
    ) -> (
        tuple[list[dict[str, Any]], dict[str, Any]]
        | tuple[list[dict[str, Any]], dict[str, Any], MethodVariantRuntimeProfile]
    ):
        """功能：运行阶段 0 的单方法执行闭环。

        Run the stage-0 protocol flow for one method variant.

        Args:
            run_id: Stable run identifier.
            event_plan: Shared event plan.
            method_config: Parsed method config.
            protocol_config: Parsed protocol config.
            output_root: Optional run root for artifact materialization.
            return_runtime_profile: Whether to append the runtime profile to the return tuple.

        Returns:
            A tuple of event score records and a threshold record, with an optional
            runtime profile when requested.
        """
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id must be a non-empty string")
        if not isinstance(event_plan, list) or not event_plan:
            raise ValueError("event_plan must be a non-empty list")
        if not isinstance(method_config, dict):
            raise TypeError("method_config must be a dictionary")
        if not isinstance(protocol_config, dict):
            raise TypeError("protocol_config must be a dictionary")

        if not isinstance(method_config.get("method_family"), str) or not method_config[
            "method_family"
        ]:
            raise ValueError("method_config method_family must be a non-empty string")
        if not isinstance(method_config.get("method_variant"), str) or not method_config[
            "method_variant"
        ]:
            raise ValueError("method_config method_variant must be a non-empty string")
        if output_root is not None and hasattr(self._latent_backend, "set_output_root"):
            self._latent_backend.set_output_root(Path(output_root))

        variant_start = perf_counter()
        method = self._method_factory(method_config)
        target_fpr = float(protocol_config["threshold_protocol"]["target_fpr_placeholder"])
        dev_records, dev_profile = self._run_event_subset(
            run_id,
            event_plan,
            method,
            method_config,
            target_fpr,
            allowed_splits={"dev"},
            allowed_sample_roles=SAMPLE_ROLES,
            threshold_record=None,
        )
        calibration_records, calibration_profile = self._run_event_subset(
            run_id,
            event_plan,
            method,
            method_config,
            target_fpr,
            allowed_splits={"calibration"},
            allowed_sample_roles=NEGATIVE_SAMPLE_ROLES,
            threshold_record=None,
        )
        threshold_start = perf_counter()
        threshold_record = self._threshold_calibrator.calibrate(
            run_id,
            method_config,
            protocol_config,
            calibration_records,
        )
        threshold_calibration_seconds = perf_counter() - threshold_start
        test_records, test_profile = self._run_event_subset(
            run_id,
            event_plan,
            method,
            method_config,
            target_fpr,
            allowed_splits={"test"},
            allowed_sample_roles=SAMPLE_ROLES,
            threshold_record=threshold_record,
        )
        split_profiles = (dev_profile, calibration_profile, test_profile)
        variant_runtime_profile = MethodVariantRuntimeProfile(
            method_variant=method_config["method_variant"],
            runtime_profile=str(protocol_config.get("runtime_profile", "smoke")),
            event_count=sum(profile.event_count for profile in split_profiles),
            threshold_calibration_seconds=round(threshold_calibration_seconds, 6),
            artifact_generation_seconds=round(
                sum(profile.artifact_generation_seconds for profile in split_profiles),
                6,
            ),
            detection_seconds=round(
                sum(profile.detection_seconds for profile in split_profiles),
                6,
            ),
            total_seconds=round(perf_counter() - variant_start, 6),
            split_profiles=split_profiles,
        )
        if return_runtime_profile:
            return (
                dev_records + calibration_records + test_records,
                threshold_record,
                variant_runtime_profile,
            )
        return dev_records + calibration_records + test_records, threshold_record

    def _run_event_subset(
        self,
        run_id: str,
        event_plan: list[EventPlanEntry],
        method: Any,
        method_config: dict[str, Any],
        target_fpr: float,
        allowed_splits: set[str],
        allowed_sample_roles: set[str],
        threshold_record: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], EventSubsetRuntimeProfile]:
        event_score_records: list[dict[str, Any]] = []
        source_sample_cache: dict[tuple[str, str, str], Any] = {}
        embedded_sample_cache: dict[tuple[str, str, str], Any] = {}
        split_name = next(iter(sorted(allowed_splits)))
        subset_start = perf_counter()
        source_artifact_seconds = 0.0
        embedded_artifact_seconds = 0.0
        attacked_artifact_seconds = 0.0
        detection_seconds = 0.0
        for event_plan_entry in event_plan:
            if event_plan_entry.split not in allowed_splits:
                continue
            if event_plan_entry.sample_role not in allowed_sample_roles:
                continue

            source_sample_id, source_sample_role = self._resolve_source_identity(
                event_plan_entry.sample_id,
                event_plan_entry.sample_role,
            )
            source_sample_key = (
                event_plan_entry.split,
                source_sample_role,
                source_sample_id,
            )
            latent_sample = source_sample_cache.get(source_sample_key)
            if latent_sample is None:
                source_sample_start = perf_counter()
                latent_sample = self._latent_backend.build_sample(
                    source_sample_id,
                    event_plan_entry.split,
                    source_sample_role,
                )
                source_artifact_seconds += perf_counter() - source_sample_start
                source_sample_cache[source_sample_key] = latent_sample
            working_sample = latent_sample
            if event_plan_entry.sample_role in {"watermarked_positive", "attacked_positive"}:
                working_sample = embedded_sample_cache.get(source_sample_key)
                if working_sample is None:
                    embedded_sample_start = perf_counter()
                    working_sample = method.embed(
                        latent_sample,
                        {
                            "event_sample_id": event_plan_entry.sample_id,
                            "event_sample_role": event_plan_entry.sample_role,
                        },
                    )
                    embedded_artifact_seconds += perf_counter() - embedded_sample_start
                    embedded_sample_cache[source_sample_key] = working_sample
            attacked_sample_start = perf_counter()
            attacked_sample = event_plan_entry.attack_object.apply(working_sample)
            attacked_artifact_seconds += perf_counter() - attacked_sample_start
            detection_start = perf_counter()
            detection_result = method.detect(attacked_sample, threshold_record)
            detection_seconds += perf_counter() - detection_start
            mechanism_trace = dict(attacked_sample.mechanism_trace or {})
            mechanism_trace.update(detection_result.mechanism_trace or {})
            record_random_fields = list(
                dict.fromkeys(
                    [
                        "latent_generation_seed_random",
                        "latent_tensor_digest_random",
                        *detection_result.random_fields,
                    ]
                )
            )
            event_score_record = {
                "run_id": run_id,
                "event_id": f"{method_config['method_variant']}:{event_plan_entry.event_id}",
                "sample_id": event_plan_entry.sample_id,
                "split": event_plan_entry.split,
                "sample_role": event_plan_entry.sample_role,
                "method_family": method_config["method_family"],
                "method_variant": method_config["method_variant"],
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
            }
            validate_event_score_record(event_score_record)
            event_score_records.append(event_score_record)
        artifact_generation_seconds = (
            source_artifact_seconds
            + embedded_artifact_seconds
            + attacked_artifact_seconds
        )
        return event_score_records, EventSubsetRuntimeProfile(
            split=split_name,
            event_count=len(event_score_records),
            source_artifact_seconds=round(source_artifact_seconds, 6),
            embedded_artifact_seconds=round(embedded_artifact_seconds, 6),
            attacked_artifact_seconds=round(attacked_artifact_seconds, 6),
            artifact_generation_seconds=round(artifact_generation_seconds, 6),
            detection_seconds=round(detection_seconds, 6),
            total_seconds=round(perf_counter() - subset_start, 6),
        )

    def _resolve_source_identity(self, sample_id: str, sample_role: str) -> tuple[str, str]:
        if sample_role == "attacked_negative":
            return sample_id.replace("attacked_negative", "clean_negative"), "clean_negative"
        if sample_role == "attacked_positive":
            return sample_id.replace("attacked_positive", "watermarked_positive"), "watermarked_positive"
        return sample_id, sample_role
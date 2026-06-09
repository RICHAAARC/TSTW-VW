"""
文件用途：构建阶段 3 trajectory statistic probe 的自定义方法工厂。
File purpose: Build the custom method factory for the stage-three trajectory statistic probe.
Module type: General module
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from main.core.schema import DetectionResult, LatentSample
from main.methods.temporal_tubelet_watermark.codebook import (
    build_codebook_config,
    build_tubelet_codebook,
)
from main.methods.temporal_tubelet_watermark.embedding import (
    build_partition_config_from_method_config,
)
from main.methods.temporal_tubelet_watermark.evidence import SyntheticProbeEvidenceExtractor
from main.methods.temporal_tubelet_watermark.fusion import build_disabled_evidence
from main.methods.temporal_tubelet_watermark.method import (
    SyntheticProbeWatermarkMethod,
    build_method_runtime_config,
)
from main.methods.temporal_tubelet_watermark.tubelet_partition import build_tubelet_descriptors
from main.trajectory.trajectory_backend_registry import build_trajectory_backend_from_config
from main.trajectory.trajectory_controls import (
    SUPPORTED_TRAJECTORY_CONTROL_KINDS,
    apply_trajectory_control,
)
from main.trajectory.trajectory_runtime import measure_trajectory_runtime
from main.trajectory.trajectory_statistic import build_velocity_projection_statistic


def build_trajectory_probe_method_factory(
    trajectory_backend_config: dict[str, Any],
) -> Callable[[dict[str, Any]], "TrajectoryProbeWatermarkMethod"]:
    """功能：构建阶段 3 自定义 method factory。

    Build the custom method factory for the stage-three probe.

    Args:
        trajectory_backend_config: Shared trajectory backend config.

    Returns:
        A callable that materializes `TrajectoryProbeWatermarkMethod`.
    """
    if not isinstance(trajectory_backend_config, dict):
        raise TypeError("trajectory_backend_config must be a dictionary")

    def _factory(method_config: dict[str, Any]) -> TrajectoryProbeWatermarkMethod:
        return TrajectoryProbeWatermarkMethod(method_config, trajectory_backend_config)

    return _factory


class TrajectoryProbeWatermarkMethod:
    """功能：提供阶段 3 detector-side trajectory statistic 的方法运行时。

    Method runtime for detector-side stage-three trajectory statistics.

    Args:
        method_config: Parsed stage-three method config.
        trajectory_backend_config: Shared trajectory backend config.

    Returns:
        None.
    """

    def __init__(
        self,
        method_config: dict[str, Any],
        trajectory_backend_config: dict[str, Any],
    ) -> None:
        if not isinstance(method_config, dict):
            raise TypeError("method_config must be a dictionary")
        if not isinstance(trajectory_backend_config, dict):
            raise TypeError("trajectory_backend_config must be a dictionary")

        self._method_config = dict(method_config)
        self._enabled_evidence = {
            "tubelet": bool(method_config.get("enable_tubelet", False))
            or bool(method_config.get("enable_frame_prc", False)),
            "sync": bool(method_config.get("enable_sync", False)),
            "trajectory": bool(method_config.get("enable_trajectory", False)),
        }
        self._base_method_config = self._build_base_method_config(method_config)
        self._base_runtime_config = build_method_runtime_config(self._base_method_config)
        self._embed_delegate = SyntheticProbeWatermarkMethod(self._base_runtime_config)
        base_method_variant = (
            self._base_runtime_config.base_method_variant
            or self._base_runtime_config.method_variant
        )
        self._base_evidence_extractor = SyntheticProbeEvidenceExtractor(
            base_method_variant,
            self._base_method_config,
            self._base_runtime_config.enabled_evidence,
            self._base_runtime_config.fusion_rule,
        )
        self._trajectory_backend_config = self._resolve_trajectory_backend_config(
            method_config,
            trajectory_backend_config,
        )
        self._trajectory_backend = build_trajectory_backend_from_config(
            self._trajectory_backend_config
        )

    def embed(self, sample: LatentSample, payload: dict[str, Any]) -> LatentSample:
        """功能：复用阶段 1 projection-margin embedding。

        Reuse the stage-one projection-margin embedding path.

        Args:
            sample: Input latent sample.
            payload: Runtime payload container.

        Returns:
            The embedded latent sample.
        """
        return self._embed_delegate.embed(sample, payload)

    def detect(
        self,
        sample: LatentSample,
        threshold_record: dict[str, Any] | None,
    ) -> DetectionResult:
        """功能：在阶段 1 base evidence 上叠加阶段 3 trajectory statistic。

        Layer the stage-three trajectory statistic on top of the stage-one base evidence.

        Args:
            sample: Input latent sample.
            threshold_record: Optional threshold record.

        Returns:
            A `DetectionResult` instance.
        """
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")

        evidence_scores, mechanism_trace = self._base_evidence_extractor.extract(sample)
        mechanism_trace = dict(mechanism_trace)
        if self._enabled_evidence["trajectory"]:
            trajectory_score, trajectory_trace = self._build_trajectory_score(sample)
            evidence_scores["S_traj"] = trajectory_score
            mechanism_trace.update(trajectory_trace)
        else:
            mechanism_trace.update(
                {
                    "trajectory_source_kind": None,
                    "trajectory_statistic_kind": None,
                    "trajectory_time_grid": None,
                    "trajectory_valid_segment_ratio": None,
                    "trajectory_projection_count": None,
                    "S_traj_velocity": None,
                    "S_traj_displacement": None,
                    "trajectory_curvature_residual": None,
                    "trajectory_backend_status": "trajectory_disabled",
                    "trajectory_fail_reason": "trajectory_disabled",
                    "trajectory_control_kind": None,
                    "trajectory_control_scores": {},
                    "trajectory_runtime_ms": None,
                    "trajectory_reconstruction_ms": None,
                    "trajectory_scoring_ms": None,
                }
            )
        evidence_scores["S_final"] = self._build_final_score(evidence_scores)
        disabled_evidence = build_disabled_evidence(self._enabled_evidence)
        return DetectionResult(
            evidence_scores=evidence_scores,
            disabled_evidence=disabled_evidence,
            decision=self._build_decision(evidence_scores, threshold_record),
            failure_reason=None,
            mechanism_trace=mechanism_trace,
            placeholder_fields=self._build_placeholder_fields(disabled_evidence),
            random_fields=[],
        )

    def detect_batch(
        self,
        samples: list[LatentSample],
        threshold_record: dict[str, Any] | None,
    ) -> list[DetectionResult]:
        """功能：按序运行批量检测。

        Run batch detection sequentially for the stage-three scaffold.

        Args:
            samples: Input latent samples.
            threshold_record: Optional threshold record.

        Returns:
            A list of `DetectionResult` instances.
        """
        if not isinstance(samples, list):
            raise TypeError("samples must be a list")
        return [self.detect(sample, threshold_record) for sample in samples]

    def _build_base_method_config(self, method_config: dict[str, Any]) -> dict[str, Any]:
        base_method_config = dict(method_config)
        base_variant = (
            "tubelet_sync"
            if bool(method_config.get("enable_sync", False))
            else "tubelet_only"
        )
        base_method_config["method_variant"] = base_variant
        base_method_config["base_method_variant"] = base_variant
        base_method_config["enable_trajectory"] = False
        base_method_config["fusion_rule"] = (
            "sync_rescue_fusion"
            if bool(method_config.get("enable_sync", False))
            else "tubelet_score_only"
        )
        return base_method_config

    def _resolve_trajectory_backend_config(
        self,
        method_config: dict[str, Any],
        trajectory_backend_config: dict[str, Any],
    ) -> dict[str, Any]:
        resolved_config = dict(trajectory_backend_config)
        if "trajectory_source_kind" in method_config:
            resolved_config["trajectory_source_kind"] = method_config[
                "trajectory_source_kind"
            ]
        if "trajectory_time_grid" in method_config:
            resolved_config["trajectory_time_grid"] = list(
                method_config["trajectory_time_grid"]
            )
        if "trajectory_statistic_kind" in method_config:
            resolved_config["trajectory_statistic_kind"] = method_config[
                "trajectory_statistic_kind"
            ]
        if "trajectory_control_kind" in method_config:
            resolved_config["trajectory_control_kind"] = method_config[
                "trajectory_control_kind"
            ]
        return resolved_config

    def _build_trajectory_score(
        self,
        sample: LatentSample,
    ) -> tuple[float, dict[str, Any]]:
        partition_config = build_partition_config_from_method_config(
            self._base_method_config
        )
        tubelet_descriptors = build_tubelet_descriptors(
            sample.latent_shape,
            partition_config,
        )
        codebook = build_tubelet_codebook(
            sample.sample_id,
            tubelet_descriptors,
            len(tubelet_descriptors[0].flat_indices),
            build_codebook_config(),
            enable_sync=bool(self._base_method_config.get("enable_sync", False)),
        )
        directions = dict(codebook.directions)
        codes = (
            dict(codebook.combined_codes)
            if bool(self._base_method_config.get("enable_sync", False))
            else dict(codebook.payload_codes)
        )

        observation_holder: dict[str, Any] = {}
        control_kind = str(
            self._trajectory_backend_config.get("trajectory_control_kind", "none")
        )

        def _reconstruct() -> Any:
            observation_holder["observation"] = self._trajectory_backend.build_observation(
                sample
            )
            return observation_holder["observation"]

        def _score() -> Any:
            observation = observation_holder["observation"]
            controlled_observation, controlled_directions, controlled_codes = (
                apply_trajectory_control(
                    observation,
                    directions,
                    codes,
                    sample.sample_id,
                    control_kind,
                )
            )
            return build_velocity_projection_statistic(
                controlled_observation,
                tubelet_descriptors,
                controlled_directions,
                controlled_codes,
            )

        observation, statistic_result, runtime_summary = measure_trajectory_runtime(
            _reconstruct,
            _score,
        )
        control_scores: dict[str, float] = {}
        for audit_control_kind in SUPPORTED_TRAJECTORY_CONTROL_KINDS:
            if audit_control_kind == "none":
                continue
            audit_observation, audit_directions, audit_codes = apply_trajectory_control(
                observation,
                directions,
                codes,
                sample.sample_id,
                audit_control_kind,
            )
            audit_result = build_velocity_projection_statistic(
                audit_observation,
                tubelet_descriptors,
                audit_directions,
                audit_codes,
            )
            control_scores[audit_control_kind] = audit_result.S_traj_velocity

        source_kind = observation.source_kind
        source_status = (
            "formal_candidate_runtime"
            if source_kind == "stage2_frozen_endpoint_replay"
            else "surrogate_runtime"
        )
        trajectory_trace = {
            "trajectory_source_kind": observation.source_kind,
            "formal_trajectory_source_status": (
                "candidate_ready"
                if source_kind == "stage2_frozen_endpoint_replay"
                else "not_formal_source"
            ),
            "trajectory_source_provenance_digest": self._trajectory_backend_config.get(
                "stage2_frozen_baseline_manifest_digest"
            ),
            "stage2_frozen_baseline_manifest_digest": self._trajectory_backend_config.get(
                "stage2_frozen_baseline_manifest_digest"
            ),
            "trajectory_statistic_kind": str(
                self._trajectory_backend_config.get(
                    "trajectory_statistic_kind",
                    "velocity_projection",
                )
            ),
            "trajectory_time_grid": list(observation.time_grid),
            "trajectory_valid_segment_ratio": statistic_result.trajectory_valid_segment_ratio,
            "trajectory_projection_count": statistic_result.trajectory_projection_count,
            "S_traj_velocity": statistic_result.S_traj_velocity,
            "S_traj_displacement": statistic_result.S_traj_displacement,
            "trajectory_curvature_residual": statistic_result.trajectory_curvature_residual,
            "trajectory_backend_status": source_status,
            "trajectory_fail_reason": None,
            "trajectory_control_kind": control_kind,
            "trajectory_control_scores": control_scores,
            "trajectory_runtime_ms": runtime_summary.trajectory_runtime_ms,
            "trajectory_reconstruction_ms": runtime_summary.trajectory_reconstruction_ms,
            "trajectory_scoring_ms": runtime_summary.trajectory_scoring_ms,
        }
        return statistic_result.S_traj_velocity, trajectory_trace

    def _build_final_score(self, evidence_scores: dict[str, float | None]) -> float:
        baseline_score = (
            0.0 if evidence_scores["S_final"] is None else float(evidence_scores["S_final"])
        )
        if not self._enabled_evidence["trajectory"]:
            return round(baseline_score, 6)

        trajectory_score = (
            0.0 if evidence_scores["S_traj"] is None else float(evidence_scores["S_traj"])
        )
        if not self._enabled_evidence["tubelet"] and not self._enabled_evidence["sync"]:
            return round(trajectory_score, 6)

        trajectory_weight = float(self._method_config.get("trajectory_weight", 0.25))
        return round(
            ((1.0 - trajectory_weight) * baseline_score)
            + (trajectory_weight * trajectory_score),
            6,
        )

    def _build_decision(
        self,
        evidence_scores: dict[str, float | None],
        threshold_record: dict[str, Any] | None,
    ) -> bool:
        if threshold_record is None:
            return False
        threshold_value = threshold_record.get("threshold_value")
        if not isinstance(threshold_value, (int, float)):
            raise ValueError("threshold_record threshold_value must be numeric")
        final_score = evidence_scores["S_final"]
        if final_score is None:
            return False
        return float(final_score) >= float(threshold_value)

    def _build_placeholder_fields(self, disabled_evidence: list[str]) -> list[str]:
        placeholder_fields: list[str] = []
        if "trajectory" in disabled_evidence:
            placeholder_fields.append("trajectory_observation_placeholder")
        return placeholder_fields

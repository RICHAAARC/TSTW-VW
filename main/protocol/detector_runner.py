"""
文件用途：提供阶段 0 的 protocol runner 骨架。
File purpose: Provide the stage-0 protocol runner scaffold.
Module type: General module
"""

from __future__ import annotations

from typing import Any

from main.backends.synthetic_latent_backend_random import SyntheticLatentBackendRandom
from main.core.schema import METHOD_FAMILY_NAME, NEGATIVE_SAMPLE_ROLES, SAMPLE_ROLES, validate_event_score_record
from main.methods.temporal_tubelet_watermark.method_placeholder import build_method_from_config
from main.protocol.calibrator import ThresholdCalibrator
from main.protocol.event_builder import EventPlanEntry


class ProtocolRunner:
    """功能：执行阶段 0 的单方法 protocol runtime。

    Stage-0 single-method protocol runner scaffold.

    Args:
        None.

    Returns:
        None.
    """

    def __init__(self) -> None:
        self._latent_backend = SyntheticLatentBackendRandom()
        self._threshold_calibrator = ThresholdCalibrator()

    def run_method_variant(
        self,
        run_id: str,
        event_plan: list[EventPlanEntry],
        method_config: dict[str, Any],
        protocol_config: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """功能：运行阶段 0 的单方法执行闭环。

        Run the stage-0 protocol flow for one method variant.

        Args:
            run_id: Stable run identifier.
            event_plan: Shared event plan.
            method_config: Parsed method config.
            protocol_config: Parsed protocol config.

        Returns:
            A tuple of event score records and a threshold record.
        """
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id must be a non-empty string")
        if not isinstance(event_plan, list) or not event_plan:
            raise ValueError("event_plan must be a non-empty list")
        if not isinstance(method_config, dict):
            raise TypeError("method_config must be a dictionary")
        if not isinstance(protocol_config, dict):
            raise TypeError("protocol_config must be a dictionary")

        method = build_method_from_config(method_config)
        target_fpr = float(protocol_config["threshold_protocol"]["target_fpr_placeholder"])
        dev_records = self._run_event_subset(
            run_id,
            event_plan,
            method,
            method_config,
            target_fpr,
            allowed_splits={"dev"},
            allowed_sample_roles=SAMPLE_ROLES,
            threshold_record=None,
        )
        calibration_records = self._run_event_subset(
            run_id,
            event_plan,
            method,
            method_config,
            target_fpr,
            allowed_splits={"calibration"},
            allowed_sample_roles=NEGATIVE_SAMPLE_ROLES,
            threshold_record=None,
        )
        threshold_record = self._threshold_calibrator.calibrate(
            run_id,
            method_config,
            protocol_config,
            calibration_records,
        )
        test_records = self._run_event_subset(
            run_id,
            event_plan,
            method,
            method_config,
            target_fpr,
            allowed_splits={"test"},
            allowed_sample_roles=SAMPLE_ROLES,
            threshold_record=threshold_record,
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
    ) -> list[dict[str, Any]]:
        event_score_records: list[dict[str, Any]] = []
        for event_plan_entry in event_plan:
            if event_plan_entry.split not in allowed_splits:
                continue
            if event_plan_entry.sample_role not in allowed_sample_roles:
                continue

            latent_sample = self._latent_backend.build_sample(
                event_plan_entry.sample_id,
                event_plan_entry.split,
                event_plan_entry.sample_role,
            )
            attacked_sample = event_plan_entry.attack_object.apply(latent_sample)
            detection_result = method.detect(attacked_sample, threshold_record)
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
                "method_family": METHOD_FAMILY_NAME,
                "method_variant": method_config["method_variant"],
                "attack_name": event_plan_entry.attack_name,
                "attack_params": event_plan_entry.attack_params,
                "target_fpr": target_fpr,
                "threshold_id": None if threshold_record is None else threshold_record["threshold_id"],
                "latent_backend_name": attacked_sample.latent_backend_name,
                "latent_backend_status": attacked_sample.latent_backend_status,
                "latent_tensor_digest_random": attacked_sample.latent_tensor_digest_random,
                "latent_generation_seed_random": attacked_sample.latent_generation_seed_random,
                "evidence_scores": detection_result.evidence_scores,
                "disabled_evidence": detection_result.disabled_evidence,
                "decision": detection_result.decision,
                "failure_reason": detection_result.failure_reason,
                "placeholder_fields": detection_result.placeholder_fields,
                "random_fields": record_random_fields,
            }
            validate_event_score_record(event_score_record)
            event_score_records.append(event_score_record)
        return event_score_records
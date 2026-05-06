"""
文件用途：验证 ProtocolRunner 的依赖注入与方法家族解耦行为。
File purpose: Validate ProtocolRunner dependency injection and method-family decoupling.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from main.attacks.identity_attack_placeholder import IdentityAttackPlaceholder
from main.core.registry import load_json_config
from main.core.schema import DetectionResult, LatentSample
from main.protocol.detector_runner import ProtocolRunner
from main.protocol.event_builder import EventPlanEntry


ROOT = Path(__file__).resolve().parents[1]


class FakeLatentBackend:
    """Provide a deterministic fake backend for dependency-injection tests."""

    def build_sample(self, sample_id: str, split: str, sample_role: str) -> LatentSample:
        return LatentSample(
            sample_id=sample_id,
            split=split,
            sample_role=sample_role,
            latent_shape=(1, 1, 1, 1),
            latent_tensor_digest_random=f"fake_digest_{sample_id}",
            latent_generation_seed_random=7001,
            latent_backend_name="fake_latent_backend",
            latent_backend_status="fake",
        )


class FakeWatermarkMethod:
    """Provide a deterministic fake method for dependency-injection tests."""

    def embed(self, sample: LatentSample, payload: dict[str, Any]) -> LatentSample:
        del payload
        return sample

    def detect(
        self,
        sample: LatentSample,
        threshold_record: dict[str, Any] | None,
    ) -> DetectionResult:
        final_score = 0.9 if sample.sample_role.endswith("positive") else 0.1
        decision = False
        if threshold_record is not None:
            decision = final_score >= float(threshold_record["threshold_value"])
        return DetectionResult(
            evidence_scores={
                "S_tubelet": None,
                "S_sync": None,
                "S_traj": None,
                "S_final": final_score,
            },
            disabled_evidence=["tubelet", "sync", "trajectory"],
            decision=decision,
            failure_reason=None,
            placeholder_fields=[
                "watermark_payload_placeholder",
                "sync_alignment_placeholder",
                "trajectory_observation_placeholder",
            ],
            random_fields=[],
        )

    def detect_batch(
        self,
        samples: list[LatentSample],
        threshold_record: dict[str, Any] | None,
    ) -> list[DetectionResult]:
        return [self.detect(sample, threshold_record) for sample in samples]


def _build_minimal_event_plan() -> list[EventPlanEntry]:
    attack_object = IdentityAttackPlaceholder(
        attack_name="identity_attack_placeholder",
        attack_params={},
    )
    return [
        EventPlanEntry(
            event_id="event_dev_clean_negative",
            sample_id="sample_dev_clean_negative_000001",
            split="dev",
            sample_role="clean_negative",
            attack_name=attack_object.attack_name,
            attack_params=attack_object.attack_params,
            attack_object=attack_object,
        ),
        EventPlanEntry(
            event_id="event_calibration_clean_negative",
            sample_id="sample_calibration_clean_negative_000001",
            split="calibration",
            sample_role="clean_negative",
            attack_name=attack_object.attack_name,
            attack_params=attack_object.attack_params,
            attack_object=attack_object,
        ),
        EventPlanEntry(
            event_id="event_calibration_attacked_negative",
            sample_id="sample_calibration_attacked_negative_000001",
            split="calibration",
            sample_role="attacked_negative",
            attack_name=attack_object.attack_name,
            attack_params=attack_object.attack_params,
            attack_object=attack_object,
        ),
        EventPlanEntry(
            event_id="event_test_clean_negative",
            sample_id="sample_test_clean_negative_000001",
            split="test",
            sample_role="clean_negative",
            attack_name=attack_object.attack_name,
            attack_params=attack_object.attack_params,
            attack_object=attack_object,
        ),
        EventPlanEntry(
            event_id="event_test_watermarked_positive",
            sample_id="sample_test_watermarked_positive_000001",
            split="test",
            sample_role="watermarked_positive",
            attack_name=attack_object.attack_name,
            attack_params=attack_object.attack_params,
            attack_object=attack_object,
        ),
    ]


def test_protocol_runner_default_constructor_runs_stage0_slice() -> None:
    """Validate that the default ProtocolRunner still runs the stage-0 slice.

    Args:
        None.

    Returns:
        None.
    """
    runner = ProtocolRunner()
    method_config = load_json_config(
        ROOT / "configs" / "method" / "random_score_detector_random.json"
    )
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "protocol_skeleton.json"
    )

    event_score_records, threshold_record = runner.run_method_variant(
        "protocol_runner_default_run",
        _build_minimal_event_plan(),
        method_config,
        protocol_config,
    )

    assert event_score_records
    assert threshold_record["method_variant"] == "random_score_detector_random"


def test_protocol_runner_supports_fake_backend() -> None:
    """Validate that ProtocolRunner can run with an injected backend.

    Args:
        None.

    Returns:
        None.
    """
    runner = ProtocolRunner(latent_backend=FakeLatentBackend())
    method_config = load_json_config(
        ROOT / "configs" / "method" / "random_score_detector_random.json"
    )
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "protocol_skeleton.json"
    )

    event_score_records, _ = runner.run_method_variant(
        "protocol_runner_fake_backend_run",
        _build_minimal_event_plan(),
        method_config,
        protocol_config,
    )

    assert event_score_records
    assert {record["latent_backend_name"] for record in event_score_records} == {
        "fake_latent_backend"
    }
    assert {record["input_artifact_trace"]["backend_name"] for record in event_score_records} == {
        "fake_latent_backend"
    }


def test_protocol_runner_supports_fake_method_factory_and_dynamic_method_family() -> None:
    """Validate fake method factory injection and method-family decoupling.

    Args:
        None.

    Returns:
        None.
    """
    captured_method_families: list[str] = []

    def fake_method_factory(method_config: dict[str, Any]) -> FakeWatermarkMethod:
        captured_method_families.append(method_config["method_family"])
        return FakeWatermarkMethod()

    runner = ProtocolRunner(
        latent_backend=FakeLatentBackend(),
        method_factory=fake_method_factory,
    )
    method_config = {
        "method_family": "generic_probe_family",
        "method_variant": "empty_watermark_method_placeholder",
        "method_status": "placeholder",
        "enabled_evidence": {
            "tubelet": False,
            "sync": False,
            "trajectory": False,
        },
        "fusion_rule": "constant_zero_fusion_placeholder",
    }
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "protocol_skeleton.json"
    )

    event_score_records, threshold_record = runner.run_method_variant(
        "protocol_runner_fake_method_run",
        _build_minimal_event_plan(),
        method_config,
        protocol_config,
    )

    assert captured_method_families == ["generic_probe_family"]
    assert {record["method_family"] for record in event_score_records} == {
        "generic_probe_family"
    }
    assert threshold_record["method_family"] == "generic_probe_family"


@pytest.mark.parametrize(
    "broken_method_config",
    [
        {
            "method_variant": "empty_watermark_method_placeholder",
            "method_status": "placeholder",
            "enabled_evidence": {
                "tubelet": False,
                "sync": False,
                "trajectory": False,
            },
            "fusion_rule": "constant_zero_fusion_placeholder",
        },
        {
            "method_family": "",
            "method_variant": "empty_watermark_method_placeholder",
            "method_status": "placeholder",
            "enabled_evidence": {
                "tubelet": False,
                "sync": False,
                "trajectory": False,
            },
            "fusion_rule": "constant_zero_fusion_placeholder",
        },
    ],
)
def test_protocol_runner_rejects_missing_or_empty_method_family(
    broken_method_config: dict[str, Any],
) -> None:
    """Validate that missing or empty method_family is rejected.

    Args:
        broken_method_config: Broken method configuration.

    Returns:
        None.
    """
    runner = ProtocolRunner(
        latent_backend=FakeLatentBackend(),
        method_factory=lambda _: FakeWatermarkMethod(),
    )
    protocol_config = load_json_config(
        ROOT / "configs" / "protocol" / "protocol_skeleton.json"
    )

    with pytest.raises(ValueError, match="method_family"):
        runner.run_method_variant(
            "protocol_runner_broken_method_family_run",
            _build_minimal_event_plan(),
            broken_method_config,
            protocol_config,
        )
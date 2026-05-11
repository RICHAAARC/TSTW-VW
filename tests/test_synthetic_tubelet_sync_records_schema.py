"""
文件用途：验证 stage-one event record 中的 mechanism_trace 与正式机制字段语义。
File purpose: Validate stage-one event records for mechanism-trace and formal mechanism fields.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.synthetic_tubelet_sync_probe.ablation_runner import AblationRunner
from main.core.records import RecordWriter


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.smoke
def test_synthetic_tubelet_sync_event_records_include_mechanism_trace(tmp_path: Path) -> None:
    """Validate that stage-one event records include the governed mechanism trace.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2, runtime_profile_override="tiny")
    event_score_records = RecordWriter(output_root).read_event_score_records()

    assert event_score_records
    for event_score_record in event_score_records:
        mechanism_trace = event_score_record["mechanism_trace"]
        assert isinstance(mechanism_trace, dict)
        assert event_score_record["base_method_variant"]
        assert isinstance(event_score_record["derived_variant"], bool)
        assert event_score_record["tubelet_length"] == mechanism_trace["tubelet_length"]
        if event_score_record["derived_variant"]:
            assert event_score_record["base_method_variant"] == "tubelet_only"
            assert event_score_record["ablation_axis"] == "tubelet_length"
        else:
            assert event_score_record["base_method_variant"] == event_score_record["method_variant"]
            assert event_score_record["ablation_axis"] is None
        assert mechanism_trace["construction_phase"] == "synthetic_tubelet_sync_probe"
        assert mechanism_trace["latent_backend_name"] == "synthetic_video_latent"
        assert mechanism_trace["latent_artifact_digest"] == event_score_record["latent_tensor_digest_random"]
        assert mechanism_trace["latent_artifact_relpath"].endswith(".npy")
        assert set(event_score_record["evidence_scores"].keys()) == {
            "S_tubelet",
            "S_sync",
            "S_traj",
            "S_final",
        }
        assert event_score_record["evidence_scores"]["S_traj"] is None
        assert "trajectory" in event_score_record["disabled_evidence"]
        assert all(
            field_name not in event_score_record["random_fields"]
            for field_name in ("S_tubelet", "S_sync", "S_traj", "S_final")
        )


@pytest.mark.smoke
def test_synthetic_tubelet_sync_records_do_not_inline_tensor_payload(tmp_path: Path) -> None:
    """Validate that event records reference tensor artifacts instead of inlining payloads.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=1, runtime_profile_override="tiny")
    event_score_record = RecordWriter(output_root).read_event_score_records()[0]

    assert "latent_tensor_values" not in event_score_record
    assert "tensor_values" not in event_score_record["mechanism_trace"]

"""
文件用途：验证阶段 3 trajectory statistic probe 的 smoke records schema。
File purpose: Validate the smoke records schema for the stage-three trajectory statistic probe.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_statistic_probe.output_layout import (
    build_trajectory_statistic_probe_output_paths,
)
from experiments.trajectory_statistic_probe.runner import TrajectoryStatisticProbeRunner
from main.core.records import RecordWriter
from main.core.schema import validate_event_score_record, validate_threshold_record


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


@pytest.mark.smoke
def test_trajectory_probe_records_schema_smoke(tmp_path: Path) -> None:
    """Validate that the stage-three smoke run writes governed records and tables.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "trajectory_statistic_probe_run"
    TrajectoryStatisticProbeRunner(ROOT).run(
        output_root,
        samples_per_role=2,
        runtime_profile_override="smoke",
    )

    record_writer = RecordWriter(output_root)
    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    output_paths = build_trajectory_statistic_probe_output_paths(output_root)
    run_manifest = json.loads(output_paths.run_manifest_path.read_text(encoding="utf-8"))
    mechanism_decision = json.loads(
        output_paths.trajectory_mechanism_decision_path.read_text(encoding="utf-8")
    )

    assert event_score_records
    assert threshold_records
    assert output_paths.trajectory_ablation_table_path.exists()
    assert output_paths.score_correlation_matrix_path.exists()
    assert output_paths.trajectory_gain_by_attack_path.exists()
    assert output_paths.trajectory_control_table_path.exists()
    assert output_paths.runtime_breakdown_path.exists()
    assert output_paths.trajectory_probe_report_path.exists()

    trajectory_enabled_variants = {
        "traj_only",
        "tubelet_traj",
        "tubelet_sync_trajectory_fusion",
    }
    trajectory_disabled_variants = {"tubelet_only", "tubelet_sync"}
    for event_score_record in event_score_records:
        validate_event_score_record(event_score_record)
        mechanism_trace = event_score_record["mechanism_trace"]
        assert mechanism_trace["construction_phase"] == "trajectory_statistic_probe"
        if event_score_record["method_variant"] in trajectory_enabled_variants:
            assert event_score_record["evidence_scores"]["S_traj"] is not None
            assert mechanism_trace["trajectory_source_kind"] == "latent_interpolation_surrogate"
            assert mechanism_trace["trajectory_statistic_kind"] == "velocity_projection"
            assert mechanism_trace["trajectory_time_grid"] == [0.0, 0.25, 0.5, 0.75, 1.0]
        if event_score_record["method_variant"] in trajectory_disabled_variants:
            assert event_score_record["evidence_scores"]["S_traj"] is None
            assert event_score_record["placeholder_fields"] == ["trajectory_observation_placeholder"]

    for threshold_record in threshold_records:
        validate_threshold_record(threshold_record)

    assert run_manifest["construction_phase"] == "trajectory_statistic_probe"
    assert mechanism_decision["Stage3ImplementationDecision"] == "PASS"
    assert mechanism_decision["Stage3MechanismDecision"] == "DEFERRED_BY_STAGE2"
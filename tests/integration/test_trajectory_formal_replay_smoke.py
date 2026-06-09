"""
文件用途：验证 trajectory statistic probe 的冻结 baseline 与 replay 闭环。
File purpose: Validate the frozen-baseline and replay loop for the trajectory statistic probe.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.trajectory_statistic_probe.formal_replay_runner import (
    FormalReplayRequest,
    run_trajectory_statistic_formal_replay,
)
from experiments.trajectory_statistic_probe.output_layout import (
    build_trajectory_statistic_probe_output_paths,
)
from experiments.trajectory_statistic_probe.real_video_vae_latent_frozen_baseline_loader import (
    load_real_video_vae_latent_frozen_baseline,
)
from experiments.trajectory_statistic_probe.runner import TrajectoryStatisticProbeRunner
from main.core.records import RecordWriter


ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.integration, pytest.mark.smoke]


def _write_passing_mechanism_decision(baseline_root: Path) -> None:
    decision_path = baseline_root / "artifacts" / "stage2_mechanism_decision.json"
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(
        json.dumps(
            {
                "Stage2ImplementationDecision": "PASS",
                "Stage2MechanismDecision": "PASS",
                "Stage2MechanismBlockingReasons": [],
                "stage2_mechanism_protocol": "aligned_payload_safety",
                "sync_confidence_gate_rule": "aligned_payload_safety_gate",
                "negative_rescue_over_threshold_count": 0,
                "NextAllowedStageByMechanism": "trajectory_statistic_probe",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _build_frozen_baseline_root(tmp_path: Path) -> Path:
    baseline_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_frozen_baseline"
    TrajectoryStatisticProbeRunner(ROOT).run(
        baseline_root,
        samples_per_role=1,
        runtime_profile_override="smoke",
        method_variants=["tubelet_only", "tubelet_sync"],
    )
    _write_passing_mechanism_decision(baseline_root)
    return baseline_root


def test_frozen_baseline_loader_accepts_passed_package(tmp_path: Path) -> None:
    """验证 loader 能将通过 gate 的冻结 baseline 判定为 PASSED。"""
    baseline_root = _build_frozen_baseline_root(tmp_path)

    frozen_package = load_real_video_vae_latent_frozen_baseline(baseline_root)

    assert frozen_package.frozen_baseline_manifest["Stage2DependencyStatus"] == "PASSED"
    assert frozen_package.frozen_baseline_manifest["Stage2FrozenBaselineManifest"] == "PASSED"
    assert frozen_package.event_score_records
    assert all(
        record["evidence_scores"]["S_traj"] is None
        for record in frozen_package.event_score_records
    )


def test_frozen_baseline_loader_rejects_non_null_s_traj(tmp_path: Path) -> None:
    """验证 baseline records 中出现 S_traj 时会被拒绝。"""
    baseline_root = _build_frozen_baseline_root(tmp_path)
    record_writer = RecordWriter(baseline_root)
    records = record_writer.read_event_score_records()
    records[0]["evidence_scores"]["S_traj"] = 0.1
    record_writer.write_event_score_records(records)

    with pytest.raises(ValueError, match="baseline_s_traj_must_be_null"):
        load_real_video_vae_latent_frozen_baseline(baseline_root)


def test_formal_replay_writes_required_artifacts_and_surrogate_blocks_pass(tmp_path: Path) -> None:
    """验证 replay 会写出完整产物, 且 surrogate source 不会形成机制 PASS。"""
    baseline_root = _build_frozen_baseline_root(tmp_path)
    output_root = tmp_path / "outputs" / "runs" / "trajectory_statistic_probe_replay"

    result = run_trajectory_statistic_formal_replay(
        FormalReplayRequest(
            repository_root=ROOT,
            output_root=output_root,
            frozen_baseline_root=baseline_root,
            samples_per_role=1,
            runtime_profile="smoke",
        )
    )
    output_paths = build_trajectory_statistic_probe_output_paths(output_root)
    decision = result.mechanism_decision

    assert output_paths.trajectory_ablation_table_path.exists()
    assert output_paths.score_correlation_matrix_path.exists()
    assert output_paths.trajectory_gain_by_attack_path.exists()
    assert output_paths.trajectory_control_table_path.exists()
    assert output_paths.runtime_breakdown_path.exists()
    assert output_paths.trajectory_probe_report_path.exists()
    assert output_paths.trajectory_mechanism_decision_path.exists()
    assert output_paths.run_manifest_path.exists()
    assert output_paths.runtime_config_path.exists()
    assert output_paths.stage2_frozen_baseline_manifest_path.exists()
    assert decision["Stage3ImplementationDecision"] == "PASS"
    assert decision["Stage2DependencyStatus"] == "PASSED"
    assert decision["Stage3MechanismDecision"] == "INCONCLUSIVE"
    assert "surrogate_source_not_sufficient" in decision["Stage3MechanismBlockingReasons"]

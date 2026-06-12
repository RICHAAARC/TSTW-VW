"""验证阶段三 baseline smoke runner 的本地阻断输出。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.smoke_runner import (
    materialize_completed_smoke_run,
    run_baseline_smoke,
)

pytestmark = [pytest.mark.quick, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]


def test_baseline_smoke_runner_writes_non_claim_skeleton_outputs(tmp_path: Path) -> None:
    """确认本地 smoke 只生成阻断型记录, 不产生正式 claim 证据。"""
    summary = run_baseline_smoke(
        run_root=tmp_path / "baseline_smoke",
        config_dir=ROOT / "configs" / "baselines",
        short_commit="abcdef0",
        timestamp_utc="20260611T000000Z",
    )

    records_path = Path(summary["records_path"])
    manifest_path = Path(summary["manifest_path"])
    limitation_report_path = Path(summary["limitation_report_path"])

    assert summary["record_count"] == 3
    assert summary["requires_colab_validation"] is True
    assert records_path.exists()
    assert manifest_path.exists()
    assert limitation_report_path.exists()

    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    assert {record["baseline_name"] for record in records} == {
        "external_videoseal",
        "external_rivagan",
        "external_hidden_framewise",
    }
    assert all(record["decision"] == "failed" for record in records)
    assert all(record["baseline_score"] is None for record in records)
    assert all(record["failure_reason"] == "external_baseline_not_integrated" for record in records)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["claim_support_allowed"] is False
    assert manifest["requires_colab_validation"] is True
    assert manifest["blocking_reason"] == "external_baseline_weights_and_gpu_smoke_not_verified"


def test_baseline_smoke_materialization_copies_only_completed_run(tmp_path: Path) -> None:
    """确认结果复制发生在 smoke 完成之后, 避免 Drive 侧出现空目录。"""
    run_root = tmp_path / "session" / "baseline_smoke"
    result_root = tmp_path / "drive_results"
    summary = run_baseline_smoke(
        run_root=run_root,
        config_dir=ROOT / "configs" / "baselines",
        short_commit="abcdef0",
        timestamp_utc="20260611T000000Z",
    )

    destination = materialize_completed_smoke_run(
        run_root=run_root,
        result_root=result_root,
        run_id=summary["run_id"],
    )

    assert destination == result_root / "baseline_comparison_gate" / summary["run_id"]
    assert (destination / "manifest.json").exists()
    assert (destination / "records" / "baseline_smoke_records.jsonl").exists()
    assert (destination / "reports" / "baseline_limitation_report.md").exists()


def test_baseline_smoke_supports_single_baseline_result_directory(tmp_path: Path) -> None:
    """确认轻量 comparison smoke 可以按 baseline 独立生成结果包。"""
    run_root = tmp_path / "session" / "external_hidden_framewise"
    result_root = tmp_path / "r" / "external_hidden_framewise" / "comparison_smoke"
    summary = run_baseline_smoke(
        run_root=run_root,
        config_dir=ROOT / "configs" / "baselines",
        short_commit="abcdef0",
        timestamp_utc="20260611T00Z",
        baseline_names=["external_hidden_framewise"],
    )

    destination = materialize_completed_smoke_run(
        run_root=run_root,
        result_root=result_root,
        workflow_key="",
        run_id=summary["run_id"],
    )

    assert summary["record_count"] == 1
    assert "external_hidden_framewise" in summary["run_id"]
    assert destination == result_root / summary["run_id"]
    assert (destination / "records" / "baseline_smoke_records.jsonl").exists()

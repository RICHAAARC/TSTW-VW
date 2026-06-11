"""验证 baseline 真实 smoke 汇总器的轻量契约。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.real_smoke_summary import (
    discover_latest_real_smoke_runs,
    summarize_real_smoke_run,
    summarize_real_smoke_runs,
    write_summary_outputs,
)
from main.core.digest import compute_object_digest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def make_record(*, baseline_name: str, run_id: str, attack_name: str, decision: str, score: float) -> dict:
    """构造满足 baseline record schema 的最小测试记录。"""
    return {
        "workflow_key": "baseline_comparison_gate",
        "run_id": run_id,
        "sample_id": f"sample_{attack_name}",
        "split": "dev",
        "sample_role": "attacked_positive",
        "baseline_name": baseline_name,
        "baseline_family": "external_video_watermark",
        "method_name": baseline_name,
        "method_family": "external_video_watermark",
        "payload_length_bits": 4,
        "payload_digest": "payload_digest",
        "attack_name": attack_name,
        "attack_family": "clean" if attack_name == "clean" else "compression",
        "attack_config_digest": "attack_digest",
        "baseline_score": score,
        "baseline_raw_detector_output": {"score": score},
        "threshold": 0.5,
        "target_fpr": None,
        "decision": decision,
        "bit_accuracy": score,
        "ber": 1.0 - score,
        "quality_metrics": {},
        "temporal_metrics": {},
        "runtime_metrics": {},
        "baseline_trace": {
            "source_digest": "source_digest",
            "model_digest": "model_digest",
            "adapter_version": f"{baseline_name}_real_smoke_adapter",
            "score_mapping_rule": "bit_accuracy_mean",
            "license_status": "recorded",
            "unsupported_attack_reason": None,
        },
        "failure_reason": None if decision == "positive" else "below_threshold",
    }


def write_run(root: Path, *, baseline_name: str, run_id: str, clean_decision: str, h264_decision: str) -> Path:
    """写出一个伪真实 smoke 结果包, 用于测试摘要器而不运行模型。"""
    run_root = root / run_id
    records_dir = run_root / "records"
    records_dir.mkdir(parents=True)
    records = [
        make_record(
            baseline_name=baseline_name,
            run_id=run_id,
            attack_name="clean",
            decision=clean_decision,
            score=0.75 if clean_decision == "positive" else 0.45,
        ),
        make_record(
            baseline_name=baseline_name,
            run_id=run_id,
            attack_name="h264_crf_28",
            decision=h264_decision,
            score=0.70 if h264_decision == "positive" else 0.40,
        ),
    ]
    record_name = f"{baseline_name}_real_smoke_records.jsonl"
    (records_dir / record_name).write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = {
        "workflow_key": "baseline_comparison_gate",
        "run_id": run_id,
        "run_kind": f"{baseline_name}_real_smoke",
        "baseline_name": baseline_name,
        "record_count": len(records),
        "records_digest": compute_object_digest(records),
        "model_digest": "model_digest",
        "adapter_version": f"{baseline_name}_real_smoke_adapter",
        "claim_support_allowed": False,
        "formal_fixed_fpr_complete": False,
    }
    (run_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_root


def test_summarize_real_smoke_run_classifies_positive_package(tmp_path: Path) -> None:
    """确认摘要器能把包完整且 clean/H.264 均通过的结果识别为 real_smoke_passed。"""
    run_root = write_run(
        tmp_path,
        baseline_name="external_videoseal",
        run_id="external_videoseal_real_smoke_20260611T071016Z_d78573c",
        clean_decision="positive",
        h264_decision="positive",
    )

    summary = summarize_real_smoke_run(run_root)

    assert summary["status"] == "real_smoke_passed"
    assert summary["schema_pass"] is True
    assert summary["records_digest_match"] is True
    assert summary["record_count_match"] is True
    assert summary["claim_support_allowed"] is False
    assert summary["formal_fixed_fpr_complete"] is False


def test_summarize_real_smoke_run_keeps_negative_smoke_as_limitation(tmp_path: Path) -> None:
    """确认可运行但分数低于阈值的 framewise baseline 不会被误判为通过。"""
    run_root = write_run(
        tmp_path,
        baseline_name="external_hidden_framewise",
        run_id="external_hidden_framewise_real_smoke_20260611T071057Z_d78573c",
        clean_decision="negative",
        h264_decision="negative",
    )

    summary = summarize_real_smoke_run(run_root)

    assert summary["status"] == "real_smoke_executed_negative"
    assert summary["limitation_reason"] == "single_baseline_smoke_score_below_threshold"
    assert summary["clean_failure_reason"] == "below_threshold"
    assert summary["h264_failure_reason"] == "below_threshold"


def test_discover_and_write_real_smoke_summary_outputs(tmp_path: Path) -> None:
    """确认结果根目录自动发现和三种摘要格式写出均可用。"""
    workflow_root = tmp_path / "results" / "baseline_comparison_gate"
    runs = [
        write_run(
            workflow_root,
            baseline_name="external_videoseal",
            run_id="external_videoseal_real_smoke_20260611T071016Z_d78573c",
            clean_decision="positive",
            h264_decision="positive",
        ),
        write_run(
            workflow_root,
            baseline_name="external_rivagan",
            run_id="external_rivagan_real_smoke_20260611T071047Z_d78573c",
            clean_decision="positive",
            h264_decision="positive",
        ),
        write_run(
            workflow_root,
            baseline_name="external_hidden_framewise",
            run_id="external_hidden_framewise_real_smoke_20260611T071057Z_d78573c",
            clean_decision="negative",
            h264_decision="negative",
        ),
    ]

    discovered = discover_latest_real_smoke_runs(tmp_path / "results")
    summary = summarize_real_smoke_runs(runs)
    outputs = write_summary_outputs(summary, tmp_path / "summary")

    assert [path.name for path in discovered] == [path.name for path in runs]
    assert summary["package_ready_for_formal_planning"] is True
    assert summary["all_real_smoke_scores_positive"] is False
    assert Path(outputs["json_path"]).exists()
    assert Path(outputs["csv_path"]).exists()
    assert Path(outputs["markdown_path"]).exists()

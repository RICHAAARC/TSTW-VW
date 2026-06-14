"""验证 `attack_strength_curve_probe` 聚合器。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.attack_strength_curve_probe.attack_strength_builder import (
    build_attack_strength_artifacts,
    build_attack_strength_tables,
)
from experiments.attack_strength_curve_probe.stage_two_record_adapter import (
    convert_stage_two_records_to_attack_strength_records,
    write_attack_strength_shard_from_stage_two,
)

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def make_record(method: str, split: str, role: str, strength: float, score: float) -> dict[str, object]:
    """构造最小 attack strength record。"""
    return {
        "method_name": method,
        "attack_name": "h264_compression",
        "attack_strength_name": f"crf_{int(strength)}",
        "attack_strength_value": strength,
        "split": split,
        "sample_role": role,
        "score": score,
    }


def test_attack_strength_tables_use_calibration_negatives_only() -> None:
    """确认阈值来自 calibration negatives, 而不是 test split。"""
    records = []
    for method in ("frame_prc", "tubelet_only", "tubelet_sync"):
        records.extend(
            [
                make_record(method, "calibration", "attacked_negative", 23, 0.1),
                make_record(method, "calibration", "attacked_negative", 28, 0.2),
                make_record(method, "test", "attacked_positive", 23, 0.9),
                make_record(method, "test", "attacked_negative", 23, 0.05),
            ]
        )

    tpr_rows, auc_rows, figure_rows = build_attack_strength_tables(records, target_fpr=0.01)

    assert len(tpr_rows) == 3
    assert len(auc_rows) == 3
    assert len(figure_rows) == 6
    assert {row["threshold"] for row in tpr_rows} == {0.2}
    assert {row["tpr_at_target_fpr"] for row in tpr_rows} == {1.0}
    assert {row["fpr_at_threshold"] for row in tpr_rows} == {0.0}


def test_build_attack_strength_artifacts_writes_required_outputs(tmp_path: Path) -> None:
    """确认聚合器写出 records、tables、figure_data 和 manifest。"""
    record_path = tmp_path / "shard" / "records" / "attack_strength_event_scores.jsonl"
    record_path.parent.mkdir(parents=True)
    records = []
    for method in ("frame_prc", "tubelet_only", "tubelet_sync"):
        records.extend(
            [
                make_record(method, "calibration", "attacked_negative", 23, 0.1),
                make_record(method, "calibration", "attacked_negative", 28, 0.2),
                make_record(method, "test", "attacked_positive", 23, 0.9),
                make_record(method, "test", "attacked_negative", 23, 0.05),
            ]
        )
    record_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")

    summary = build_attack_strength_artifacts(
        output_root=tmp_path / "aggregated",
        record_paths=[record_path],
        run_id="attack_strength_curve_probe_test",
    )

    assert summary["claim_support_allowed"] is True
    assert (tmp_path / "aggregated" / "tables" / "attack_strength_tpr_table.csv").exists()
    assert (tmp_path / "aggregated" / "tables" / "attack_strength_auc_table.csv").exists()
    assert (tmp_path / "aggregated" / "figure_data" / "attack_strength_curve_figure_data.csv").exists()
    assert (tmp_path / "aggregated" / "artifacts" / "attack_strength_curve_manifest.json").exists()


def test_base_record_source_mode_blocks_aggregate_claim_support(tmp_path: Path) -> None:
    """确认阶段二基础 records 聚合后不会被误标记为完整多强度 claim 证据。"""
    record_path = tmp_path / "base" / "records" / "attack_strength_event_scores.jsonl"
    record_path.parent.mkdir(parents=True)
    records = []
    for method in ("frame_prc", "tubelet_only", "tubelet_sync"):
        base_rows = [
            make_record(method, "calibration", "attacked_negative", 23, 0.1),
            make_record(method, "test", "attacked_positive", 23, 0.9),
            make_record(method, "test", "attacked_negative", 23, 0.05),
        ]
        for row in base_rows:
            row["source_mode"] = "from_stage_two_existing_records"
            records.append(row)
    record_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")

    summary = build_attack_strength_artifacts(
        output_root=tmp_path / "aggregated",
        record_paths=[record_path],
        run_id="attack_strength_curve_probe_base_records_test",
    )

    assert summary["claim_support_allowed"] is False
    assert summary["claim_support_blocking_reason"] == "base_records_only_not_full_multi_strength_sweep"
    assert summary["source_modes"] == ["from_stage_two_existing_records"]


def test_attack_strength_probe_contract_is_documented() -> None:
    """确认图表补充流程和命令行入口已登记。"""
    root = Path(__file__).resolve().parents[2]
    doc = (root / "docs" / "builds" / "图表补充流程.md").read_text(encoding="utf-8")
    script = root / "scripts" / "package_results" / "build_attack_strength_curve_probe.py"
    base_record_script = root / "scripts" / "package_results" / "run_attack_strength_curve_probe_from_stage_two.py"
    notebook = root / "paper_workflow" / "run_attack_strength_curve_probe.ipynb"
    figure_source = (root / "experiments" / "paper_artifact_gate" / "figure_builder.py").read_text(encoding="utf-8")

    assert "attack_strength_curve_probe" in doc
    assert "H.264" in doc
    assert "frame_dropping" in doc
    assert "from_stage_two_existing_records" in doc
    assert script.exists()
    assert base_record_script.exists()
    assert notebook.exists()
    assert "paper_attack_strength_curves" in figure_source


def test_stage_two_records_can_seed_attack_strength_base_records(tmp_path: Path) -> None:
    """确认可以从阶段二 records 产出攻击强度曲线基础 records。"""
    source_records = []
    for method in ("frame_prc", "tubelet_only", "tubelet_sync"):
        source_records.extend(
            [
                {
                    "run_id": "stage_two_run",
                    "event_id": f"{method}_calibration_negative",
                    "sample_id": "sample_calibration_negative",
                    "method_variant": method,
                    "attack_name": "h264_compression",
                    "attack_params": {"crf": 28},
                    "split": "calibration",
                    "sample_role": "attacked_negative",
                    "evidence_scores": {"S_final": 0.1},
                },
                {
                    "run_id": "stage_two_run",
                    "event_id": f"{method}_test_positive",
                    "sample_id": "sample_test_positive",
                    "method_variant": method,
                    "attack_name": "h264_compression",
                    "attack_params": {"crf": 28},
                    "split": "test",
                    "sample_role": "attacked_positive",
                    "evidence_scores": {"S_final": 0.9},
                },
            ]
        )

    converted = convert_stage_two_records_to_attack_strength_records(source_records)

    assert len(converted) == 6
    assert {row["attack_strength_name"] for row in converted} == {"crf_28"}
    assert {row["source_mode"] for row in converted} == {"from_stage_two_existing_records"}
    assert {row["method_name"] for row in converted} == {"frame_prc", "tubelet_only", "tubelet_sync"}


def test_stage_two_record_adapter_writes_shard_run_outputs(tmp_path: Path) -> None:
    """确认阶段二 adapter 写出 shard run records 和 manifest。"""
    stage_two_root = tmp_path / "stage_two"
    record_path = stage_two_root / "records" / "event_scores.jsonl"
    record_path.parent.mkdir(parents=True)
    records = [
        {
            "run_id": "stage_two_run",
            "event_id": "event_001",
            "sample_id": "sample_001",
            "method_variant": "tubelet_sync",
            "attack_name": "frame_dropping",
            "attack_params": {"drop_rate": 0.3},
            "split": "test",
            "sample_role": "attacked_positive",
            "evidence_scores": {"S_final": 0.8},
        }
    ]
    record_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")

    summary = write_attack_strength_shard_from_stage_two(
        output_root=tmp_path / "shard_run",
        stage_two_root=stage_two_root,
        run_id="attack_strength_curve_probe_base_records_test",
        method_names=("tubelet_sync",),
        attack_names=("frame_dropping",),
    )

    assert summary["claim_support_allowed"] is False
    assert summary["claim_support_blocking_reason"] == "base_records_only_not_full_multi_strength_sweep"
    assert (tmp_path / "shard_run" / "records" / "attack_strength_event_scores.jsonl").exists()
    assert (tmp_path / "shard_run" / "artifacts" / "attack_strength_base_records_manifest.json").exists()

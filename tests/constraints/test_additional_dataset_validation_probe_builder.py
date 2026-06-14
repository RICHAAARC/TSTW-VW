"""验证 `additional_dataset_validation_probe` 聚合器。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.additional_dataset_validation_probe.additional_dataset_builder import (
    build_additional_dataset_artifacts,
    build_additional_dataset_tables,
)

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def make_record(method: str, split: str, role: str, attack: str, score: float) -> dict[str, object]:
    """构造最小附加数据集验证 record。"""
    return {
        "dataset_name": "ucf101",
        "dataset_subset_id": "ucf101_subset_smoke",
        "method_name": method,
        "attack_name": attack,
        "split": split,
        "sample_role": role,
        "score": score,
    }


def test_additional_dataset_tables_use_calibration_negatives_only() -> None:
    """确认阈值只来自 calibration negatives, 不使用 test split。"""
    records = []
    for method in ("frame_prc", "tubelet_only", "tubelet_sync"):
        records.extend(
            [
                make_record(method, "calibration", "clean_negative", "no_attack", 0.1),
                make_record(method, "calibration", "attacked_negative", "h264_compression", 0.2),
                make_record(method, "test", "attacked_positive", "h264_compression", 0.9),
                make_record(method, "test", "attacked_negative", "h264_compression", 0.05),
            ]
        )

    main_rows, attack_rows, figure_rows = build_additional_dataset_tables(records, target_fpr=0.01)

    assert len(main_rows) == 3
    assert len(attack_rows) == 3
    assert len(figure_rows) == 3
    assert {row["threshold"] for row in main_rows} == {0.2}
    assert {row["tpr_at_target_fpr"] for row in main_rows} == {1.0}
    assert {row["fpr_at_threshold"] for row in main_rows} == {0.0}


def test_build_additional_dataset_artifacts_writes_required_outputs(tmp_path: Path) -> None:
    """确认聚合器写出 records、tables、figure_data 和 manifest。"""
    record_path = tmp_path / "shard" / "records" / "additional_dataset_event_scores.jsonl"
    record_path.parent.mkdir(parents=True)
    records = []
    for method in ("frame_prc", "tubelet_only", "tubelet_sync"):
        records.extend(
            [
                make_record(method, "calibration", "clean_negative", "no_attack", 0.1),
                make_record(method, "calibration", "attacked_negative", "h264_compression", 0.2),
                make_record(method, "test", "attacked_positive", "h264_compression", 0.9),
                make_record(method, "test", "attacked_negative", "h264_compression", 0.05),
            ]
        )
    record_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")

    summary = build_additional_dataset_artifacts(
        output_root=tmp_path / "aggregated",
        record_paths=[record_path],
        dataset_name="ucf101",
        run_id="additional_dataset_validation_probe_ucf101_test",
    )

    assert summary["claim_support_allowed"] is True
    assert (tmp_path / "aggregated" / "records" / "additional_dataset_event_scores.jsonl").exists()
    assert (tmp_path / "aggregated" / "tables" / "additional_dataset_main_tpr_fpr_table.csv").exists()
    assert (tmp_path / "aggregated" / "tables" / "additional_dataset_attack_breakdown_table.csv").exists()
    assert (tmp_path / "aggregated" / "figure_data" / "additional_dataset_comparison_figure_data.csv").exists()
    assert (tmp_path / "aggregated" / "artifacts" / "additional_dataset_validation_manifest.json").exists()


def test_additional_dataset_probe_contract_is_documented() -> None:
    """确认附加数据集补充流程和命令行入口已经登记。"""
    root = Path(__file__).resolve().parents[2]
    doc = (root / "docs" / "builds" / "图表补充流程.md").read_text(encoding="utf-8")
    contract = (root / ".codex" / "project_contract.md").read_text(encoding="utf-8")
    script = root / "scripts" / "package_results" / "build_additional_dataset_validation_probe.py"
    figure_source = (root / "experiments" / "paper_artifact_gate" / "figure_builder.py").read_text(encoding="utf-8")

    assert "additional_dataset_validation_probe" in doc
    assert "UCF101" in doc
    assert "additional_dataset_validation_probe" in contract
    assert script.exists()
    assert "paper_additional_dataset_comparison" in figure_source


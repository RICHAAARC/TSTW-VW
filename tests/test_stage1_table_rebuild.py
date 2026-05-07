"""
文件用途：验证 stage-one 表格、曲线与报告可由 records 重建。
File purpose: Validate that stage-one tables, curves, and report are rebuildable from records.
Module type: General module
"""

from __future__ import annotations

import csv
from pathlib import Path

from main.analysis.table_builder import TableBuilder
from main.core.digest import compute_path_collection_digest
from main.core.records import RecordWriter
from main.protocol.ablation_runner import AblationRunner


ROOT = Path(__file__).resolve().parents[1]


def test_stage1_table_and_curve_rebuild_preserves_tables_digest(tmp_path: Path) -> None:
    """Validate that deleting CSV outputs and rebuilding preserves the manifest tables digest.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2, runtime_profile_override="tiny")
    record_writer = RecordWriter(output_root)
    run_manifest = record_writer.read_run_manifest()

    for csv_path in record_writer.output_paths.table_paths():
        assert csv_path.exists()
        csv_path.unlink()
    report_path = record_writer.output_paths.report_path
    assert report_path.exists()
    report_path.unlink()

    rebuilt_paths = TableBuilder().rebuild_tables(output_root)
    assert rebuilt_paths["report_path"].exists()
    rebuilt_tables_digest = compute_path_collection_digest(record_writer.output_paths.table_paths())
    assert rebuilt_tables_digest == run_manifest["tables_digest"]


def test_stage1_rebuild_restores_required_outputs(tmp_path: Path) -> None:
    """Validate that rebuild restores all required stage-one CSV and report outputs.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=1, runtime_profile_override="tiny")
    record_writer = RecordWriter(output_root)

    for path in record_writer.output_paths.table_paths():
        path.unlink()
    record_writer.output_paths.report_path.unlink()

    TableBuilder().rebuild_tables(output_root)
    assert record_writer.output_paths.main_metrics_path.exists()
    assert record_writer.output_paths.ablation_table_path.exists()
    assert record_writer.output_paths.local_clip_curve_path.exists()
    assert record_writer.output_paths.temporal_attack_curve_path.exists()
    assert record_writer.output_paths.tubelet_length_ablation_path.exists()
    assert record_writer.output_paths.report_path.exists()

    local_clip_rows = list(
        csv.DictReader(
            record_writer.output_paths.local_clip_curve_path.open(encoding="utf-8")
        )
    )
    assert {int(row["clip_length"]) for row in local_clip_rows} == {4, 8}

    tubelet_rows = list(
        csv.DictReader(
            record_writer.output_paths.tubelet_length_ablation_path.open(
                encoding="utf-8"
            )
        )
    )
    assert {int(row["tubelet_length"]) for row in tubelet_rows} == {1, 4}

    report_text = record_writer.output_paths.report_path.read_text(encoding="utf-8")
    # 中文注释：tiny profile 仅证明完整闭环可生成 report；机制 check 字段在 tiny 下
    # 因 local_clip / tubelet_length 集合被裁剪而注定为 false，故只断言字段存在。
    assert "- required_local_clip_lengths_present:" in report_text
    assert "- required_tubelet_length_sweep_present:" in report_text
    assert "- attacked_negative_fpr_meets_target_for_all_variants:" in report_text
    assert "- worst_attacked_negative_fpr_variants:" in report_text
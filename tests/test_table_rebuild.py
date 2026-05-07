"""
文件用途：验证阶段 0 tables 可由 records 重建。
File purpose: Validate that stage-0 tables are rebuildable from records.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.analysis.table_builder import TableBuilder
from main.core.digest import compute_path_collection_digest
from main.core.records import RecordWriter
from main.protocol.ablation_runner import AblationRunner


ROOT = Path(__file__).resolve().parents[1]


def test_stage0_table_rebuild_preserves_tables_digest(tmp_path: Path) -> None:
    """Validate that deleting and rebuilding a table preserves the tables digest.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "protocol_skeleton_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2, runtime_profile_override="tiny")
    record_writer = RecordWriter(output_root)
    run_manifest = record_writer.read_run_manifest()

    main_metrics_path = record_writer.output_paths.main_metrics_path
    assert main_metrics_path.exists()
    main_metrics_path.unlink()

    TableBuilder().rebuild_tables(output_root)
    rebuilt_tables_digest = compute_path_collection_digest(record_writer.output_paths.table_paths())
    assert rebuilt_tables_digest == run_manifest["tables_digest"]
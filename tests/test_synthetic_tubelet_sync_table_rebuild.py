"""
鏂囦欢鐢ㄩ€旓細楠岃瘉 stage-one 琛ㄦ牸銆佹洸绾夸笌鎶ュ憡鍙敱 records 閲嶅缓銆?
File purpose: Validate that stage-one tables, curves, and report are rebuildable from records.
Module type: General module
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from main.analysis.table_builder import TableBuilder
from main.core.digest import compute_path_collection_digest
from main.core.records import RecordWriter
from main.protocol.ablation_runner import AblationRunner


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.smoke
def test_synthetic_tubelet_sync_table_and_curve_rebuild_preserves_tables_digest(tmp_path: Path) -> None:
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
    for figure_path in record_writer.output_paths.figure_paths():
        assert figure_path.exists()
        figure_path.unlink()
    report_path = record_writer.output_paths.report_path
    assert report_path.exists()
    report_path.unlink()

    rebuilt_paths = TableBuilder().rebuild_tables(output_root)
    assert rebuilt_paths["report_path"].exists()
    assert rebuilt_paths["sync_peak_examples_path"].exists()
    rebuilt_tables_digest = compute_path_collection_digest(record_writer.output_paths.table_paths())
    rebuilt_figures_digest = compute_path_collection_digest(record_writer.output_paths.figure_paths())
    assert rebuilt_tables_digest == run_manifest["tables_digest"]
    assert rebuilt_figures_digest == run_manifest["figures_digest"]


@pytest.mark.smoke
def test_synthetic_tubelet_sync_rebuild_restores_required_outputs(tmp_path: Path) -> None:
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
    for path in record_writer.output_paths.figure_paths():
        path.unlink()
    record_writer.output_paths.report_path.unlink()

    TableBuilder().rebuild_tables(output_root)
    assert record_writer.output_paths.main_metrics_path.exists()
    assert record_writer.output_paths.ablation_table_path.exists()
    assert record_writer.output_paths.local_clip_curve_path.exists()
    assert record_writer.output_paths.temporal_attack_curve_path.exists()
    assert record_writer.output_paths.tubelet_length_ablation_path.exists()
    assert record_writer.output_paths.sync_peak_examples_path.exists()
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
    # 涓枃娉ㄩ噴锛歵iny profile 浠呰瘉鏄庡畬鏁撮棴鐜彲鐢熸垚 report锛涙満鍒?check 瀛楁鍦?tiny 涓?
    # 鍥?local_clip / tubelet_length 闆嗗悎琚鍓€屾敞瀹氫负 false锛屾晠鍙柇瑷€瀛楁瀛樺湪銆?
    assert "- closure_target_pass:" in report_text
    assert "- validation_target_fpr_pass:" in report_text
    assert "- strict_target_fpr_pass:" in report_text
    assert "- primary_method_variants:" in report_text
    assert "- derived_ablation_variants:" in report_text
    assert "- required_local_clip_lengths_present:" in report_text
    assert "- required_tubelet_length_sweep_present:" in report_text
    assert "- attacked_negative_fpr_meets_validation_target_for_all_variants:" in report_text
    assert "- attacked_negative_fpr_meets_strict_target_for_all_variants:" in report_text
    assert "- worst_attacked_negative_fpr_variants:" in report_text


@pytest.mark.slow
def test_synthetic_tubelet_sync_proof_profile_meets_strict_gate(tmp_path: Path) -> None:
    """Validate that the proof profile closes with an explicit strict low-FPR pass.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_proof_run"
    AblationRunner(ROOT).run(output_root, samples_per_role=2, runtime_profile_override="proof")
    report_text = RecordWriter(output_root).output_paths.report_path.read_text(encoding="utf-8")

    assert "- primary_stage1_completion_pass: true" in report_text
    assert "- primary_strict_target_fpr_pass: true" in report_text
    assert "- strict_target_fpr_pass: true" in report_text
    assert "- attacked_negative_fpr_meets_strict_target_for_primary_variants: true" in report_text


@pytest.mark.slow
def test_proof_profile_writes_expected_record_counts(tmp_path: Path) -> None:
    """Validate that the proof profile materializes the expected governed artifact counts.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_proof_counts"
    result = AblationRunner(ROOT).run(
        output_root,
        samples_per_role=2,
        runtime_profile_override="proof",
        emit_progress_logs=False,
    )
    record_writer = RecordWriter(output_root)

    assert len(result.event_score_records) == 1008
    assert len(result.threshold_records) == 7
    assert len(result.method_variant_runtime_profiles) == 7
    assert record_writer.output_paths.report_path.exists()
    assert record_writer.output_paths.run_manifest_path.exists()


@pytest.mark.slow
def test_proof_profile_supports_single_variant_benchmark_runs(tmp_path: Path) -> None:
    """Validate that proof runs can target a single derived variant for benchmarking.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "synthetic_tubelet_sync_probe_lt01_benchmark"
    result = AblationRunner(ROOT).run(
        output_root,
        samples_per_role=2,
        runtime_profile_override="proof",
        method_variants=["tubelet_only_lt01"],
        emit_progress_logs=False,
    )

    assert len(result.event_score_records) == 144
    assert len(result.threshold_records) == 1
    assert [record["method_variant"] for record in result.threshold_records] == [
        "tubelet_only_lt01"
    ]
    assert [profile.method_variant for profile in result.method_variant_runtime_profiles] == [
        "tubelet_only_lt01"
    ]

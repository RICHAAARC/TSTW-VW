"""
文件用途：验证阶段 2 scaffold 表格与报告可从 records 重建。
File purpose: Validate that stage-two scaffold tables and report can be rebuilt from records.
Module type: General module
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from experiments.real_video_vae_latent_probe.artifact_builder import (
    RealVideoVaeLatentArtifactBuilder,
)
from tests.helpers.real_video_probe_run import run_real_video_vae_latent_tiny


@pytest.mark.smoke
def test_real_video_vae_latent_tables_and_report_rebuild_from_records(tmp_path: Path) -> None:
    """Validate that stage-two scaffold artifacts rebuild from persisted records.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = run_real_video_vae_latent_tiny(tmp_path)
    for relative_path in ("tables", "figures", "reports", "failure_case_gallery"):
        shutil.rmtree(output_root / relative_path)
    rebuilt_paths = RealVideoVaeLatentArtifactBuilder().rebuild_artifacts(output_root)
    assert rebuilt_paths["main_tpr_fpr_table_path"].exists()
    assert rebuilt_paths["quality_table_path"].exists()
    assert rebuilt_paths["temporal_consistency_table_path"].exists()
    assert rebuilt_paths["real_video_vae_latent_governance_summary_path"].exists()
    assert rebuilt_paths["report_path"].exists()
    with rebuilt_paths["real_video_vae_latent_governance_summary_path"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["real_video_vae_latent_decision"] == "INCONCLUSIVE"
    assert rows[0]["next_allowed_stage"] == "remain_in_real_video_vae_latent_probe"
    assert "notebook_entrypoint_deferred_under_current_stage_governance" not in rows[0]["blocking_reasons"]
    report_text = rebuilt_paths["report_path"].read_text(encoding="utf-8")
    assert f"- method_variants: {rows[0]['method_variants_summary']}" in report_text
    assert f"- attack_names: {rows[0]['attack_names_summary']}" in report_text
    assert f"- target_fprs: {rows[0]['target_fprs_summary']}" in report_text
    assert f"- quality_metrics_runtime: {rows[0]['quality_metrics_runtime']}" in report_text
    assert f"- temporal_metrics_runtime: {rows[0]['temporal_metrics_runtime']}" in report_text

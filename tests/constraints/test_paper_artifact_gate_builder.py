"""验证 paper_artifact_gate 论文产物构建器。"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest

from experiments.paper_artifact_gate.artifact_builder import (
    PaperArtifactInputs,
    build_paper_artifacts,
    discover_latest_inputs,
)

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    """写出测试 CSV。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_stage_two_package(root: Path) -> Path:
    """构造最小阶段二聚合 zip。"""
    package_dir = root / "packages"
    package_dir.mkdir(parents=True)
    archive = package_dir / "real_video_vae_latent_probe_shard_aggregated.zip"
    fieldnames = [
        "run_id", "construction_phase", "method_variant", "attack_name", "attack_strength", "threshold_id",
        "clean_negative_FPR", "attacked_negative_FPR", "clean_positive_TPR", "attacked_positive_TPR",
        "local_clip_TPR", "sync_alignment_error_mean", "sync_peak_rank_median", "positive_count", "negative_count",
    ]
    rows = []
    values = {
        "frame_prc": {"no_attack": 0.5, "local_clip": 0.1, "temporal_crop": 0.1},
        "tubelet_only": {"no_attack": 0.6, "local_clip": 0.4, "temporal_crop": 0.45},
        "tubelet_sync": {"no_attack": 0.7, "local_clip": 0.85, "temporal_crop": 0.8},
    }
    for method, attacks in values.items():
        for attack, tpr in attacks.items():
            rows.append(
                {
                    "run_id": "stage_two_run",
                    "construction_phase": "real_video_vae_latent_probe",
                    "method_variant": method,
                    "attack_name": attack,
                    "attack_strength": "default",
                    "threshold_id": f"threshold:{method}",
                    "clean_negative_FPR": 0.0 if attack == "no_attack" else "",
                    "attacked_negative_FPR": "" if attack == "no_attack" else 0.0,
                    "clean_positive_TPR": tpr if attack == "no_attack" else "",
                    "attacked_positive_TPR": "" if attack == "no_attack" else tpr,
                    "local_clip_TPR": tpr if attack == "local_clip" else "",
                    "sync_alignment_error_mean": "",
                    "sync_peak_rank_median": "",
                    "positive_count": 10,
                    "negative_count": 10,
                }
            )
    with zipfile.ZipFile(archive, "w") as zf:
        import io

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        zf.writestr(
            "real_video_vae_latent_probe_shard_aggregated/tables/real_video_attack_breakdown.csv",
            buffer.getvalue(),
        )
    return root


def write_baseline_aggregation(root: Path, baseline_name: str, tpr: float) -> Path:
    """构造最小 baseline 聚合目录。"""
    (root / "artifacts").mkdir(parents=True)
    (root / "artifacts" / "baseline_score_records_aggregation_manifest.json").write_text(
        json.dumps(
            {
                "formal_fixed_fpr_complete": True,
                "claim_support_allowed": True,
                "record_count": 100,
                "target_fpr": 0.01,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_csv(
        root / "tables" / "baseline_comparison_table.csv",
        [
            {
                "baseline_name": baseline_name,
                "target_fpr": 0.01,
                "record_count": 20,
                "scored_count": 20,
                "positive_count": 10,
                "negative_count": 10,
                "tpr_at_target_fpr": tpr,
                "fpr_at_threshold": 0.0,
                "mean_score": 0.5,
            }
        ],
        [
            "baseline_name", "target_fpr", "record_count", "scored_count", "positive_count", "negative_count",
            "tpr_at_target_fpr", "fpr_at_threshold", "mean_score",
        ],
    )
    write_csv(
        root / "tables" / "baseline_attack_breakdown.csv",
        [
            {
                "baseline_name": baseline_name,
                "attack_name": "local_clip",
                "target_fpr": 0.01,
                "record_count": 20,
                "scored_count": 20,
                "positive_count": 10,
                "negative_count": 10,
                "tpr_at_target_fpr": tpr,
                "fpr_at_threshold": 0.0,
                "mean_score": 0.5,
            }
        ],
        [
            "baseline_name", "attack_name", "target_fpr", "record_count", "scored_count", "positive_count",
            "negative_count", "tpr_at_target_fpr", "fpr_at_threshold", "mean_score",
        ],
    )
    return root


def test_build_paper_artifacts_writes_tables_and_claim_audit(tmp_path: Path) -> None:
    """确认阶段四构建器从受治理输入生成论文表格和 claim audit。"""
    stage_two = write_stage_two_package(tmp_path / "stage_two")
    baselines = {
        "external_videoseal": write_baseline_aggregation(tmp_path / "external_videoseal", "external_videoseal", 0.2),
        "external_rivagan": write_baseline_aggregation(tmp_path / "external_rivagan", "external_rivagan", 0.1),
        "external_hidden_framewise": write_baseline_aggregation(tmp_path / "external_hidden_framewise", "external_hidden_framewise", 0.01),
    }
    output = tmp_path / "paper"

    summary = build_paper_artifacts(
        output_root=output,
        inputs=PaperArtifactInputs(stage_two_root=stage_two, baseline_aggregation_roots=baselines),
        run_id="paper_artifact_gate_test",
    )

    assert summary["paper_artifact_gate_complete"] is True
    assert (output / "tables" / "paper_method_comparison_table.csv").exists()
    assert (output / "tables" / "paper_sync_gain_table.csv").exists()
    assert (output / "figure_data" / "paper_method_comparison_figure_data.csv").exists()
    claim_rows = read_csv_rows(output / "claim_audit" / "paper_claim_audit.csv")
    assert {row["claim_support_allowed"] for row in claim_rows} == {"True"}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """读取测试输出 CSV。"""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_discover_latest_inputs_uses_per_baseline_layout(tmp_path: Path) -> None:
    """确认阶段四自动发现逻辑使用每个 baseline 独立的 shard_aggregated 目录。"""
    result_root = tmp_path / "results"
    stage_two = result_root / "real_video_vae_latent_probe" / "shard_aggregated" / "real_video_vae_latent_probe_aggregated_commit"
    stage_two.mkdir(parents=True)
    for baseline in ("external_videoseal", "external_rivagan", "external_hidden_framewise"):
        (result_root / "baseline_comparison_gate" / baseline / "shard_aggregated" / f"aggregation_{baseline}").mkdir(parents=True)

    inputs = discover_latest_inputs(result_root)

    assert inputs.stage_two_root == stage_two
    assert set(inputs.baseline_aggregation_roots) == {"external_videoseal", "external_rivagan", "external_hidden_framewise"}


def test_paper_artifact_gate_contract_is_documented() -> None:
    """确认阶段四结果目录和命令行入口已写入治理文档。"""
    root = Path(__file__).resolve().parents[2]
    project_contract = (root / ".codex" / "project_contract.md").read_text(encoding="utf-8")
    file_organization = (root / "docs" / "file_organization.md").read_text(encoding="utf-8")
    script = root / "scripts" / "package_results" / "build_paper_artifact_gate.py"

    assert "`project_stage`: `paper_artifact_gate`" in project_contract
    assert "## Paper Artifact Gate Contract" in project_contract
    assert "Paper Artifact Gate Result Layout" in file_organization
    assert script.exists()

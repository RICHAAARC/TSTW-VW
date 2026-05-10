"""
文件用途：定义阶段 2 scaffold 的固定输出路径布局。
File purpose: Define the governed output layout for the stage-two scaffold.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Stage2OutputPaths:
    """功能：定义阶段 2 运行产物的固定路径。

    Output layout for the stage-two scaffold runtime.

    Args:
        root_path: Run root path.
        event_scores_path: Event score JSONL path.
        thresholds_path: Threshold JSON path.
        run_manifest_path: Run manifest JSON path.
        artifact_manifest_path: Artifact manifest JSON path.
        colab_runtime_manifest_path: Runtime manifest JSON path.
        colab_stage2_runtime_config_path: Runtime-config JSON path.
        main_tpr_fpr_table_path: Main metrics table path.
        ablation_table_path: Ablation table path.
        real_video_attack_breakdown_path: Attack-breakdown table path.
        quality_table_path: Quality table path.
        temporal_consistency_table_path: Temporal table path.
        stage2_governance_summary_path: Governance-summary table path.
        quality_robustness_tradeoff_path: Figure path.
        report_path: Report path.
        failure_case_gallery_path: Failure gallery directory.

    Returns:
        None.
    """

    root_path: Path
    event_scores_path: Path
    thresholds_path: Path
    run_manifest_path: Path
    artifact_manifest_path: Path
    colab_runtime_manifest_path: Path
    colab_stage2_runtime_config_path: Path
    main_tpr_fpr_table_path: Path
    ablation_table_path: Path
    real_video_attack_breakdown_path: Path
    quality_table_path: Path
    temporal_consistency_table_path: Path
    stage2_governance_summary_path: Path
    quality_robustness_tradeoff_path: Path
    report_path: Path
    failure_case_gallery_path: Path

    def table_paths(self) -> list[Path]:
        return [
            self.main_tpr_fpr_table_path,
            self.ablation_table_path,
            self.real_video_attack_breakdown_path,
            self.quality_table_path,
            self.temporal_consistency_table_path,
            self.stage2_governance_summary_path,
        ]

    def figure_paths(self) -> list[Path]:
        return [self.quality_robustness_tradeoff_path]


def build_stage2_output_paths(output_root: str | Path) -> Stage2OutputPaths:
    """功能：构建阶段 2 scaffold 的固定输出路径。

    Build the fixed output layout for the stage-two scaffold.

    Args:
        output_root: Run root path.

    Returns:
        A `Stage2OutputPaths` instance.
    """
    output_root_path = Path(output_root)
    return Stage2OutputPaths(
        root_path=output_root_path,
        event_scores_path=output_root_path / "records" / "event_scores.jsonl",
        thresholds_path=output_root_path / "thresholds" / "thresholds.json",
        run_manifest_path=output_root_path / "artifacts" / "run_manifest.json",
        artifact_manifest_path=output_root_path / "artifacts" / "artifact_manifest.json",
        colab_runtime_manifest_path=(
            output_root_path / "artifacts" / "colab_runtime_manifest.json"
        ),
        colab_stage2_runtime_config_path=(
            output_root_path / "artifacts" / "colab_stage2_runtime_config.json"
        ),
        main_tpr_fpr_table_path=output_root_path / "tables" / "main_tpr_fpr_table.csv",
        ablation_table_path=output_root_path / "tables" / "ablation_table.csv",
        real_video_attack_breakdown_path=(
            output_root_path / "tables" / "real_video_attack_breakdown.csv"
        ),
        quality_table_path=output_root_path / "tables" / "quality_table.csv",
        temporal_consistency_table_path=(
            output_root_path / "tables" / "temporal_consistency_table.csv"
        ),
        stage2_governance_summary_path=(
            output_root_path / "tables" / "stage2_governance_summary.csv"
        ),
        quality_robustness_tradeoff_path=(
            output_root_path / "figures" / "quality_robustness_tradeoff.png"
        ),
        report_path=output_root_path / "reports" / "vae_latent_probe_report.md",
        failure_case_gallery_path=output_root_path / "failure_case_gallery",
    )
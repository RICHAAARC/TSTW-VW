"""
File purpose: Define the governed output layout for the real-video VAE-latent scaffold.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from main.protocol.output_layout import BaseRunOutputPaths, build_base_run_output_paths


@dataclass(frozen=True)
class RealVideoVaeLatentOutputPaths(BaseRunOutputPaths):
    """Output layout for the real-video VAE-latent scaffold runtime.

    Args:
        root_path: Run root path.
        event_scores_path: Event score JSONL path.
        thresholds_path: Threshold JSON path.
        run_manifest_path: Run manifest JSON path.
        artifact_manifest_path: Artifact manifest JSON path.
        runtime_manifest_path: Runtime manifest JSON path.
        runtime_config_path: Runtime-config JSON path.
        main_tpr_fpr_table_path: Main metrics table path.
        ablation_table_path: Ablation table path.
        real_video_attack_breakdown_path: Attack-breakdown table path.
        quality_table_path: Quality table path.
        temporal_consistency_table_path: Temporal table path.
        real_video_vae_latent_governance_summary_path: Governance-summary table path.
        quality_robustness_tradeoff_path: Figure path.
        report_path: Report path.
        failure_case_gallery_path: Failure gallery directory.

    Returns:
        None.
    """
    main_tpr_fpr_table_path: Path
    ablation_table_path: Path
    real_video_attack_breakdown_path: Path
    quality_table_path: Path
    temporal_consistency_table_path: Path
    real_video_vae_latent_governance_summary_path: Path
    quality_robustness_tradeoff_path: Path
    report_path: Path
    failure_case_gallery_path: Path
    stage2_mechanism_audit_table_path: Path
    stage2_score_distribution_table_path: Path
    stage2_sync_gain_table_path: Path
    stage2_mechanism_report_path: Path
    stage2_mechanism_decision_path: Path

    def table_paths(self) -> list[Path]:
        return [
            self.main_tpr_fpr_table_path,
            self.ablation_table_path,
            self.real_video_attack_breakdown_path,
            self.quality_table_path,
            self.temporal_consistency_table_path,
            self.real_video_vae_latent_governance_summary_path,
        ]

    def figure_paths(self) -> list[Path]:
        return [self.quality_robustness_tradeoff_path]

    def analysis_only_table_paths(self) -> list[Path]:
        return [
            self.stage2_mechanism_audit_table_path,
            self.stage2_score_distribution_table_path,
            self.stage2_sync_gain_table_path,
        ]


def build_real_video_vae_latent_output_paths(output_root: str | Path) -> RealVideoVaeLatentOutputPaths:
    """Build the fixed output layout for the real-video VAE-latent scaffold.

    Args:
        output_root: Run root path.

    Returns:
        A `RealVideoVaeLatentOutputPaths` instance.
    """
    output_root_path = Path(output_root)
    base_paths = build_base_run_output_paths(output_root_path)
    return RealVideoVaeLatentOutputPaths(
        root_path=base_paths.root_path,
        event_scores_path=base_paths.event_scores_path,
        thresholds_path=base_paths.thresholds_path,
        run_manifest_path=base_paths.run_manifest_path,
        artifact_manifest_path=base_paths.artifact_manifest_path,
        runtime_manifest_path=base_paths.runtime_manifest_path,
        runtime_config_path=base_paths.runtime_config_path,
        main_tpr_fpr_table_path=output_root_path / "tables" / "main_tpr_fpr_table.csv",
        ablation_table_path=output_root_path / "tables" / "ablation_table.csv",
        real_video_attack_breakdown_path=(
            output_root_path / "tables" / "real_video_attack_breakdown.csv"
        ),
        quality_table_path=output_root_path / "tables" / "quality_table.csv",
        temporal_consistency_table_path=(
            output_root_path / "tables" / "temporal_consistency_table.csv"
        ),
        real_video_vae_latent_governance_summary_path=(
            output_root_path / "tables" / "real_video_vae_latent_governance_summary.csv"
        ),
        quality_robustness_tradeoff_path=(
            output_root_path / "figures" / "quality_robustness_tradeoff.png"
        ),
        report_path=output_root_path / "reports" / "vae_latent_probe_report.md",
        failure_case_gallery_path=output_root_path / "failure_case_gallery",
        stage2_mechanism_audit_table_path=(
            output_root_path / "tables" / "stage2_mechanism_audit_table.csv"
        ),
        stage2_score_distribution_table_path=(
            output_root_path / "tables" / "stage2_score_distribution_table.csv"
        ),
        stage2_sync_gain_table_path=(
            output_root_path / "tables" / "stage2_sync_gain_table.csv"
        ),
        stage2_mechanism_report_path=(
            output_root_path / "reports" / "stage2_mechanism_audit_report.md"
        ),
        stage2_mechanism_decision_path=(
            output_root_path / "artifacts" / "stage2_mechanism_decision.json"
        ),
    )
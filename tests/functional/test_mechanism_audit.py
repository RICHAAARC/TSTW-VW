"""
文件用途：验证阶段 2 mechanism audit 能重建表格与决策文件。
File purpose: Validate that the stage-two mechanism audit rebuilds tables and decision artifacts.
Module type: General module
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from experiments.real_video_vae_latent_probe.mechanism_audit import (
    build_stage2_mechanism_audit_rows,
    run_stage2_mechanism_audit,
)
from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)


pytestmark = pytest.mark.quick


def test_stage2_mechanism_audit_rows_recompute_missing_threshold_decisions() -> None:
    """Validate dev and calibration rows recompute TPR from resolved thresholds.

    Args:
        None.

    Returns:
        None.
    """
    threshold_records = [
        {
            "threshold_id": "threshold:tubelet_only_anchor",
            "method_variant": "tubelet_only_anchor",
            "target_fpr": 0.001,
            "threshold_value": 0.3,
        }
    ]
    event_records = [
        _build_event_record(
            split_name="dev",
            method_variant="tubelet_only_anchor",
            base_method_variant="tubelet_only",
            attack_name="no_attack",
            sample_role="clean_negative",
            decision=False,
            s_tubelet=0.1,
            s_sync=None,
            s_final=0.1,
        ),
        _build_event_record(
            split_name="dev",
            method_variant="tubelet_only_anchor",
            base_method_variant="tubelet_only",
            attack_name="no_attack",
            sample_role="watermarked_positive",
            decision=False,
            s_tubelet=0.6,
            s_sync=None,
            s_final=0.6,
            quality_psnr=float("inf"),
            quality_ssim=1.0,
        ),
        _build_event_record(
            split_name="calibration",
            method_variant="tubelet_only_anchor",
            base_method_variant="tubelet_only",
            attack_name="no_attack",
            sample_role="clean_negative",
            decision=False,
            s_tubelet=0.05,
            s_sync=None,
            s_final=0.05,
        ),
        _build_event_record(
            split_name="calibration",
            method_variant="tubelet_only_anchor",
            base_method_variant="tubelet_only",
            attack_name="no_attack",
            sample_role="watermarked_positive",
            decision=False,
            s_tubelet=0.5,
            s_sync=None,
            s_final=0.5,
            quality_psnr=float("inf"),
            quality_ssim=1.0,
        ),
    ]

    audit_rows = build_stage2_mechanism_audit_rows(
        event_records,
        threshold_records,
        allowed_splits={"dev", "calibration"},
    )

    no_attack_positive_row = next(
        row
        for row in audit_rows
        if row["method_variant"] == "tubelet_only_anchor"
        and row["attack_name"] == "no_attack"
        and row["sample_role"] == "watermarked_positive"
    )
    no_attack_negative_row = next(
        row
        for row in audit_rows
        if row["method_variant"] == "tubelet_only_anchor"
        and row["attack_name"] == "no_attack"
        and row["sample_role"] == "clean_negative"
    )

    assert no_attack_positive_row["decision_rate"] == 1.0
    assert no_attack_positive_row["clean_positive_TPR"] == 1.0
    assert math.isinf(float(no_attack_positive_row["quality_psnr_mean"]))
    assert no_attack_positive_row["quality_ssim_mean"] == 1.0
    assert no_attack_negative_row["decision_rate"] == 0.0
    assert no_attack_negative_row["clean_negative_FPR"] == 0.0


def test_stage2_mechanism_audit_writes_expected_artifacts(tmp_path: Path) -> None:
    """Validate stage-two mechanism audit writes governed outputs.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = _build_stage2_mechanism_run_root(tmp_path)
    result = run_stage2_mechanism_audit(run_root=run_root)
    output_paths = build_real_video_vae_latent_output_paths(run_root)

    assert output_paths.stage2_mechanism_audit_table_path.exists()
    assert output_paths.stage2_score_distribution_table_path.exists()
    assert output_paths.stage2_sync_gain_table_path.exists()
    assert output_paths.stage2_mechanism_report_path.exists()
    assert output_paths.stage2_mechanism_decision_path.exists()
    assert result["Stage2ImplementationDecision"] == "PASS"
    assert result["Stage2MechanismDecision"] == "INCONCLUSIVE"
    assert "sample_count_insufficient" in result["Stage2MechanismBlockingReasons"]

    with output_paths.stage2_sync_gain_table_path.open("r", encoding="utf-8", newline="") as handle:
        sync_rows = list(csv.DictReader(handle))
    assert any(row["attack_name"] == "local_clip" for row in sync_rows)


def _build_stage2_mechanism_run_root(tmp_path: Path) -> Path:
    run_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_probe_formal"
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    for directory in (
        output_paths.event_scores_path.parent,
        output_paths.thresholds_path.parent,
        output_paths.real_video_vae_latent_governance_summary_path.parent,
        output_paths.runtime_config_path.parent,
        output_paths.report_path.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    event_records = []
    for method_variant, no_attack_positive, local_clip_positive, local_clip_negative, sync_scores in (
        ("frame_prc", True, False, False, (None, None)),
        ("tubelet_only", False, True, False, (None, None)),
        ("tubelet_sync", False, True, True, (0.45, -0.15)),
    ):
        base_method_variant = method_variant
        event_records.extend(
            [
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_tubelet=-0.2,
                    s_sync=None,
                    s_final=-0.2,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=no_attack_positive,
                    s_tubelet=0.6,
                    s_sync=sync_scores[0],
                    s_final=0.6,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=local_clip_negative,
                    s_tubelet=-0.1,
                    s_sync=sync_scores[1],
                    s_final=-0.05,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=local_clip_positive,
                    s_tubelet=0.4,
                    s_sync=sync_scores[0],
                    s_final=0.5,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="temporal_crop",
                    sample_role="attacked_negative",
                    decision=False,
                    s_tubelet=-0.2,
                    s_sync=sync_scores[1],
                    s_final=-0.1,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=method_variant == "tubelet_sync",
                    s_tubelet=0.3,
                    s_sync=sync_scores[0],
                    s_final=0.45,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="frame_dropping",
                    sample_role="attacked_negative",
                    decision=False,
                    s_tubelet=-0.15,
                    s_sync=sync_scores[1],
                    s_final=-0.1,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=method_variant == "tubelet_sync",
                    s_tubelet=0.35,
                    s_sync=sync_scores[0],
                    s_final=0.4,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="h264_compression",
                    sample_role="attacked_negative",
                    decision=False,
                    s_tubelet=-0.15,
                    s_sync=sync_scores[1],
                    s_final=-0.1,
                ),
                _build_event_record(
                    method_variant=method_variant,
                    base_method_variant=base_method_variant,
                    attack_name="h264_compression",
                    sample_role="attacked_positive",
                    decision=method_variant != "frame_prc",
                    s_tubelet=0.42,
                    s_sync=sync_scores[0],
                    s_final=0.48,
                ),
            ]
        )
    output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in event_records),
        encoding="utf-8",
    )
    output_paths.thresholds_path.write_text(
        json.dumps(
            [
                {
                    "threshold_id": f"threshold:{method_variant}",
                    "run_id": "real_video_vae_latent_probe_formal",
                    "method_variant": method_variant,
                    "target_fpr": 0.001,
                    "calibration_split": "calibration",
                    "calibration_negative_roles": ["clean_negative", "attacked_negative"],
                }
                for method_variant in ("frame_prc", "tubelet_only", "tubelet_sync")
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    output_paths.real_video_vae_latent_governance_summary_path.write_text(
        "run_id,construction_phase,method_variants_summary,attack_names_summary,target_fprs_summary,event_record_count,threshold_record_count,clean_negative_fpr_controlled,attacked_negative_fpr_reported,quality_table_non_empty,quality_metrics_runtime,temporal_table_non_empty,temporal_metrics_runtime,records_to_tables,records_to_report,records_to_failure_gallery,real_video_vae_latent_decision,blocking_reasons,next_allowed_stage\n"
        "real_video_vae_latent_probe_formal,real_video_vae_latent_probe,\"frame_prc, tubelet_only, tubelet_sync\",\"no_attack, temporal_crop, frame_dropping, local_clip, h264_compression\",0.001,30,3,True,True,True,real_video_frame_metrics,True,real_video_frame_metrics,True,True,True,PASS,,trajectory_statistic_probe\n",
        encoding="utf-8",
    )
    output_paths.runtime_config_path.write_text(
        json.dumps(
            {
                "quality_metrics": {
                    "enable_lpips": True,
                    "enable_clip_similarity": False,
                },
                "temporal_metrics": {
                    "enable_motion_consistency": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    output_paths.report_path.write_text("# placeholder\n", encoding="utf-8")
    return run_root


def _build_event_record(
    *,
    method_variant: str,
    base_method_variant: str,
    attack_name: str,
    sample_role: str,
    decision: bool,
    s_tubelet: float,
    s_sync: float | None,
    s_final: float,
    split_name: str = "test",
    threshold_id: str | None = None,
    quality_psnr: float = 28.0,
    quality_ssim: float = 0.8,
) -> dict[str, object]:
    return {
        "run_id": "real_video_vae_latent_probe_formal",
        "event_id": f"{method_variant}:{attack_name}:{sample_role}",
        "sample_id": f"sample:{method_variant}:{attack_name}:{sample_role}",
        "split": split_name,
        "sample_role": sample_role,
        "method_variant": method_variant,
        "base_method_variant": base_method_variant,
        "attack_name": attack_name,
        "decision": decision,
        "threshold_id": threshold_id,
        "target_fpr": 0.001,
        "evidence_scores": {
            "S_tubelet": s_tubelet,
            "S_sync": s_sync,
            "S_traj": None,
            "S_final": s_final,
        },
        "quality_metrics": {
            "watermarked_video_psnr": quality_psnr,
            "watermarked_video_ssim": quality_ssim,
            "watermarked_video_lpips": 0.1 if method_variant == "tubelet_sync" else None,
            "clip_similarity_score": None,
            "lpips_failure_reason": None if method_variant == "tubelet_sync" else "lpips_disabled_by_config",
        },
        "temporal_metrics": {
            "temporal_consistency_score": 0.9,
            "flicker_score": 0.1,
            "motion_consistency_score": 0.8 if method_variant == "tubelet_sync" else None,
            "motion_consistency_failure_reason": None if method_variant == "tubelet_sync" else "motion_consistency_disabled_by_config",
        },
        "mechanism_trace": {
            "construction_phase": "real_video_vae_latent_probe",
            "sync_alignment_error": 2.0 if method_variant == "tubelet_sync" else None,
            "sync_peak_rank": 4.0 if method_variant == "tubelet_sync" else None,
        },
    }

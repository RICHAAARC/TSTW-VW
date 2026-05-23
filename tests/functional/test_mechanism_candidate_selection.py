"""
文件用途：验证 real_video_vae_latent_probe mechanism calibration candidate selector 的 quick 行为。
File purpose: Validate quick behavior of the stage-two mechanism calibration candidate selector.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)
from scripts.check_results.select_stage2_mechanism_candidate import (
    _build_tubelet_sync_scan_seed,
    _resolve_projection_support_weight,
    select_stage2_mechanism_candidate,
)


pytestmark = pytest.mark.quick


def test_projection_support_weight_falls_back_to_variant_name() -> None:
    """Validate support weight parsing falls back to the calibration variant name.

    Args:
        None.

    Returns:
        None.
    """
    weight = _resolve_projection_support_weight(
        {
            "method_variant": "tubelet_only_cal_tl01_sp04x04_w075",
            "mechanism_trace": {},
        }
    )

    assert weight == 0.75


def test_tubelet_sync_scan_seed_uses_selected_candidate_defaults_for_missing_stage_grid_fields() -> None:
    """Validate tubelet_sync scan seed tolerates stage-local refine grids.

    Args:
        None.

    Returns:
        None.
    """
    selected_candidate = {
        "tubelet_length": 1,
        "tubelet_partition": {
            "spatial_patch_size": [4, 4],
        },
        "score_calibration": {
            "embedding_projection_support_weight": 0.45,
        },
    }

    seed_payload = _build_tubelet_sync_scan_seed(
        selected_candidate,
        {
            "grid": {
                "lambda_sync": [0.0, 0.025],
                "sync_search_radius": [6, 8],
            }
        },
    )

    assert seed_payload["parameter_scan"]["fusion_rule"] == ["sync_rescue_fusion"]
    assert seed_payload["parameter_scan"]["lambda_sync"] == [0.0, 0.025]
    assert seed_payload["parameter_scan"]["sync_search_radius"] == [6, 8]
    assert seed_payload["parameter_scan"]["min_sync_positive_margin"] == [0.0]
    assert seed_payload["parameter_scan"]["min_sync_alignment_coverage_ratio"] == [0.5]
    assert seed_payload["parameter_scan"]["min_sync_alignment_matched_count"] == [1]
    assert seed_payload["parameter_scan"]["min_sync_candidate_score"] == [0.0]


def test_mechanism_candidate_selector_uses_dev_and_calibration_only(
    tmp_path: Path,
) -> None:
    """Validate candidate selection ignores the forbidden test split.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "runs" / "real_video_vae_latent_probe_formal"
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)

    grid_config_path = tmp_path / "stage2_grid.json"
    mechanism_config_path = tmp_path / "stage2_gate.json"
    grid_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "calibration_purpose": "stage2_mechanism_effect_calibration",
                "allowed_splits": ["dev", "calibration"],
                "forbidden_splits": ["test"],
                "grid": {
                    "tubelet_length": [1, 4],
                    "spatial_patch_size": [[4, 4], [8, 8]],
                    "embedding_projection_support_weight": [0.25, 0.45],
                    "lambda_sync": [0.0, 0.1],
                    "sync_search_radius": [4, 8],
                    "min_sync_positive_margin": [0.0, 0.12],
                    "min_sync_alignment_coverage_ratio": [0.125, 0.5],
                    "min_sync_alignment_matched_count": [1, 4],
                    "fusion_rule": ["sync_rescue_fusion", "calibrated_tubelet_sync"]
                },
                "selection_metrics": [
                    "no_attack_clean_positive_tpr",
                    "clean_negative_fpr",
                    "max_attacked_negative_fpr"
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mechanism_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "required_mechanism_attacks": [
                    "no_attack",
                    "temporal_crop",
                    "frame_dropping",
                    "local_clip"
                ],
                "max_clean_negative_fpr": 0.05,
                "max_attacked_negative_fpr": 0.1,
                "min_no_attack_clean_positive_tpr": 0.5
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    records = []
    for split_name in ("dev", "calibration"):
        records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only",
                    base_method_variant="tubelet_only",
                    tubelet_length=4,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only",
                    base_method_variant="tubelet_only",
                    tubelet_length=4,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_lt01",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_lt01",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only",
                    base_method_variant="tubelet_only",
                    tubelet_length=4,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only",
                    base_method_variant="tubelet_only",
                    tubelet_length=4,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_lt01",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_lt01",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only",
                    base_method_variant="tubelet_only",
                    tubelet_length=4,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_lt01",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only",
                    base_method_variant="tubelet_only",
                    tubelet_length=4,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_lt01",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=4,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.1,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=4,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=False,
                    s_sync=0.05,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=4,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.2,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=4,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=False,
                    s_sync=0.1,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.05,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                    sync_confidence_min_margin=0.12,
                    sync_confidence_min_coverage_ratio=0.125,
                    sync_confidence_min_matched_count=4,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.35,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.3,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.32,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.1,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.28,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls100_frcal_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=True,
                    s_sync=0.15,
                    fusion_rule="calibrated_tubelet_sync",
                    lambda_sync=0.1,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls100_frcal_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.33,
                    fusion_rule="calibrated_tubelet_sync",
                    lambda_sync=0.1,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls100_frcal_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.29,
                    fusion_rule="calibrated_tubelet_sync",
                    lambda_sync=0.1,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls100_frcal_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.31,
                    fusion_rule="calibrated_tubelet_sync",
                    lambda_sync=0.1,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls100_frcal_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=True,
                    s_sync=0.12,
                    fusion_rule="calibrated_tubelet_sync",
                    lambda_sync=0.1,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls100_frcal_sync",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.25,
                    fusion_rule="calibrated_tubelet_sync",
                    lambda_sync=0.1,
                ),
            ]
        )
    records.extend(
        [
            _build_event_record(
                split_name="test",
                method_variant="tubelet_only",
                base_method_variant="tubelet_only",
                tubelet_length=4,
                attack_name="no_attack",
                sample_role="watermarked_positive",
                decision=True,
            ),
            _build_event_record(
                split_name="test",
                method_variant="tubelet_only_lt01",
                base_method_variant="tubelet_only",
                tubelet_length=1,
                attack_name="no_attack",
                sample_role="watermarked_positive",
                decision=False,
            ),
        ]
    )
    output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    output_paths.thresholds_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.thresholds_path.write_text(
        json.dumps(
            [
                {
                    "threshold_id": "threshold:tubelet_only",
                    "method_variant": "tubelet_only",
                    "target_fpr": 0.001,
                    "threshold_value": 0.5,
                },
                {
                    "threshold_id": "threshold:tubelet_only_lt01",
                    "method_variant": "tubelet_only_lt01",
                    "target_fpr": 0.001,
                    "threshold_value": 0.4,
                },
                {
                    "threshold_id": "threshold:tubelet_sync",
                    "method_variant": "tubelet_sync",
                    "target_fpr": 0.001,
                    "threshold_value": 0.5,
                },
                {
                    "threshold_id": "threshold:tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_frsync_rescue",
                    "method_variant": "tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_frsync_rescue",
                    "target_fpr": 0.001,
                    "threshold_value": 0.4,
                },
                {
                    "threshold_id": "threshold:tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls100_frcal_sync",
                    "method_variant": "tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls100_frcal_sync",
                    "target_fpr": 0.001,
                    "threshold_value": 0.5,
                },
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = select_stage2_mechanism_candidate(
        run_root=run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
    )

    assert result["selected_tubelet_only_candidate"]["method_variant"] == "tubelet_only_lt01"
    assert result["selected_tubelet_only_candidate"]["tubelet_length"] == 1
    assert result["observed_forbidden_splits"] == ["test"]
    assert result["tubelet_sync_scan_seed"]["seed_method_config"]["tubelet_length"] == 1
    assert result["tubelet_sync_scan_seed"]["parameter_scan"]["lambda_sync"] == [0.0, 0.1]
    assert result["tubelet_sync_scan_seed"]["parameter_scan"]["min_sync_positive_margin"] == [0.0, 0.12]
    assert result["tubelet_sync_scan_seed"]["parameter_scan"]["min_sync_candidate_score"] == [0.0]
    assert result["selected_tubelet_sync_candidate"] is None
    assert result["selection_completion_status"] == "incomplete_no_eligible_tubelet_sync_candidate"
    assert result["selection_blocking_reason"] == "no_tubelet_sync_candidate_passes_selection_gate"
    assert Path(result["grid_output_path"]).exists()
    assert Path(result["report_path"]).exists()
    assert Path(result["output_path"]).exists()
    assert result["selection_scope"] == "full"
    assert len(result["top_tubelet_only_candidates"]) >= 1
    assert len(result["top_tubelet_sync_candidates"]) >= 1
    assert result["parameter_interval_summary"]["tubelet_sync"]["lambda_sync"]["min"] == 0.0


def test_mechanism_candidate_selector_prefers_headroom_anchor_over_saturated_anchor(
    tmp_path: Path,
) -> None:
    """Validate tubelet-only selection prefers headroom-bearing anchors.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "runs" / "headroom_anchor"
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)

    grid_config_path = tmp_path / "headroom_grid.json"
    mechanism_config_path = tmp_path / "headroom_gate.json"
    grid_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "calibration_purpose": "stage2_mechanism_effect_calibration",
                "allowed_splits": ["dev", "calibration"],
                "forbidden_splits": ["test"],
                "grid": {
                    "tubelet_length": [1],
                    "spatial_patch_size": [[4, 4]],
                    "embedding_projection_support_weight": [0.45],
                    "lambda_sync": [0.0],
                    "sync_search_radius": [4],
                    "min_sync_positive_margin": [0.0],
                    "min_sync_alignment_coverage_ratio": [0.125],
                    "min_sync_alignment_matched_count": [1],
                    "fusion_rule": ["sync_rescue_fusion"]
                },
                "selection_metrics": [
                    "no_attack_clean_positive_tpr",
                    "clean_negative_fpr",
                    "max_attacked_negative_fpr"
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mechanism_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "required_mechanism_attacks": [
                    "no_attack",
                    "temporal_crop",
                    "frame_dropping",
                    "local_clip"
                ],
                "required_sync_gain_attacks": ["temporal_crop", "local_clip"],
                "max_clean_negative_fpr": 0.05,
                "max_attacked_negative_fpr": 0.1,
                "min_no_attack_clean_positive_tpr": 0.5,
                "absolute_rescue_tpr_threshold": 1.0,
                "sync_gain_saturation_threshold": 1.0
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    records: list[dict[str, object]] = []
    for split_name in ("dev", "calibration"):
        records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_saturated_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_saturated_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_saturated_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_saturated_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_saturated_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_saturated_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_saturated_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_headroom_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_headroom_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_headroom_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=(split_name == "calibration"),
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_headroom_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_headroom_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=(split_name == "calibration"),
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_headroom_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_headroom_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                ),
            ]
        )

    output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    result = select_stage2_mechanism_candidate(
        run_root=run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
        selection_scope="tubelet_only",
        top_candidate_limit=2,
    )

    assert result["selected_tubelet_only_candidate"]["method_variant"] == (
        "tubelet_only_headroom_anchor"
    )
    assert result["selected_tubelet_only_candidate"]["candidate_selection_status"] == (
        "strong_anchor_with_headroom"
    )
    assert result["top_tubelet_only_candidates"][0]["method_variant"] == (
        "tubelet_only_headroom_anchor"
    )
    assert result["top_tubelet_only_candidates"][1]["method_variant"] == (
        "tubelet_only_saturated_anchor"
    )


def test_mechanism_candidate_selector_supports_stage_scopes(
    tmp_path: Path,
) -> None:
    """Validate stage-scoped tubelet-only and tubelet-sync candidate selection.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    anchor_run_root = tmp_path / "runs" / "stage1_anchor"
    sync_run_root = tmp_path / "runs" / "stage2_sync"
    anchor_output_paths = build_real_video_vae_latent_output_paths(anchor_run_root)
    sync_output_paths = build_real_video_vae_latent_output_paths(sync_run_root)
    anchor_output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)
    sync_output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)

    grid_config_path = tmp_path / "stage_scope_grid.json"
    mechanism_config_path = tmp_path / "stage_scope_gate.json"
    grid_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "calibration_purpose": "stage2_mechanism_effect_calibration",
                "allowed_splits": ["dev", "calibration"],
                "forbidden_splits": ["test"],
                "grid": {
                    "tubelet_length": [1, 2],
                    "spatial_patch_size": [[4, 4]],
                    "embedding_projection_support_weight": [0.45, 0.75],
                    "lambda_sync": [0.0, 0.05],
                    "sync_search_radius": [4, 8],
                    "min_sync_positive_margin": [0.0, 0.12],
                    "min_sync_alignment_coverage_ratio": [0.125, 0.5],
                    "min_sync_alignment_matched_count": [1, 4],
                    "fusion_rule": ["sync_rescue_fusion"],
                },
                "selection_metrics": [
                    "no_attack_clean_positive_tpr",
                    "clean_negative_fpr",
                    "max_attacked_negative_fpr",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mechanism_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "required_mechanism_attacks": [
                    "no_attack",
                    "temporal_crop",
                    "frame_dropping",
                    "local_clip",
                ],
                "max_clean_negative_fpr": 0.05,
                "max_attacked_negative_fpr": 0.1,
                "min_no_attack_clean_positive_tpr": 0.5,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    anchor_records = []
    for split_name in ("dev", "calibration"):
        anchor_records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_a",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_a",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_a",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_a",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_a",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_b",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_b",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_b",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_b",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_b",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_a",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor_a",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                ),
            ]
        )
    anchor_output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in anchor_records),
        encoding="utf-8",
    )

    anchor_result = select_stage2_mechanism_candidate(
        run_root=anchor_run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
        selection_scope="tubelet_only",
        top_candidate_limit=2,
    )

    assert anchor_result["selection_scope"] == "tubelet_only"
    assert anchor_result["selected_tubelet_only_candidate"]["method_variant"] == "tubelet_only_anchor_a"
    assert anchor_result["selected_tubelet_sync_candidate"] is None
    assert len(anchor_result["top_tubelet_only_candidates"]) == 2

    sync_records = []
    for split_name in ("dev", "calibration"):
        sync_records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.03,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.32,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.28,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=False,
                    s_sync=0.08,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.05,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.26,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls050_mg120_cv500_mc04_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=True,
                    s_sync=0.2,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.05,
                    sync_confidence_min_margin=0.12,
                    sync_confidence_min_coverage_ratio=0.5,
                    sync_confidence_min_matched_count=4,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls050_mg120_cv500_mc04_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.18,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.05,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls050_mg120_cv500_mc04_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=False,
                    s_sync=0.1,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.05,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls050_mg120_cv500_mc04_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=False,
                    s_sync=0.05,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.05,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls050_mg120_cv500_mc04_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=True,
                    s_sync=0.16,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.05,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr08_ls050_mg120_cv500_mc04_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=False,
                    s_sync=0.09,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.05,
                ),
            ]
        )
    sync_output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in sync_records),
        encoding="utf-8",
    )

    sync_result = select_stage2_mechanism_candidate(
        run_root=sync_run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
        selection_scope="tubelet_sync",
        selected_tubelet_only_candidate=anchor_result["selected_tubelet_only_candidate"],
        top_candidate_limit=2,
    )

    assert sync_result["selection_scope"] == "tubelet_sync"
    assert sync_result["selected_tubelet_only_candidate"]["method_variant"] == "tubelet_only_anchor_a"
    assert sync_result["selected_tubelet_sync_candidate"] is None
    assert (
        sync_result["selection_completion_status"]
        == "incomplete_no_eligible_tubelet_sync_candidate"
    )
    assert (
        sync_result["selection_blocking_reason"]
        == "no_tubelet_sync_candidate_passes_selection_gate"
    )
    assert len(sync_result["top_tubelet_sync_candidates"]) == 2
    assert sync_result["parameter_interval_summary"]["tubelet_sync"]["lambda_sync"]["max"] == 0.05


def test_mechanism_candidate_selector_uses_any_of_k_sync_gain_policy(
    tmp_path: Path,
) -> None:
    """Validate a single required attack gain can satisfy the governed sync gain policy.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "runs" / "any_of_k_sync"
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.thresholds_path.parent.mkdir(parents=True, exist_ok=True)

    grid_config_path = tmp_path / "any_of_k_grid.json"
    mechanism_config_path = tmp_path / "any_of_k_gate.json"
    grid_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "calibration_purpose": "stage2_mechanism_effect_calibration",
                "allowed_splits": ["dev", "calibration"],
                "forbidden_splits": ["test"],
                "grid": {
                    "tubelet_length": [1],
                    "spatial_patch_size": [[4, 4]],
                    "embedding_projection_support_weight": [0.45],
                    "lambda_sync": [0.0],
                    "sync_search_radius": [4],
                    "min_sync_positive_margin": [0.0],
                    "min_sync_alignment_coverage_ratio": [0.125],
                    "min_sync_alignment_matched_count": [1],
                    "fusion_rule": ["sync_rescue_fusion"],
                },
                "selection_metrics": [
                    "no_attack_clean_positive_tpr",
                    "clean_negative_fpr",
                    "max_attacked_negative_fpr",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mechanism_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "required_mechanism_attacks": [
                    "no_attack",
                    "temporal_crop",
                    "frame_dropping",
                    "local_clip",
                ],
                "required_sync_gain_attacks": ["temporal_crop", "local_clip"],
                "sync_gain_policy": "any_required_temporal_attack",
                "min_required_sync_gain_attack_count": 1,
                "max_clean_negative_fpr": 0.05,
                "max_attacked_negative_fpr": 0.1,
                "min_no_attack_clean_positive_tpr": 0.5,
                "min_mean_temporal_sync_gain": 0.05,
                "require_quality_not_collapsed": True,
                "min_watermarked_video_psnr": 20.0,
                "min_watermarked_video_ssim": 0.5,
                "sync_gain_saturation_threshold": 1.0,
                "absolute_rescue_tpr_threshold": 1.0,
                "leakage_exceeded_multiplier": 2.0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    records = []
    for split_name in ("dev", "calibration"):
        records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.04,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.22,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.3,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="frame_dropping",
                    sample_role="attacked_positive",
                    decision=False,
                    s_sync=0.08,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.18,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.01,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.01,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
            ]
        )

    output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    output_paths.thresholds_path.write_text(
        json.dumps(
            [
                {
                    "threshold_id": "threshold:tubelet_only_anchor",
                    "method_variant": "tubelet_only_anchor",
                    "target_fpr": 0.001,
                    "threshold_value": 0.4,
                },
                {
                    "threshold_id": "threshold:tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    "method_variant": "tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    "target_fpr": 0.001,
                    "threshold_value": 0.4,
                },
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = select_stage2_mechanism_candidate(
        run_root=run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
    )

    selected_sync_candidate = result["selected_tubelet_sync_candidate"]
    assert selected_sync_candidate["candidate_selection_status"] == "eligible"
    assert selected_sync_candidate["incremental_gain_status"] == "positive_gain"
    assert selected_sync_candidate["sync_rescue_decision"] == "PASS"
    assert selected_sync_candidate["sync_leakage_decision"] == "PASS"
    assert selected_sync_candidate["metrics"]["local_clip_saturated_anchor"] is True
    assert selected_sync_candidate["metrics"]["local_clip_anchor_headroom"] == 0.0


def test_mechanism_candidate_selector_returns_no_best_effort_sync_candidate_without_eligible_row(
    tmp_path: Path,
) -> None:
    """Validate sync selection stops exporting best-effort rows when no eligible candidate exists.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    anchor_run_root = tmp_path / "runs" / "controlled_frontier_anchor"
    sync_run_root = tmp_path / "runs" / "controlled_frontier_sync"
    anchor_output_paths = build_real_video_vae_latent_output_paths(anchor_run_root)
    sync_output_paths = build_real_video_vae_latent_output_paths(sync_run_root)
    anchor_output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)
    sync_output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)

    grid_config_path = tmp_path / "controlled_frontier_grid.json"
    mechanism_config_path = tmp_path / "controlled_frontier_gate.json"
    grid_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "calibration_purpose": "stage2_mechanism_effect_calibration",
                "allowed_splits": ["dev", "calibration"],
                "forbidden_splits": ["test"],
                "grid": {
                    "tubelet_length": [2],
                    "spatial_patch_size": [[4, 4]],
                    "embedding_projection_support_weight": [0.25],
                    "lambda_sync": [0.0, 0.025],
                    "sync_search_radius": [8],
                    "min_sync_positive_margin": [0.0],
                    "min_sync_alignment_coverage_ratio": [0.0625],
                    "min_sync_alignment_matched_count": [1],
                    "fusion_rule": ["sync_rescue_fusion"],
                },
                "selection_metrics": [
                    "no_attack_clean_positive_tpr",
                    "clean_negative_fpr",
                    "max_attacked_negative_fpr",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mechanism_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "required_mechanism_attacks": [
                    "no_attack",
                    "temporal_crop",
                    "local_clip",
                ],
                "required_sync_gain_attacks": ["temporal_crop", "local_clip"],
                "sync_gain_policy": "any_required_temporal_attack",
                "min_required_sync_gain_attack_count": 1,
                "max_clean_negative_fpr": 0.05,
                "max_attacked_negative_fpr": 0.1,
                "min_no_attack_clean_positive_tpr": 0.5,
                "min_mean_temporal_sync_gain": 0.05,
                "require_quality_not_collapsed": True,
                "min_watermarked_video_psnr": 20.0,
                "min_watermarked_video_ssim": 0.5,
                "sync_gain_saturation_threshold": 1.0,
                "absolute_rescue_tpr_threshold": 1.0,
                "leakage_exceeded_multiplier": 2.0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    anchor_records = []
    for split_name in ("dev", "calibration"):
        anchor_records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_controlled_frontier_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_controlled_frontier_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_controlled_frontier_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_controlled_frontier_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_controlled_frontier_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="temporal_crop",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_controlled_frontier_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                ),
            ]
        )

    anchor_output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in anchor_records),
        encoding="utf-8",
    )

    anchor_result = select_stage2_mechanism_candidate(
        run_root=anchor_run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
        selection_scope="tubelet_only",
        top_candidate_limit=1,
    )

    sync_records = []
    for split_name in ("dev", "calibration"):
        sync_records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls000_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.02,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls000_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.28,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls000_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.16,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls000_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.03,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg120_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.03,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg120_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.34,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg120_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.24,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg120_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.18,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg120_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=True,
                    s_sync=0.19,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
            ]
        )

    sync_output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in sync_records),
        encoding="utf-8",
    )

    sync_result = select_stage2_mechanism_candidate(
        run_root=sync_run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
        selection_scope="tubelet_sync",
        selected_tubelet_only_candidate=anchor_result["selected_tubelet_only_candidate"],
        top_candidate_limit=2,
    )

    assert sync_result["selected_tubelet_sync_candidate"] is None
    assert (
        sync_result["selection_completion_status"]
        == "incomplete_no_eligible_tubelet_sync_candidate"
    )
    assert (
        sync_result["selection_blocking_reason"]
        == "no_tubelet_sync_candidate_passes_selection_gate"
    )
    assert sync_result["top_tubelet_sync_candidates"][1]["method_variant"] == (
        "tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg120_cv062_mc01_frsync_rescue"
    )
    assert (
        sync_result["top_tubelet_sync_candidates"][1]["candidate_selection_status"]
        == "rescue_with_leakage"
    )
    assert (
        sync_result["top_tubelet_sync_candidates"][1]["negative_leakage_status"]
        == "leakage_exceeded"
    )


def test_mechanism_candidate_selector_prefers_strict_sync_seal_over_higher_gain_leakage(
    tmp_path: Path,
) -> None:
    """Validate sync selection rejects local_clip negative sync-confidence leakage even when gain is higher.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "runs" / "strict_sync_seal"
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)

    grid_config_path = tmp_path / "strict_sync_seal_grid.json"
    mechanism_config_path = tmp_path / "strict_sync_seal_gate.json"
    grid_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "calibration_purpose": "stage2_mechanism_effect_calibration",
                "allowed_splits": ["dev", "calibration"],
                "forbidden_splits": ["test"],
                "grid": {
                    "tubelet_length": [2],
                    "spatial_patch_size": [[4, 4]],
                    "embedding_projection_support_weight": [0.25],
                    "lambda_sync": [0.025],
                    "sync_search_radius": [8],
                    "min_sync_positive_margin": [0.0],
                    "min_sync_alignment_coverage_ratio": [0.0625],
                    "min_sync_alignment_matched_count": [1],
                    "min_sync_candidate_score": [0.0, 0.6],
                    "fusion_rule": ["sync_rescue_fusion"],
                },
                "selection_metrics": [
                    "no_attack_clean_positive_tpr",
                    "clean_negative_fpr",
                    "max_attacked_negative_fpr",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mechanism_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "required_mechanism_attacks": [
                    "no_attack",
                    "temporal_crop",
                    "local_clip",
                ],
                "required_sync_gain_attacks": ["temporal_crop", "local_clip"],
                "sync_gain_policy": "any_required_temporal_attack",
                "min_required_sync_gain_attack_count": 1,
                "max_clean_negative_fpr": 0.05,
                "max_attacked_negative_fpr": 0.1,
                "min_no_attack_clean_positive_tpr": 0.5,
                "min_mean_temporal_sync_gain": 0.05,
                "require_quality_not_collapsed": True,
                "min_watermarked_video_psnr": 20.0,
                "min_watermarked_video_ssim": 0.5,
                "sync_gain_saturation_threshold": 1.0,
                "absolute_rescue_tpr_threshold": 1.0,
                "leakage_exceeded_multiplier": 2.0,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    records: list[dict[str, object]] = []
    for split_name in ("dev", "calibration"):
        records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_strict_sync_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_strict_sync_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_strict_sync_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_strict_sync_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_strict_sync_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="temporal_crop",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_only_strict_sync_anchor",
                    base_method_variant="tubelet_only",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.03,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.34,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.24,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.18,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.19,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                    sync_confident=True,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_cs600_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.03,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_cs600_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.31,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_cs600_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=False,
                    s_sync=0.08,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_cs600_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.16,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_cs600_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=2,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.04,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.025,
                    sync_confident=False,
                ),
            ]
        )

    output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    result = select_stage2_mechanism_candidate(
        run_root=run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
    )

    assert result["selected_tubelet_only_candidate"]["method_variant"] == (
        "tubelet_only_strict_sync_anchor"
    )
    assert result["selected_tubelet_sync_candidate"]["method_variant"] == (
        "tubelet_sync_cal_tl02_sp04x04_w025_sr08_ls025_mg000_cv062_mc01_cs600_frsync_rescue"
    )
    assert result["selected_tubelet_sync_candidate"]["sync_search"]["min_sync_candidate_score"] == 0.6
    assert result["selection_completion_status"] == "complete"


def test_mechanism_candidate_selector_reports_incompatible_sync_stage_rows(
    tmp_path: Path,
) -> None:
    """Validate sync-only selection returns a governed partial result when no rows match the selected anchor.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "runs" / "incompatible_sync_stage"
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    output_paths.event_scores_path.parent.mkdir(parents=True, exist_ok=True)

    grid_config_path = tmp_path / "incompatible_sync_grid.json"
    mechanism_config_path = tmp_path / "incompatible_sync_gate.json"
    grid_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "calibration_purpose": "stage2_mechanism_effect_calibration",
                "allowed_splits": ["dev", "calibration"],
                "forbidden_splits": ["test"],
                "grid": {
                    "tubelet_length": [1, 4],
                    "spatial_patch_size": [[4, 4]],
                    "embedding_projection_support_weight": [0.45, 0.75],
                    "lambda_sync": [0.0],
                    "sync_search_radius": [4],
                    "min_sync_positive_margin": [0.0],
                    "min_sync_alignment_coverage_ratio": [0.125],
                    "min_sync_alignment_matched_count": [1],
                    "fusion_rule": ["sync_rescue_fusion"],
                },
                "selection_metrics": [
                    "no_attack_clean_positive_tpr",
                    "clean_negative_fpr",
                    "max_attacked_negative_fpr",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mechanism_config_path.write_text(
        json.dumps(
            {
                "construction_phase": "real_video_vae_latent_probe",
                "required_mechanism_attacks": [
                    "no_attack",
                    "temporal_crop",
                    "frame_dropping",
                    "local_clip",
                ],
                "required_sync_gain_attacks": ["temporal_crop", "local_clip"],
                "sync_gain_policy": "any_required_temporal_attack",
                "min_required_sync_gain_attack_count": 1,
                "max_clean_negative_fpr": 0.05,
                "max_attacked_negative_fpr": 0.1,
                "min_no_attack_clean_positive_tpr": 0.5,
                "min_mean_temporal_sync_gain": 0.05,
                "require_quality_not_collapsed": True,
                "min_watermarked_video_psnr": 20.0,
                "min_watermarked_video_ssim": 0.5,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    records = []
    for split_name in ("dev", "calibration"):
        records.extend(
            [
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="clean_negative",
                    decision=False,
                    s_sync=0.03,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="no_attack",
                    sample_role="watermarked_positive",
                    decision=True,
                    s_sync=0.3,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="temporal_crop",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.28,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_positive",
                    decision=True,
                    s_sync=0.26,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
                _build_event_record(
                    split_name=split_name,
                    method_variant="tubelet_sync_cal_tl01_sp04x04_w045_sr04_ls000_mg000_cv125_mc01_frsync_rescue",
                    base_method_variant="tubelet_sync",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
                    decision=False,
                    s_sync=0.01,
                    fusion_rule="sync_rescue_fusion",
                    lambda_sync=0.0,
                ),
            ]
        )
    output_paths.event_scores_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    result = select_stage2_mechanism_candidate(
        run_root=run_root,
        grid_config_path=grid_config_path,
        mechanism_config_path=mechanism_config_path,
        selection_scope="tubelet_sync",
        selected_tubelet_only_candidate={
            "candidate_status": "best_effort_candidate_selected",
            "method_variant": "tubelet_only_cal_tl04_sp04x04_w075",
            "base_method_variant": "tubelet_only",
            "tubelet_length": 4,
            "tubelet_partition": {"spatial_patch_size": [4, 4]},
            "score_calibration": {"embedding_projection_support_weight": 0.75},
            "metrics": {
                "no_attack_clean_negative_fpr": 0.0,
                "no_attack_clean_positive_tpr": 1.0,
                "max_attacked_negative_fpr": 0.5,
                "temporal_crop_attacked_positive_tpr": 1.0,
                "frame_dropping_attacked_positive_tpr": 1.0,
                "local_clip_attacked_positive_tpr": 1.0,
            },
        },
    )

    assert result["selected_tubelet_sync_candidate"] is None
    assert result["selection_completion_status"] == "incomplete_no_compatible_tubelet_sync_rows"
    assert result["selection_blocking_reason"] == "selected_anchor_not_covered_by_sync_stage_records"
    assert result["selection_blocking_details"]["selected_anchor_signature"]["tubelet_length"] == 4
    assert result["selection_blocking_details"]["selected_anchor_signature"]["embedding_projection_support_weight"] == 0.75
    assert result["selection_blocking_details"]["matching_sync_stage_signature_count"] == 0
    assert result["top_tubelet_sync_candidates"] == []


def _build_event_record(
    *,
    split_name: str,
    method_variant: str,
    base_method_variant: str,
    tubelet_length: int,
    attack_name: str,
    sample_role: str,
    decision: bool,
    s_sync: float | None = None,
    fusion_rule: str = "calibrated_tubelet_sync",
    lambda_sync: float = 0.1,
    sync_confidence_min_margin: float = 0.0,
    sync_confidence_min_coverage_ratio: float = 0.5,
    sync_confidence_min_matched_count: int = 1,
    sync_confident: bool | None = None,
) -> dict[str, object]:
    event_record: dict[str, object] = {
        "run_id": "real_video_vae_latent_probe_formal",
        "event_id": f"{split_name}:{method_variant}:{attack_name}:{sample_role}",
        "split": split_name,
        "sample_id": f"sample:{split_name}:{method_variant}:{attack_name}:{sample_role}",
        "sample_role": sample_role,
        "method_variant": method_variant,
        "base_method_variant": base_method_variant,
        "attack_name": attack_name,
        "decision": decision,
        "tubelet_length": tubelet_length,
        "target_fpr": 0.001,
        "evidence_scores": {
            "S_tubelet": 0.6 if decision else 0.2,
            "S_sync": s_sync,
            "S_traj": None,
            "S_final": 0.6 if decision else 0.2
        },
        "quality_metrics": {
            "watermarked_video_psnr": 24.0,
            "watermarked_video_ssim": 0.7
        },
        "temporal_metrics": {
            "temporal_consistency_score": 0.95,
            "flicker_score": 0.05
        },
        "mechanism_trace": {
            "construction_phase": "real_video_vae_latent_probe",
            "tubelet_length": tubelet_length,
            "spatial_patch_size": [4, 4],
            "embedding_projection_support_weight": 0.45,
            "fusion_rule": fusion_rule,
            "lambda_sync": lambda_sync,
            "sync_confidence_min_margin": sync_confidence_min_margin,
            "sync_confidence_min_coverage_ratio": sync_confidence_min_coverage_ratio,
            "sync_confidence_min_matched_count": sync_confidence_min_matched_count,
        }
    }
    if sync_confident is not None:
        event_record["sync_confident"] = bool(sync_confident)
    return event_record
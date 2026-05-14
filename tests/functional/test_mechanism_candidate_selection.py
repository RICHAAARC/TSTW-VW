"""
文件用途：验证 stage2 mechanism calibration candidate selector 的 quick 行为。
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
    select_stage2_mechanism_candidate,
)


pytestmark = pytest.mark.quick


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
                    method_variant="tubelet_only_lt01",
                    base_method_variant="tubelet_only",
                    tubelet_length=1,
                    attack_name="local_clip",
                    sample_role="attacked_negative",
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
    assert Path(result["grid_output_path"]).exists()
    assert Path(result["report_path"]).exists()
    assert Path(result["output_path"]).exists()


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
) -> dict[str, object]:
    return {
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
            "embedding_projection_support_weight": 0.45
        }
    }
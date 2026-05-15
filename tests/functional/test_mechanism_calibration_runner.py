"""
文件用途：验证 stage2 mechanism calibration runner 的 orchestration 行为。
File purpose: Validate orchestration behavior of the stage-two mechanism calibration runner.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import experiments.real_video_vae_latent_probe.mechanism_calibration_runner as calibration_runner_module

from experiments.real_video_vae_latent_probe.mechanism_calibration_runner import (
    run_stage2_mechanism_calibration,
)


pytestmark = pytest.mark.quick


@pytest.mark.unit
def test_stage2_mechanism_calibration_runner_builds_temp_configs_and_candidate_method(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate calibration runner emits governed temp configs and a candidate sync method.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    captured_runner_call: dict[str, object] = {}

    class _FakeRunner:
        def __init__(self, repository_root: str | Path) -> None:
            captured_runner_call["repository_root"] = str(repository_root)

        def run(self, **kwargs: object) -> dict[str, object]:
            captured_runner_call["kwargs"] = dict(kwargs)
            return {"status": "ok"}

    monkeypatch.setattr(calibration_runner_module, "RealVideoVaeLatentRunner", _FakeRunner)
    monkeypatch.setattr(
        calibration_runner_module,
        "select_stage2_mechanism_candidate",
        lambda **kwargs: {
            "output_path": str(tmp_path / "selected_candidate.json"),
            "report_path": str(tmp_path / "selected_candidate.md"),
            "grid_output_path": str(tmp_path / "selected_candidate.csv"),
            "selected_tubelet_only_candidate": {
                "candidate_status": "fpr_controlled_candidate_selected",
                "method_variant": "tubelet_only_calibration_tl01_sp04x04_w045",
                "tubelet_length": 1,
                "tubelet_partition": {"spatial_patch_size": [4, 4]},
                "score_calibration": {"embedding_projection_support_weight": 0.45},
                "metrics": {
                    "no_attack_clean_negative_fpr": 0.0,
                    "no_attack_clean_positive_tpr": 1.0,
                    "max_attacked_negative_fpr": 0.0,
                    "temporal_crop_attacked_positive_tpr": 0.9,
                    "frame_dropping_attacked_positive_tpr": 0.9,
                    "local_clip_attacked_positive_tpr": 0.9,
                },
            },
            "selected_tubelet_sync_candidate": {
                "candidate_status": "sync_gain_candidate_selected",
                "method_variant": "tubelet_sync_real_video_vae_candidate",
                "base_method_variant": "tubelet_sync",
                "tubelet_length": 1,
                "tubelet_partition": {"spatial_patch_size": [4, 4]},
                "score_calibration": {"embedding_projection_support_weight": 0.45},
                "fusion_rule": "sync_rescue_fusion",
                "lambda_sync": 0.05,
                "sync_search": {
                    "offset_search_min": -8,
                    "offset_search_max": 8,
                },
                "metrics": {
                    "no_attack_clean_negative_fpr": 0.0,
                    "no_attack_clean_positive_tpr": 1.0,
                    "max_attacked_negative_fpr": 0.0,
                    "temporal_crop_attacked_positive_tpr": 1.0,
                    "frame_dropping_attacked_positive_tpr": 1.0,
                    "local_clip_attacked_positive_tpr": 1.0,
                    "quality_psnr_mean": 24.0,
                    "quality_ssim_mean": 0.7,
                    "temporal_crop_sync_gain": 0.1,
                    "frame_dropping_sync_gain": 0.1,
                    "local_clip_sync_gain": 0.1,
                    "mean_temporal_sync_gain": 0.1,
                },
            },
            "tubelet_sync_scan_seed": {
                "base_method_variant": "tubelet_sync",
                "recommended_method_variant": "tubelet_sync_real_video_vae_candidate",
                "parameter_scan": {
                    "fusion_rule": ["sync_rescue_fusion", "calibrated_tubelet_sync"],
                    "lambda_sync": [0.0, 0.05, 0.1],
                    "sync_search_radius": [4, 8, 12],
                },
            },
            "kwargs": kwargs,
        },
    )

    candidate_method_config_path = tmp_path / "tubelet_sync_real_video_vae_candidate.json"
    run_root = tmp_path / "mechanism_calibration_run"
    summary = run_stage2_mechanism_calibration(
        run_root=run_root,
        runtime_profile="formal",
        samples_per_role=2,
        batch_size_frames=8,
        output_method_config_path=candidate_method_config_path,
    )

    protocol_config_path = Path(summary["protocol_config_path"])
    ablation_config_path = Path(summary["ablation_config_path"])
    calibration_summary_path = Path(summary["calibration_summary_path"])
    assert protocol_config_path.exists()
    assert ablation_config_path.exists()
    assert calibration_summary_path.exists()

    protocol_payload = json.loads(protocol_config_path.read_text(encoding="utf-8"))
    assert protocol_payload["splits"] == ["dev", "calibration"]
    assert protocol_payload["splits_by_profile"]["formal"] == ["dev", "calibration"]

    ablation_payload = json.loads(ablation_config_path.read_text(encoding="utf-8"))
    assert ablation_payload["method_config_paths"]
    assert ablation_payload["tubelet_length_sweep_variant"] is None
    assert ablation_payload["tubelet_length_sweep_formal"] == []
    assert any(
        method_variant.startswith("tubelet_only_cal_")
        for method_variant in ablation_payload["method_variants"]
    )
    assert any(
        method_variant.startswith("tubelet_sync_cal_")
        for method_variant in ablation_payload["method_variants"]
    )

    runner_kwargs = captured_runner_call["kwargs"]
    assert runner_kwargs["protocol_config_path"] == protocol_config_path
    assert runner_kwargs["ablation_config_path"] == ablation_config_path
    assert runner_kwargs["runtime_profile_override"] == "formal"
    assert runner_kwargs["samples_per_role"] == 2
    assert runner_kwargs["batch_size_frames"] == 8

    candidate_method_config = json.loads(
        candidate_method_config_path.read_text(encoding="utf-8")
    )
    assert candidate_method_config["method_variant"] == "tubelet_sync_real_video_vae_candidate"
    assert candidate_method_config["target_construction_phase"] == "real_video_vae_latent_probe"
    assert candidate_method_config["tubelet_length"] == 1
    assert candidate_method_config["tubelet_partition"]["spatial_patch_size"] == [4, 4]
    assert candidate_method_config["score_calibration"]["embedding_projection_support_weight"] == 0.45
    assert candidate_method_config["lambda_sync"] == 0.05
    assert candidate_method_config["fusion_rule"] == "sync_rescue_fusion"
    assert candidate_method_config["sync_search"]["offset_search_min"] == -8
    assert candidate_method_config["sync_search"]["offset_search_max"] == 8
    assert summary["generated_tubelet_sync_candidate_config_path"] == str(
        candidate_method_config_path
    )
    assert summary["selected_tubelet_sync_candidate"]["method_variant"] == "tubelet_sync_real_video_vae_candidate"
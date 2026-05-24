"""
文件用途：验证 real_video_vae_latent_probe mechanism calibration runner 的 orchestration 行为。
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
    captured_runner_calls: list[dict[str, object]] = []
    selector_calls: list[dict[str, object]] = []

    class _FakeRunner:
        def __init__(self, repository_root: str | Path) -> None:
            self._repository_root = str(repository_root)

        def run(self, **kwargs: object) -> dict[str, object]:
            captured_runner_calls.append(
                {
                    "repository_root": self._repository_root,
                    "kwargs": dict(kwargs),
                }
            )
            return {"status": "ok"}

    monkeypatch.setattr(calibration_runner_module, "RealVideoVaeLatentRunner", _FakeRunner)

    anchor_candidate = {
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
    }
    wide_sync_candidate = {
        "candidate_status": "sync_gain_candidate_selected",
        "candidate_selection_status": "rescue_with_leakage",
        "negative_leakage_status": "leakage_risk",
        "method_variant": "tubelet_sync_real_video_vae_wide_candidate",
        "base_method_variant": "tubelet_sync",
        "tubelet_length": 1,
        "tubelet_partition": {"spatial_patch_size": [4, 4]},
        "score_calibration": {"embedding_projection_support_weight": 0.45},
        "fusion_rule": "sync_rescue_fusion",
        "lambda_sync": 0.1,
        "sync_search": {
            "offset_search_min": -12,
            "offset_search_max": 12,
            "min_sync_positive_margin": 0.0,
            "min_sync_alignment_coverage_ratio": 0.25,
            "min_sync_alignment_matched_count": 2,
            "min_sync_candidate_score": 0.0,
        },
        "metrics": {
            "no_attack_clean_negative_fpr": 0.0,
            "no_attack_clean_positive_tpr": 1.0,
            "max_attacked_negative_fpr": 0.0,
            "temporal_crop_attacked_positive_tpr": 1.0,
            "frame_dropping_attacked_positive_tpr": 0.9,
            "local_clip_attacked_positive_tpr": 0.95,
            "quality_psnr_mean": 24.0,
            "quality_ssim_mean": 0.7,
            "temporal_crop_sync_gain": 0.08,
            "frame_dropping_sync_gain": 0.05,
            "local_clip_sync_gain": 0.09,
            "mean_temporal_sync_gain": 0.073333,
        },
    }
    refined_sync_candidate = {
        "candidate_status": "sync_gain_candidate_selected",
        "candidate_selection_status": "eligible",
        "negative_leakage_status": "controlled",
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
            "min_sync_positive_margin": 0.12,
            "min_sync_alignment_coverage_ratio": 0.125,
            "min_sync_alignment_matched_count": 4,
            "min_sync_candidate_score": 0.55,
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
    }

    def _fake_select_stage2_mechanism_candidate(**kwargs: object) -> dict[str, object]:
        selector_calls.append(dict(kwargs))
        stage_name = Path(str(kwargs["run_root"])).name
        selection_scope = str(kwargs.get("selection_scope"))
        if selection_scope == "tubelet_only":
            return {
                "selection_scope": "tubelet_only",
                "output_path": str(tmp_path / f"{stage_name}_selected_candidate.json"),
                "report_path": str(tmp_path / f"{stage_name}_selected_candidate.md"),
                "grid_output_path": str(tmp_path / f"{stage_name}_selected_candidate.csv"),
                "selected_tubelet_only_candidate": anchor_candidate,
                "selected_tubelet_sync_candidate": None,
                "tubelet_sync_scan_seed": None,
                "top_tubelet_only_candidates": [anchor_candidate],
                "top_tubelet_sync_candidates": [],
                "parameter_interval_summary": {
                    "tubelet_only": {
                        "tubelet_length": {
                            "min": 1.0,
                            "max": 4.0,
                            "unique_count": 3,
                            "unique_values": [1.0, 2.0, 4.0],
                        }
                    },
                    "tubelet_sync": {},
                },
            }
        if stage_name == "sync_wide_scan":
            return {
                "selection_scope": "tubelet_sync",
                "output_path": str(tmp_path / f"{stage_name}_selected_candidate.json"),
                "report_path": str(tmp_path / f"{stage_name}_selected_candidate.md"),
                "grid_output_path": str(tmp_path / f"{stage_name}_selected_candidate.csv"),
                "selected_tubelet_only_candidate": anchor_candidate,
                "selected_tubelet_sync_candidate": wide_sync_candidate,
                "tubelet_sync_scan_seed": {
                    "base_method_variant": "tubelet_sync",
                    "recommended_method_variant": "tubelet_sync_real_video_vae_wide_candidate",
                    "seed_method_config": {
                        "tubelet_length": anchor_candidate["tubelet_length"],
                        "tubelet_partition": {
                            "spatial_patch_size": anchor_candidate["tubelet_partition"][
                                "spatial_patch_size"
                            ]
                        },
                        "score_calibration": {
                            "embedding_projection_support_weight": anchor_candidate[
                                "score_calibration"
                            ]["embedding_projection_support_weight"]
                        },
                    },
                    "parameter_scan": {
                        "fusion_rule": ["sync_rescue_fusion"],
                        "lambda_sync": [0.0, 0.025, 0.05, 0.1],
                        "sync_search_radius": [4, 8, 12],
                        "min_sync_positive_margin": [0.0, 0.05, 0.12],
                        "min_sync_alignment_coverage_ratio": [0.125, 0.25, 0.5],
                        "min_sync_alignment_matched_count": [1, 2, 4],
                        "min_sync_candidate_score": [0.0],
                    },
                },
                "top_tubelet_only_candidates": [],
                "top_tubelet_sync_candidates": [wide_sync_candidate],
                "parameter_interval_summary": {
                    "tubelet_only": {},
                    "tubelet_sync": {
                        "lambda_sync": {
                            "min": 0.0,
                            "max": 0.1,
                            "unique_count": 4,
                            "unique_values": [0.0, 0.025, 0.05, 0.1],
                        }
                    },
                },
            }
        return {
            "selection_scope": "tubelet_sync",
            "output_path": str(tmp_path / f"{stage_name}_selected_candidate.json"),
            "report_path": str(tmp_path / f"{stage_name}_selected_candidate.md"),
            "grid_output_path": str(tmp_path / f"{stage_name}_selected_candidate.csv"),
            "selected_tubelet_only_candidate": anchor_candidate,
            "selected_tubelet_sync_candidate": refined_sync_candidate,
            "tubelet_sync_scan_seed": {
                "base_method_variant": "tubelet_sync",
                "recommended_method_variant": "tubelet_sync_real_video_vae_candidate",
                "seed_method_config": {
                    "tubelet_length": anchor_candidate["tubelet_length"],
                    "tubelet_partition": {
                        "spatial_patch_size": anchor_candidate["tubelet_partition"][
                            "spatial_patch_size"
                        ]
                    },
                    "score_calibration": {
                        "embedding_projection_support_weight": anchor_candidate[
                            "score_calibration"
                        ]["embedding_projection_support_weight"]
                    },
                },
                "parameter_scan": {
                    "fusion_rule": ["sync_rescue_fusion"],
                    "lambda_sync": [0.0, 0.025, 0.05, 0.075],
                    "sync_search_radius": [6, 8, 10, 12],
                    "min_sync_positive_margin": [0.0, 0.03, 0.06, 0.09, 0.12],
                    "min_sync_alignment_coverage_ratio": [0.125, 0.2, 0.3, 0.4, 0.5],
                    "min_sync_alignment_matched_count": [1, 2, 3, 4],
                    "min_sync_candidate_score": [0.0, 0.55],
                },
            },
            "top_tubelet_only_candidates": [],
            "top_tubelet_sync_candidates": [refined_sync_candidate],
            "parameter_interval_summary": {
                "tubelet_only": {},
                "tubelet_sync": {
                    "lambda_sync": {
                        "min": 0.0,
                        "max": 0.075,
                        "unique_count": 4,
                        "unique_values": [0.0, 0.025, 0.05, 0.075],
                    }
                },
            },
        }

    monkeypatch.setattr(
        calibration_runner_module,
        "select_stage2_mechanism_candidate",
        _fake_select_stage2_mechanism_candidate,
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
    runtime_config_path = Path(summary["runtime_config_path"])
    ablation_config_path = Path(summary["ablation_config_path"])
    calibration_summary_path = Path(summary["calibration_summary_path"])
    assert protocol_config_path.exists()
    assert runtime_config_path.exists()
    assert ablation_config_path.exists()
    assert calibration_summary_path.exists()
    assert summary["campaign_mode"] == "staged_search"
    assert summary["search_stage_count"] == 3
    assert Path(summary["search_stage_plan_path"]).exists()

    protocol_payload = json.loads(protocol_config_path.read_text(encoding="utf-8"))
    runtime_payload = json.loads(runtime_config_path.read_text(encoding="utf-8"))
    assert protocol_payload["splits"] == ["dev", "calibration"]
    assert protocol_payload["splits_by_profile"]["formal"] == ["dev", "calibration"]
    assert runtime_payload["quality_metrics"]["enable_lpips"] is False
    assert runtime_payload["quality_metrics"]["enable_clip_similarity"] is False
    assert runtime_payload["quality_metrics"]["enabled_attack_names"] == ["no_attack"]
    assert runtime_payload["quality_metrics"]["enabled_sample_roles"] == ["watermarked_positive"]
    assert runtime_payload["temporal_metrics"]["enable_temporal_metrics"] is False
    assert runtime_payload["temporal_metrics"]["enable_motion_consistency"] is False

    stage_summaries = summary["search_stage_summaries"]
    anchor_ablation_payload = json.loads(
        Path(stage_summaries[0]["ablation_config_path"]).read_text(encoding="utf-8")
    )
    assert anchor_ablation_payload["method_config_paths"]
    assert anchor_ablation_payload["tubelet_length_sweep_variant"] is None
    assert anchor_ablation_payload["tubelet_length_sweep_formal"] == []
    assert any(
        method_variant.startswith("tubelet_only_cal_")
        for method_variant in anchor_ablation_payload["method_variants"]
    )
    assert not any(
        method_variant.startswith("tubelet_sync_cal_")
        for method_variant in anchor_ablation_payload["method_variants"]
    )

    refine_ablation_payload = json.loads(ablation_config_path.read_text(encoding="utf-8"))
    assert refine_ablation_payload["method_config_paths"]
    assert any(
        method_variant.startswith("tubelet_sync_cal_")
        for method_variant in refine_ablation_payload["method_variants"]
    )
    generated_sync_config_path = next(
        Path(config_path)
        for method_variant, config_path in refine_ablation_payload["method_config_paths"].items()
        if method_variant.startswith("tubelet_sync_cal_")
    )
    generated_sync_config = json.loads(
        generated_sync_config_path.read_text(encoding="utf-8")
    )
    assert "min_sync_positive_margin" in generated_sync_config["sync_search"]
    assert "min_sync_alignment_coverage_ratio" in generated_sync_config["sync_search"]
    assert "min_sync_alignment_matched_count" in generated_sync_config["sync_search"]

    assert len(captured_runner_calls) == 3
    assert [Path(call["kwargs"]["output_root"]).name for call in captured_runner_calls] == [
        "anchor_tubelet_only_wide",
        "sync_wide_scan",
        "sync_refine_scan",
    ]
    for runner_call in captured_runner_calls:
        runner_kwargs = runner_call["kwargs"]
        assert runner_kwargs["protocol_config_path"] == protocol_config_path
        assert runner_kwargs["runtime_config_path"] == runtime_config_path
        assert runner_kwargs["runtime_profile_override"] == "formal"
        assert runner_kwargs["samples_per_role"] == 2
        assert runner_kwargs["batch_size_frames"] == 8

    assert len(selector_calls) == 3
    assert [str(call["selection_scope"]) for call in selector_calls] == [
        "tubelet_only",
        "tubelet_sync",
        "tubelet_sync",
    ]
    assert selector_calls[1]["selected_tubelet_only_candidate"]["method_variant"] == anchor_candidate[
        "method_variant"
    ]
    assert selector_calls[2]["selected_tubelet_only_candidate"]["method_variant"] == anchor_candidate[
        "method_variant"
    ]

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
    assert candidate_method_config["sync_search"]["min_sync_positive_margin"] == 0.12
    assert candidate_method_config["sync_search"]["min_sync_alignment_coverage_ratio"] == 0.125
    assert candidate_method_config["sync_search"]["min_sync_alignment_matched_count"] == 4
    assert candidate_method_config["sync_search"]["min_sync_candidate_score"] == 0.55
    assert summary["generated_tubelet_sync_candidate_config_path"] == str(
        candidate_method_config_path
    )
    assert summary["selected_tubelet_only_candidate"]["method_variant"] == anchor_candidate[
        "method_variant"
    ]
    assert summary["selected_tubelet_sync_candidate"]["method_variant"] == "tubelet_sync_real_video_vae_candidate"
    assert summary["selection_completion_status"] == "complete"
    assert summary["selection_blocking_reason"] is None
    assert summary["selected_sync_method_variant"] == "tubelet_sync_real_video_vae_candidate"
    assert summary["selected_sync_candidate_status"] == "eligible"
    assert summary["selected_sync_negative_leakage_status"] == "controlled"
    assert summary["selected_sync_local_clip_gain"] == 0.1
    assert summary["selected_sync_max_attacked_negative_fpr"] == 0.0
    assert Path(summary["timing_summary_path"]).exists()
    assert Path(summary["calibration_runtime_profile_summary_path"]).exists()
    assert Path(summary["calibration_runtime_profile_report_path"]).exists()
    for stage_summary in summary["search_stage_summaries"]:
        assert Path(stage_summary["runtime_timing_summary_path"]).exists()
        assert Path(stage_summary["runtime_timing_report_path"]).exists()
        assert stage_summary["runtime_timing_summary"]["total_recorded_seconds"] >= 0.0

    timing_summary_payload = json.loads(
        Path(summary["timing_summary_path"]).read_text(encoding="utf-8")
    )
    assert timing_summary_payload["search_stage_count"] == 3
    assert timing_summary_payload["stage_timing_summaries"][0]["stage_name"] == (
        "anchor_tubelet_only_wide"
    )
    assert timing_summary_payload["calibration_timing_summary"]["event_count"] >= 7


@pytest.mark.unit
def test_stage2_mechanism_calibration_runner_continues_refine_scan_from_sync_scan_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate default staged search can refine from tubelet_sync_scan_seed.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    captured_runner_calls: list[dict[str, object]] = []

    class _FakeRunner:
        def __init__(self, repository_root: str | Path) -> None:
            self._repository_root = str(repository_root)

        def run(self, **kwargs: object) -> dict[str, object]:
            captured_runner_calls.append(
                {
                    "repository_root": self._repository_root,
                    "kwargs": dict(kwargs),
                }
            )
            return {"status": "ok"}

    monkeypatch.setattr(calibration_runner_module, "RealVideoVaeLatentRunner", _FakeRunner)

    anchor_candidate = {
        "candidate_status": "fpr_controlled_candidate_selected",
        "method_variant": "tubelet_only_cal_tl02_sp04x04_w025",
        "tubelet_length": 2,
        "tubelet_partition": {"spatial_patch_size": [4, 4]},
        "score_calibration": {"embedding_projection_support_weight": 0.25},
        "metrics": {
            "no_attack_clean_negative_fpr": 0.0,
            "no_attack_clean_positive_tpr": 1.0,
            "max_attacked_negative_fpr": 0.0,
            "temporal_crop_attacked_positive_tpr": 1.0,
            "frame_dropping_attacked_positive_tpr": 1.0,
            "local_clip_attacked_positive_tpr": 0.5,
        },
    }
    refined_sync_candidate = {
        "candidate_status": "sync_gain_candidate_selected",
        "candidate_selection_status": "eligible",
        "negative_leakage_status": "controlled",
        "method_variant": "tubelet_sync_real_video_vae_candidate",
        "base_method_variant": "tubelet_sync",
        "tubelet_length": 2,
        "tubelet_partition": {"spatial_patch_size": [4, 4]},
        "score_calibration": {"embedding_projection_support_weight": 0.25},
        "fusion_rule": "sync_rescue_fusion",
        "lambda_sync": 0.05,
        "sync_search": {
            "offset_search_min": -8,
            "offset_search_max": 8,
            "min_sync_positive_margin": 0.12,
            "min_sync_alignment_coverage_ratio": 0.125,
            "min_sync_alignment_matched_count": 3,
            "min_sync_candidate_score": 0.55,
        },
        "metrics": {
            "no_attack_clean_negative_fpr": 0.0,
            "no_attack_clean_positive_tpr": 1.0,
            "max_attacked_negative_fpr": 0.0,
            "temporal_crop_attacked_positive_tpr": 1.0,
            "frame_dropping_attacked_positive_tpr": 1.0,
            "local_clip_attacked_positive_tpr": 0.75,
            "quality_psnr_mean": 24.0,
            "quality_ssim_mean": 0.7,
            "temporal_crop_sync_gain": 0.0,
            "frame_dropping_sync_gain": 0.0,
            "local_clip_sync_gain": 0.25,
            "mean_temporal_sync_gain": 0.083333,
        },
    }

    def _build_sync_scan_seed() -> dict[str, object]:
        return {
            "base_method_variant": "tubelet_sync",
            "recommended_method_variant": "tubelet_sync_real_video_vae_candidate",
            "seed_method_config": {
                "tubelet_length": anchor_candidate["tubelet_length"],
                "tubelet_partition": {
                    "spatial_patch_size": anchor_candidate["tubelet_partition"][
                        "spatial_patch_size"
                    ]
                },
                "score_calibration": {
                    "embedding_projection_support_weight": anchor_candidate[
                        "score_calibration"
                    ]["embedding_projection_support_weight"]
                },
            },
            "parameter_scan": {
                "fusion_rule": ["sync_rescue_fusion"],
                "lambda_sync": [0.0, 0.025, 0.05, 0.1],
                "sync_search_radius": [4, 8, 12],
                "min_sync_positive_margin": [0.0, 0.05, 0.12],
                "min_sync_alignment_coverage_ratio": [0.125, 0.25, 0.5],
                "min_sync_alignment_matched_count": [1, 2, 4],
                "min_sync_candidate_score": [0.0],
            },
        }

    def _fake_select_stage2_mechanism_candidate(**kwargs: object) -> dict[str, object]:
        stage_name = Path(str(kwargs["run_root"])).name
        if stage_name == "anchor_tubelet_only_wide":
            return {
                "selection_scope": "tubelet_only",
                "selection_completion_status": "complete",
                "selection_blocking_reason": None,
                "selection_blocking_details": None,
                "output_path": str(tmp_path / f"{stage_name}_selected_candidate.json"),
                "report_path": str(tmp_path / f"{stage_name}_selected_candidate.md"),
                "grid_output_path": str(tmp_path / f"{stage_name}_selected_candidate.csv"),
                "selected_tubelet_only_candidate": anchor_candidate,
                "selected_tubelet_sync_candidate": None,
                "tubelet_sync_scan_seed": None,
                "top_tubelet_only_candidates": [anchor_candidate],
                "top_tubelet_sync_candidates": [],
                "parameter_interval_summary": {"tubelet_only": {}, "tubelet_sync": {}},
            }
        if stage_name == "sync_wide_scan":
            return {
                "selection_scope": "tubelet_sync",
                "selection_completion_status": "incomplete_no_eligible_tubelet_sync_candidate",
                "selection_blocking_reason": "no_tubelet_sync_candidate_passes_selection_gate",
                "selection_blocking_details": None,
                "output_path": str(tmp_path / f"{stage_name}_selected_candidate.json"),
                "report_path": str(tmp_path / f"{stage_name}_selected_candidate.md"),
                "grid_output_path": str(tmp_path / f"{stage_name}_selected_candidate.csv"),
                "selected_tubelet_only_candidate": anchor_candidate,
                "selected_tubelet_sync_candidate": None,
                "tubelet_sync_scan_seed": _build_sync_scan_seed(),
                "top_tubelet_only_candidates": [],
                "top_tubelet_sync_candidates": [],
                "parameter_interval_summary": {"tubelet_only": {}, "tubelet_sync": {}},
            }
        return {
            "selection_scope": "tubelet_sync",
            "selection_completion_status": "complete",
            "selection_blocking_reason": None,
            "selection_blocking_details": None,
            "output_path": str(tmp_path / f"{stage_name}_selected_candidate.json"),
            "report_path": str(tmp_path / f"{stage_name}_selected_candidate.md"),
            "grid_output_path": str(tmp_path / f"{stage_name}_selected_candidate.csv"),
            "selected_tubelet_only_candidate": anchor_candidate,
            "selected_tubelet_sync_candidate": refined_sync_candidate,
            "tubelet_sync_scan_seed": _build_sync_scan_seed(),
            "top_tubelet_only_candidates": [],
            "top_tubelet_sync_candidates": [refined_sync_candidate],
            "parameter_interval_summary": {"tubelet_only": {}, "tubelet_sync": {}},
        }

    monkeypatch.setattr(
        calibration_runner_module,
        "select_stage2_mechanism_candidate",
        _fake_select_stage2_mechanism_candidate,
    )

    candidate_method_config_path = tmp_path / "candidate_from_scan_seed.json"
    summary = run_stage2_mechanism_calibration(
        run_root=tmp_path / "mcal_scan_seed_refine",
        runtime_profile="formal",
        samples_per_role=2,
        batch_size_frames=8,
        output_method_config_path=candidate_method_config_path,
    )

    assert len(captured_runner_calls) == 3
    assert [Path(call["kwargs"]["output_root"]).name for call in captured_runner_calls] == [
        "anchor_tubelet_only_wide",
        "sync_wide_scan",
        "sync_refine_scan",
    ]
    assert summary["search_terminated_early"] is False
    assert summary["terminated_before_stage_name"] is None
    assert summary["selected_tubelet_sync_candidate"]["method_variant"] == refined_sync_candidate[
        "method_variant"
    ]
    assert summary["search_stage_summaries"][1]["selected_tubelet_sync_candidate"] is None
    assert summary["search_stage_summaries"][1]["tubelet_sync_scan_seed"][
        "seed_method_config"
    ]["tubelet_length"] == anchor_candidate["tubelet_length"]
    assert summary["search_stage_summaries"][2]["selected_tubelet_sync_candidate"][
        "method_variant"
    ] == refined_sync_candidate["method_variant"]
    assert candidate_method_config_path.exists()


@pytest.mark.unit
def test_stage2_mechanism_calibration_runner_returns_anchor_only_partial_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate staged search returns a governed partial summary when sync wide rows are incompatible with the anchor.

    Args:
        tmp_path: Temporary output root.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    captured_runner_calls: list[dict[str, object]] = []

    class _FakeRunner:
        def __init__(self, repository_root: str | Path) -> None:
            self._repository_root = str(repository_root)

        def run(self, **kwargs: object) -> dict[str, object]:
            captured_runner_calls.append(
                {
                    "repository_root": self._repository_root,
                    "kwargs": dict(kwargs),
                }
            )
            return {"status": "ok"}

    monkeypatch.setattr(calibration_runner_module, "RealVideoVaeLatentRunner", _FakeRunner)

    anchor_candidate = {
        "candidate_status": "best_effort_candidate_selected",
        "method_variant": "tubelet_only_cal_tl04_sp04x04_w075",
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
    }

    def _fake_select_stage2_mechanism_candidate(**kwargs: object) -> dict[str, object]:
        stage_name = Path(str(kwargs["run_root"])).name
        if stage_name == "anchor_tubelet_only_wide":
            return {
                "selection_scope": "tubelet_only",
                "selection_completion_status": "complete",
                "selection_blocking_reason": None,
                "selection_blocking_details": None,
                "output_path": str(tmp_path / f"{stage_name}_selected_candidate.json"),
                "report_path": str(tmp_path / f"{stage_name}_selected_candidate.md"),
                "grid_output_path": str(tmp_path / f"{stage_name}_selected_candidate.csv"),
                "selected_tubelet_only_candidate": anchor_candidate,
                "selected_tubelet_sync_candidate": None,
                "tubelet_sync_scan_seed": None,
                "top_tubelet_only_candidates": [anchor_candidate],
                "top_tubelet_sync_candidates": [],
                "parameter_interval_summary": {"tubelet_only": {}, "tubelet_sync": {}},
            }
        return {
            "selection_scope": "tubelet_sync",
            "selection_completion_status": "incomplete_no_compatible_tubelet_sync_rows",
            "selection_blocking_reason": "selected_anchor_not_covered_by_sync_stage_records",
            "selection_blocking_details": {
                "selected_anchor_signature": {
                    "tubelet_length": 4,
                    "spatial_patch_size": [4, 4],
                    "embedding_projection_support_weight": 0.75,
                },
                "observed_sync_stage_signature_count": 1,
                "observed_sync_stage_signatures": [
                    {
                        "tubelet_length": 1,
                        "spatial_patch_size": [4, 4],
                        "embedding_projection_support_weight": 0.45,
                    }
                ],
                "matching_sync_stage_signature_count": 0,
            },
            "output_path": str(tmp_path / f"{stage_name}_selected_candidate.json"),
            "report_path": str(tmp_path / f"{stage_name}_selected_candidate.md"),
            "grid_output_path": str(tmp_path / f"{stage_name}_selected_candidate.csv"),
            "selected_tubelet_only_candidate": anchor_candidate,
            "selected_tubelet_sync_candidate": None,
            "tubelet_sync_scan_seed": {
                "base_method_variant": "tubelet_sync",
                "recommended_method_variant": "tubelet_sync_real_video_vae_candidate",
                "seed_method_config": {
                    "tubelet_length": anchor_candidate["tubelet_length"],
                    "tubelet_partition": {
                        "spatial_patch_size": anchor_candidate["tubelet_partition"][
                            "spatial_patch_size"
                        ]
                    },
                    "score_calibration": {
                        "embedding_projection_support_weight": anchor_candidate[
                            "score_calibration"
                        ]["embedding_projection_support_weight"]
                    },
                },
                "parameter_scan": {
                    "fusion_rule": ["sync_rescue_fusion"],
                    "lambda_sync": [0.0, 0.025, 0.05, 0.1],
                    "sync_search_radius": [4, 8, 12],
                    "min_sync_positive_margin": [0.0, 0.05, 0.12],
                    "min_sync_alignment_coverage_ratio": [0.125, 0.25, 0.5],
                    "min_sync_alignment_matched_count": [1, 2, 4],
                    "min_sync_candidate_score": [0.0],
                },
            },
            "top_tubelet_only_candidates": [],
            "top_tubelet_sync_candidates": [],
            "parameter_interval_summary": {"tubelet_only": {}, "tubelet_sync": {}},
        }

    monkeypatch.setattr(
        calibration_runner_module,
        "select_stage2_mechanism_candidate",
        _fake_select_stage2_mechanism_candidate,
    )

    grid_config = json.loads(
        Path(calibration_runner_module.DEFAULT_GRID_CONFIG_PATH).read_text(encoding="utf-8")
    )
    for stage_payload in grid_config["search_stages"]:
        if stage_payload["stage_name"] == "sync_refine_scan":
            stage_payload["candidate_source"] = "selected_tubelet_sync_candidate"
    grid_config_path = tmp_path / "grid_requires_selected_sync_candidate.json"
    grid_config_path.write_text(
        json.dumps(grid_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    candidate_method_config_path = tmp_path / "candidate.json"
    summary = run_stage2_mechanism_calibration(
        run_root=tmp_path / "mcal_partial",
        runtime_profile="formal",
        samples_per_role=2,
        batch_size_frames=8,
        grid_config_path=grid_config_path,
        output_method_config_path=candidate_method_config_path,
    )

    assert len(captured_runner_calls) == 2
    assert [Path(call["kwargs"]["output_root"]).name for call in captured_runner_calls] == [
        "anchor_tubelet_only_wide",
        "sync_wide_scan",
    ]
    assert summary["calibration_completion_status"] == "anchor_only_partial_selection"
    assert summary["calibration_blocking_reason"] == "selected_anchor_not_covered_by_sync_stage_records"
    assert summary["search_terminated_early"] is True
    assert summary["terminated_before_stage_name"] == "sync_refine_scan"
    assert summary["selected_tubelet_only_candidate"]["method_variant"] == anchor_candidate[
        "method_variant"
    ]
    assert summary["selected_tubelet_sync_candidate"] is None
    assert summary["selection_completion_status"] == "incomplete_no_compatible_tubelet_sync_rows"
    assert summary["selection_blocking_reason"] == "selected_anchor_not_covered_by_sync_stage_records"
    assert summary["selected_sync_method_variant"] is None
    assert summary["selected_sync_candidate_status"] is None
    assert summary["selected_sync_negative_leakage_status"] is None
    assert summary["selected_sync_local_clip_gain"] is None
    assert summary["selected_sync_max_attacked_negative_fpr"] is None
    assert summary["generated_tubelet_sync_candidate_config_path"] is None
    assert Path(summary["timing_summary_path"]).exists()
    assert not candidate_method_config_path.exists()
    assert summary["search_stage_count"] == 2
    assert summary["search_stage_summaries"][1]["selection_completion_status"] == (
        "incomplete_no_compatible_tubelet_sync_rows"
    )
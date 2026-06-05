"""
文件用途：验证阶段 2 scaffold 消融配置共享同一协议语义。File purpose: Validate that the stage-two scaffold ablation config shares one protocol contract.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

from pathlib import Path

from main.core.registry import load_json_config


def test_real_video_vae_latent_ablation_config_reuses_shared_protocol_semantics() -> None:
    """Validate that stage-two ablation config reuses one shared protocol contract.

    Args:
        None.

    Returns:
        None.
    """
    repository_root = Path(__file__).resolve().parents[2]
    protocol_config = load_json_config(
        repository_root / "configs" / "protocol" / "real_video_vae_latent_probe.json"
    )
    ablation_config = load_json_config(
        repository_root / "configs" / "ablation" / "real_video_vae_latent_ablation.json"
    )
    assert protocol_config["required_method_variants"] == ["frame_prc", "tubelet_only", "tubelet_sync"]
    assert ablation_config["method_variants"] == ["frame_prc", "tubelet_only", "tubelet_sync"]
    assert ablation_config["shared_protocol_name"] == protocol_config["protocol_name"]
    assert ablation_config["shared_target_fpr"] == protocol_config["threshold_protocol"]["target_fpr_placeholder"]
    assert ablation_config["shared_attack_matrix_name"] == "real_video_attack_matrix"


def test_real_video_vae_latent_default_method_configs_use_frozen_mechanism_candidate() -> None:
    """???? 2 completion run ??????? w005 sync ?????

    ???????????: ?? synthetic ???????, real-video
    formal runner ?? ablation method_config_paths ?????????
    """
    repository_root = Path(__file__).resolve().parents[2]
    ablation_config = load_json_config(
        repository_root / "configs" / "ablation" / "real_video_vae_latent_ablation.json"
    )
    tubelet_only_config = load_json_config(
        repository_root / "configs" / "method" / "real_video_tubelet_only_anchor.json"
    )
    tubelet_sync_config = load_json_config(
        repository_root / "configs" / "method" / "real_video_tubelet_sync_candidate_runtime.json"
    )
    candidate_config = load_json_config(
        repository_root / "configs" / "method" / "tubelet_sync_real_video_vae_candidate.json"
    )

    assert ablation_config["method_config_paths"] == {
        "tubelet_only": "configs/method/real_video_tubelet_only_anchor.json",
        "tubelet_sync": "configs/method/real_video_tubelet_sync_candidate_runtime.json",
    }
    assert ablation_config["tubelet_length_sweep_formal"] == []

    assert tubelet_only_config["method_variant"] == "tubelet_only"
    assert tubelet_only_config["tubelet_length"] == 8
    assert tubelet_only_config["score_calibration"]["embedding_projection_support_weight"] == 0.05
    assert tubelet_only_config["tubelet_partition"]["spatial_patch_size"] == [8, 8]

    assert candidate_config["method_variant"].startswith("tubelet_sync_cal_")
    assert tubelet_sync_config["method_variant"] == "tubelet_sync"
    assert tubelet_sync_config["base_method_variant"] == "tubelet_sync"
    assert tubelet_sync_config["tubelet_length"] == candidate_config["tubelet_length"]
    assert tubelet_sync_config["lambda_sync"] == candidate_config["lambda_sync"]
    assert tubelet_sync_config["score_calibration"] == candidate_config["score_calibration"]
    assert tubelet_sync_config["sync_search"] == candidate_config["sync_search"]

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


def test_real_video_vae_latent_ablation_uses_confirmed_stage2_candidate_for_final_audit() -> None:
    """验证最终 formal audit 使用已确认的阶段 2 anchor 与 sync candidate。

    Args:
        None.

    Returns:
        None.
    """
    repository_root = Path(__file__).resolve().parents[2]
    ablation_config = load_json_config(
        repository_root / "configs" / "ablation" / "real_video_vae_latent_ablation.json"
    )
    method_config_paths = ablation_config["method_config_paths"]

    assert method_config_paths == {
        "tubelet_only": "configs/method/real_video_tubelet_only_anchor.json",
        "tubelet_sync": "configs/method/real_video_tubelet_sync_candidate_runtime.json",
    }
    assert ablation_config["mechanism_default_candidate_method_config_path"] == (
        "configs/method/real_video_tubelet_sync_candidate_runtime.json"
    )
    assert ablation_config["mechanism_default_anchor_method_config_path"] == (
        "configs/method/real_video_tubelet_only_anchor.json"
    )
    assert ablation_config["tubelet_length_sweep_formal"] == []

    anchor_config = load_json_config(repository_root / method_config_paths["tubelet_only"])
    sync_config = load_json_config(repository_root / method_config_paths["tubelet_sync"])
    assert anchor_config["method_variant"] == "tubelet_only"
    assert anchor_config["score_calibration"]["embedding_projection_support_weight"] == 0.09
    assert anchor_config["tubelet_partition"]["spatial_patch_size"] == [4, 4]
    assert sync_config["method_variant"] == "tubelet_sync"
    assert sync_config["candidate_source_method_variant"] == (
        "tubelet_sync_cal_tl04_sp04x04_w009_em1000_sr08_ls010_mg000_cv125_mc64_grapsafe_rg010_as095_frsync_rescue"
    )
    assert sync_config["sync_search"]["sync_confidence_gate_rule"] == (
        "aligned_payload_safety_gate"
    )
    assert "min_sync_candidate_score" not in sync_config["sync_search"]
    assert sync_config["sync_search"]["min_payload_rescue_gain"] == 0.01
    assert sync_config["sync_search"]["min_aligned_payload_score"] == 0.095

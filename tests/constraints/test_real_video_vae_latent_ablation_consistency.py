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


def test_real_video_vae_latent_ablation_does_not_keep_failed_completion_candidate() -> None:
    """验证 formal 失败候选不会继续作为默认 completion 配置。

    Args:
        None.

    Returns:
        None.
    """
    repository_root = Path(__file__).resolve().parents[2]
    ablation_config = load_json_config(
        repository_root / "configs" / "ablation" / "real_video_vae_latent_ablation.json"
    )
    stale_candidate_paths = [
        repository_root / "configs" / "method" / "real_video_tubelet_only_anchor.json",
        repository_root / "configs" / "method" / "real_video_tubelet_sync_candidate_runtime.json",
        repository_root / "configs" / "method" / "tubelet_sync_real_video_vae_candidate.json",
    ]

    assert "method_config_paths" not in ablation_config
    assert "mechanism_default_candidate_method_config_path" not in ablation_config
    assert ablation_config["tubelet_length_sweep_formal"] == []
    assert all(not stale_path.exists() for stale_path in stale_candidate_paths)

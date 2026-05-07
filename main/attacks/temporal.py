"""
文件用途：声明阶段 1 temporal attack matrix 的受治理攻击名称与默认参数。
File purpose: Declare governed attack names and support defaults for the stage-1 temporal attack matrix.
Module type: Semi-general module
"""

from __future__ import annotations


PROJECT_STAGE = "protocol_skeleton"
TARGET_CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"
ATTACK_MATRIX_NAME = "temporal_attack_matrix"
SUPPORTED_TEMPORAL_ATTACK_NAMES = (
    "no_attack",
    "temporal_crop",
    "frame_dropping",
    "speed_change",
    "local_clip",
    "latent_gaussian_noise",
)


def build_temporal_attack_matrix_support_defaults() -> dict[str, object]:
    """功能：返回阶段 1 temporal attack matrix 的冻结默认值。

    Build the governed default payload for the stage-1 temporal attack matrix.

    Args:
        None.

    Returns:
        A dictionary containing the frozen temporal attack entries.
    """
    return {
        "project_stage": PROJECT_STAGE,
        "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
        "attack_matrix_name": ATTACK_MATRIX_NAME,
        "attacks": [
            {"attack_name": "no_attack", "attack_params": {}},
            {
                "attack_name": "temporal_crop",
                "attack_params": {
                    "crop_start_candidates": [4, 8, 12],
                    "crop_length": 20,
                },
            },
            {
                "attack_name": "frame_dropping",
                "attack_params": {
                    "drop_rate": 0.25,
                    "drop_policy": "deterministic_keyed",
                },
            },
            {
                "attack_name": "speed_change",
                "attack_params": {
                    "speed_ratio": 1.25,
                    "resample_policy": "nearest",
                },
            },
            {
                "attack_name": "local_clip",
                "attack_params": {"clip_lengths": [4, 8, 12, 16]},
            },
            {
                "attack_name": "latent_gaussian_noise",
                "attack_params": {"sigma": 0.05},
            },
        ],
    }
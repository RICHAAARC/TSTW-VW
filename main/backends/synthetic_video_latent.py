"""
文件用途：声明阶段 1 synthetic video latent backend 的受治理配置默认值。
File purpose: Declare governed defaults for the stage-1 synthetic video latent backend.
Module type: Semi-general module
"""

from __future__ import annotations


PROJECT_STAGE = "protocol_skeleton"
TARGET_CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"
LATENT_BACKEND_NAME = "synthetic_video_latent"
LATENT_DISTRIBUTION = "standard_normal"
LATENT_STORAGE = "npy_artifact"
DEFAULT_LATENT_SHAPE = {
    "frames": 32,
    "channels": 4,
    "height": 32,
    "width": 32,
}
DEFAULT_LATENT_GENERATION_SEED = 20260507


def build_synthetic_video_latent_support_defaults() -> dict[str, object]:
    """功能：返回阶段 1 synthetic latent backend 的冻结默认值。

    Build the governed default payload for the stage-1 synthetic latent backend.

    Args:
        None.

    Returns:
        A dictionary containing the frozen support defaults.
    """
    return {
        "project_stage": PROJECT_STAGE,
        "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
        "latent_backend_name": LATENT_BACKEND_NAME,
        "latent_distribution": LATENT_DISTRIBUTION,
        "latent_shape": dict(DEFAULT_LATENT_SHAPE),
        "latent_generation_seed": DEFAULT_LATENT_GENERATION_SEED,
        "latent_storage": LATENT_STORAGE,
    }
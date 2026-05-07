"""
文件用途：声明阶段 1 synthetic tubelet sync 变体的受治理配置契约。
File purpose: Declare governed method-variant defaults for the stage-1 synthetic tubelet sync entry contract.
Module type: Semi-general module
"""

from __future__ import annotations


PROJECT_STAGE = "protocol_skeleton"
TARGET_CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"
METHOD_FAMILY = "temporal_tubelet_watermark"
METHOD_STATUS = "reserved_for_next_stage"
SUPPORTED_METHOD_VARIANTS = (
    "frame_prc",
    "tubelet_only",
    "tubelet_sync",
)


def build_reserved_method_support_matrix() -> dict[str, dict[str, object]]:
    """功能：返回阶段 1 三个正式 variant 的冻结默认配置。

    Build the frozen support config matrix for the stage-1 formal method variants.

    Args:
        None.

    Returns:
        A dictionary keyed by method variant.
    """
    return {
        "frame_prc": {
            "project_stage": PROJECT_STAGE,
            "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
            "method_family": METHOD_FAMILY,
            "method_variant": "frame_prc",
            "method_status": METHOD_STATUS,
            "enable_frame_prc": True,
            "enable_tubelet": False,
            "enable_sync": False,
            "enable_trajectory": False,
            "tubelet_length": 1,
            "fusion_rule": "tubelet_score_only",
        },
        "tubelet_only": {
            "project_stage": PROJECT_STAGE,
            "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
            "method_family": METHOD_FAMILY,
            "method_variant": "tubelet_only",
            "method_status": METHOD_STATUS,
            "enable_frame_prc": False,
            "enable_tubelet": True,
            "enable_sync": False,
            "enable_trajectory": False,
            "tubelet_length": 4,
            "fusion_rule": "tubelet_score_only",
        },
        "tubelet_sync": {
            "project_stage": PROJECT_STAGE,
            "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
            "method_family": METHOD_FAMILY,
            "method_variant": "tubelet_sync",
            "method_status": METHOD_STATUS,
            "enable_frame_prc": False,
            "enable_tubelet": True,
            "enable_sync": True,
            "enable_trajectory": False,
            "tubelet_length": 4,
            "fusion_rule": "calibrated_tubelet_sync",
        },
    }
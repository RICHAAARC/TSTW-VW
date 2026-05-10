"""
鏂囦欢鐢ㄩ€旓細澹版槑闃舵 1 synthetic tubelet sync 鍙樹綋鐨勫彈娌荤悊閰嶇疆濂戠害銆?
File purpose: Declare governed method-variant defaults for the synthetic_tubelet_sync_probe synthetic tubelet sync entry contract.
Module type: Semi-general module
"""

from __future__ import annotations


PROJECT_STAGE = "synthetic_tubelet_sync_probe"
TARGET_CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"
METHOD_FAMILY = "temporal_tubelet_watermark"
METHOD_STATUS = "formal_synthetic_probe"
SUPPORTED_METHOD_VARIANTS = (
    "frame_prc",
    "tubelet_only",
    "tubelet_sync",
)


def build_reserved_method_support_matrix() -> dict[str, dict[str, object]]:
    """鍔熻兘锛氳繑鍥為樁娈?1 涓変釜姝ｅ紡 variant 鐨勫喕缁撻粯璁ら厤缃€?

    Build the frozen support config matrix for the synthetic_tubelet_sync_probe formal method variants.

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
            "fusion_rule": "sync_rescue_fusion",
        },
    }

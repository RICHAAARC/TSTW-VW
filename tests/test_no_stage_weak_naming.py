"""
文件用途：验证阶段 0 新增 runtime 名称不使用弱阶段编号语义。
File purpose: Validate that stage-0 runtime names avoid weak stage-number naming.
Module type: General module
"""

from __future__ import annotations

from tools.harness.lib.naming_rules import find_forbidden_version_like_names


def test_stage0_runtime_names_avoid_weak_stage_identifiers() -> None:
    """Validate that new stage-0 runtime names do not use weak version-like suffixes.

    Args:
        None.

    Returns:
        None.
    """
    governed_names = " ".join(
        [
            "protocol_skeleton",
            "fixed_low_fpr_calibrated_detection",
            "empty_watermark_method_placeholder",
            "random_score_detector_random",
            "synthetic_latent_backend_random",
            "protocol_skeleton_methods",
            "identity_attack_placeholder",
            "threshold_record",
            "run_manifest_record",
        ]
    )
    assert find_forbidden_version_like_names(governed_names) == []
    assert "stage_0" not in governed_names
    assert "probe_p0" not in governed_names
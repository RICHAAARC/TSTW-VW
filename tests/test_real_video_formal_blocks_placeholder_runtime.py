"""
文件用途：验证 formal 模式会阻断 placeholder runtime。
File purpose: Validate that formal mode blocks placeholder runtime outputs.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from scripts.check_results.real_video_vae_latent_output_checker import (
    check_real_video_vae_latent_outputs,
)
from tests.real_video_vae_latent_test_support import run_real_video_vae_latent_tiny


def test_stage2_formal_blocks_placeholder_runtime(tmp_path: Path) -> None:
    """Validate formal checker blocks placeholder runtime outputs.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = run_real_video_vae_latent_tiny(tmp_path)
    checks_payload = check_real_video_vae_latent_outputs(
        output_root,
        run_mode="formal",
        require_formal_pass_criteria=True,
    )
    assert checks_payload["status"] is False
    assert checks_payload["RealVideoVaeLatentDecision"] in {"INCONCLUSIVE", "FAIL"}
    blocking_reasons = set(checks_payload["BlockingReasons"])
    assert blocking_reasons
    assert checks_payload["NextAllowedStage"] == "remain_in_real_video_vae_latent_probe"
    formal_checks = checks_payload["formal_checks"]
    assert formal_checks is not None
    assert formal_checks["no_placeholder_run_manifest"] is False
    assert formal_checks["random_fields_governed"] is False
    assert formal_checks["next_allowed_stage_valid"] is False

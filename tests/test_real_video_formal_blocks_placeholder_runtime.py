"""
文件用途：验证 formal 模式会阻断 placeholder runtime。
File purpose: Validate that formal mode blocks placeholder runtime outputs.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.colab.notebook_result_checker import check_real_video_vae_latent_outputs
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
    assert "video_vae_backend_placeholder" in blocking_reasons or "real_video_runtime_not_enabled" in blocking_reasons
    assert checks_payload["NextAllowedStage"] == "remain_in_real_video_vae_latent_probe"

"""
文件用途：提供阶段 2 测试公共 helper。
File purpose: Provide shared helpers for stage-two tests.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner


ROOT = Path(__file__).resolve().parents[2]


def run_real_video_vae_latent_debug(tmp_path: Path) -> Path:
    """功能：执行极小 real-video debug profile 并返回输出目录。

    Run the extremely small real-video debug profile and return its output root.

    Args:
        tmp_path: Temporary root path.

    Returns:
        The stage-two run root path.
    """
    output_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_probe_debug"
    RealVideoVaeLatentRunner(ROOT).run(
        output_root=output_root,
        run_mode="smoke",
        runtime_profile_override="debug_real_video",
    )
    return output_root
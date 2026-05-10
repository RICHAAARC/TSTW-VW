"""
文件用途：提供阶段 2 测试公共 helper。
File purpose: Provide shared helpers for stage-two tests.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.protocol.real_video_vae_latent_runner import RealVideoVaeLatentRunner


ROOT = Path(__file__).resolve().parents[1]


def run_real_video_vae_latent_tiny(tmp_path: Path) -> Path:
    """功能：执行最小阶段 2 smoke 运行并返回输出目录。

    Run the minimal stage-two smoke flow and return its output root.

    Args:
        tmp_path: Temporary root path.

    Returns:
        The stage-two run root path.
    """
    output_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_probe_scaffold"
    RealVideoVaeLatentRunner(ROOT).run(
        output_root=output_root,
        run_mode="smoke",
        samples_per_role=1,
        runtime_profile_override="tiny",
    )
    return output_root
"""
文件用途：验证阶段 2 scaffold 不依赖 Flow Matching、DiT hook 或 trajectory 实现。File purpose: Validate that the stage-two scaffold does not depend on Flow Matching, DiT hooks, or trajectory implementations.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path


def test_real_video_vae_latent_scaffold_has_no_flow_matching_dependency() -> None:
    """Validate that stage-two scaffold files avoid forbidden dependency strings.

    Args:
        None.

    Returns:
        None.
    """
    repository_root = Path(__file__).resolve().parents[1]
    stage_two_files = [
        repository_root / "experiments" / "real_video_vae_latent_probe" / "runner.py",
        repository_root / "experiments" / "real_video_vae_latent_probe" / "artifact_builder.py",
        repository_root / "main" / "backends" / "real_video_vae_latent.py",
    ]
    forbidden_fragments = [
        "flow_matching_backend",
        "dit_sampling",
    ]
    for file_path in stage_two_files:
        text = file_path.read_text(encoding="utf-8").lower()
        for forbidden_fragment in forbidden_fragments:
            assert forbidden_fragment not in text
    for file_path in stage_two_files:
        text = file_path.read_text(encoding="utf-8")
        forbidden_imports = [
            "from main.analysis.trajectory_statistic",
            "import trajectory_statistic",
            "flow_matching_trajectory",
        ]
        for forbidden_import in forbidden_imports:
            assert forbidden_import not in text
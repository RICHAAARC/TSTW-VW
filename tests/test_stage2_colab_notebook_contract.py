"""
文件用途：验证阶段 2 当前治理边界下的 notebook 合同状态。
File purpose: Validate the notebook contract status under the current stage-two governance boundary.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path


def test_stage2_notebook_is_deferred_under_current_governance() -> None:
    """Validate that the stage-two notebook entrypoint is intentionally deferred.

    Args:
        None.

    Returns:
        None.
    """
    repository_root = Path(__file__).resolve().parents[1]
    assert not (
        repository_root / "paper_workflow" / "Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb"
    ).exists()
    assert (repository_root / "main" / "colab" / "notebook_result_checker.py").exists()
    assert (repository_root / "main" / "colab" / "drive_packager.py").exists()

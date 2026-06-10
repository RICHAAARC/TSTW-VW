"""
文件用途：验证真实视频 VAE latent runner 的 formal 质量指标默认配置。
File purpose: Validate formal quality-metric defaults for the real-video VAE latent runner.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.quick]

from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner


ROOT = Path(__file__).resolve().parents[2]


def test_formal_runner_defaults_enable_lpips_without_mutating_input() -> None:
    """验证 formal runner 默认启用 LPIPS, 并且不原地修改调用方配置。

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    original_config: dict[str, object] = {}

    resolved_config = runner._apply_formal_quality_metric_defaults(
        original_config,
        run_mode="formal",
    )

    assert original_config == {}
    assert resolved_config["quality_metrics"]["enable_lpips"] is True


def test_formal_runner_preserves_explicit_lpips_disable_for_calibration_paths() -> None:
    """验证显式禁用 LPIPS 的校准路径不会被 runner 默认值覆盖。

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)
    original_config = {"quality_metrics": {"enable_lpips": False}}

    resolved_config = runner._apply_formal_quality_metric_defaults(
        original_config,
        run_mode="formal",
    )

    assert resolved_config["quality_metrics"]["enable_lpips"] is False


def test_smoke_runner_does_not_enable_lpips_by_default() -> None:
    """验证 smoke 路径不会默认启用 LPIPS, 避免默认快速测试加载模型。

    Args:
        None.

    Returns:
        None.
    """
    runner = RealVideoVaeLatentRunner(ROOT)

    resolved_config = runner._apply_formal_quality_metric_defaults(
        {},
        run_mode="smoke",
    )

    assert "quality_metrics" not in resolved_config

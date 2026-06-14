"""验证 `temporal_quality_metric_probe` 的轻量构建契约。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from experiments.temporal_quality_metric_probe.temporal_quality_builder import (
    build_temporal_quality_table,
    compute_temporal_ssim,
)

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_compute_temporal_ssim_accepts_frame_tensor() -> None:
    """确认 t-SSIM 可以从相邻帧张量直接计算。"""
    frames = np.zeros((3, 16, 16, 3), dtype=np.float32)
    frames[1] = 0.1
    frames[2] = 0.2

    mean_value, std_value = compute_temporal_ssim(frames)

    assert mean_value is not None
    assert std_value is not None
    assert 0.0 <= mean_value <= 1.0


def test_temporal_quality_table_preserves_metric_availability() -> None:
    """确认聚合表明确区分 t-SSIM 可用和 t-LPIPS 缺失。"""
    rows = build_temporal_quality_table(
        [
            {
                "method_name": "tubelet_sync",
                "attack_name": "h264_compression",
                "video_role": "attacked",
                "mean_t_ssim": 0.9,
                "mean_t_lpips": None,
            },
            {
                "method_name": "tubelet_sync",
                "attack_name": "h264_compression",
                "video_role": "attacked",
                "mean_t_ssim": 0.8,
                "mean_t_lpips": None,
            },
        ]
    )

    assert len(rows) == 1
    assert rows[0]["method_name"] == "tubelet_sync"
    assert rows[0]["t_ssim_available"] is True
    assert rows[0]["t_lpips_available"] is False
    assert rows[0]["mean_t_ssim"] == pytest.approx(0.85)


def test_temporal_quality_probe_contract_is_documented() -> None:
    """确认图表补充流程和命令行入口已经登记。"""
    root = Path(__file__).resolve().parents[2]
    doc = (root / "docs" / "builds" / "图表补充流程.md").read_text(encoding="utf-8")
    script = root / "scripts" / "package_results" / "build_temporal_quality_metric_probe.py"
    source = (root / "experiments" / "temporal_quality_metric_probe" / "temporal_quality_builder.py").read_text(
        encoding="utf-8"
    )

    assert "temporal_quality_metric_probe" in doc
    assert "t-LPIPS" in doc
    assert "t-SSIM" in doc
    assert script.exists()
    assert "lpips_model_not_configured" in source


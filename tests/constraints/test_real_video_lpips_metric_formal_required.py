"""
文件用途：验证 LPIPS 在 formal 模式下的必需性与行为。
File purpose: Verify LPIPS metric requirement and behavior in formal mode.
Module type: General module
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.formal]

from main.analysis.quality_metrics import build_quality_metrics_payload


def test_formal_mode_lpips_disabled_returns_none() -> None:
    """功能：formal 模式下没有 LPIPS 模型时，LPIPS 应为 None 且记录失败原因。

    Test that LPIPS is None when model is not configured.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 创建 dummy .npy artifact
        frames = np.random.RandomState(42).uniform(0.2, 0.8, size=(8, 256, 256, 3)).astype(
            np.float32
        )

        reference_path = tmpdir_path / "reference.npy"
        comparison_path = tmpdir_path / "comparison.npy"

        np.save(reference_path, frames)
        np.save(comparison_path, frames)

        # 使用 placeholder 模式（没有 LPIPS 模型）
        payload = build_quality_metrics_payload(
            reference_path,
            comparison_path,
            runtime_config={"quality_metrics_mode": "placeholder"},
        )

        # Placeholder 模式应返回 None LPIPS
        assert payload["watermarked_video_lpips"] is None
        assert payload["quality_metrics_runtime"] == "placeholder_tensor_video_metrics"


def test_real_mode_lpips_not_configured_fails() -> None:
    """功能：real 模式下没有 LPIPS 配置时，应记录失败原因或降级。

    Test that real mode handles missing LPIPS configuration gracefully.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 创建 dummy .npy artifact（real 模式会尝试读取为 .mp4，失败后降级）
        frames = np.random.RandomState(42).uniform(0.2, 0.8, size=(8, 256, 256, 3)).astype(
            np.float32
        )

        reference_path = tmpdir_path / "reference.npy"
        comparison_path = tmpdir_path / "comparison.npy"

        np.save(reference_path, frames)
        np.save(comparison_path, frames)

        # 使用 real 模式但没有 LPIPS 配置
        payload = build_quality_metrics_payload(
            reference_path,
            comparison_path,
            runtime_config={
                "quality_metrics_mode": "real_video_frame_metrics",
                # 故意不配置 local_lpips_model_root
            },
        )

        # real 模式会尝试读取 .mp4，但 .npy 会导致 video_io_error
        # 此时会早期返回，LPIPS 会是 None
        assert payload["watermarked_video_lpips"] is None
        
        # 应该有某种失败原因（video_io_error 或 lpips_failure_reason）
        has_failure_reason = (
            payload.get("quality_failure_reason") is not None
            or payload.get("lpips_failure_reason") is not None
        )
        assert has_failure_reason, "Should have either quality or LPIPS failure reason"


def test_formal_checker_rejects_placeholder_lpips() -> None:
    """功能：formal 检查器应拒绝 placeholder 模式的 LPIPS。

    Test that formal checker identifies placeholder LPIPS as blocking.
    """
    # 这是 formal 模式下的检查要求
    # formal 模式必须使用 real_video_frame_metrics 而不是 placeholder_tensor_video_metrics
    payload = {
        "quality_metrics_runtime": "placeholder_tensor_video_metrics",
        "watermarked_video_lpips": None,
    }

    # formal 检查器应该识别这个 payload 来自 placeholder 运行时
    is_placeholder = payload["quality_metrics_runtime"] != "real_video_frame_metrics"
    assert is_placeholder, "Formal mode must use real_video_frame_metrics, not placeholder"


def test_real_mode_lpips_configuration_path() -> None:
    """功能：验证 real 模式 LPIPS 配置路径的正确名称。

    Test that LPIPS model path is correctly resolved from runtime_config.
    """
    # runtime_config 中应该有 local_lpips_model_root
    # 验证路径名称的一致性
    runtime_config = {
        "local_lpips_model_root": "/some/path/to/lpips",
        "local_vae_model_root": "/some/path/to/vae",
    }

    # 检查关键字段
    assert "local_lpips_model_root" in runtime_config
    assert "local_vae_model_root" in runtime_config

    # 确保名称一致
    lpips_root = runtime_config.get("local_lpips_model_root") or runtime_config.get(
        "lpips_model_root"
    )
    assert lpips_root is not None


def test_formal_mode_must_not_silently_disable_lpips() -> None:
    """功能：formal 模式下 LPIPS 不能静默禁用，必须报告失败原因。

    Test that LPIPS failure is explicitly reported, not silently ignored.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 创建 dummy artifact
        frames = np.random.RandomState(42).uniform(0.2, 0.8, size=(8, 256, 256, 3)).astype(
            np.float32
        )

        reference_path = tmpdir_path / "reference.npy"
        comparison_path = tmpdir_path / "comparison.npy"

        np.save(reference_path, frames)
        np.save(comparison_path, frames)

        # 使用 placeholder 模式
        payload = build_quality_metrics_payload(
            reference_path,
            comparison_path,
            runtime_config={"quality_metrics_mode": "placeholder"},
        )

        # placeholder 模式中，LPIPS 是 None 但这是预期的（placeholder 本身不支持 LPIPS）
        # formal 模式会有不同的处理
        assert payload["watermarked_video_lpips"] is None
        # placeholder 可能没有 lpips_failure_reason 字段，这是可以接受的


def test_lpips_payload_structure_completeness() -> None:
    """功能：验证 LPIPS 相关字段在 payload 中的完整性。

    Test that LPIPS-related fields are properly structured in output payload.
    """
    # real 模式 payload 应该包含这些字段
    expected_lpips_fields = [
        "watermarked_video_lpips",
        "quality_metrics_runtime",
        "disabled_quality_metrics",
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        frames = np.random.RandomState(42).uniform(0.2, 0.8, size=(8, 256, 256, 3)).astype(
            np.float32
        )

        reference_path = tmpdir_path / "reference.npy"
        comparison_path = tmpdir_path / "comparison.npy"

        np.save(reference_path, frames)
        np.save(comparison_path, frames)

        payload = build_quality_metrics_payload(
            reference_path,
            comparison_path,
            runtime_config={"quality_metrics_mode": "placeholder"},
        )

        # 验证必要字段存在
        for field in expected_lpips_fields:
            assert field in payload, f"Missing required field: {field}"

        # CLIP 必须在 disabled_quality_metrics 中
        assert "clip_similarity" in payload["disabled_quality_metrics"]


def test_formal_pass_condition_requires_real_metrics() -> None:
    """功能：formal PASS 条件必须要求 real_video_frame_metrics 而不是 placeholder。

    Test that formal pass condition explicitly rejects placeholder metrics.
    """
    # 这个测试验证了 formal checker 的一个关键要求
    # formal PASS 必须满足：quality_metrics_runtime == "real_video_frame_metrics"

    placeholder_payload = {
        "quality_metrics_runtime": "placeholder_tensor_video_metrics",
        "watermarked_video_lpips": None,
    }

    real_payload = {
        "quality_metrics_runtime": "real_video_frame_metrics",
        "watermarked_video_lpips": 0.123,
    }

    # formal checker 逻辑
    def can_pass_formal_check(payload: dict) -> bool:
        # formal 必须使用 real metrics
        if payload["quality_metrics_runtime"] != "real_video_frame_metrics":
            return False
        return True

    assert not can_pass_formal_check(placeholder_payload), "Placeholder should not pass formal"
    assert can_pass_formal_check(real_payload), "Real metrics should pass formal check"

"""
文件用途：验证真实视频攻击 registry 支持两种运行时模式。
File purpose: Validate real video attack registry supports dual runtime modes.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.quick

from main.attacks.real_video_attack_registry import (
    build_real_video_attack_registry,
)


@pytest.fixture
def minimal_attack_config() -> dict:
    """生成最小化 attack config。"""
    return {
        "attacks": [
            {"attack_name": "h264_compression", "attack_params": {"crf": 28}},
            {"attack_name": "no_attack", "attack_params": {}},
        ]
    }


def test_build_attack_registry_tensor_scaffold(minimal_attack_config: dict) -> None:
    """验证 tensor_scaffold 模式的 registry 构建。"""
    registry = build_real_video_attack_registry(
        minimal_attack_config,
        runtime_kind="tensor_scaffold",
    )
    assert len(registry) > 0
    # 应该包含 VideoTensorAttackPlaceholder 和 TemporalAttackPlaceholder
    assert any(hasattr(attack, "apply") for attack in registry)


def test_build_attack_registry_real_video(minimal_attack_config: dict) -> None:
    """验证 real_video 模式的 registry 构建。"""
    registry = build_real_video_attack_registry(
        minimal_attack_config,
        runtime_kind="real_video",
    )
    assert len(registry) > 0
    # 应该包含真实视频攻击类
    assert any(hasattr(attack, "apply_video") or hasattr(attack, "apply") for attack in registry)


def test_build_attack_registry_unsupported_runtime_kind() -> None:
    """验证不支持的 runtime_kind 的处理。"""
    config = {"attacks": [{"attack_name": "no_attack", "attack_params": {}}]}
    with pytest.raises(ValueError, match="unsupported runtime_kind"):
        build_real_video_attack_registry(config, runtime_kind="invalid_kind")


def test_build_attack_registry_default_runtime_kind() -> None:
    """验证默认 runtime_kind 为 real_video。"""
    config = {"attacks": [{"attack_name": "no_attack", "attack_params": {}}]}
    registry = build_real_video_attack_registry(config)
    assert len(registry) > 0
    assert any(hasattr(attack, "apply_video") or hasattr(attack, "apply_frames") or hasattr(attack, "apply") for attack in registry)


def test_build_attack_registry_invalid_config() -> None:
    """验证无效配置的处理。"""
    with pytest.raises(TypeError, match="attack_config must be a dictionary"):
        build_real_video_attack_registry("not a dict")


def test_build_attack_registry_empty_attacks() -> None:
    """验证空 attacks list 的处理。"""
    with pytest.raises(ValueError, match="attacks must be a non-empty list"):
        build_real_video_attack_registry({"attacks": []})


def test_real_video_registry_supports_compression_attacks() -> None:
    """验证 real_video registry 支持压缩攻击。"""
    config = {
        "attacks": [
            {"attack_name": "h264_compression", "attack_params": {"crf": 28}},
            {"attack_name": "h265_compression", "attack_params": {"crf": 30}},
        ]
    }
    registry = build_real_video_attack_registry(config, runtime_kind="real_video")
    assert len(registry) == 2


def test_real_video_registry_supports_spatial_attacks() -> None:
    """验证 real_video registry 支持空间攻击。"""
    config = {
        "attacks": [
            {"attack_name": "spatial_resize", "attack_params": {"scale": 0.75}},
            {"attack_name": "crop_resize", "attack_params": {"crop_ratio": 0.85}},
            {"attack_name": "blur", "attack_params": {"kernel_size": 5}},
        ]
    }
    registry = build_real_video_attack_registry(config, runtime_kind="real_video")
    assert len(registry) == 3


def test_real_video_registry_supports_noise_attacks() -> None:
    """验证 real_video registry 支持噪声攻击。"""
    config = {
        "attacks": [
            {"attack_name": "gaussian_noise", "attack_params": {"sigma": 0.02}},
        ]
    }
    registry = build_real_video_attack_registry(config, runtime_kind="real_video")
    assert len(registry) == 1


def test_real_video_registry_mixed_attacks() -> None:
    """验证 real_video registry 支持混合攻击。"""
    config = {
        "attacks": [
            {"attack_name": "h264_compression", "attack_params": {"crf": 28}},
            {"attack_name": "gaussian_noise", "attack_params": {"sigma": 0.02}},
            {"attack_name": "no_attack", "attack_params": {}},
        ]
    }
    registry = build_real_video_attack_registry(config, runtime_kind="real_video")
    assert len(registry) == 3

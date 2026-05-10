"""
文件用途：验证真实视频噪声攻击功能。
File purpose: Validate real video noise attack functionality.
Module type: General module
"""

from __future__ import annotations

import numpy as np
import pytest

from main.attacks.video_noise import GaussianNoiseVideoAttack


@pytest.fixture
def sample_frames() -> np.ndarray:
    """生成采样帧数据 [F, H, W, 3] float32 in [0, 1]。"""
    np.random.seed(42)
    return np.ones((4, 256, 256, 3), dtype=np.float32) * 0.5


@pytest.mark.smoke
def test_gaussian_noise_attack_initialization() -> None:
    """验证高斯噪声攻击初始化。"""
    attack_params = {"sigma": 0.02}
    attack = GaussianNoiseVideoAttack(attack_params)
    assert attack.attack_name == "gaussian_noise"
    assert attack.attack_params["sigma"] == 0.02


@pytest.mark.smoke
def test_gaussian_noise_attack_invalid_sigma() -> None:
    """验证无效 sigma 参数的处理。"""
    attack = GaussianNoiseVideoAttack({"sigma": -0.1})
    frames = np.ones((2, 64, 64, 3), dtype=np.float32) * 0.5
    with pytest.raises(ValueError, match="sigma must be non-negative"):
        attack.apply_frames(frames)


@pytest.mark.smoke
def test_gaussian_noise_attack_apply_frames(sample_frames: np.ndarray) -> None:
    """验证高斯噪声的应用。"""
    attack = GaussianNoiseVideoAttack({"sigma": 0.02})
    result = attack.apply_frames(sample_frames)
    assert result.shape == sample_frames.shape
    assert result.dtype == np.float32
    assert np.all(result >= 0.0) and np.all(result <= 1.0)
    # 验证添加了噪声（不完全相同）
    assert not np.allclose(result, sample_frames)


@pytest.mark.smoke
def test_gaussian_noise_attack_deterministic_seeding() -> None:
    """验证确定性种子产生一致的结果。"""
    attack = GaussianNoiseVideoAttack({"sigma": 0.02})
    frames = np.ones((4, 64, 64, 3), dtype=np.float32) * 0.5

    result1 = attack.apply_frames(frames.copy())
    result2 = attack.apply_frames(frames.copy())
    # 由于使用 compute_object_digest，结果应该一致
    assert np.allclose(result1, result2, atol=1e-6)


@pytest.mark.smoke
def test_gaussian_noise_attack_with_runtime_config() -> None:
    """验证使用 runtime config 的噪声攻击。"""
    attack = GaussianNoiseVideoAttack({"sigma": 0.02})
    frames = np.ones((2, 64, 64, 3), dtype=np.float32) * 0.5
    runtime_config = {
        "run_id": "test_run_001",
        "sample_id": "sample_001",
    }
    result = attack.apply_frames(frames, runtime_config=runtime_config)
    assert result.shape == frames.shape
    assert np.all(result >= 0.0) and np.all(result <= 1.0)


@pytest.mark.smoke
def test_gaussian_noise_zero_sigma() -> None:
    """验证 sigma=0 时的情况（无噪声）。"""
    attack = GaussianNoiseVideoAttack({"sigma": 0.0})
    frames = np.ones((2, 64, 64, 3), dtype=np.float32) * 0.5
    result = attack.apply_frames(frames)
    # 由于使用 RandomState，即使 sigma=0，可能仍有浮点数精度差异
    assert np.allclose(result, frames, atol=1e-6)


@pytest.mark.smoke
def test_gaussian_noise_attack_invalid_frames_shape() -> None:
    """验证无效帧形状的处理。"""
    attack = GaussianNoiseVideoAttack({"sigma": 0.02})
    invalid_frames = np.random.rand(2, 64, 64, 4).astype(np.float32)  # 4 channels
    with pytest.raises(ValueError, match="frames must be"):
        attack.apply_frames(invalid_frames)


@pytest.mark.smoke
def test_gaussian_noise_high_sigma() -> None:
    """验证高 sigma 值的情况。"""
    attack = GaussianNoiseVideoAttack({"sigma": 0.5})
    frames = np.ones((2, 64, 64, 3), dtype=np.float32) * 0.5
    result = attack.apply_frames(frames)
    # 结果应该 clipped 到 [0, 1]
    assert np.all(result >= 0.0) and np.all(result <= 1.0)
    # 结果应该与输入显著不同
    assert not np.allclose(result, frames, atol=0.1)

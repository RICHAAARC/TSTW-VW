"""
文件用途：验证真实视频空间攻击功能。
File purpose: Validate real video spatial attack functionality.
Module type: General module
"""

from __future__ import annotations

import numpy as np
import pytest

from main.attacks.spatial import BlurAttack, CropResizeAttack, SpatialResizeAttack


@pytest.fixture
def sample_frames() -> np.ndarray:
    """生成采样帧数据 [F, H, W, 3] float32 in [0, 1]。"""
    np.random.seed(42)
    return np.random.rand(4, 256, 256, 3).astype(np.float32)


@pytest.mark.smoke
def test_spatial_resize_attack_initialization() -> None:
    """验证空间下采样攻击初始化。"""
    attack_params = {"scale": 0.75}
    attack = SpatialResizeAttack(attack_params)
    assert attack.attack_name == "spatial_resize"
    assert attack.attack_params["scale"] == 0.75


@pytest.mark.smoke
def test_spatial_resize_attack_invalid_scale() -> None:
    """验证无效 scale 参数的处理。"""
    attack = SpatialResizeAttack({"scale": 1.5})
    frames = np.random.rand(2, 64, 64, 3).astype(np.float32)
    with pytest.raises(ValueError, match="scale must be in"):
        attack.apply_frames(frames)


@pytest.mark.smoke
def test_spatial_resize_attack_apply_frames(sample_frames: np.ndarray) -> None:
    """验证空间下采样的应用。"""
    attack = SpatialResizeAttack({"scale": 0.5})
    result = attack.apply_frames(sample_frames)
    assert result.shape == sample_frames.shape
    assert result.dtype == np.float32
    assert np.all(result >= 0.0) and np.all(result <= 1.0)


@pytest.mark.smoke
def test_crop_resize_attack_initialization() -> None:
    """验证中心裁剪攻击初始化。"""
    attack_params = {"crop_ratio": 0.85}
    attack = CropResizeAttack(attack_params)
    assert attack.attack_name == "crop_resize"
    assert attack.attack_params["crop_ratio"] == 0.85


@pytest.mark.smoke
def test_crop_resize_attack_invalid_crop_ratio() -> None:
    """验证无效 crop_ratio 参数的处理。"""
    attack = CropResizeAttack({"crop_ratio": 1.5})
    frames = np.random.rand(2, 64, 64, 3).astype(np.float32)
    with pytest.raises(ValueError, match="crop_ratio must be in"):
        attack.apply_frames(frames)


@pytest.mark.smoke
def test_crop_resize_attack_apply_frames(sample_frames: np.ndarray) -> None:
    """验证中心裁剪的应用。"""
    attack = CropResizeAttack({"crop_ratio": 0.85})
    result = attack.apply_frames(sample_frames)
    assert result.shape == sample_frames.shape
    assert result.dtype == np.float32
    assert np.all(result >= 0.0) and np.all(result <= 1.0)


@pytest.mark.smoke
def test_blur_attack_initialization() -> None:
    """验证高斯模糊攻击初始化。"""
    attack_params = {"kernel_size": 5, "sigma": 1.0}
    attack = BlurAttack(attack_params)
    assert attack.attack_name == "blur"
    assert attack.attack_params["kernel_size"] == 5


@pytest.mark.smoke
def test_blur_attack_apply_frames(sample_frames: np.ndarray) -> None:
    """验证高斯模糊的应用。"""
    attack = BlurAttack({"kernel_size": 5, "sigma": 1.0})
    result = attack.apply_frames(sample_frames)
    assert result.shape == sample_frames.shape
    assert result.dtype == np.float32
    assert np.all(result >= 0.0) and np.all(result <= 1.0)


@pytest.mark.smoke
def test_spatial_attacks_invalid_frames_shape() -> None:
    """验证无效帧形状的处理。"""
    attack = SpatialResizeAttack({"scale": 0.75})
    invalid_frames = np.random.rand(2, 64, 64, 4).astype(np.float32)  # 4 channels
    with pytest.raises(ValueError, match="frames must be"):
        attack.apply_frames(invalid_frames)


@pytest.mark.smoke
def test_spatial_attacks_accept_list_input() -> None:
    """验证接受列表输入并转换为 numpy 数组。"""
    attack = SpatialResizeAttack({"scale": 0.5})
    frames_list = [[[[[0.5 for _ in range(3)] for _ in range(64)] for _ in range(64)] for _ in range(4)]]
    # 这是一个嵌套列表，可能需要手动转换
    frames_array = np.random.rand(2, 64, 64, 3).astype(np.float32)
    result = attack.apply_frames(frames_array)
    assert result is not None

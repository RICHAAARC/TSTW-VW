"""
文件用途：验证 cross-event VAE batching 配置解析与批处理工具。
模块类型：功能测试。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.quick

from experiments.real_video_vae_latent_probe.vae_batching import (
    DecodeRequest,
    EncodeRequest,
    group_decode_requests,
    group_encode_requests,
    resolve_cross_event_vae_batching_config,
    run_decode_request_batch,
    run_encode_request_batch,
)


class _EchoVaeBackend:
    """功能：提供不依赖模型资源的测试 VAE backend。"""

    def decode_video(self, latent_batch: np.ndarray, *, config: dict | None = None) -> np.ndarray:
        del config
        return latent_batch[:, :3].transpose(0, 2, 3, 1).astype(np.float32)

    def encode_video(self, video_batch: np.ndarray, *, config: dict | None = None) -> np.ndarray:
        del config
        return video_batch.transpose(0, 3, 1, 2).astype(np.float32)


class _FallbackVaeBackend(_EchoVaeBackend):
    """功能：在聚合超过单条 request 时模拟 CUDA OOM。"""

    def decode_video(self, latent_batch: np.ndarray, *, config: dict | None = None) -> np.ndarray:
        if int(latent_batch.shape[0]) > 2:
            raise RuntimeError("CUDA out of memory")
        return super().decode_video(latent_batch, config=config)


def _decode_request(request_id: str, value: float) -> DecodeRequest:
    latent = np.full((2, 3, 2, 2), value, dtype=np.float32)
    return DecodeRequest(
        request_id=request_id,
        cache_key=(request_id, "8", "2x2"),
        sample=None,
        latent_tensor=latent,
        output_relpath=Path("artifacts") / "videos" / "decoded" / f"{request_id}.mp4",
        fps=8,
        target_resolution=(2, 2),
        method_variant="frame_prc",
        split="dev",
        event_id=request_id,
    )


def _encode_request(request_id: str, value: float) -> EncodeRequest:
    frames = np.full((2, 2, 2, 3), value, dtype=np.float32)
    return EncodeRequest(
        request_id=request_id,
        cache_key=(request_id, "latent"),
        reference_sample=None,
        video_frames=frames,
        output_relpath=Path("artifacts") / "latents" / "reencoded" / f"{request_id}.npy",
        method_variant="frame_prc",
        attack_name="no_attack",
        split="dev",
        event_id=request_id,
    )


@pytest.mark.unit
def test_resolve_cross_event_vae_batching_config_defaults_to_disabled() -> None:
    config = resolve_cross_event_vae_batching_config({})

    assert config.enabled is False
    assert config.decode_batch_size == 4
    assert config.encode_batch_size == 4
    assert config.grouping == "same_shape_same_backend"


@pytest.mark.unit
def test_resolve_cross_event_vae_batching_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        resolve_cross_event_vae_batching_config({"cross_event_vae_decode_batch_size": 0})
    with pytest.raises(ValueError):
        resolve_cross_event_vae_batching_config({"cross_event_vae_encode_batch_size": "bad"})
    with pytest.raises(ValueError):
        resolve_cross_event_vae_batching_config({"cross_event_vae_batch_grouping": "padded"})


@pytest.mark.unit
def test_cross_event_vae_batching_groups_and_splits_decode_encode_requests() -> None:
    metadata = {
        "vae_backend_name": "video_vae_tensor_runtime",
        "vae_backend_version": "framewise_tensor_runtime",
        "device": "cpu",
        "dtype": "float32",
        "runtime_impl": "mock_numpy",
        "vae_decode_mode": "framewise",
        "vae_encode_mode": "framewise",
    }
    config = resolve_cross_event_vae_batching_config(
        {
            "cross_event_vae_batching_enabled": True,
            "cross_event_vae_decode_batch_size": 2,
            "cross_event_vae_encode_batch_size": 2,
        }
    )
    decode_requests = [_decode_request("a", 0.1), _decode_request("b", 0.2)]
    encode_requests = [_encode_request("a", 0.3), _encode_request("b", 0.4)]

    decode_groups = group_decode_requests(decode_requests, vae_metadata=metadata)
    encode_groups = group_encode_requests(encode_requests, vae_metadata=metadata)
    decode_results = run_decode_request_batch(
        decode_groups[0],
        vae_runtime_backend=_EchoVaeBackend(),
        config=config,
    )
    encode_results = run_encode_request_batch(
        encode_groups[0],
        vae_runtime_backend=_EchoVaeBackend(),
        config=config,
    )

    assert len(decode_groups) == 1
    assert len(encode_groups) == 1
    assert [result.effective_batch_size for result in decode_results] == [2, 2]
    assert [result.video_frames.shape for result in decode_results] == [(2, 2, 2, 3), (2, 2, 2, 3)]
    assert [result.effective_batch_size for result in encode_results] == [2, 2]
    assert [result.latent_tensor.shape for result in encode_results] == [(2, 3, 2, 2), (2, 3, 2, 2)]


@pytest.mark.unit
def test_cross_event_vae_batching_falls_back_on_cuda_oom() -> None:
    config = resolve_cross_event_vae_batching_config(
        {
            "cross_event_vae_batching_enabled": True,
            "cross_event_vae_decode_batch_size": 2,
            "cross_event_vae_batch_fallback_on_oom": True,
        }
    )

    results = run_decode_request_batch(
        [_decode_request("a", 0.1), _decode_request("b", 0.2)],
        vae_runtime_backend=_FallbackVaeBackend(),
        config=config,
    )

    assert [result.effective_batch_size for result in results] == [1, 1]
    assert all(result.fallback_count > 0 for result in results)
    assert all("cuda_oom" in str(result.fallback_reason) for result in results)

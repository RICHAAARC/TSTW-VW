"""
文件用途：为真实视频 VAE latent probe runner 提供跨事件 VAE batching 调度工具。
模块类型：阶段性实验 runner 辅助模块。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


DEFAULT_CROSS_EVENT_VAE_BATCH_GROUPING = "same_shape_same_backend"


@dataclass(frozen=True)
class CrossEventVaeBatchingConfig:
    """跨事件 VAE batching 的受治理运行配置。"""

    enabled: bool
    decode_batch_size: int
    encode_batch_size: int
    grouping: str
    fallback_on_oom: bool
    write_trace: bool


@dataclass(frozen=True)
class DecodeRequest:
    """单条 decode 请求。

    该结构只描述调度所需的信息，不改变 event 的方法语义。
    """

    request_id: str
    cache_key: tuple[str, str, str]
    sample: Any
    latent_tensor: np.ndarray
    output_relpath: Path
    fps: int
    target_resolution: tuple[int, int]
    method_variant: str
    split: str
    event_id: str


@dataclass(frozen=True)
class DecodeResult:
    """单条 decode 结果。"""

    request_id: str
    cache_key: tuple[str, str, str]
    video_frames: np.ndarray
    output_relpath: Path
    fps: int
    target_resolution: tuple[int, int]
    batch_group_id: str
    batch_request_count: int
    effective_batch_size: int
    fallback_count: int
    fallback_reason: str | None
    split: str


@dataclass(frozen=True)
class EncodeRequest:
    """单条 encode 请求。"""

    request_id: str
    cache_key: tuple[str, str]
    reference_sample: Any
    video_frames: np.ndarray
    output_relpath: Path
    method_variant: str
    attack_name: str
    split: str
    event_id: str


@dataclass(frozen=True)
class EncodeResult:
    """单条 encode 结果。"""

    request_id: str
    cache_key: tuple[str, str]
    latent_tensor: np.ndarray
    output_relpath: Path
    batch_group_id: str
    batch_request_count: int
    effective_batch_size: int
    fallback_count: int
    fallback_reason: str | None
    split: str


def resolve_cross_event_vae_batching_config(
    runtime_config: dict[str, Any] | None,
) -> CrossEventVaeBatchingConfig:
    """解析跨事件 VAE batching 配置。

    Args:
        runtime_config: runner 已解析的 runtime 配置字典。

    Returns:
        规范化后的 batching 配置。
    """
    config_payload = dict(runtime_config or {})
    enabled = _coerce_bool(
        config_payload.get("cross_event_vae_batching_enabled", False),
        field_name="cross_event_vae_batching_enabled",
    )
    decode_batch_size = _coerce_positive_int(
        config_payload.get("cross_event_vae_decode_batch_size", 4),
        field_name="cross_event_vae_decode_batch_size",
    )
    encode_batch_size = _coerce_positive_int(
        config_payload.get("cross_event_vae_encode_batch_size", 4),
        field_name="cross_event_vae_encode_batch_size",
    )
    grouping = str(
        config_payload.get(
            "cross_event_vae_batch_grouping",
            DEFAULT_CROSS_EVENT_VAE_BATCH_GROUPING,
        )
    )
    if grouping != DEFAULT_CROSS_EVENT_VAE_BATCH_GROUPING:
        raise ValueError(
            "cross_event_vae_batch_grouping must be same_shape_same_backend"
        )
    fallback_on_oom = _coerce_bool(
        config_payload.get("cross_event_vae_batch_fallback_on_oom", True),
        field_name="cross_event_vae_batch_fallback_on_oom",
    )
    write_trace = _coerce_bool(
        config_payload.get("cross_event_vae_batch_write_trace", True),
        field_name="cross_event_vae_batch_write_trace",
    )
    return CrossEventVaeBatchingConfig(
        enabled=enabled,
        decode_batch_size=decode_batch_size,
        encode_batch_size=encode_batch_size,
        grouping=grouping,
        fallback_on_oom=fallback_on_oom,
        write_trace=write_trace,
    )


def group_decode_requests(
    requests: list[DecodeRequest],
    *,
    vae_metadata: dict[str, Any],
) -> list[list[DecodeRequest]]:
    """按同构 decode 条件分组。

    Args:
        requests: decode 请求列表。
        vae_metadata: 当前 VAE backend 元数据。

    Returns:
        保持输入稳定顺序的同构请求组。
    """
    groups: dict[tuple[Any, ...], list[DecodeRequest]] = {}
    for request in requests:
        key = (
            "decode",
            tuple(int(value) for value in request.latent_tensor.shape),
            tuple(int(value) for value in request.target_resolution),
            int(request.fps),
            request.split,
            vae_metadata.get("vae_backend_name", "unknown"),
            vae_metadata.get("vae_backend_version", "unknown"),
            vae_metadata.get("device", "unknown"),
            vae_metadata.get("dtype", "unknown"),
            vae_metadata.get("runtime_impl", "unknown"),
            vae_metadata.get("vae_decode_mode", "unknown"),
        )
        groups.setdefault(key, []).append(request)
    return list(groups.values())


def group_encode_requests(
    requests: list[EncodeRequest],
    *,
    vae_metadata: dict[str, Any],
) -> list[list[EncodeRequest]]:
    """按同构 encode 条件分组。

    Args:
        requests: encode 请求列表。
        vae_metadata: 当前 VAE backend 元数据。

    Returns:
        保持输入稳定顺序的同构请求组。
    """
    groups: dict[tuple[Any, ...], list[EncodeRequest]] = {}
    for request in requests:
        key = (
            "encode",
            tuple(int(value) for value in request.video_frames.shape),
            request.split,
            vae_metadata.get("vae_backend_name", "unknown"),
            vae_metadata.get("vae_backend_version", "unknown"),
            vae_metadata.get("device", "unknown"),
            vae_metadata.get("dtype", "unknown"),
            vae_metadata.get("runtime_impl", "unknown"),
            vae_metadata.get("vae_encode_mode", "unknown"),
        )
        groups.setdefault(key, []).append(request)
    return list(groups.values())


def run_decode_request_batch(
    requests: list[DecodeRequest],
    *,
    vae_runtime_backend: Any,
    config: CrossEventVaeBatchingConfig,
) -> list[DecodeResult]:
    """执行一组同构 decode 请求。

    Args:
        requests: 同构 decode 请求列表。
        vae_runtime_backend: 具备 `decode_video()` 的 VAE backend。
        config: batching 配置。

    Returns:
        与请求一一对应的 decode 结果。
    """
    results: list[DecodeResult] = []
    for chunk_start in range(0, len(requests), config.decode_batch_size):
        chunk = requests[chunk_start : chunk_start + config.decode_batch_size]
        results.extend(
            _run_decode_chunk_with_fallback(
                chunk,
                vae_runtime_backend=vae_runtime_backend,
                config=config,
                fallback_count=0,
                fallback_reason=None,
            )
        )
    return results


def run_encode_request_batch(
    requests: list[EncodeRequest],
    *,
    vae_runtime_backend: Any,
    config: CrossEventVaeBatchingConfig,
) -> list[EncodeResult]:
    """执行一组同构 encode 请求。

    Args:
        requests: 同构 encode 请求列表。
        vae_runtime_backend: 具备 `encode_video()` 的 VAE backend。
        config: batching 配置。

    Returns:
        与请求一一对应的 encode 结果。
    """
    results: list[EncodeResult] = []
    for chunk_start in range(0, len(requests), config.encode_batch_size):
        chunk = requests[chunk_start : chunk_start + config.encode_batch_size]
        results.extend(
            _run_encode_chunk_with_fallback(
                chunk,
                vae_runtime_backend=vae_runtime_backend,
                config=config,
                fallback_count=0,
                fallback_reason=None,
            )
        )
    return results


def is_probable_cuda_oom(exc: BaseException) -> bool:
    """判断异常是否近似 CUDA OOM。

    Args:
        exc: 捕获到的异常。

    Returns:
        当异常文本指向显存不足时返回 True。
    """
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "cuda out of memory",
            "out of memory",
            "cublas_status_alloc_failed",
            "cuda error: out of memory",
        )
    )


def _run_decode_chunk_with_fallback(
    requests: list[DecodeRequest],
    *,
    vae_runtime_backend: Any,
    config: CrossEventVaeBatchingConfig,
    fallback_count: int,
    fallback_reason: str | None,
) -> list[DecodeResult]:
    if not requests:
        return []
    try:
        return _run_decode_chunk(
            requests,
            vae_runtime_backend=vae_runtime_backend,
            fallback_count=fallback_count,
            fallback_reason=fallback_reason,
        )
    except Exception as exc:
        if not config.fallback_on_oom or not is_probable_cuda_oom(exc) or len(requests) <= 1:
            raise
        fallback_message = _format_cuda_oom_reason(exc)
        mid = max(1, len(requests) // 2)
        return (
            _run_decode_chunk_with_fallback(
                requests[:mid],
                vae_runtime_backend=vae_runtime_backend,
                config=config,
                fallback_count=fallback_count + 1,
                fallback_reason=fallback_message,
            )
            + _run_decode_chunk_with_fallback(
                requests[mid:],
                vae_runtime_backend=vae_runtime_backend,
                config=config,
                fallback_count=fallback_count + 1,
                fallback_reason=fallback_message,
            )
        )


def _run_encode_chunk_with_fallback(
    requests: list[EncodeRequest],
    *,
    vae_runtime_backend: Any,
    config: CrossEventVaeBatchingConfig,
    fallback_count: int,
    fallback_reason: str | None,
) -> list[EncodeResult]:
    if not requests:
        return []
    try:
        return _run_encode_chunk(
            requests,
            vae_runtime_backend=vae_runtime_backend,
            fallback_count=fallback_count,
            fallback_reason=fallback_reason,
        )
    except Exception as exc:
        if not config.fallback_on_oom or not is_probable_cuda_oom(exc) or len(requests) <= 1:
            raise
        fallback_message = _format_cuda_oom_reason(exc)
        mid = max(1, len(requests) // 2)
        return (
            _run_encode_chunk_with_fallback(
                requests[:mid],
                vae_runtime_backend=vae_runtime_backend,
                config=config,
                fallback_count=fallback_count + 1,
                fallback_reason=fallback_message,
            )
            + _run_encode_chunk_with_fallback(
                requests[mid:],
                vae_runtime_backend=vae_runtime_backend,
                config=config,
                fallback_count=fallback_count + 1,
                fallback_reason=fallback_message,
            )
        )


def _run_decode_chunk(
    requests: list[DecodeRequest],
    *,
    vae_runtime_backend: Any,
    fallback_count: int,
    fallback_reason: str | None,
) -> list[DecodeResult]:
    frame_counts = [int(request.latent_tensor.shape[0]) for request in requests]
    concat_latents = np.concatenate([request.latent_tensor for request in requests], axis=0)
    decoded = vae_runtime_backend.decode_video(
        concat_latents,
        config={"target_resolution": requests[0].target_resolution},
    )
    normalized_decoded = _normalize_decoded_video(decoded)
    split_videos = _split_by_frame_counts(normalized_decoded, frame_counts)
    batch_group_id = _build_batch_group_id("decode", requests)
    return [
        DecodeResult(
            request_id=request.request_id,
            cache_key=request.cache_key,
            video_frames=split_video,
            output_relpath=request.output_relpath,
            fps=request.fps,
            target_resolution=request.target_resolution,
            batch_group_id=batch_group_id,
            batch_request_count=len(requests),
            effective_batch_size=len(requests),
            fallback_count=fallback_count,
            fallback_reason=fallback_reason,
            split=request.split,
        )
        for request, split_video in zip(requests, split_videos, strict=True)
    ]


def _run_encode_chunk(
    requests: list[EncodeRequest],
    *,
    vae_runtime_backend: Any,
    fallback_count: int,
    fallback_reason: str | None,
) -> list[EncodeResult]:
    frame_counts = [int(request.video_frames.shape[0]) for request in requests]
    concat_frames = np.concatenate([request.video_frames for request in requests], axis=0)
    encoded = vae_runtime_backend.encode_video(concat_frames)
    normalized_encoded = _normalize_encoded_latent(encoded)
    split_latents = _split_by_frame_counts(normalized_encoded, frame_counts)
    batch_group_id = _build_batch_group_id("encode", requests)
    return [
        EncodeResult(
            request_id=request.request_id,
            cache_key=request.cache_key,
            latent_tensor=split_latent,
            output_relpath=request.output_relpath,
            batch_group_id=batch_group_id,
            batch_request_count=len(requests),
            effective_batch_size=len(requests),
            fallback_count=fallback_count,
            fallback_reason=fallback_reason,
            split=request.split,
        )
        for request, split_latent in zip(requests, split_latents, strict=True)
    ]


def _normalize_decoded_video(decoded_video: Any) -> np.ndarray:
    if not isinstance(decoded_video, np.ndarray):
        raise TypeError("decoded video must be a numpy ndarray")
    if decoded_video.ndim == 4 and decoded_video.shape[-1] == 3:
        return np.clip(decoded_video.astype(np.float32), 0.0, 1.0)
    if decoded_video.ndim == 4 and decoded_video.shape[1] == 3:
        return np.clip(decoded_video.astype(np.float32).transpose(0, 2, 3, 1), 0.0, 1.0)
    raise ValueError("decoded video must be shaped as [F, H, W, 3] or [F, 3, H, W]")


def _normalize_encoded_latent(encoded_latent: Any) -> np.ndarray:
    if not isinstance(encoded_latent, np.ndarray):
        raise TypeError("encoded latent must be a numpy ndarray")
    if encoded_latent.ndim != 4:
        raise ValueError("encoded latent must be a 4D tensor")
    if encoded_latent.shape[-1] == 3:
        encoded_latent = encoded_latent.transpose(0, 3, 1, 2)
    return encoded_latent.astype(np.float32)


def _split_by_frame_counts(batch_tensor: np.ndarray, frame_counts: list[int]) -> list[np.ndarray]:
    split_tensors: list[np.ndarray] = []
    frame_start = 0
    for frame_count in frame_counts:
        frame_stop = frame_start + frame_count
        split_tensors.append(batch_tensor[frame_start:frame_stop].astype(np.float32))
        frame_start = frame_stop
    if frame_start != int(batch_tensor.shape[0]):
        raise ValueError("batch split frame counts do not match the concatenated tensor")
    return split_tensors


def _build_batch_group_id(operation: str, requests: list[Any]) -> str:
    first_request = requests[0]
    return (
        f"{operation}:"
        f"{first_request.method_variant}:"
        f"{first_request.split}:"
        f"{first_request.request_id}:"
        f"{len(requests)}"
    )


def _format_cuda_oom_reason(exc: BaseException) -> str:
    message = str(exc).strip().replace("\n", " ")
    if not message:
        return "cuda_oom"
    return f"cuda_oom:{message[:160]}"


def _coerce_positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer")
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer") from exc
    if normalized < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return normalized


def _coerce_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"{field_name} must be a boolean")

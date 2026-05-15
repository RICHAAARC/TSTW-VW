"""
文件用途：计算阶段 2 真实视频帧级 CLIP 相似度指标。
File purpose: Compute CLIP-based frame similarity metrics for stage-two real video runtime.
Module type: General module
"""

from __future__ import annotations

import hashlib
import importlib
from typing import Any

import numpy as np


DEFAULT_CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
DEFAULT_CLIP_FRAME_SAMPLE_COUNT = 4
DEFAULT_CLIP_BATCH_SIZE = 8
_CLIP_BACKEND_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_CLIP_EMBEDDING_CACHE: dict[tuple[str, str, str], Any] = {}
_CLIP_EMBEDDING_CACHE_MAX_ENTRIES = 4096


def compute_clip_similarity_payload_from_frames(
    reference_frames: np.ndarray,
    comparison_frames: np.ndarray,
    *,
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """功能：从已加载帧张量计算 CLIP 相似度负载。

    Compute the governed CLIP-similarity payload from already loaded frame tensors.

    Args:
        reference_frames: Reference frames in `[F, H, W, 3]`.
        comparison_frames: Comparison frames in `[F, H, W, 3]`.
        runtime_config: Runtime configuration with optional CLIP settings.

    Returns:
        A payload containing the CLIP similarity score and auditable metadata.
    """
    runtime_config = runtime_config or {}
    quality_config = runtime_config.get("quality_metrics", {})
    clip_model_id = _resolve_clip_model_id(quality_config)
    clip_frame_sample_count = _resolve_clip_frame_sample_count(
        quality_config.get(
            "clip_frame_sample_count",
            runtime_config.get("clip_frame_sample_count", DEFAULT_CLIP_FRAME_SAMPLE_COUNT),
        )
    )
    frame_count = min(reference_frames.shape[0], comparison_frames.shape[0])
    resolved_sample_count = min(frame_count, clip_frame_sample_count)
    clip_payload = {
        "clip_similarity_score": None,
        "clip_model_id": clip_model_id,
        "clip_frame_sample_count": resolved_sample_count,
        "clip_failure_reason": None,
    }
    if resolved_sample_count < 1:
        clip_payload["clip_failure_reason"] = "clip_similarity_frame_sampling_failed"
        return clip_payload

    try:
        clip_payload["clip_similarity_score"] = round(
            _compute_clip_similarity_score(
                reference_frames[:frame_count],
                comparison_frames[:frame_count],
                runtime_config=runtime_config,
                clip_model_id=clip_model_id,
                clip_frame_sample_count=resolved_sample_count,
            ),
            6,
        )
    except ImportError as exc:
        clip_payload["clip_failure_reason"] = f"clip_backend_unavailable: {str(exc)}"
    except RuntimeError as exc:
        clip_payload["clip_failure_reason"] = f"clip_similarity_computation_error: {str(exc)}"
    except Exception as exc:
        clip_payload["clip_failure_reason"] = f"clip_similarity_runtime_error: {str(exc)}"
    return clip_payload


def _compute_clip_similarity_score(
    reference_frames: np.ndarray,
    comparison_frames: np.ndarray,
    *,
    runtime_config: dict[str, Any],
    clip_model_id: str,
    clip_frame_sample_count: int,
) -> float:
    """功能：计算均值 CLIP 相似度分数。

    Compute the mean CLIP similarity score over sampled video frames.

    Args:
        reference_frames: Reference frames in `[F, H, W, 3]`, float32, [0, 1].
        comparison_frames: Comparison frames in `[F, H, W, 3]`, float32, [0, 1].
        runtime_config: Runtime configuration with CLIP backend settings.
        clip_model_id: CLIP model identifier.
        clip_frame_sample_count: Number of frames sampled for CLIP scoring.

    Returns:
        The mean cosine similarity across sampled frame pairs.

    Raises:
        ImportError: Raised when the CLIP backend dependencies are unavailable.
        RuntimeError: Raised when CLIP inference fails.
    """
    quality_config = runtime_config.get("quality_metrics", {})
    clip_device = str(
        quality_config.get("clip_device", runtime_config.get("device", "cuda"))
        or runtime_config.get("device", "cuda")
        or "cuda"
    )
    clip_batch_size = _resolve_clip_batch_size(
        quality_config.get(
            "clip_batch_size",
            runtime_config.get("clip_batch_size", DEFAULT_CLIP_BATCH_SIZE),
        )
    )
    reference_indices = _sample_frame_indices(reference_frames.shape[0], clip_frame_sample_count)
    comparison_indices = _sample_frame_indices(comparison_frames.shape[0], clip_frame_sample_count)
    sampled_reference_frames = reference_frames[reference_indices]
    sampled_comparison_frames = comparison_frames[comparison_indices]
    torch_module, processor, model, device = _get_clip_backend(
        clip_model_id=clip_model_id,
        clip_device=clip_device,
    )

    cosine_scores: list[float] = []
    with torch_module.no_grad():
        for start_index in range(0, clip_frame_sample_count, clip_batch_size):
            stop_index = min(start_index + clip_batch_size, clip_frame_sample_count)
            reference_embeddings = _encode_clip_image_batch(
                torch_module=torch_module,
                processor=processor,
                model=model,
                device=device,
                frames=sampled_reference_frames[start_index:stop_index],
            )
            comparison_embeddings = _encode_clip_image_batch(
                torch_module=torch_module,
                processor=processor,
                model=model,
                device=device,
                frames=sampled_comparison_frames[start_index:stop_index],
            )
            cosine_scores.extend(
                _compute_cosine_similarity_batch(
                    torch_module=torch_module,
                    reference_embeddings=reference_embeddings,
                    comparison_embeddings=comparison_embeddings,
                )
            )

    if not cosine_scores:
        raise RuntimeError("CLIP cosine score list is empty")
    return float(np.mean(cosine_scores))


def _resolve_clip_model_id(quality_config: dict[str, Any]) -> str:
    clip_model_id = quality_config.get("clip_model_id", DEFAULT_CLIP_MODEL_ID)
    if not isinstance(clip_model_id, str) or not clip_model_id:
        return DEFAULT_CLIP_MODEL_ID
    return clip_model_id


def _resolve_clip_frame_sample_count(raw_value: Any) -> int:
    try:
        resolved_value = int(raw_value)
    except (TypeError, ValueError):
        resolved_value = DEFAULT_CLIP_FRAME_SAMPLE_COUNT
    if resolved_value < 1:
        return DEFAULT_CLIP_FRAME_SAMPLE_COUNT
    return resolved_value


def _resolve_clip_batch_size(raw_value: Any) -> int:
    try:
        resolved_value = int(raw_value)
    except (TypeError, ValueError):
        resolved_value = DEFAULT_CLIP_BATCH_SIZE
    if resolved_value < 1:
        return DEFAULT_CLIP_BATCH_SIZE
    return resolved_value


def _sample_frame_indices(frame_count: int, sample_count: int) -> np.ndarray:
    if frame_count < 1:
        return np.zeros((0,), dtype=np.int64)
    if sample_count >= frame_count:
        return np.arange(frame_count, dtype=np.int64)
    return np.linspace(0, frame_count - 1, num=sample_count, dtype=np.int64)


def _get_clip_backend(
    *,
    clip_model_id: str,
    clip_device: str,
) -> tuple[Any, Any, Any, Any]:
    try:
        torch_module = importlib.import_module("torch")
        transformers_module = importlib.import_module("transformers")
    except ImportError as exc:
        raise ImportError("torch and transformers packages are required for CLIP scoring") from exc

    clip_processor_class = getattr(transformers_module, "CLIPProcessor", None)
    clip_model_class = getattr(transformers_module, "CLIPModel", None)
    if clip_processor_class is None or clip_model_class is None:
        raise ImportError("transformers CLIP classes are unavailable")

    resolved_device_name = _resolve_clip_device_name(torch_module, clip_device)
    cache_key = (clip_model_id, resolved_device_name)
    cached_backend = _CLIP_BACKEND_CACHE.get(cache_key)
    if cached_backend is not None:
        return (
            torch_module,
            cached_backend["processor"],
            cached_backend["model"],
            cached_backend["device"],
        )

    processor_loader = getattr(clip_processor_class, "from_pretrained", None)
    model_loader = getattr(clip_model_class, "from_pretrained", None)
    if not callable(processor_loader) or not callable(model_loader):
        raise ImportError("CLIP from_pretrained loaders are unavailable")

    device = torch_module.device(resolved_device_name)
    try:
        processor = processor_loader(clip_model_id)
        model = model_loader(clip_model_id)
        model.to(device)
        model.eval()
    except Exception as exc:
        raise RuntimeError(f"failed to initialize CLIP backend: {str(exc)}") from exc

    _CLIP_BACKEND_CACHE[cache_key] = {
        "processor": processor,
        "model": model,
        "device": device,
    }
    return torch_module, processor, model, device


def _resolve_clip_device_name(torch_module: Any, clip_device: str) -> str:
    requested_device = str(clip_device or "cuda")
    cuda_runtime = getattr(torch_module, "cuda", None)
    cuda_available = False
    if cuda_runtime is not None:
        try:
            cuda_available = bool(cuda_runtime.is_available())
        except Exception:
            cuda_available = False
    if requested_device.startswith("cuda") and not cuda_available:
        return "cpu"
    return requested_device


def _encode_clip_image_batch(
    *,
    torch_module: Any,
    processor: Any,
    model: Any,
    device: Any,
    frames: np.ndarray,
) -> Any:
    images_array = np.rint(np.clip(frames, 0.0, 1.0) * 255.0).astype(np.uint8)
    cache_key = _build_clip_embedding_cache_key(model, device, images_array)
    cached_embedding = _CLIP_EMBEDDING_CACHE.get(cache_key)
    if cached_embedding is not None:
        to_function = getattr(cached_embedding, "to", None)
        if callable(to_function):
            return to_function(device)
        return cached_embedding

    images = [image for image in images_array]
    processor_inputs = processor(images=images, return_tensors="pt", padding=True)
    if hasattr(processor_inputs, "to"):
        processor_inputs = processor_inputs.to(device)
    elif isinstance(processor_inputs, dict):
        processor_inputs = {
            key: value.to(device) if hasattr(value, "to") else value
            for key, value in processor_inputs.items()
        }
    get_image_features = getattr(model, "get_image_features", None)
    if not callable(get_image_features):
        raise RuntimeError("CLIP model does not expose get_image_features")
    image_features = get_image_features(**processor_inputs)
    image_features = _extract_clip_embedding_tensor(image_features)
    normalized_embeddings = _normalize_embeddings(torch_module, image_features)
    _store_clip_embedding_cache(cache_key, normalized_embeddings)
    return normalized_embeddings


def _build_clip_embedding_cache_key(model: Any, device: Any, images_array: np.ndarray) -> tuple[str, str, str]:
    model_identifier = str(getattr(model, "name_or_path", model.__class__.__name__))
    device_identifier = str(device)
    contiguous_images = np.ascontiguousarray(images_array)
    digest = hashlib.sha256()
    digest.update(str(tuple(contiguous_images.shape)).encode("utf-8"))
    digest.update(contiguous_images.tobytes())
    return (model_identifier, device_identifier, digest.hexdigest())


def _store_clip_embedding_cache(cache_key: tuple[str, str, str], normalized_embeddings: Any) -> None:
    detach_function = getattr(normalized_embeddings, "detach", None)
    cached_embedding = detach_function() if callable(detach_function) else normalized_embeddings
    cpu_function = getattr(cached_embedding, "cpu", None)
    if callable(cpu_function):
        cached_embedding = cpu_function()
    _CLIP_EMBEDDING_CACHE[cache_key] = cached_embedding
    while len(_CLIP_EMBEDDING_CACHE) > _CLIP_EMBEDDING_CACHE_MAX_ENTRIES:
        oldest_key = next(iter(_CLIP_EMBEDDING_CACHE))
        _CLIP_EMBEDDING_CACHE.pop(oldest_key, None)


def _extract_clip_embedding_tensor(image_features: Any) -> Any:
    for attribute_name in ("image_embeds", "pooler_output"):
        attribute_value = getattr(image_features, attribute_name, None)
        if attribute_value is not None:
            return attribute_value
    last_hidden_state = getattr(image_features, "last_hidden_state", None)
    if last_hidden_state is not None:
        mean_function = getattr(last_hidden_state, "mean", None)
        if callable(mean_function):
            return mean_function(dim=1)
    if isinstance(image_features, (list, tuple)) and image_features:
        return image_features[0]
    if not hasattr(image_features, "norm"):
        raise RuntimeError("CLIP image feature output is not a tensor-like embedding")
    return image_features


def _normalize_embeddings(torch_module: Any, image_features: Any) -> Any:
    embedding_norms = image_features.norm(p=2, dim=-1, keepdim=True)
    clamp_function = getattr(embedding_norms, "clamp", None)
    if callable(clamp_function):
        embedding_norms = clamp_function(min=1e-12)
    else:
        embedding_norms = torch_module.clamp(embedding_norms, min=1e-12)
    return image_features / embedding_norms


def _compute_cosine_similarity_batch(
    *,
    torch_module: Any,
    reference_embeddings: Any,
    comparison_embeddings: Any,
) -> list[float]:
    cosine_tensor = (reference_embeddings * comparison_embeddings).sum(dim=-1)
    detach_function = getattr(cosine_tensor, "detach", None)
    if callable(detach_function):
        cosine_tensor = detach_function()
    cpu_function = getattr(cosine_tensor, "cpu", None)
    if callable(cpu_function):
        cosine_tensor = cpu_function()
    tolist_function = getattr(cosine_tensor, "tolist", None)
    if callable(tolist_function):
        raw_values = tolist_function()
    else:
        raw_values = list(cosine_tensor)
    if isinstance(raw_values, (int, float)):
        return [float(raw_values)]
    return [float(value) for value in raw_values]
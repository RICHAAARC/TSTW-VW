"""
文件用途：计算阶段 2 真实视频帧级质量指标。
File purpose: Compute frame-based video quality metrics for stage-two real video runtime.
Module type: General module
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from main.video.video_io import read_video_frames


_LPIPS_MODEL_CACHE: dict[tuple[str, str, str], Any] = {}


def build_real_video_quality_metrics_payload(
    reference_video_path: str | Path,
    comparison_video_path: str | Path,
    *,
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """功能：从两个真实视频文件构建帧级质量指标。

    Build frame-based quality-metrics payload from two real video files.

    Args:
        reference_video_path: Reference video path (e.g., decoded watermarked video).
        comparison_video_path: Comparison video path (e.g., attacked video).
        runtime_config: Runtime configuration with optional LPIPS model path.

    Returns:
        A quality-metrics payload with PSNR, SSIM, and optionally LPIPS.

    Raises:
        FileNotFoundError: Raised when video files are missing.
        ValueError: Raised when frame counts or shapes do not align.
    """
    runtime_config = runtime_config or {}
    quality_config = runtime_config.get("quality_metrics", {})
    enable_lpips = bool(
        quality_config.get("enable_lpips")
        or runtime_config.get("local_lpips_model_root")
        or runtime_config.get("lpips_model_root")
    )
    enable_clip_similarity = bool(quality_config.get("enable_clip_similarity"))
    lpips_backbone = str(quality_config.get("lpips_backbone", "alex") or "alex")
    lpips_device = str(quality_config.get("lpips_device", "cuda") or "cuda")
    clip_model_id = quality_config.get("clip_model_id")
    clip_frame_sample_count = quality_config.get("clip_frame_sample_count")
    disabled_quality_metrics = []
    if not enable_lpips:
        disabled_quality_metrics.append("watermarked_video_lpips")
    if not enable_clip_similarity:
        disabled_quality_metrics.append("clip_similarity")
    clip_failure_reason = (
        "clip_similarity_not_implemented"
        if enable_clip_similarity
        else "clip_similarity_disabled_by_config"
    )
    
    try:
        reference_video = read_video_frames(reference_video_path)
        comparison_video = read_video_frames(comparison_video_path)
    except (FileNotFoundError, ValueError) as exc:
        return {
            "quality_metrics_runtime": "real_video_frame_metrics",
            "vae_reconstruction_psnr": None,
            "vae_reconstruction_ssim": None,
            "watermarked_video_psnr": None,
            "watermarked_video_ssim": None,
            "watermarked_video_lpips": None,
            "lpips_backbone": lpips_backbone if enable_lpips else None,
            "lpips_device": lpips_device if enable_lpips else None,
            "clip_similarity_score": None,
            "clip_model_id": clip_model_id,
            "clip_frame_sample_count": clip_frame_sample_count,
            "disabled_quality_metrics": disabled_quality_metrics,
            "quality_failure_reason": f"video_io_error: {str(exc)}",
            "lpips_failure_reason": (
                "lpips_disabled_by_config"
                if not enable_lpips
                else "lpips_not_attempted_due_video_io_error"
            ),
            "clip_failure_reason": clip_failure_reason,
        }

    return build_real_video_quality_metrics_payload_from_frames(
        reference_video.frames,
        comparison_video.frames,
        runtime_config=runtime_config,
    )


def build_real_video_quality_metrics_payload_from_frames(
    reference_frames: np.ndarray,
    comparison_frames: np.ndarray,
    *,
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """功能：从已加载帧张量构建真实视频质量指标。

    Build real-video quality metrics from already loaded frame tensors.

    Args:
        reference_frames: Reference frames in `[F, H, W, 3]`.
        comparison_frames: Comparison frames in `[F, H, W, 3]`.
        runtime_config: Runtime configuration with optional LPIPS and CLIP flags.

    Returns:
        A quality-metrics payload with score directionality preserved.
    """
    runtime_config = runtime_config or {}
    quality_config = runtime_config.get("quality_metrics", {})
    enable_lpips = bool(
        quality_config.get("enable_lpips")
        or runtime_config.get("local_lpips_model_root")
        or runtime_config.get("lpips_model_root")
    )
    enable_clip_similarity = bool(quality_config.get("enable_clip_similarity"))
    lpips_backbone = str(quality_config.get("lpips_backbone", "alex") or "alex")
    lpips_device = str(quality_config.get("lpips_device", "cuda") or "cuda")
    clip_model_id = quality_config.get("clip_model_id")
    clip_frame_sample_count = quality_config.get("clip_frame_sample_count")
    disabled_quality_metrics = []
    if not enable_lpips:
        disabled_quality_metrics.append("watermarked_video_lpips")
    if not enable_clip_similarity:
        disabled_quality_metrics.append("clip_similarity")
    clip_failure_reason = (
        "clip_similarity_not_implemented"
        if enable_clip_similarity
        else "clip_similarity_disabled_by_config"
    )

    ref_frames = reference_frames
    cmp_frames = comparison_frames

    if ref_frames.ndim != 4 or cmp_frames.ndim != 4:
        return {
            "quality_metrics_runtime": "real_video_frame_metrics",
            "vae_reconstruction_psnr": None,
            "vae_reconstruction_ssim": None,
            "watermarked_video_psnr": None,
            "watermarked_video_ssim": None,
            "watermarked_video_lpips": None,
            "lpips_backbone": lpips_backbone if enable_lpips else None,
            "lpips_device": lpips_device if enable_lpips else None,
            "clip_similarity_score": None,
            "clip_model_id": clip_model_id,
            "clip_frame_sample_count": clip_frame_sample_count,
            "disabled_quality_metrics": disabled_quality_metrics,
            "quality_failure_reason": "invalid_frame_tensor_shape",
            "lpips_failure_reason": (
                "lpips_disabled_by_config"
                if not enable_lpips
                else "lpips_not_attempted_due_invalid_frame_tensor_shape"
            ),
            "clip_failure_reason": clip_failure_reason,
        }

    # 对齐帧数
    frame_count = min(ref_frames.shape[0], cmp_frames.shape[0])
    if frame_count < 1:
        return {
            "quality_metrics_runtime": "real_video_frame_metrics",
            "vae_reconstruction_psnr": None,
            "vae_reconstruction_ssim": None,
            "watermarked_video_psnr": None,
            "watermarked_video_ssim": None,
            "watermarked_video_lpips": None,
            "lpips_backbone": lpips_backbone if enable_lpips else None,
            "lpips_device": lpips_device if enable_lpips else None,
            "clip_similarity_score": None,
            "clip_model_id": clip_model_id,
            "clip_frame_sample_count": clip_frame_sample_count,
            "disabled_quality_metrics": disabled_quality_metrics,
            "quality_failure_reason": "frame_count_alignment_failed",
            "lpips_failure_reason": (
                "lpips_disabled_by_config"
                if not enable_lpips
                else "lpips_not_attempted_due_frame_count_alignment_failed"
            ),
            "clip_failure_reason": clip_failure_reason,
        }

    # 按帧计算 PSNR 与 SSIM
    psnr_scores: list[float] = []
    ssim_scores: list[float] = []

    for frame_idx in range(frame_count):
        ref_frame = np.clip(ref_frames[frame_idx], 0.0, 1.0)
        cmp_frame = np.clip(cmp_frames[frame_idx], 0.0, 1.0)

        try:
            frame_psnr = peak_signal_noise_ratio(ref_frame, cmp_frame, data_range=1.0)
            psnr_scores.append(float(frame_psnr))
        except Exception:
            psnr_scores.append(0.0)

        try:
            frame_ssim = structural_similarity(
                ref_frame, cmp_frame, data_range=1.0, channel_axis=-1
            )
            ssim_scores.append(float(frame_ssim))
        except Exception:
            ssim_scores.append(0.0)

    if not psnr_scores:
        return {
            "quality_metrics_runtime": "real_video_frame_metrics",
            "vae_reconstruction_psnr": None,
            "vae_reconstruction_ssim": None,
            "watermarked_video_psnr": None,
            "watermarked_video_ssim": None,
            "watermarked_video_lpips": None,
            "lpips_backbone": lpips_backbone if enable_lpips else None,
            "lpips_device": lpips_device if enable_lpips else None,
            "clip_similarity_score": None,
            "clip_model_id": clip_model_id,
            "clip_frame_sample_count": clip_frame_sample_count,
            "disabled_quality_metrics": disabled_quality_metrics,
            "quality_failure_reason": "metric_computation_failed",
            "lpips_failure_reason": (
                "lpips_disabled_by_config"
                if not enable_lpips
                else "lpips_not_attempted_due_metric_computation_failed"
            ),
            "clip_failure_reason": clip_failure_reason,
        }

    mean_psnr = float(np.mean(psnr_scores))
    mean_ssim = float(np.mean(ssim_scores))

    # 计算 LPIPS（如果配置可用）
    lpips_score: float | None = None
    lpips_failure_reason: str | None = None

    lpips_model_root = runtime_config.get("local_lpips_model_root") or runtime_config.get(
        "lpips_model_root"
    )
    lpips_batch_size = int(quality_config.get("lpips_batch_size", 8) or 8)
    if not enable_lpips:
        lpips_failure_reason = "lpips_disabled_by_config"
    elif lpips_model_root:
        try:
            lpips_score = _compute_lpips_score(
                ref_frames[:frame_count],
                cmp_frames[:frame_count],
                lpips_model_root,
                lpips_backbone=lpips_backbone,
                lpips_device=lpips_device,
                lpips_batch_size=lpips_batch_size,
            )
        except Exception as exc:
            lpips_failure_reason = f"lpips_computation_error: {str(exc)}"
    else:
        lpips_failure_reason = "lpips_model_not_configured"

    quality_failure_reason = None
    if mean_psnr < 15.0:
        quality_failure_reason = "psnr_below_threshold"

    return {
        "quality_metrics_runtime": "real_video_frame_metrics",
        "vae_reconstruction_psnr": round(mean_psnr, 6),
        "vae_reconstruction_ssim": round(mean_ssim, 6),
        "watermarked_video_psnr": round(mean_psnr, 6),
        "watermarked_video_ssim": round(mean_ssim, 6),
        "watermarked_video_lpips": round(lpips_score, 6) if lpips_score is not None else None,
        "lpips_backbone": lpips_backbone if enable_lpips else None,
        "lpips_device": lpips_device if enable_lpips else None,
        "clip_similarity_score": None,
        "clip_model_id": clip_model_id,
        "clip_frame_sample_count": clip_frame_sample_count,
        "disabled_quality_metrics": disabled_quality_metrics,
        "quality_failure_reason": quality_failure_reason,
        "lpips_failure_reason": lpips_failure_reason,
        "clip_failure_reason": clip_failure_reason,
    }


def _compute_lpips_score(
    reference_frames: np.ndarray,
    comparison_frames: np.ndarray,
    lpips_model_root: str | Path,
    *,
    lpips_backbone: str = "alex",
    lpips_device: str = "cuda",
    lpips_batch_size: int = 8,
) -> float:
    """功能：计算平均 LPIPS 距离。

    Compute average LPIPS distance across frames.

    Args:
        reference_frames: Reference frames in `[F, H, W, 3]`, float32, [0, 1].
        comparison_frames: Comparison frames in `[F, H, W, 3]`, float32, [0, 1].
        lpips_model_root: Path to local LPIPS model directory or weights cache directory.
        lpips_backbone: LPIPS backbone identifier.
        lpips_device: Requested torch device.
        lpips_batch_size: Number of frames evaluated per LPIPS call.

    Returns:
        Average LPIPS score across all frames.

    Raises:
        ImportError: Raised when lpips module is unavailable.
        RuntimeError: Raised when LPIPS computation fails.
    """
    try:
        import lpips
        import torch
    except ImportError as exc:
        raise ImportError("lpips and torch packages required for LPIPS computation") from exc

    lpips_model_root = Path(lpips_model_root)
    lpips_model_root.mkdir(parents=True, exist_ok=True)

    torch_hub = getattr(torch, "hub", None)
    torch_hub_set_dir = getattr(torch_hub, "set_dir", None) if torch_hub is not None else None
    if callable(torch_hub_set_dir):
        try:
            torch_hub_set_dir(str(lpips_model_root))
        except Exception:
            # 中文注释：hub 目录设置失败不应阻断 LPIPS 初始化，保留后续真实错误路径。
            pass
    os.environ["TORCH_HOME"] = str(lpips_model_root)

    resolved_device_name = _resolve_lpips_device_name(torch, lpips_device)
    device = torch.device(resolved_device_name)
    loss_fn = _get_cached_lpips_model(
        lpips_module=lpips,
        torch_module=torch,
        lpips_model_root=lpips_model_root,
        lpips_backbone=lpips_backbone,
        resolved_device_name=resolved_device_name,
        device=device,
    )

    # 保证帧数对齐
    frame_count = min(reference_frames.shape[0], comparison_frames.shape[0])
    if frame_count < 1:
        raise RuntimeError("No frames available for LPIPS computation")
    
    if not isinstance(lpips_batch_size, int) or lpips_batch_size < 1:
        raise RuntimeError("lpips_batch_size must be a positive integer")

    lpips_scores: list[float] = []

    with torch.no_grad():
        for start_index in range(0, frame_count, lpips_batch_size):
            stop_index = min(start_index + lpips_batch_size, frame_count)
            ref_batch = np.clip(reference_frames[start_index:stop_index], 0.0, 1.0)
            cmp_batch = np.clip(comparison_frames[start_index:stop_index], 0.0, 1.0)

            ref_tensor = torch.from_numpy(ref_batch).permute(0, 3, 1, 2).float()
            cmp_tensor = torch.from_numpy(cmp_batch).permute(0, 3, 1, 2).float()

            ref_tensor = (ref_tensor * 2.0 - 1.0).to(device)
            cmp_tensor = (cmp_tensor * 2.0 - 1.0).to(device)

            try:
                lpips_distance = loss_fn(ref_tensor, cmp_tensor)
                if hasattr(lpips_distance, "mean"):
                    lpips_distance = lpips_distance.mean()
                lpips_scores.append(float(lpips_distance.item()))
            except Exception as exc:
                raise RuntimeError(
                    f"LPIPS computation failed for frame batch {start_index}:{stop_index}: {str(exc)}"
                ) from exc

    if not lpips_scores:
        raise RuntimeError("LPIPS score list is empty after processing all frames")

    return float(np.mean(lpips_scores))


def _resolve_lpips_device_name(torch_module: Any, lpips_device: str) -> str:
    requested_device = str(lpips_device or "cuda")
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


def _get_cached_lpips_model(
    *,
    lpips_module: Any,
    torch_module: Any,
    lpips_model_root: Path,
    lpips_backbone: str,
    resolved_device_name: str,
    device: Any,
) -> Any:
    cache_key = (str(lpips_model_root), str(lpips_backbone), str(resolved_device_name))
    cached_model = _LPIPS_MODEL_CACHE.get(cache_key)
    if cached_model is not None:
        return cached_model
    try:
        loss_fn = lpips_module.LPIPS(net=lpips_backbone, verbose=False)
        loss_fn.to(device)
        loss_fn.eval()
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize LPIPS network: {str(exc)}") from exc
    _LPIPS_MODEL_CACHE[cache_key] = loss_fn
    return loss_fn

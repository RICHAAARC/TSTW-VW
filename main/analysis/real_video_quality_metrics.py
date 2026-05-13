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
            "clip_similarity_score": None,
            "disabled_quality_metrics": disabled_quality_metrics,
            "quality_failure_reason": f"video_io_error: {str(exc)}",
            "lpips_failure_reason": (
                "lpips_disabled_by_config"
                if not enable_lpips
                else "lpips_not_attempted_due_video_io_error"
            ),
            "clip_failure_reason": clip_failure_reason,
        }

    ref_frames = reference_video.frames
    cmp_frames = comparison_video.frames

    if ref_frames.ndim != 4 or cmp_frames.ndim != 4:
        return {
            "quality_metrics_runtime": "real_video_frame_metrics",
            "vae_reconstruction_psnr": None,
            "vae_reconstruction_ssim": None,
            "watermarked_video_psnr": None,
            "watermarked_video_ssim": None,
            "watermarked_video_lpips": None,
            "clip_similarity_score": None,
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
            "clip_similarity_score": None,
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
            "clip_similarity_score": None,
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
    if not enable_lpips:
        lpips_failure_reason = "lpips_disabled_by_config"
    elif lpips_model_root:
        try:
            lpips_score = _compute_lpips_score(
                ref_frames[:frame_count], cmp_frames[:frame_count], lpips_model_root
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
        "clip_similarity_score": None,
        "disabled_quality_metrics": disabled_quality_metrics,
        "quality_failure_reason": quality_failure_reason,
        "lpips_failure_reason": lpips_failure_reason,
        "clip_failure_reason": clip_failure_reason,
    }


def _compute_lpips_score(
    reference_frames: np.ndarray,
    comparison_frames: np.ndarray,
    lpips_model_root: str | Path,
) -> float:
    """功能：计算平均 LPIPS 距离。

    Compute average LPIPS distance across frames.

    Args:
        reference_frames: Reference frames in `[F, H, W, 3]`, float32, [0, 1].
        comparison_frames: Comparison frames in `[F, H, W, 3]`, float32, [0, 1].
        lpips_model_root: Path to local LPIPS model directory or weights cache directory.

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

    # 初始化 LPIPS 网络
    # 注意：LPIPS 会尝试从缓存或 lpips_model_root 目录加载预训练权重
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    try:
        # 初始化 LPIPS 网络；torch.hub会尝试使用 lpips_model_root 作为 hub_dir
        loss_fn = lpips.LPIPS(net="alex", verbose=False)
        loss_fn.to(device)
        loss_fn.eval()
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize LPIPS network: {str(exc)}") from exc

    # 保证帧数对齐
    frame_count = min(reference_frames.shape[0], comparison_frames.shape[0])
    if frame_count < 1:
        raise RuntimeError("No frames available for LPIPS computation")
    
    lpips_scores: list[float] = []

    with torch.no_grad():
        for frame_idx in range(frame_count):
            # 转换帧格式：[H, W, 3] RGB [0, 1] -> [1, 3, H, W] RGB [-1, 1]
            ref_frame = np.clip(reference_frames[frame_idx], 0.0, 1.0)
            cmp_frame = np.clip(comparison_frames[frame_idx], 0.0, 1.0)

            ref_tensor = torch.from_numpy(ref_frame).permute(2, 0, 1).unsqueeze(0).float()
            cmp_tensor = torch.from_numpy(cmp_frame).permute(2, 0, 1).unsqueeze(0).float()

            ref_tensor = (ref_tensor * 2.0 - 1.0).to(device)
            cmp_tensor = (cmp_tensor * 2.0 - 1.0).to(device)

            try:
                lpips_distance = loss_fn(ref_tensor, cmp_tensor).item()
                lpips_scores.append(float(lpips_distance))
            except Exception as exc:
                raise RuntimeError(f"LPIPS computation failed at frame {frame_idx}: {str(exc)}") from exc

    if not lpips_scores:
        raise RuntimeError("LPIPS score list is empty after processing all frames")

    return float(np.mean(lpips_scores))

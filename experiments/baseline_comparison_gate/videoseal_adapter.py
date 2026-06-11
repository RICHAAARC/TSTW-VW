"""external_videoseal 的 Colab 真实 smoke adapter。

该模块只服务 `baseline_comparison_gate` 的外部 baseline 复现验证。它不会进入
`main/` 核心方法层, 也不会改变项目自身的 `tubelet_sync` 方法语义。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Iterator

from experiments.baseline_comparison_gate.baseline_adapter import (
    BaselineDetectionResult,
    BaselineEmbedResult,
    BaselineEvaluationResult,
    BaselineRuntimeContext,
)
from main.core.digest import compute_file_digest, compute_object_digest


ADAPTER_VERSION = "external_videoseal_real_smoke_adapter"
SCORE_MAPPING_RULE = "bit_accuracy_from_mean_frame_logits_excluding_detection_bit"


@dataclass(frozen=True)
class VideoSealModelHandle:
    """保存已加载的 VideoSeal 模型及其可审计来源。"""

    model: Any
    device: str
    model_digest: str
    checkpoint_path: Path


@contextmanager
def temporary_working_directory(path: Path) -> Iterator[None]:
    """临时切换工作目录。

    VideoSeal 上游代码会把自动下载的权重写入当前工作目录下的 `ckpts/`。
    因此这里显式切换到本次 baseline work_dir, 使权重缓存可以被结果包追踪,
    也避免污染仓库根目录。
    """
    previous = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class ExternalVideoSealAdapter:
    """对 VideoSeal 上游模型进行最小真实 smoke 封装。

    该 adapter 的目标是验证上游模型在 Colab 中可以真实完成视频嵌入和检测,
    并把输出映射为项目统一的 baseline record。它不是正式全量评估 runner。
    """

    baseline_name = "external_videoseal"

    def __init__(
        self,
        *,
        upstream_root: str | Path,
        compile_model: bool = False,
        chunk_size: int = 16,
    ) -> None:
        self.upstream_root = Path(upstream_root)
        self.compile_model = compile_model
        self.chunk_size = int(chunk_size)
        self.context: BaselineRuntimeContext | None = None
        self.handle: VideoSealModelHandle | None = None
        self.payload_bits: list[int] | None = None

    def prepare(self, context: BaselineRuntimeContext) -> dict[str, Any]:
        """加载 VideoSeal 模型并计算权重 digest。"""
        self.context = context
        if not self.upstream_root.exists():
            raise FileNotFoundError(f"VideoSeal upstream root not found: {self.upstream_root}")

        config_repair = ensure_videoseal_package_config_paths(self.upstream_root)
        if str(self.upstream_root) not in sys.path:
            sys.path.insert(0, str(self.upstream_root))

        with temporary_working_directory(context.work_dir):
            started_at = time.perf_counter()
            import torch
            import videoseal

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = videoseal.load("videoseal")
            model.eval()
            model.to(device)
            if self.compile_model and hasattr(model, "compile"):
                model.compile()
            checkpoint_path = resolve_single_videoseal_checkpoint(context.work_dir)
            model_digest = compute_file_digest(checkpoint_path)
            self.handle = VideoSealModelHandle(
                model=model,
                device=device,
                model_digest=model_digest,
                checkpoint_path=checkpoint_path,
            )
            prepare_seconds = time.perf_counter() - started_at

        return {
            "baseline_name": self.baseline_name,
            "adapter_status": "real_smoke_adapter_loaded",
            "adapter_version": ADAPTER_VERSION,
            "device": self.handle.device,
            "model_digest": self.handle.model_digest,
            "checkpoint_path": self.handle.checkpoint_path.as_posix(),
            "config_path_repair": config_repair,
            "prepare_seconds": prepare_seconds,
        }

    def embed(
        self,
        input_video_path: Path,
        payload_bits: list[int],
        output_video_path: Path,
        metadata: dict[str, Any],
    ) -> BaselineEmbedResult:
        """把固定 payload 嵌入输入视频。"""
        handle = self._require_handle()
        started_at = time.perf_counter()
        output_video_path.parent.mkdir(parents=True, exist_ok=True)

        import torch

        frames, fps = read_video_with_ffmpeg(input_video_path)
        video_tensor = frames_to_tensor(frames)
        model_payload = normalize_payload_bits(
            payload_bits=payload_bits,
            expected_length=get_model_message_length(handle.model),
        )
        payload_tensor = torch.tensor([model_payload], dtype=torch.float32, device=handle.device)

        with torch.no_grad():
            outputs = handle.model.embed(
                video_tensor,
                msgs=payload_tensor,
                is_video=True,
                lowres_attenuation=True,
            )
        watermarked_frames = tensor_to_frames(outputs["imgs_w"])
        write_video_with_ffmpeg(watermarked_frames, output_video_path, fps=fps)
        self.payload_bits = model_payload
        embed_seconds = time.perf_counter() - started_at

        return BaselineEmbedResult(
            baseline_name=self.baseline_name,
            output_video_path=output_video_path,
            embed_success=True,
            runtime_metrics={"embed_seconds": embed_seconds, "frame_count": int(frames.shape[0])},
            baseline_trace={
                "adapter_version": ADAPTER_VERSION,
                "model_digest": handle.model_digest,
                "checkpoint_path": handle.checkpoint_path.as_posix(),
                "payload_digest": compute_object_digest(model_payload),
            },
        )

    def detect(
        self,
        input_video_path: Path,
        metadata: dict[str, Any],
    ) -> BaselineDetectionResult:
        """检测视频中的 VideoSeal 消息并映射为统一 score。"""
        handle = self._require_handle()
        payload_bits = metadata.get("payload_bits") or self.payload_bits
        if payload_bits is None:
            raise ValueError("payload_bits is required for VideoSeal real smoke detection")

        started_at = time.perf_counter()
        import torch

        frames, fps = read_video_with_ffmpeg(input_video_path)
        video_tensor = frames_to_tensor(frames)
        with torch.no_grad():
            outputs = handle.model.detect(video_tensor, is_video=True)
        logits = outputs["preds"][:, 1:]
        mean_logits = logits.mean(dim=0)
        predicted_bits = (mean_logits > 0).int().detach().cpu().tolist()
        expected_bits = [int(bit) for bit in payload_bits]
        compared_length = min(len(predicted_bits), len(expected_bits))
        if compared_length == 0:
            raise ValueError("VideoSeal detection returned no comparable bits")
        correct = sum(
            int(predicted_bits[index] == expected_bits[index])
            for index in range(compared_length)
        )
        bit_accuracy = correct / compared_length
        detect_seconds = time.perf_counter() - started_at

        return BaselineDetectionResult(
            baseline_name=self.baseline_name,
            baseline_score=float(bit_accuracy),
            baseline_raw_detector_output={
                "bit_accuracy": float(bit_accuracy),
                "ber": float(1.0 - bit_accuracy),
                "predicted_bits_prefix": predicted_bits[:32],
                "payload_bits_prefix": expected_bits[:32],
                "compared_length_bits": compared_length,
                "fps": float(fps),
                "frame_count": int(frames.shape[0]),
            },
            runtime_metrics={"detect_seconds": detect_seconds},
            baseline_trace={
                "adapter_version": ADAPTER_VERSION,
                "model_digest": handle.model_digest,
                "score_mapping_rule": SCORE_MAPPING_RULE,
            },
        )

    def evaluate(
        self,
        detection_output: BaselineDetectionResult,
        payload_bits: list[int],
        threshold: float,
        target_fpr: float,
    ) -> BaselineEvaluationResult:
        """根据 smoke 阈值形成显式判定。

        该阈值只用于真实可运行性 smoke, 不能替代后续 calibration split 上的
        fixed-FPR 正式阈值。
        """
        if detection_output.baseline_score is None:
            return BaselineEvaluationResult(
                baseline_name=self.baseline_name,
                threshold=threshold,
                target_fpr=target_fpr,
                decision="failed",
                failure_reason=detection_output.failure_reason or "videoseal_detection_failed",
            )
        bit_accuracy = float(detection_output.baseline_score)
        return BaselineEvaluationResult(
            baseline_name=self.baseline_name,
            threshold=threshold,
            target_fpr=target_fpr,
            decision="positive" if bit_accuracy >= threshold else "negative",
            bit_accuracy=bit_accuracy,
            ber=1.0 - bit_accuracy,
            failure_reason=None if bit_accuracy >= threshold else "videoseal_smoke_below_threshold",
        )

    def _require_handle(self) -> VideoSealModelHandle:
        if self.handle is None:
            raise RuntimeError("ExternalVideoSealAdapter.prepare must be called first")
        return self.handle


def resolve_single_videoseal_checkpoint(work_dir: Path) -> Path:
    """定位 VideoSeal 自动下载的权重文件。"""
    candidates = sorted((work_dir / "ckpts").glob("*.pth"))
    if not candidates:
        raise FileNotFoundError(f"no VideoSeal checkpoint found under {work_dir / 'ckpts'}")
    if len(candidates) > 1:
        preferred = [path for path in candidates if path.name == "videoseal_y_256b_img.pth"]
        if preferred:
            return preferred[0]
    return candidates[0]


def ensure_videoseal_package_config_paths(upstream_root: Path) -> dict[str, Any]:
    """修复 VideoSeal 上游包内配置查找路径。

    当前固定的 VideoSeal 上游 commit 中, `videoseal.utils.cfg.resolve_config_path`
    会把 `configs/attenuation.yaml` 解析到 `videoseal/configs/attenuation.yaml`。
    但仓库实际配置目录位于上游根目录 `configs/`。这里把根目录配置复制到
    包内 `videoseal/configs/`, 属于复现路径修复, 不修改模型结构、权重或检测
    分数定义。
    """
    source_config_dir = upstream_root / "configs"
    package_config_dir = upstream_root / "videoseal" / "configs"
    required_files = ("attenuation.yaml", "embedder.yaml", "extractor.yaml")
    if not source_config_dir.exists():
        raise FileNotFoundError(f"VideoSeal source config dir not found: {source_config_dir}")

    copied_files: list[str] = []
    package_config_dir.mkdir(parents=True, exist_ok=True)
    for filename in required_files:
        source_path = source_config_dir / filename
        destination_path = package_config_dir / filename
        if not source_path.exists():
            raise FileNotFoundError(f"VideoSeal required config missing: {source_path}")
        if not destination_path.exists():
            shutil.copy2(source_path, destination_path)
            copied_files.append(filename)
    return {
        "repair_name": "copy_root_configs_into_videoseal_package_configs",
        "source_config_dir": source_config_dir.as_posix(),
        "package_config_dir": package_config_dir.as_posix(),
        "copied_files": copied_files,
        "required_files": list(required_files),
    }


def get_model_message_length(model: Any) -> int:
    """读取模型消息位数, 失败时使用 VideoSeal v1.0 的 256-bit 默认值。"""
    for owner in (model, getattr(model, "embedder", None)):
        if owner is None:
            continue
        nbits = getattr(owner, "nbits", None)
        if isinstance(nbits, int) and nbits > 0:
            return nbits
    return 256


def normalize_payload_bits(payload_bits: list[int], expected_length: int) -> list[int]:
    """把项目 payload 扩展或截断到 VideoSeal 模型所需长度。"""
    if not payload_bits:
        payload_bits = [0, 1]
    normalized = [int(bit) & 1 for bit in payload_bits]
    while len(normalized) < expected_length:
        normalized.extend(normalized)
    return normalized[:expected_length]


def read_video_with_ffmpeg(input_video_path: Path) -> tuple[Any, float]:
    """使用上游依赖 `ffmpeg-python` 读取视频为 RGB 帧数组。"""
    import ffmpeg
    import numpy as np

    probe = ffmpeg.probe(str(input_video_path))
    video_info = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    width = int(video_info["width"])
    height = int(video_info["height"])
    fps_parts = str(video_info.get("r_frame_rate", "8/1")).split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1])
    raw_video = (
        ffmpeg.input(str(input_video_path))
        .output("pipe:", format="rawvideo", pix_fmt="rgb24")
        .run(capture_stdout=True, capture_stderr=True)[0]
    )
    frames = np.frombuffer(raw_video, np.uint8).reshape([-1, height, width, 3])
    return frames, fps


def write_video_with_ffmpeg(frames: Any, output_video_path: Path, *, fps: float) -> None:
    """使用 `ffmpeg-python` 写出 RGB 帧数组为 mp4。"""
    import ffmpeg

    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    height, width = int(frames.shape[1]), int(frames.shape[2])
    process = (
        ffmpeg.input(
            "pipe:",
            format="rawvideo",
            pix_fmt="rgb24",
            s=f"{width}x{height}",
            r=fps,
        )
        .output(str(output_video_path), vcodec="libx264", pix_fmt="yuv420p", crf=23, r=fps)
        .overwrite_output()
        .run_async(pipe_stdin=True, pipe_stderr=True)
    )
    _, stderr = process.communicate(input=frames.tobytes())
    if process.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="replace"))


def frames_to_tensor(frames: Any) -> Any:
    """把 uint8 RGB 帧数组转换为 VideoSeal 需要的 FCHW float tensor。"""
    import torch

    return torch.tensor(frames, dtype=torch.float32).permute(0, 3, 1, 2) / 255.0


def tensor_to_frames(tensor: Any) -> Any:
    """把 VideoSeal 输出 tensor 转回 uint8 RGB 帧数组。"""
    return (
        (tensor.detach().cpu().clamp(0, 1) * 255.0)
        .byte()
        .permute(0, 2, 3, 1)
        .numpy()
    )

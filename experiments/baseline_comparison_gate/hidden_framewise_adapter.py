"""external_hidden_framewise 的 Colab 真实 smoke adapter。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

from experiments.baseline_comparison_gate.baseline_adapter import (
    BaselineDetectionResult,
    BaselineEmbedResult,
    BaselineEvaluationResult,
    BaselineRuntimeContext,
)
from main.core.digest import compute_file_digest


ADAPTER_VERSION = "external_hidden_framewise_real_smoke_adapter"
SCORE_MAPPING_RULE = "mean_frame_bit_accuracy_from_framewise_decoder_logits"
DEFAULT_EXPERIMENT_NAME = "combined-noise"


@dataclass(frozen=True)
class HiddenFramewiseModelHandle:
    """保存已加载的 HiDDeN framewise 模型和权重来源。"""

    model: Any
    device: str
    model_digest: str
    checkpoint_path: Path
    options_path: Path
    height: int
    width: int
    message_length: int


class ExternalHiddenFramewiseAdapter:
    """把图像 HiDDeN 模型逐帧迁移为视频 baseline smoke。"""

    baseline_name = "external_hidden_framewise"

    def __init__(
        self,
        *,
        upstream_root: str | Path,
        experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    ) -> None:
        self.upstream_root = Path(upstream_root)
        self.experiment_name = experiment_name
        self.context: BaselineRuntimeContext | None = None
        self.handle: HiddenFramewiseModelHandle | None = None
        self.payload_bits: list[int] | None = None

    def prepare(self, context: BaselineRuntimeContext) -> dict[str, Any]:
        """加载 HiDDeN checkpoint 和配置。"""
        self.context = context
        if not self.upstream_root.exists():
            raise FileNotFoundError(f"HiDDeN upstream root not found: {self.upstream_root}")
        if str(self.upstream_root) not in sys.path:
            sys.path.insert(0, str(self.upstream_root))

        started_at = time.perf_counter()
        import torch
        import utils
        from model.hidden import Hidden
        from noise_layers.noiser import Noiser

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        experiment_root = self.upstream_root / "experiments" / self.experiment_name
        options_path = experiment_root / "options-and-config.pickle"
        checkpoint_path = resolve_hidden_checkpoint(experiment_root)
        _, hidden_config, _ = utils.load_options(str(options_path))
        hidden_net = Hidden(hidden_config, device, Noiser([], device), None)
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        hidden_net.encoder_decoder.load_state_dict(checkpoint["enc-dec-model"])
        hidden_net.encoder_decoder.eval()
        self.handle = HiddenFramewiseModelHandle(
            model=hidden_net,
            device=str(device),
            model_digest=compute_file_digest(checkpoint_path),
            checkpoint_path=checkpoint_path,
            options_path=options_path,
            height=int(hidden_config.H),
            width=int(hidden_config.W),
            message_length=int(hidden_config.message_length),
        )
        prepare_seconds = time.perf_counter() - started_at
        return {
            "baseline_name": self.baseline_name,
            "adapter_status": "real_smoke_adapter_loaded",
            "adapter_version": ADAPTER_VERSION,
            "device": self.handle.device,
            "model_digest": self.handle.model_digest,
            "checkpoint_path": self.handle.checkpoint_path.as_posix(),
            "options_path": self.handle.options_path.as_posix(),
            "experiment_name": self.experiment_name,
            "prepare_seconds": prepare_seconds,
        }

    def embed(
        self,
        input_video_path: Path,
        payload_bits: list[int],
        output_video_path: Path,
        metadata: dict[str, Any],
    ) -> BaselineEmbedResult:
        """对每一帧独立嵌入同一个 HiDDeN payload。"""
        handle = self._require_handle()
        started_at = time.perf_counter()
        frames, fps = read_video_frames(input_video_path, resize_to=(handle.width, handle.height))
        model_payload = normalize_payload_bits(payload_bits, handle.message_length)

        import numpy as np
        import torch

        encoded_frames = []
        message = torch.tensor([model_payload], dtype=torch.float32, device=handle.model.device)
        with torch.no_grad():
            for frame in frames:
                image_tensor = frame_to_tensor(frame, handle.model.device)
                encoded = handle.model.encoder_decoder.encoder(image_tensor, message)
                encoded_frames.append(tensor_to_frame(encoded))
        output_frames = np.stack(encoded_frames, axis=0)
        write_video_frames(output_frames, output_video_path, fps=fps)
        self.payload_bits = model_payload
        embed_seconds = time.perf_counter() - started_at
        return BaselineEmbedResult(
            baseline_name=self.baseline_name,
            output_video_path=output_video_path,
            embed_success=True,
            runtime_metrics={"embed_seconds": embed_seconds, "frame_count": int(len(frames))},
            baseline_trace={
                "adapter_version": ADAPTER_VERSION,
                "model_digest": handle.model_digest,
                "checkpoint_path": handle.checkpoint_path.as_posix(),
            },
        )

    def detect(self, input_video_path: Path, metadata: dict[str, Any]) -> BaselineDetectionResult:
        """逐帧解码 HiDDeN payload 并计算平均 bit accuracy。"""
        handle = self._require_handle()
        payload_bits = metadata.get("payload_bits") or self.payload_bits
        if payload_bits is None:
            raise ValueError("payload_bits is required for HiDDeN framewise real smoke detection")

        started_at = time.perf_counter()
        import numpy as np
        import torch

        frames, fps = read_video_frames(input_video_path, resize_to=(handle.width, handle.height))
        expected = np.array([int(bit) for bit in payload_bits], dtype=np.int64)
        frame_scores: list[float] = []
        predicted_prefix: list[int] | None = None
        with torch.no_grad():
            for frame in frames:
                image_tensor = frame_to_tensor(frame, handle.model.device)
                logits = handle.model.encoder_decoder.decoder(image_tensor)[0].detach().cpu().numpy()
                predicted = np.round(logits).clip(0, 1).astype(np.int64)
                compared_length = min(len(predicted), len(expected))
                if compared_length == 0:
                    continue
                frame_scores.append(float((predicted[:compared_length] == expected[:compared_length]).mean()))
                if predicted_prefix is None:
                    predicted_prefix = predicted[:32].astype(int).tolist()
        if not frame_scores:
            raise ValueError("HiDDeN framewise detection returned no decodable frames")
        bit_accuracy = float(np.mean(frame_scores))
        detect_seconds = time.perf_counter() - started_at
        return BaselineDetectionResult(
            baseline_name=self.baseline_name,
            baseline_score=bit_accuracy,
            baseline_raw_detector_output={
                "bit_accuracy": bit_accuracy,
                "ber": 1.0 - bit_accuracy,
                "frame_score_mean": bit_accuracy,
                "frame_score_min": float(np.min(frame_scores)),
                "frame_score_max": float(np.max(frame_scores)),
                "decoded_frame_count": len(frame_scores),
                "fps": float(fps),
                "payload_bits_prefix": expected[:32].astype(int).tolist(),
                "predicted_bits_prefix": predicted_prefix or [],
                "compared_length_bits": int(len(expected)),
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
        """根据 smoke 阈值形成可运行性判定。"""
        if detection_output.baseline_score is None:
            return BaselineEvaluationResult(
                baseline_name=self.baseline_name,
                threshold=threshold,
                target_fpr=target_fpr,
                decision="failed",
                failure_reason=detection_output.failure_reason or "hidden_framewise_detection_failed",
            )
        bit_accuracy = float(detection_output.baseline_score)
        return BaselineEvaluationResult(
            baseline_name=self.baseline_name,
            threshold=threshold,
            target_fpr=target_fpr,
            decision="positive" if bit_accuracy >= threshold else "negative",
            bit_accuracy=bit_accuracy,
            ber=1.0 - bit_accuracy,
            failure_reason=None if bit_accuracy >= threshold else "hidden_framewise_smoke_below_threshold",
        )

    def _require_handle(self) -> HiddenFramewiseModelHandle:
        if self.handle is None:
            raise RuntimeError("ExternalHiddenFramewiseAdapter.prepare must be called first")
        return self.handle


def resolve_hidden_checkpoint(experiment_root: Path) -> Path:
    """选择 HiDDeN 实验目录中的最后一个 checkpoint。"""
    checkpoint_dir = experiment_root / "checkpoints"
    candidates = sorted(checkpoint_dir.glob("*.pyt"))
    if not candidates:
        raise FileNotFoundError(f"no HiDDeN checkpoint found under {checkpoint_dir}")
    return candidates[-1]


def normalize_payload_bits(payload_bits: list[int], expected_length: int) -> list[int]:
    """把项目 payload 扩展或截断到 HiDDeN 消息长度。"""
    if not payload_bits:
        payload_bits = [0, 1]
    normalized = [int(bit) & 1 for bit in payload_bits]
    while len(normalized) < expected_length:
        normalized.extend(normalized)
    return normalized[:expected_length]


def create_hidden_probe_video(output_path: Path, *, duration_seconds: int = 2, fps: int = 8, size: int = 128) -> None:
    """创建 HiDDeN framewise smoke 使用的输入视频。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_binary = shutil.which("ffmpeg")
    if not ffmpeg_binary:
        try:
            import imageio_ffmpeg
        except ImportError as exc:
            raise RuntimeError("ffmpeg not found; install ffmpeg or imageio_ffmpeg") from exc
        ffmpeg_binary = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_binary,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration_seconds}:size={size}x{size}:rate={fps}",
        "-vcodec",
        "mpeg4",
        str(output_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)


def read_video_frames(input_video_path: Path, *, resize_to: tuple[int, int]) -> tuple[Any, float]:
    """使用 OpenCV 读取视频帧并统一为模型尺寸。"""
    import cv2

    capture = cv2.VideoCapture(str(input_video_path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {input_video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 8.0)
    frames = []
    while True:
        ok, frame_bgr = capture.read()
        if not ok:
            break
        frame_bgr = cv2.resize(frame_bgr, resize_to)
        frames.append(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    capture.release()
    if not frames:
        raise RuntimeError(f"no frames read from video: {input_video_path}")
    import numpy as np

    return np.stack(frames, axis=0), fps


def write_video_frames(frames: Any, output_video_path: Path, *, fps: float) -> None:
    """使用 OpenCV 写出 RGB 帧数组。"""
    import cv2

    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    height, width = int(frames.shape[1]), int(frames.shape[2])
    writer = cv2.VideoWriter(
        str(output_video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        float(fps),
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"cannot open video writer: {output_video_path}")
    for frame_rgb in frames:
        writer.write(cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
    writer.release()


def frame_to_tensor(frame_rgb: Any, device: Any) -> Any:
    """把 RGB 帧转换为 HiDDeN 需要的 BCHW [-1,1] tensor。"""
    import torch

    tensor = torch.tensor(frame_rgb, dtype=torch.float32, device=device)
    return tensor.unsqueeze(0).permute(0, 3, 1, 2) / 127.5 - 1.0


def tensor_to_frame(tensor: Any) -> Any:
    """把 HiDDeN 输出 tensor 转回 uint8 RGB 帧。"""
    import numpy as np

    frame = tensor.detach().cpu().permute(0, 2, 3, 1).numpy()[0]
    frame = (frame + 1.0) * 127.5
    return np.clip(frame, 0, 255).astype("uint8")

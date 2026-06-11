"""external_rivagan 的 Colab 真实 smoke adapter。"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import urllib.request

from experiments.baseline_comparison_gate.baseline_adapter import (
    BaselineDetectionResult,
    BaselineEmbedResult,
    BaselineEvaluationResult,
    BaselineRuntimeContext,
)
from main.core.digest import compute_file_digest


ADAPTER_VERSION = "external_rivagan_real_smoke_adapter"
SCORE_MAPPING_RULE = "mean_frame_bit_accuracy_from_decoder_logits"
DEFAULT_RIVAGAN_WEIGHT_URL = (
    "https://raw.githubusercontent.com/Peachypie98/RivaGAN/main/model_weight/"
    "rivagan_32bit_model.pt"
)


@dataclass(frozen=True)
class RivaGANModelHandle:
    """保存已加载的 RivaGAN 模型和权重来源。"""

    model: Any
    device: str
    model_digest: str
    checkpoint_path: Path


class ExternalRivaGANAdapter:
    """对 RivaGAN 上游模型进行最小真实 smoke 封装。"""

    baseline_name = "external_rivagan"

    def __init__(
        self,
        *,
        upstream_root: str | Path,
        model_path: str | Path | None = None,
        model_url: str = DEFAULT_RIVAGAN_WEIGHT_URL,
    ) -> None:
        self.upstream_root = Path(upstream_root)
        self.model_path = Path(model_path) if model_path is not None else None
        self.model_url = model_url
        self.context: BaselineRuntimeContext | None = None
        self.handle: RivaGANModelHandle | None = None
        self.payload_bits: list[int] | None = None

    def prepare(self, context: BaselineRuntimeContext) -> dict[str, Any]:
        """准备 RivaGAN 上游代码、权重和反序列化兼容环境。"""
        self.context = context
        if not self.upstream_root.exists():
            raise FileNotFoundError(f"RivaGAN upstream root not found: {self.upstream_root}")
        if str(self.upstream_root) not in sys.path:
            sys.path.insert(0, str(self.upstream_root))

        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("external_rivagan real smoke requires CUDA because upstream code calls .cuda()")

        started_at = time.perf_counter()
        checkpoint_path = self.model_path or (context.work_dir / "ckpts" / "rivagan_32bit_model.pt")
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        if not checkpoint_path.exists():
            urllib.request.urlretrieve(self.model_url, checkpoint_path)
        install_rivagan_pickle_compatibility_classes()
        model = torch.load(checkpoint_path, map_location="cuda", weights_only=False)
        model.encoder.eval()
        model.decoder.eval()
        self.handle = RivaGANModelHandle(
            model=model,
            device="cuda",
            model_digest=compute_file_digest(checkpoint_path),
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
            "model_weight_url": self.model_url,
            "prepare_seconds": prepare_seconds,
        }

    def embed(
        self,
        input_video_path: Path,
        payload_bits: list[int],
        output_video_path: Path,
        metadata: dict[str, Any],
    ) -> BaselineEmbedResult:
        """把固定 32-bit payload 嵌入输入视频。"""
        handle = self._require_handle()
        started_at = time.perf_counter()
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        model_payload = normalize_payload_bits(payload_bits, expected_length=32)
        handle.model.encode(str(input_video_path), tuple(model_payload), str(output_video_path))
        self.payload_bits = model_payload
        embed_seconds = time.perf_counter() - started_at
        return BaselineEmbedResult(
            baseline_name=self.baseline_name,
            output_video_path=output_video_path,
            embed_success=True,
            runtime_metrics={"embed_seconds": embed_seconds},
            baseline_trace={
                "adapter_version": ADAPTER_VERSION,
                "model_digest": handle.model_digest,
                "checkpoint_path": handle.checkpoint_path.as_posix(),
            },
        )

    def detect(self, input_video_path: Path, metadata: dict[str, Any]) -> BaselineDetectionResult:
        """检测视频中的 RivaGAN payload 并计算平均逐帧 bit accuracy。"""
        handle = self._require_handle()
        payload_bits = metadata.get("payload_bits") or self.payload_bits
        if payload_bits is None:
            raise ValueError("payload_bits is required for RivaGAN real smoke detection")

        started_at = time.perf_counter()
        import numpy as np

        expected = np.array([int(bit) for bit in payload_bits], dtype=np.int64)
        frame_scores: list[float] = []
        predicted_prefix: list[int] | None = None
        for logits in handle.model.decode(str(input_video_path)):
            predicted = (logits >= 0.0).astype(np.int64)
            compared_length = min(len(predicted), len(expected))
            if compared_length == 0:
                continue
            frame_scores.append(float((predicted[:compared_length] == expected[:compared_length]).mean()))
            if predicted_prefix is None:
                predicted_prefix = predicted[:32].astype(int).tolist()
        if not frame_scores:
            raise ValueError("RivaGAN detection returned no decodable frames")
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
                failure_reason=detection_output.failure_reason or "rivagan_detection_failed",
            )
        bit_accuracy = float(detection_output.baseline_score)
        return BaselineEvaluationResult(
            baseline_name=self.baseline_name,
            threshold=threshold,
            target_fpr=target_fpr,
            decision="positive" if bit_accuracy >= threshold else "negative",
            bit_accuracy=bit_accuracy,
            ber=1.0 - bit_accuracy,
            failure_reason=None if bit_accuracy >= threshold else "rivagan_smoke_below_threshold",
        )

    def _require_handle(self) -> RivaGANModelHandle:
        if self.handle is None:
            raise RuntimeError("ExternalRivaGANAdapter.prepare must be called first")
        return self.handle


def install_rivagan_pickle_compatibility_classes() -> None:
    """把 RivaGAN checkpoint 需要的 `__main__` 类名映射到 DAI 上游实现。

    选用的公开权重使用 `__main__.RivaGAN` 等类名序列化。这里仅在加载时
    注册兼容类名, 不修改模型权重和算法结构。
    """
    import __main__
    from rivagan.adversary import Adversary, Critic
    from rivagan.attention import AttentiveDecoder, AttentiveEncoder
    from rivagan.rivagan import RivaGAN

    __main__.Adversary = Adversary
    __main__.Critic = Critic
    __main__.AttentiveDecoder = AttentiveDecoder
    __main__.AttentiveEncoder = AttentiveEncoder
    __main__.RivaGAN = RivaGAN


def normalize_payload_bits(payload_bits: list[int], expected_length: int = 32) -> list[int]:
    """把项目 payload 扩展或截断到 RivaGAN 的 32-bit 消息长度。"""
    if not payload_bits:
        payload_bits = [0, 1]
    normalized = [int(bit) & 1 for bit in payload_bits]
    while len(normalized) < expected_length:
        normalized.extend(normalized)
    return normalized[:expected_length]


def create_rivagan_probe_video(output_path: Path, *, duration_seconds: int = 2, fps: int = 20, size: int = 128) -> None:
    """创建 RivaGAN smoke 使用的 AVI 输入视频。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
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

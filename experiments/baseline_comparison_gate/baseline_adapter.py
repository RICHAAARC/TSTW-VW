"""阶段三外部 baseline 的统一 adapter 契约。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class BaselineRuntimeContext:
    """保存一次 baseline 调用所需的最小上下文。"""

    baseline_name: str
    run_id: str
    work_dir: Path
    source_manifest: dict[str, Any]
    adapter_version: str = "adapter_skeleton"


@dataclass(frozen=True)
class BaselineEmbedResult:
    """描述一次外部 baseline 嵌入调用的结果。"""

    baseline_name: str
    output_video_path: Path | None
    embed_success: bool
    runtime_metrics: dict[str, Any] = field(default_factory=dict)
    baseline_trace: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None


@dataclass(frozen=True)
class BaselineDetectionResult:
    """描述一次外部 baseline 检测调用的原始结果和统一分数。"""

    baseline_name: str
    baseline_score: float | None
    baseline_raw_detector_output: dict[str, Any]
    runtime_metrics: dict[str, Any] = field(default_factory=dict)
    baseline_trace: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None


@dataclass(frozen=True)
class BaselineEvaluationResult:
    """描述 fixed-FPR 阈值协议下的 baseline 判定结果。"""

    baseline_name: str
    threshold: float | None
    target_fpr: float
    decision: str
    bit_accuracy: float | None = None
    ber: float | None = None
    failure_reason: str | None = None


class BaselineAdapter(Protocol):
    """统一外部 baseline 接口, 用于隔离不同上游项目的实现差异。"""

    baseline_name: str

    def prepare(self, context: BaselineRuntimeContext) -> dict[str, Any]:
        """准备依赖、权重、运行目录和审计 trace。"""

    def embed(
        self,
        input_video_path: Path,
        payload_bits: list[int],
        output_video_path: Path,
        metadata: dict[str, Any],
    ) -> BaselineEmbedResult:
        """将 payload 嵌入视频并返回统一嵌入结果。"""

    def detect(
        self,
        input_video_path: Path,
        metadata: dict[str, Any],
    ) -> BaselineDetectionResult:
        """检测视频中的水印并返回统一分数。"""

    def evaluate(
        self,
        detection_output: BaselineDetectionResult,
        payload_bits: list[int],
        threshold: float,
        target_fpr: float,
    ) -> BaselineEvaluationResult:
        """根据 calibration 阈值生成最终判定。"""


class UnimplementedExternalBaselineAdapter:
    """尚未接入真实上游代码时使用的阻断型 adapter。"""

    def __init__(self, baseline_name: str) -> None:
        self.baseline_name = baseline_name

    def prepare(self, context: BaselineRuntimeContext) -> dict[str, Any]:
        """返回可审计的未实现状态, 防止误当作正式结果。"""
        return {
            "baseline_name": self.baseline_name,
            "adapter_status": "adapter_skeleton_only",
            "blocking_reason": "external_baseline_not_integrated",
            "source_manifest_baseline": context.source_manifest.get("baseline_name"),
        }

    def embed(
        self,
        input_video_path: Path,
        payload_bits: list[int],
        output_video_path: Path,
        metadata: dict[str, Any],
    ) -> BaselineEmbedResult:
        """阻断真实嵌入, 避免 skeleton 产生伪实验结果。"""
        return BaselineEmbedResult(
            baseline_name=self.baseline_name,
            output_video_path=None,
            embed_success=False,
            baseline_trace={"adapter_status": "adapter_skeleton_only"},
            failure_reason="external_baseline_not_integrated",
        )

    def detect(
        self,
        input_video_path: Path,
        metadata: dict[str, Any],
    ) -> BaselineDetectionResult:
        """阻断真实检测, 避免 skeleton 产生伪分数。"""
        return BaselineDetectionResult(
            baseline_name=self.baseline_name,
            baseline_score=None,
            baseline_raw_detector_output={},
            baseline_trace={"adapter_status": "adapter_skeleton_only"},
            failure_reason="external_baseline_not_integrated",
        )

    def evaluate(
        self,
        detection_output: BaselineDetectionResult,
        payload_bits: list[int],
        threshold: float,
        target_fpr: float,
    ) -> BaselineEvaluationResult:
        """阻断正式判定, 要求先完成 Colab smoke。"""
        return BaselineEvaluationResult(
            baseline_name=self.baseline_name,
            threshold=threshold,
            target_fpr=target_fpr,
            decision="failed",
            failure_reason=detection_output.failure_reason
            or "external_baseline_not_integrated",
        )

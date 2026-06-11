"""阶段三 baseline adapter registry。"""

from __future__ import annotations

from experiments.baseline_comparison_gate.baseline_adapter import (
    BaselineAdapter,
    UnimplementedExternalBaselineAdapter,
)
from experiments.baseline_comparison_gate.source_intake import REQUIRED_BASELINE_NAMES


def build_adapter_registry() -> dict[str, BaselineAdapter]:
    """构建固定 baseline 名称到 adapter 的映射。"""
    return {
        baseline_name: UnimplementedExternalBaselineAdapter(baseline_name)
        for baseline_name in REQUIRED_BASELINE_NAMES
    }


def get_baseline_adapter(baseline_name: str) -> BaselineAdapter:
    """按名称获取 baseline adapter, 未登记名称直接阻断。"""
    registry = build_adapter_registry()
    if baseline_name not in registry:
        raise KeyError(f"unsupported baseline adapter: {baseline_name}")
    return registry[baseline_name]

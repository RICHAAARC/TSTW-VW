"""
文件用途：构建阶段 0 的 split plan。
File purpose: Build the governed split plan for stage 0.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass

from main.core.schema import SAMPLE_ROLE_ORDER, SPLIT_ORDER, ensure_supported_sample_role, ensure_supported_split


@dataclass(frozen=True)
class SplitPlanEntry:
    """功能：定义阶段 0 split plan 条目。

    Stage-0 split plan entry.

    Args:
        sample_id: Stable sample identifier.
        split: Governed split name.
        sample_role: Governed sample role.

    Returns:
        None.
    """

    sample_id: str
    split: str
    sample_role: str


def build_sample_id(split: str, sample_role: str, sample_index: int) -> str:
    """功能：根据 split、role 与索引构建样本标识。

    Build a stable stage-0 sample identifier.

    Args:
        split: Governed split name.
        sample_role: Governed sample role.
        sample_index: One-based sample index.

    Returns:
        A governed sample identifier.
    """
    ensure_supported_split(split)
    ensure_supported_sample_role(sample_role)
    if not isinstance(sample_index, int) or sample_index < 1:
        raise ValueError("sample_index must be a positive integer")
    return f"sample_{split}_{sample_role}_{sample_index:06d}"


def build_split_plan(samples_per_role: int = 2) -> list[SplitPlanEntry]:
    """功能：构建阶段 0 的共享 split plan。

    Build the shared stage-0 split plan.

    Args:
        samples_per_role: Number of samples per split-role pair.

    Returns:
        A list of `SplitPlanEntry` instances.
    """
    if not isinstance(samples_per_role, int) or samples_per_role < 1:
        raise ValueError("samples_per_role must be a positive integer")

    split_plan: list[SplitPlanEntry] = []
    for split in SPLIT_ORDER:
        for sample_role in SAMPLE_ROLE_ORDER:
            for sample_index in range(1, samples_per_role + 1):
                split_plan.append(
                    SplitPlanEntry(
                        sample_id=build_sample_id(split, sample_role, sample_index),
                        split=split,
                        sample_role=sample_role,
                    )
                )
    return split_plan
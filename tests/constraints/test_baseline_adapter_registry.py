"""验证阶段三 baseline adapter registry 的阻断语义。"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.baseline_adapter import BaselineRuntimeContext
from experiments.baseline_comparison_gate.baseline_registry import (
    build_adapter_registry,
    get_baseline_adapter,
)
from experiments.baseline_comparison_gate.source_intake import REQUIRED_BASELINE_NAMES

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_baseline_adapter_registry_contains_governed_baselines() -> None:
    """确认 registry 只暴露阶段三固定的三个 baseline。"""
    registry = build_adapter_registry()

    assert tuple(registry) == REQUIRED_BASELINE_NAMES


def test_unimplemented_adapter_blocks_formal_scores(tmp_path: Path) -> None:
    """确认 skeleton adapter 不会产生可误用的正式检测分数。"""
    adapter = get_baseline_adapter("external_videoseal")
    context = BaselineRuntimeContext(
        baseline_name="external_videoseal",
        run_id="baseline_comparison_smoke_20260611T000000Z_abcdef0",
        work_dir=tmp_path,
        source_manifest={"baseline_name": "external_videoseal"},
    )

    prepare_result = adapter.prepare(context)
    detection_result = adapter.detect(tmp_path / "input.mp4", {})
    evaluation_result = adapter.evaluate(detection_result, [0, 1], 0.5, 0.001)

    assert prepare_result["adapter_status"] == "adapter_skeleton_only"
    assert detection_result.baseline_score is None
    assert detection_result.failure_reason == "external_baseline_not_integrated"
    assert evaluation_result.decision == "failed"


def test_unknown_baseline_adapter_is_rejected() -> None:
    """确认未登记 baseline 不能绕过固定 baseline 范围。"""
    with pytest.raises(KeyError):
        get_baseline_adapter("external_unknown")

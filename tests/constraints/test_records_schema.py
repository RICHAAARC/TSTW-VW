"""
文件用途：验证 active formal stage 的 records schema 约束。
File purpose: Validate active-stage record schema constraints.
Module type: Constraint test module
"""

from __future__ import annotations

from collections import Counter

import pytest

from main.protocol.split_builder import build_split_plan


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_build_split_plan_supports_calibration_negative_overrides() -> None:
    """Validate that calibration negative counts can grow without widening test coverage."""
    split_plan = build_split_plan(
        samples_per_role=2,
        split_role_sample_counts={
            "calibration": {
                "clean_negative": 8,
                "attacked_negative": 8,
            }
        },
    )
    counts = Counter((entry.split, entry.sample_role) for entry in split_plan)

    assert counts[("dev", "clean_negative")] == 2
    assert counts[("calibration", "clean_negative")] == 8
    assert counts[("calibration", "attacked_negative")] == 8
    assert counts[("calibration", "watermarked_positive")] == 2
    assert counts[("test", "attacked_negative")] == 2

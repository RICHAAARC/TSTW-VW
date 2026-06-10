"""
文件用途：验证报告构建中的 saturated anchor 同步救援判定。
File purpose: Validate saturated-anchor sync rescue handling in report construction.
Module type: Test module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.quick, pytest.mark.unit]

from main.analysis.report_builder import _compare_variant_attack_metric


def test_report_sync_gain_accepts_saturated_anchor_with_positive_rescue() -> None:
    """验证 tubelet_only 已饱和时, 正向 aligned payload rescue 可支撑 sync gain gate。

    Args:
        None.

    Returns:
        None.
    """
    main_rows = [
        {
            "method_variant": "tubelet_only",
            "attack_name": "local_clip",
            "attacked_positive_TPR": 1.0,
        },
        {
            "method_variant": "tubelet_sync",
            "attack_name": "local_clip",
            "attacked_positive_TPR": 1.0,
        },
    ]
    event_score_records = [
        {
            "method_variant": "tubelet_sync",
            "attack_name": "local_clip",
            "split": "test",
            "sample_role": "attacked_positive",
            "mechanism_trace": {
                "sync_rescue_applied": True,
                "S_payload_rescue_gain": 0.05,
            },
        }
    ]

    assert _compare_variant_attack_metric(
        main_rows,
        left_variant="tubelet_sync",
        right_variant="tubelet_only",
        attack_names=["local_clip"],
        event_score_records=event_score_records,
        allow_saturated_anchor_sync_rescue=True,
    )


def test_report_sync_gain_rejects_saturated_anchor_without_positive_rescue() -> None:
    """验证没有正向 rescue trace 时, 饱和 anchor 不能被误判为 sync gain。

    Args:
        None.

    Returns:
        None.
    """
    main_rows = [
        {
            "method_variant": "tubelet_only",
            "attack_name": "local_clip",
            "attacked_positive_TPR": 1.0,
        },
        {
            "method_variant": "tubelet_sync",
            "attack_name": "local_clip",
            "attacked_positive_TPR": 1.0,
        },
    ]

    assert not _compare_variant_attack_metric(
        main_rows,
        left_variant="tubelet_sync",
        right_variant="tubelet_only",
        attack_names=["local_clip"],
        event_score_records=[],
        allow_saturated_anchor_sync_rescue=True,
    )

"""验证外部 baseline 拉取脚本的无网络计划生成能力。"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.prepare_baselines.fetch_external_baselines import build_fetch_plan

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]


def test_external_baseline_fetch_plan_uses_pinned_commits() -> None:
    """确认拉取计划只使用 source manifest 中的固定 commit。"""
    plan = build_fetch_plan(
        config_dir=ROOT / "configs" / "baselines",
        external_root=ROOT / "external_baselines",
    )

    assert plan["project_stage"] == "baseline_comparison_gate"
    assert {entry["baseline_name"] for entry in plan["baselines"]} == {
        "external_videoseal",
        "external_rivagan",
        "external_hidden_framewise",
    }
    for entry in plan["baselines"]:
        assert len(entry["upstream_commit"]) == 40
        assert entry["target_path"].endswith("upstream")

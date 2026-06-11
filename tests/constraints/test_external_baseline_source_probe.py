"""验证阶段三外部 baseline source probe。"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.source_probe import probe_baseline_source_tree

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]


def test_external_baseline_source_probe_finds_checked_out_sources() -> None:
    """确认已拉取的三个 baseline 源码树包含预期基础文件。"""
    payload = probe_baseline_source_tree(ROOT / "external_baselines")

    assert payload["project_stage"] == "baseline_comparison_gate"
    assert len(payload["entries"]) == 3
    assert {entry["baseline_name"] for entry in payload["entries"]} == {
        "external_videoseal",
        "external_rivagan",
        "external_hidden_framewise",
    }
    assert all(entry["source_tree_present"] for entry in payload["entries"])
    assert all(not entry["missing_required_files"] for entry in payload["entries"])


def test_external_baseline_source_probe_blocks_missing_tree(tmp_path: Path) -> None:
    """确认源码树缺失时 preflight 会显式阻断。"""
    payload = probe_baseline_source_tree(tmp_path / "missing_external_baselines")

    assert payload["probe_status"] == "blocked"
    assert any(reason.endswith("source_tree_missing") for reason in payload["blocking_reasons"])

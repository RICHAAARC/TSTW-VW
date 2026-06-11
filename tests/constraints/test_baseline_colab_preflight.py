"""验证阶段三 Colab preflight 检查。"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.colab_preflight import run_colab_preflight

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]


def test_colab_preflight_reports_pending_weight_and_adapter_state() -> None:
    """确认 preflight 会把未下载权重和 skeleton adapter 标记为待 Colab 验证。"""
    payload = run_colab_preflight(
        config_dir=ROOT / "configs" / "baselines",
        external_root=ROOT / "external_baselines",
    )

    assert payload["project_stage"] == "baseline_comparison_gate"
    assert payload["preflight_status"] == "requires_colab_or_setup"
    assert len(payload["baseline_entries"]) == 3
    assert any(reason.endswith("model_weights_need_colab_digest") for reason in payload["blocking_reasons"])
    assert any(reason.endswith("adapter_needs_colab_smoke") for reason in payload["blocking_reasons"])


def test_colab_preflight_checks_optional_stage_two_package_root(tmp_path: Path) -> None:
    """确认显式传入阶段二结果包路径时会检查其存在性。"""
    missing_path = tmp_path / "missing_stage_two_package"
    payload = run_colab_preflight(
        config_dir=ROOT / "configs" / "baselines",
        external_root=ROOT / "external_baselines",
        stage_two_package_root=missing_path,
    )

    assert payload["stage_two_package_status"] == "missing"
    assert "stage_two_package_root_missing" in payload["blocking_reasons"]

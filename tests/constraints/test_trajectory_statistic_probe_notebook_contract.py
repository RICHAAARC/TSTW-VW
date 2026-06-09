"""
文件用途：验证阶段 3 trajectory statistic probe notebook 入口遵循受治理合同。
File purpose: Validate the stage-three trajectory statistic probe notebook contract.
Module type: Constraint test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = ROOT / "paper_workflow" / "run_trajectory_statistic_probe.ipynb"
WORKFLOW_PATH = (
    ROOT
    / "paper_workflow"
    / "notebook_utils"
    / "trajectory_statistic_probe_workflow.py"
)
REQUIRED_STEP_KEYS = [
    "00_runtime_identity_and_user_config",
    "01_mount_google_drive",
    "02_clone_or_update_repository",
    "03_install_runtime_dependencies",
    "04_verify_repository_contract",
    "05_run_trajectory_smoke_tests",
    "06_extract_stage_two_frozen_baseline",
    "07_run_trajectory_formal_replay",
    "08_package_trajectory_results",
    "09_print_final_summary",
]


def _load_notebook(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cell_text(cell: dict[str, object]) -> str:
    source = cell.get("source", [])
    if isinstance(source, list):
        return "".join(str(line) for line in source)
    return str(source)


def _cell_step_key(cell: dict[str, object]) -> str | None:
    metadata = cell.get("metadata", {})
    if not isinstance(metadata, dict):
        return None
    step_key = metadata.get("step_key")
    return step_key if isinstance(step_key, str) else None


def test_trajectory_statistic_probe_notebook_delegates_to_repository_cli() -> None:
    """验证阶段 3 notebook 只调度仓库 helper 和 CLI, 不承载正式协议逻辑。"""
    assert NOTEBOOK_PATH.exists()
    assert WORKFLOW_PATH.exists()
    notebook = _load_notebook(NOTEBOOK_PATH)
    cells = notebook.get("cells", [])
    assert isinstance(cells, list) and cells
    observed_step_keys = [
        _cell_step_key(cell)
        for cell in cells
        if isinstance(cell, dict) and _cell_step_key(cell) is not None
    ]
    notebook_text = "\n".join(
        _cell_text(cell) for cell in cells if isinstance(cell, dict)
    )
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert observed_step_keys == REQUIRED_STEP_KEYS
    assert "trajectory_statistic_probe_workflow" in notebook_text
    assert "trajectory_workflow.run_formal_replay_cli(" in notebook_text
    assert "trajectory_workflow.extract_frozen_baseline_package(" in notebook_text
    assert "trajectory_workflow.package_trajectory_probe_run(" in notebook_text
    assert "experiments.trajectory_statistic_probe.formal_replay_cli" in workflow_text
    assert "write_event_score_records(" not in notebook_text
    assert "write_threshold_records(" not in notebook_text
    assert "TrajectoryStatisticProbeRunner(" not in notebook_text

"""
文件用途: 验证 trajectory-aware sampling probe notebook 入口遵守受治理合同。
Module type: Constraint test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = ROOT / "paper_workflow" / "run_trajectory_aware_sampling_probe.ipynb"
WORKFLOW_PATH = (
    ROOT
    / "paper_workflow"
    / "notebook_utils"
    / "trajectory_aware_sampling_probe_workflow.py"
)
REQUIRED_STEP_KEYS = [
    "00_runtime_identity_and_user_config",
    "01_mount_google_drive",
    "02_clone_or_update_repository",
    "03_install_runtime_dependencies",
    "04_verify_gpu_runtime",
    "05_verify_repository_contract",
    "06_run_sampling_scaffold_smoke_tests",
    "07_locate_stage_three_trajectory_output",
    "08_run_sampling_scaffold_validation",
    "09_package_sampling_results",
    "10_print_final_summary",
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


def test_trajectory_aware_sampling_probe_notebook_delegates_to_repository_cli() -> None:
    """验证 sampling notebook 只调度 helper 和 CLI, 不承载正式协议逻辑。"""
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
    assert "trajectory_aware_sampling_probe_workflow" in notebook_text
    assert "sampling_workflow.run_sampling_scaffold_cli(" in notebook_text
    assert "sampling_workflow.read_gpu_validation_contract(" in notebook_text
    assert "sampling_workflow.read_backend_transition_guard(" in notebook_text
    assert "sampling_workflow.read_backend_transition_decision(" in notebook_text
    assert "sampling_workflow.read_runtime_interface_scaffold(" in notebook_text
    assert "sampling_workflow.read_runtime_interface_implementation(" in notebook_text
    assert "sampling_workflow.package_sampling_probe_run(" in notebook_text
    assert "sampling_workflow.find_latest_trajectory_probe_root(" in notebook_text
    assert "sampling_workflow.extract_trajectory_probe_package(" in notebook_text
    assert "experiments.trajectory_aware_sampling_probe.scaffold_cli" in workflow_text
    assert "trajectory_aware_sampling_probe_scaffold_gpu_validation_utc_time_short_commit" in notebook_text
    assert "git', 'rev-parse', '--short=7', 'HEAD'" in notebook_text
    assert "datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')" in notebook_text
    assert "nvidia-smi" in notebook_text
    assert "TSTW_STAGE3_TRAJECTORY_ROOT" in notebook_text
    assert "TSTW_STAGE3_TRAJECTORY_PACKAGE_PATH" in notebook_text
    assert "STAGE3_RESULT_ROOT" in notebook_text
    assert "DRIVE_ROOT / 'results' / 'trajectory_aware_sampling_probe' / RUN_ID / 'packages'" in notebook_text
    assert "write_event_score_records(" not in notebook_text
    assert "write_threshold_records(" not in notebook_text
    assert "TrajectoryAwareSamplingProbeRunner(" not in notebook_text
    assert "sampling_policy_manifest.json" in workflow_text
    assert "trajectory_aware_sampling_gpu_validation_contract.json" in notebook_text
    assert "trajectory_aware_sampling_gpu_validation_contract.json" in workflow_text
    assert "trajectory_aware_sampling_backend_transition_guard.json" in notebook_text
    assert "trajectory_aware_sampling_backend_transition_guard.json" in workflow_text
    assert "trajectory_aware_sampling_backend_transition_decision.json" in notebook_text
    assert "trajectory_aware_sampling_backend_transition_decision.json" in workflow_text
    assert "trajectory_aware_sampling_runtime_interface_scaffold.json" in notebook_text
    assert "trajectory_aware_sampling_runtime_interface_scaffold.json" in workflow_text
    assert "trajectory_aware_sampling_runtime_interface_implementation.json" in notebook_text
    assert "trajectory_aware_sampling_runtime_interface_implementation.json" in workflow_text
    assert "TrajectoryAwareSamplingGpuValidationContractDecision" in notebook_text
    assert "NextAllowedConstructionAfterGpuValidationContract" in notebook_text
    assert "TrajectoryAwareSamplingBackendTransitionGuardDecision" in notebook_text
    assert "NextAllowedConstructionAfterBackendTransitionGuard" in notebook_text
    assert "TrajectoryAwareSamplingBackendTransitionDecision" in notebook_text
    assert "NextAllowedConstructionAfterBackendTransitionDecision" in notebook_text
    assert "TrajectoryAwareSamplingRuntimeInterfaceScaffoldDecision" in notebook_text
    assert "NextAllowedConstructionAfterRuntimeInterfaceScaffold" in notebook_text
    assert "TrajectoryAwareSamplingRuntimeInterfaceImplementationDecision" in notebook_text
    assert "NextAllowedConstructionAfterRuntimeInterfaceImplementation" in notebook_text

"""
文件用途：验证 runtime_profile 治理边界、配置目录与 release 可移除性约束。
File purpose: Validate runtime-profile governance boundaries, config roots, and release removability constraints.
Module type: Constraint test module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paper_workflow.notebook_utils.runtime_profile_workflow import (
    ALLOWED_RUNTIME_PROFILE_KEYS,
    FORBIDDEN_RUNTIME_PROFILE_KEYS,
)
from tools.harness.audits.audit_runtime_profile_boundaries import run_audit
from tools.harness.run_all_audits import AUDIT_MODULE_NAMES


pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_RUNTIME_PROFILES = {
    "l4_debug.json",
    "l4_smoke.json",
    "l4_formal.json",
    "a100_80g_formal.json",
    "a100_80g_paper_main.json",
    "cpu_dataset_build.json",
}


def test_runtime_profile_boundary_audit_is_registered_and_passes() -> None:
    """Validate the runtime-profile boundary audit is registered and passes.

    Args:
        None.

    Returns:
        None.
    """
    assert "tools.harness.audits.audit_runtime_profile_boundaries" in AUDIT_MODULE_NAMES
    report = run_audit(ROOT)
    assert report["decision"] == "pass"
    assert report["violations"] == []


def test_runtime_profile_governance_doc_and_profile_configs_exist() -> None:
    """Validate the governance doc and governed runtime-profile configs exist.

    Args:
        None.

    Returns:
        None.
    """
    doc_path = ROOT / "docs" / "gpu_runtime_optimization_governance.md"
    config_root = ROOT / "configs" / "runtime_profiles"

    assert doc_path.exists()
    assert config_root.exists()
    assert {path.name for path in config_root.glob("*.json")} == EXPECTED_RUNTIME_PROFILES


def test_runtime_profile_configs_remain_execution_only() -> None:
    """Validate runtime-profile configs stay within execution-only key boundaries.

    Args:
        None.

    Returns:
        None.
    """
    config_root = ROOT / "configs" / "runtime_profiles"
    for config_path in sorted(config_root.glob("*.json")):
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert set(payload.keys()) <= ALLOWED_RUNTIME_PROFILE_KEYS
        assert not (set(payload.keys()) & FORBIDDEN_RUNTIME_PROFILE_KEYS)
        assert payload["runtime_profile"] == config_path.stem
        assert all(not isinstance(value, (dict, list)) for value in payload.values())


def test_release_boundary_allows_paper_workflow_removal() -> None:
    """Validate release-boundary docs keep paper_workflow removable.

    Args:
        None.

    Returns:
        None.
    """
    file_organization_text = (ROOT / "docs" / "file_organization.md").read_text(encoding="utf-8")
    governance_text = (ROOT / "docs" / "gpu_runtime_optimization_governance.md").read_text(encoding="utf-8")

    assert "paper_workflow/ 可以完全删除" in file_organization_text
    assert "paper_workflow/ 不属于最终发布版默认内容" in governance_text
    assert "最终 release 可以移除 paper_workflow/" in governance_text

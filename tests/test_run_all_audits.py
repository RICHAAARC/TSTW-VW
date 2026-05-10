"""
文件用途：验证全部 harness 审计可执行并输出治理摘要。
File purpose: Validate harness audit runner module coverage.
Module type: General module
"""

from __future__ import annotations

from tools.harness.run_all_audits import AUDIT_MODULE_NAMES


def test_run_all_audits_includes_required_modules() -> None:
    assert "tools.harness.audits.audit_naming_conventions" in AUDIT_MODULE_NAMES
    assert "tools.harness.audits.audit_placeholder_random_fields" in AUDIT_MODULE_NAMES


def test_run_all_audits_module_list_has_no_duplicates() -> None:
    assert len(AUDIT_MODULE_NAMES) == len(set(AUDIT_MODULE_NAMES))


"""
文件用途：验证全部 harness 审计可执行并输出治理摘要。
File purpose: Validate harness audit runner module coverage.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from tools.harness.audits.audit_utf8_encoding_contract import run_audit
from tools.harness.run_all_audits import AUDIT_MODULE_NAMES


def test_run_all_audits_includes_required_modules() -> None:
    assert "tools.harness.audits.audit_naming_conventions" in AUDIT_MODULE_NAMES
    assert "tools.harness.audits.audit_file_organization_contract" in AUDIT_MODULE_NAMES
    assert "tools.harness.audits.audit_utf8_encoding_contract" in AUDIT_MODULE_NAMES
    assert "tools.harness.audits.audit_main_no_colab_dependency" in AUDIT_MODULE_NAMES
    assert "tools.harness.audits.audit_main_no_stage_specific_runner" in AUDIT_MODULE_NAMES
    assert "tools.harness.audits.audit_release_no_placeholder_core" in AUDIT_MODULE_NAMES
    assert "tools.harness.audits.audit_notebook_import_boundaries" in AUDIT_MODULE_NAMES
    assert "tools.harness.audits.audit_placeholder_random_fields" in AUDIT_MODULE_NAMES


def test_run_all_audits_module_list_has_no_duplicates() -> None:
    assert len(AUDIT_MODULE_NAMES) == len(set(AUDIT_MODULE_NAMES))


def test_utf8_encoding_audit_accepts_utf8_governed_files(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir(parents=True)
    (docs_root / "contract.md").write_text("UTF-8 文本\n", encoding="utf-8")

    report = run_audit(tmp_path)

    assert report["decision"] == "pass"
    assert report["violations"] == []


def test_utf8_encoding_audit_rejects_non_utf8_governed_files(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir(parents=True)
    (docs_root / "broken.md").write_bytes(b"\xff\xfe\x00a")

    report = run_audit(tmp_path)

    assert report["decision"] == "fail"
    assert report["violations"][0]["reason"] == "text_file_not_utf8_encoded"


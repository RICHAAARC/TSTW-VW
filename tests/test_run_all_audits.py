"""
文件用途：验证全部 harness 审计可执行并生成汇总报告。
File purpose: Validate the end-to-end harness audit runner and summary output.
Module type: General module
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_all_audits_passes_and_writes_summary() -> None:
    """Validate that the audit runner succeeds and writes a passing summary.

    Args:
        None.

    Returns:
        None.
    """
    audit_reports_root = ROOT / "audit_reports"
    if audit_reports_root.exists():
        shutil.rmtree(audit_reports_root)

    result = subprocess.run(
        [sys.executable, "tools/harness/run_all_audits.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    summary_path = audit_reports_root / "harness_audit_summary.json"
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["overall_decision"] == "pass"
    assert all(
        report["decision"] == "pass" for report in summary["audit_results"]
    )

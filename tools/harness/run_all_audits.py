"""
文件用途：统一执行全部 harness 审计并写出汇总报告。
File purpose: Run all harness audits and write the governed summary report.
Module type: General module
"""

from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.json_report import write_report


AUDIT_MODULE_NAMES = [
    "tools.harness.audits.audit_naming_conventions",
    "tools.harness.audits.audit_file_organization_contract",
    "tools.harness.audits.audit_utf8_encoding_contract",
    "tools.harness.audits.audit_main_no_colab_dependency",
    "tools.harness.audits.audit_main_no_stage_specific_runner",
    "tools.harness.audits.audit_release_no_placeholder_core",
    "tools.harness.audits.audit_notebook_import_boundaries",
    "tools.harness.audits.audit_notebook_naming_contract",
    "tools.harness.audits.audit_placeholder_random_fields",
    "tools.harness.audits.audit_protocol_skeleton_contract",
    "tools.harness.audits.audit_protocol_artifact_schema",
    "tools.harness.audits.audit_protocol_support_configs",
    "tools.harness.audits.audit_threshold_protocol_fields",
    "tools.harness.audits.audit_notebook_formal_output_bypass",
    "tools.harness.audits.audit_test_case_constraints",
    "tools.harness.audits.audit_skill_file_presence",
]


def run_all_audits(root: str | Path) -> dict[str, Any]:
    """Run every governed harness audit and persist per-audit reports.

    Args:
        root: Repository root path.

    Returns:
        A summary report for all executed audits.
    """
    root_path = Path(root)
    output_root = root_path / "audit_reports"
    audit_results: list[dict[str, Any]] = []

    for module_name in AUDIT_MODULE_NAMES:
        audit_module = importlib.import_module(module_name)
        report = audit_module.run_audit(root_path)
        report_path = output_root / f"{report['audit_name']}.json"
        write_report(report, report_path)
        audit_results.append(report)

    pass_count = sum(1 for report in audit_results if report["decision"] == "pass")
    fail_count = len(audit_results) - pass_count
    overall_decision = "pass" if fail_count == 0 else "fail"
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_decision": overall_decision,
        "audit_results": audit_results,
        "summary": {
            "total_audits": len(audit_results),
            "pass_count": pass_count,
            "fail_count": fail_count,
        },
    }
    write_report(summary, output_root / "harness_audit_summary.json")
    return summary


def main(argv: list[str] | None = None) -> None:
    """Run the harness audit suite as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.

    Raises:
        SystemExit: Raised with exit code 0 for pass and 1 for fail.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    summary = run_all_audits(root)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    raise SystemExit(0 if summary["overall_decision"] == "pass" else 1)


if __name__ == "__main__":
    main(sys.argv)

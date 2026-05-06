"""
文件用途：提供统一的 JSON 审计报告构建与输出能力。
File purpose: Provide normalized JSON report helpers for harness audits.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_report(
    audit_name: str,
    decision: str,
    violations: list[dict[str, Any]],
    checked_paths: list[str],
) -> dict[str, Any]:
    """Build a normalized JSON audit report.

    Args:
        audit_name: Canonical audit identifier.
        decision: Final audit decision. Only "pass" or "fail" is allowed.
        violations: Violation records produced by the audit.
        checked_paths: Repository paths inspected by the audit.

    Returns:
        A normalized report dictionary ready for serialization.

    Raises:
        ValueError: Raised when the decision is not supported.
    """
    if decision not in {"pass", "fail"}:
        # 中文：报告判定必须标准化，否则汇总器无法稳定统计结果。
        raise ValueError(f"Unsupported audit decision: {decision}")

    normalized_paths = [str(Path(path)) for path in checked_paths]
    return {
        "audit_name": audit_name,
        "decision": decision,
        "violations": violations,
        "checked_paths": normalized_paths,
        "summary": {
            "violation_count": len(violations),
            "checked_path_count": len(normalized_paths),
        },
    }


def write_report(report: dict[str, Any], output_path: str | Path) -> None:
    """Write a JSON audit report to disk.

    Args:
        report: Report dictionary returned by `build_report`.
        output_path: Target JSON file path.

    Returns:
        None.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def exit_with_report(report: dict[str, Any]) -> None:
    """Print a report and exit with a decision-aligned status code.

    Args:
        report: Report dictionary returned by `build_report`.

    Returns:
        None.

    Raises:
        SystemExit: Raised with exit code 0 for pass and 1 for fail.
    """
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report.get("decision") == "pass" else 1)

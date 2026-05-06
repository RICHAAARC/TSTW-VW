"""
文件用途：执行阈值协议字段审计。
File purpose: Audit threshold protocol fields for fixed low-FPR governance.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.json_report import build_report, exit_with_report
from tools.harness.validate_project_contract import (
    load_json_config,
    validate_protocol_config_data,
)


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the threshold protocol audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized threshold protocol audit report.
    """
    root_path = Path(root)
    protocol_path = root_path / "configs" / "protocol" / "protocol_skeleton.json"
    checked_paths = [str(protocol_path)]
    violations: list[dict[str, Any]] = []

    if not protocol_path.exists():
        violations.append(
            {
                "path": str(protocol_path),
                "reason": "missing_protocol_skeleton_config",
            }
        )
    else:
        for violation in validate_protocol_config_data(load_json_config(protocol_path)):
            violation["path"] = str(protocol_path)
            violations.append(violation)

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_threshold_protocol_fields",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the threshold protocol audit as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    exit_with_report(run_audit(root))


if __name__ == "__main__":
    main(sys.argv)

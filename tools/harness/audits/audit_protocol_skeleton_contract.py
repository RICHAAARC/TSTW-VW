"""
文件用途：执行 protocol_skeleton 项目契约审计。
File purpose: Audit the governed project contract for the protocol_skeleton stage.
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
    validate_project_contract_data,
)


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the project contract audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized project contract audit report.
    """
    root_path = Path(root)
    contract_path = root_path / "configs" / "project" / "project_contract.json"
    checked_paths = [str(contract_path)]
    violations: list[dict[str, Any]] = []

    if not contract_path.exists():
        violations.append(
            {
                "path": str(contract_path),
                "reason": "missing_project_contract",
            }
        )
    else:
        for violation in validate_project_contract_data(load_json_config(contract_path)):
            violation["path"] = str(contract_path)
            violations.append(violation)

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_protocol_skeleton_contract",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the project contract audit as a CLI.

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

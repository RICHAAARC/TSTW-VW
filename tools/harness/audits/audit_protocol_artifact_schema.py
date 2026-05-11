"""
文件用途：执行阶段 0 protocol artifact schema 骨架审计。File purpose: Audit the governed protocol skeleton runtime protocol artifact schema skeleton.
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
    validate_protocol_artifact_schema_data,
)


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the protocol artifact schema audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized protocol artifact schema audit report.
    """
    root_path = Path(root)
    artifact_schema_path = (
        root_path / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    checked_paths = [str(artifact_schema_path)]
    violations: list[dict[str, Any]] = []

    if not artifact_schema_path.exists():
        violations.append(
            {
                "path": str(artifact_schema_path),
                "reason": "missing_protocol_artifact_schema",
            }
        )
    else:
        for violation in validate_protocol_artifact_schema_data(
            load_json_config(artifact_schema_path)
        ):
            violation["path"] = str(artifact_schema_path)
            violations.append(violation)

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_protocol_artifact_schema",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the protocol artifact schema audit as a CLI.

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
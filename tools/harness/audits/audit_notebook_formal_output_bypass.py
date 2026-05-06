"""
文件用途：执行 notebook 正式输出绕过审计。
File purpose: Audit notebook bypass risks for formal output paths.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.file_scanner import iter_text_files, read_text
from tools.harness.lib.json_report import build_report, exit_with_report


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the notebook bypass audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized notebook bypass audit report.
    """
    root_path = Path(root)
    violations: list[dict[str, Any]] = []
    checked_paths: list[str] = []

    for file_path in iter_text_files(root_path):
        if file_path.suffix.lower() != ".ipynb":
            continue
        checked_paths.append(str(file_path))
        text = read_text(file_path)
        if "tables/" in text:
            violations.append(
                {
                    "path": str(file_path),
                    "reason": "notebook_writes_tables_directly",
                }
            )
        if "thresholds/" in text:
            violations.append(
                {
                    "path": str(file_path),
                    "reason": "notebook_writes_thresholds_directly",
                }
            )
        if "ProtocolRunner" not in text and (
            "tables/" in text or "thresholds/" in text
        ):
            violations.append(
                {
                    "path": str(file_path),
                    "reason": "notebook_bypasses_formal_runner",
                }
            )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_notebook_formal_output_bypass",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the notebook bypass audit as a CLI.

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

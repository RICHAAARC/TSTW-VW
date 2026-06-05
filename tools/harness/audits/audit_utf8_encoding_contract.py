"""
文件用途：执行 UTF-8 文本编码契约审计。
File purpose: Audit governed text files against the UTF-8 encoding contract.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.file_scanner import iter_governed_text_files
from tools.harness.lib.json_report import build_report, exit_with_report


UTF8_GOVERNED_SCAN_ROOTS = (
    "AGENTS.md",
    "README.md",
    ".gitignore",
    ".editorconfig",
    ".vscode",
    "pyproject.toml",
    "sitecustomize.py",
    ".codex",
    "configs",
    "docs",
    "experiments",
    "main",
    "paper_workflow",
    "scripts",
    "tests",
    "tools",
)


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the UTF-8 encoding contract audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized audit report.
    """
    root_path = Path(root)
    violations: list[dict[str, Any]] = []
    checked_paths: list[str] = []

    for file_path in iter_governed_text_files(root_path, UTF8_GOVERNED_SCAN_ROOTS):
        checked_paths.append(str(file_path))
        try:
            file_path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            violations.append(
                {
                    "path": str(file_path),
                    "reason": "text_file_not_utf8_encoded",
                    "byte_start": error.start,
                    "byte_end": error.end,
                }
            )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_utf8_encoding_contract",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the audit as a CLI.

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

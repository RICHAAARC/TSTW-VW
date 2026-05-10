"""
文件用途：执行 notebook 正式输出绕过审计。
File purpose: Audit notebook bypass risks for formal output paths.
Module type: General module
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.file_scanner import iter_text_files, read_text
from tools.harness.lib.json_report import build_report, exit_with_report


FORMAL_OUTPUT_FRAGMENTS = ("tables/", "thresholds/")
DIRECT_WRITE_HINTS = (
    "write_text(",
    "write_bytes(",
    ".to_csv(",
    ".to_json(",
    "json.dump(",
    "csv.writer(",
    "csv.dictwriter(",
    "open(",
    ".open(",
    "shutil.copy(",
    "shutil.copytree(",
    "path(",
    "mkdir(",
    "makedirs(",
    "touch(",
    "cp ",
    "mv ",
    "rm ",
)


def _extract_notebook_sources(notebook_text: str) -> list[str]:
    """Extract cell sources from a notebook JSON payload.

    Args:
        notebook_text: Raw notebook text.

    Returns:
        A list of notebook cell sources.
    """
    try:
        notebook_payload = json.loads(notebook_text)
    except json.JSONDecodeError:
        return [notebook_text]

    cell_sources: list[str] = []
    for cell in notebook_payload.get("cells", []):
        if not isinstance(cell, dict):
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            cell_sources.append("".join(str(line) for line in source))
        elif isinstance(source, str):
            cell_sources.append(source)
    return cell_sources


def _find_direct_output_write_reason(cell_source: str) -> str | None:
    """Identify whether a notebook cell directly writes formal outputs.

    Args:
        cell_source: Notebook cell source text.

    Returns:
        A violation reason, or `None` when the cell is safe.
    """
    for raw_line in cell_source.splitlines():
        normalized_line = raw_line.strip().lower()
        if not normalized_line:
            continue
        if not any(fragment in normalized_line for fragment in FORMAL_OUTPUT_FRAGMENTS):
            continue
        if any(hint in normalized_line for hint in DIRECT_WRITE_HINTS) or re.search(
            r"(>|>>).*?(tables/|thresholds/)",
            normalized_line,
        ):
            if "thresholds/" in normalized_line:
                return "notebook_writes_thresholds_directly"
            return "notebook_writes_tables_directly"
    return None


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
        for cell_source in _extract_notebook_sources(read_text(file_path)):
            violation_reason = _find_direct_output_write_reason(cell_source)
            if violation_reason is None:
                continue
            violations.append(
                {
                    "path": str(file_path),
                    "reason": violation_reason,
                }
            )
            break

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

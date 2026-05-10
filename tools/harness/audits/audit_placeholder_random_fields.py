"""
文件用途：执行 placeholder 与 random 字段治理审计。
File purpose: Audit placeholder and random-trace field governance across governed configs and docs.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.field_rules import (
    check_random_field_has_seed_or_digest,
    find_governed_field_candidates,
    find_placeholder_suffix_violations,
    find_random_suffix_violations,
    find_unregistered_governed_fields,
    load_field_registry,
    validate_field_registry_row,
)
from tools.harness.lib.file_scanner import iter_governed_text_files, read_text
from tools.harness.lib.json_report import build_report, exit_with_report


def _parse_field_registry_rows(text: str) -> list[dict[str, str]]:
    """Parse Markdown field registry rows.

    Args:
        text: Raw field registry Markdown content.

    Returns:
        A list of registry row dictionaries.
    """
    rows: list[dict[str, str]] = []
    headers = [
        "field_name",
        "category",
        "required_suffix",
        "allowed_in_records",
        "allowed_in_claims",
        "replacement_required",
        "description",
    ]
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        if cells[0] in {"field_name", "---"} or set(cells[0]) == {"-"}:
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the placeholder and random field governance audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized field governance audit report.
    """
    root_path = Path(root)
    violations: list[dict[str, Any]] = []
    checked_paths: list[str] = []

    registry = load_field_registry(root_path)
    for file_path in iter_governed_text_files(root_path):
        checked_paths.append(str(file_path))
        text = read_text(file_path)
        candidates = find_governed_field_candidates(text, file_path)
        for violation in find_placeholder_suffix_violations(candidates):
            violation["violation_level"] = "blocking_violation"
            violations.append(violation)
        for violation in find_random_suffix_violations(candidates):
            violation["violation_level"] = "blocking_violation"
            violations.append(violation)
        for violation in find_unregistered_governed_fields(candidates, registry):
            violation["violation_level"] = "blocking_violation"
            violations.append(violation)

    field_registry_path = root_path / "docs" / "field_registry.md"
    if field_registry_path.exists():
        field_registry_text = read_text(field_registry_path)
        registry_rows = _parse_field_registry_rows(field_registry_text)
        seen_field_names: set[str] = set()
        for row in registry_rows:
            field_name = row["field_name"].strip()
            if field_name in seen_field_names:
                violations.append(
                    {
                        "path": str(field_registry_path),
                        "field_name": field_name,
                        "reason": "duplicate_field_registry_entry",
                        "violation_level": "blocking_violation",
                    }
                )
            seen_field_names.add(field_name)
            for row_violation in validate_field_registry_row(row):
                row_violation["path"] = str(field_registry_path)
                row_violation["violation_level"] = "blocking_violation"
                violations.append(row_violation)
            if field_name.endswith("_random") and not check_random_field_has_seed_or_digest(
                field_name,
                field_registry_text,
            ):
                violations.append(
                    {
                        "path": str(field_registry_path),
                        "field_name": field_name,
                        "reason": "random_field_missing_seed_or_digest_trace",
                        "violation_level": "blocking_violation",
                    }
                )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_placeholder_random_fields",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the placeholder and random field audit as a CLI.

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

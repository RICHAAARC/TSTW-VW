"""
文件用途：执行测试用例构建约束审计。
File purpose: Audit the governed test-case construction constraints.
Module type: General module
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.file_scanner import read_text
from tools.harness.lib.json_report import build_report, exit_with_report


REQUIRED_TEST_DIRS = (
    "tests/constraints",
    "tests/functional",
    "tests/integration",
    "tests/helpers",
    "tests/fixtures",
)
REQUIRED_MARKERS = (
    "unit",
    "constraint",
    "quick",
    "integration",
    "smoke",
    "slow",
    "formal",
)
REQUIRED_ADDOPTS = (
    "(constraint or unit or quick) and not integration and not smoke and not slow and not formal"
)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _has_any_marker(text: str, marker_names: tuple[str, ...]) -> bool:
    return any(f"pytest.mark.{marker_name}" in text for marker_name in marker_names)


def _record_violation(
    violations: list[dict[str, Any]],
    path: Path,
    reason: str,
    root: Path,
    value: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "path": _relative(path, root),
        "reason": reason,
    }
    if value is not None:
        payload["value"] = value
    violations.append(payload)


def _iter_test_files(root: Path, relative_dir: str) -> list[Path]:
    candidate = root / relative_dir
    if not candidate.exists():
        return []
    return sorted(candidate.glob("test_*.py"))


def _find_test_function_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]


def _audit_pyproject(root: Path, violations: list[dict[str, Any]], checked_paths: list[str]) -> None:
    pyproject_path = root / "pyproject.toml"
    checked_paths.append(str(pyproject_path))
    if not pyproject_path.exists():
        _record_violation(violations, pyproject_path, "missing_pyproject", root)
        return
    text = read_text(pyproject_path)
    if REQUIRED_ADDOPTS not in text:
        _record_violation(
            violations,
            pyproject_path,
            "pytest_default_marker_expression_not_governed",
            root,
            REQUIRED_ADDOPTS,
        )
    for marker_name in REQUIRED_MARKERS:
        if f'"{marker_name}:' not in text:
            _record_violation(
                violations,
                pyproject_path,
                "missing_required_pytest_marker",
                root,
                marker_name,
            )


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the test-case construction governance audit."""
    root_path = Path(root)
    checked_paths: list[str] = []
    violations: list[dict[str, Any]] = []

    contract_path = root_path / "docs" / "test_case_constraints.md"
    checked_paths.append(str(contract_path))
    if not contract_path.exists():
        _record_violation(violations, contract_path, "missing_test_case_constraints_doc", root_path)

    for relative_dir in REQUIRED_TEST_DIRS:
        candidate = root_path / relative_dir
        checked_paths.append(str(candidate))
        if not candidate.exists():
            _record_violation(violations, candidate, "missing_required_test_directory", root_path)

    root_flat_tests = sorted((root_path / "tests").glob("test_*.py"))
    for test_path in root_flat_tests:
        checked_paths.append(str(test_path))
        _record_violation(violations, test_path, "root_level_test_file_forbidden", root_path)

    for helper_path in sorted((root_path / "tests" / "helpers").glob("test_*.py")):
        checked_paths.append(str(helper_path))
        _record_violation(violations, helper_path, "helper_file_must_not_start_with_test", root_path)

    for test_path in _iter_test_files(root_path, "tests/constraints"):
        checked_paths.append(str(test_path))
        text = read_text(test_path)
        if "pytest.mark.constraint" not in text:
            _record_violation(violations, test_path, "constraint_test_missing_constraint_marker", root_path)
        if _has_any_marker(text, ("integration", "smoke", "slow")):
            _record_violation(violations, test_path, "constraint_test_has_runtime_marker", root_path)

    for test_path in _iter_test_files(root_path, "tests/functional"):
        checked_paths.append(str(test_path))
        text = read_text(test_path)
        if not _has_any_marker(text, ("quick", "unit")):
            _record_violation(violations, test_path, "functional_test_missing_quick_or_unit_marker", root_path)
        if _has_any_marker(text, ("integration", "smoke", "slow", "formal")):
            _record_violation(violations, test_path, "functional_test_has_non_default_marker", root_path)

    for test_path in _iter_test_files(root_path, "tests/integration"):
        checked_paths.append(str(test_path))
        text = read_text(test_path)
        if "pytest.mark.integration" not in text:
            _record_violation(violations, test_path, "integration_test_missing_integration_marker", root_path)

    seen_test_names: dict[str, str] = {}
    for test_dir in ("tests/constraints", "tests/functional", "tests/integration"):
        for test_path in _iter_test_files(root_path, test_dir):
            for test_name in _find_test_function_names(test_path):
                previous_path = seen_test_names.get(test_name)
                if previous_path is not None:
                    _record_violation(
                        violations,
                        test_path,
                        "duplicate_test_function_name",
                        root_path,
                        f"{test_name} also in {previous_path}",
                    )
                    continue
                seen_test_names[test_name] = _relative(test_path, root_path)

    _audit_pyproject(root_path, violations, checked_paths)

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_test_case_constraints",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the test-case construction governance audit as a CLI."""
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    exit_with_report(run_audit(root))


if __name__ == "__main__":
    main(sys.argv)

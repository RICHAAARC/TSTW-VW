"""
文件用途：验证 main 运行时代码与外层 governance 层之间的边界。
File purpose: Validate runtime boundary layering between main code and outer governance layers.
Module type: General module
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = ROOT / "main"
FORBIDDEN_GOVERNANCE_SYMBOLS = {
    "skill_file_presence",
    "stage_progression_guard",
    "notebook_formal_output_bypass",
    "run_all_audits",
}
FORBIDDEN_OUTER_DIRECTORY_ROOT_NAMES = {
    "experiments",
    "paper_workflow",
    "audit_reports",
}
FORBIDDEN_OUTER_DIRECTORY_PATH_FRAGMENTS = (
    "experiments/",
    "paper_workflow/",
    "audit_reports/",
    "docs/builds/",
)


def _iter_main_python_files() -> list[Path]:
    return sorted(MAIN_ROOT.rglob("*.py"))


def _parse_python_file(file_path: Path) -> ast.AST:
    return ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))


def test_main_runtime_does_not_import_governance_layers() -> None:
    """Validate that `main/` does not import `tools` or `tests`.

    Args:
        None.

    Returns:
        None.
    """
    for file_path in _iter_main_python_files():
        tree = _parse_python_file(file_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
                assert all(
                    not name.startswith("tools") and not name.startswith("tests")
                    for name in imported_names
                ), file_path
            if isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                assert not module_name.startswith("tools"), file_path
                assert not module_name.startswith("tests"), file_path


def test_main_runtime_does_not_reference_outer_governance_symbols() -> None:
    """Validate that `main/` does not reference outer-governance audit symbols.

    Args:
        None.

    Returns:
        None.
    """
    for file_path in _iter_main_python_files():
        tree = _parse_python_file(file_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id not in FORBIDDEN_GOVERNANCE_SYMBOLS, file_path
            if isinstance(node, ast.Attribute):
                assert node.attr not in FORBIDDEN_GOVERNANCE_SYMBOLS, file_path


def test_main_runtime_does_not_embed_outer_directory_roots() -> None:
    """Validate that `main/` does not hard-code outer directory roots.

    Args:
        None.

    Returns:
        None.
    """
    for file_path in _iter_main_python_files():
        tree = _parse_python_file(file_path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            constant_value = node.value
            assert constant_value not in FORBIDDEN_OUTER_DIRECTORY_ROOT_NAMES, file_path
            assert all(
                fragment not in constant_value
                for fragment in FORBIDDEN_OUTER_DIRECTORY_PATH_FRAGMENTS
            ), file_path
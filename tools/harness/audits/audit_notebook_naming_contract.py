"""
文件用途：执行 notebook 命名与 helper 归属契约审计。
File purpose: Audit governed notebook naming and notebook-helper placement under paper_workflow.
Module type: General module
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.json_report import build_report, exit_with_report


NOTEBOOK_FILE_PATTERN = re.compile(r"^Stage[0-9]+(?:_[A-Z][A-Za-z0-9]*)+\.ipynb$")
NOTEBOOK_UTIL_FILE_PATTERN = re.compile(r"^stage[0-9]+(?:_[a-z0-9]+)+\.py$")
COLAB_UTIL_FILE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.py$")
FORBIDDEN_NOTEBOOK_NAME_PATTERNS = (
    re.compile(r"_Colab\.ipynb$"),
    re.compile(r"_Notebook\.ipynb$"),
    re.compile(r"^Run_"),
)
REQUIRED_PATHS = {
    "stage_two_notebook_entrypoint": "paper_workflow/Stage2_Real_Video_VAE_Latent_Probe.ipynb",
    "paper_workflow_notebook_utils": "paper_workflow/notebook_utils",
    "stage_two_notebook_drive_packager": (
        "paper_workflow/notebook_utils/stage2_real_video_vae_latent_probe_drive_packager.py"
    ),
    "stage_two_notebook_result_checker": (
        "paper_workflow/notebook_utils/stage2_real_video_vae_latent_probe_result_checker.py"
    ),
}
FORBIDDEN_PATHS = {
    "legacy_stage_two_notebook_entrypoint": "paper_workflow/Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb",
    "legacy_stage_two_drive_packager_wrapper": "paper_workflow/colab_utils/drive_packager.py",
    "legacy_stage_two_notebook_result_checker_wrapper": "paper_workflow/colab_utils/notebook_result_checker.py",
}


def _check_required_and_forbidden_paths(
    root_path: Path,
    violations: list[dict[str, Any]],
    checked_paths: list[str],
) -> None:
    for requirement_name, relative_path in REQUIRED_PATHS.items():
        candidate = root_path / relative_path
        checked_paths.append(str(candidate))
        if candidate.exists():
            continue
        violations.append(
            {
                "path": str(candidate),
                "reason": "missing_required_notebook_naming_path",
                "requirement": requirement_name,
            }
        )

    for requirement_name, relative_path in FORBIDDEN_PATHS.items():
        candidate = root_path / relative_path
        checked_paths.append(str(candidate))
        if not candidate.exists():
            continue
        violations.append(
            {
                "path": str(candidate),
                "reason": "forbidden_legacy_notebook_naming_path_present",
                "requirement": requirement_name,
            }
        )


def _scan_root_notebooks(
    paper_workflow_root: Path,
    violations: list[dict[str, Any]],
    checked_paths: list[str],
) -> None:
    for notebook_path in sorted(paper_workflow_root.glob("*.ipynb")):
        checked_paths.append(str(notebook_path))
        if NOTEBOOK_FILE_PATTERN.fullmatch(notebook_path.name) is None:
            violations.append(
                {
                    "path": str(notebook_path),
                    "reason": "notebook_file_name_not_stage_purpose_pascal_case",
                    "value": notebook_path.name,
                }
            )
        if any(pattern.search(notebook_path.name) for pattern in FORBIDDEN_NOTEBOOK_NAME_PATTERNS):
            violations.append(
                {
                    "path": str(notebook_path),
                    "reason": "notebook_file_name_uses_forbidden_legacy_suffix",
                    "value": notebook_path.name,
                }
            )


def _scan_notebook_utils(
    notebook_utils_root: Path,
    violations: list[dict[str, Any]],
    checked_paths: list[str],
) -> None:
    if not notebook_utils_root.exists():
        return
    for path in sorted(notebook_utils_root.iterdir()):
        checked_paths.append(str(path))
        if path.is_dir():
            if path.name == "__pycache__":
                continue
            violations.append(
                {
                    "path": str(path),
                    "reason": "notebook_utils_must_not_contain_nested_directories",
                }
            )
            continue
        if path.name == "__init__.py":
            continue
        if path.suffix != ".py" or NOTEBOOK_UTIL_FILE_PATTERN.fullmatch(path.name) is None:
            violations.append(
                {
                    "path": str(path),
                    "reason": "notebook_utils_file_name_not_stage_purpose_snake_case",
                    "value": path.name,
                }
            )


def _scan_colab_utils(
    colab_utils_root: Path,
    violations: list[dict[str, Any]],
    checked_paths: list[str],
) -> None:
    if not colab_utils_root.exists():
        return
    for path in sorted(colab_utils_root.iterdir()):
        checked_paths.append(str(path))
        if path.is_dir():
            if path.name == "__pycache__":
                continue
            violations.append(
                {
                    "path": str(path),
                    "reason": "colab_utils_must_not_contain_nested_directories",
                }
            )
            continue
        if path.name == "__init__.py":
            continue
        if path.suffix != ".py" or COLAB_UTIL_FILE_PATTERN.fullmatch(path.name) is None:
            violations.append(
                {
                    "path": str(path),
                    "reason": "colab_utils_file_name_not_generic_snake_case",
                    "value": path.name,
                }
            )


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the notebook naming and placement audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized audit report for governed notebook naming and placement.
    """
    root_path = Path(root)
    paper_workflow_root = root_path / "paper_workflow"
    notebook_utils_root = paper_workflow_root / "notebook_utils"
    colab_utils_root = paper_workflow_root / "colab_utils"

    checked_paths: list[str] = []
    violations: list[dict[str, Any]] = []

    _check_required_and_forbidden_paths(root_path, violations, checked_paths)
    if paper_workflow_root.exists():
        checked_paths.append(str(paper_workflow_root))
        _scan_root_notebooks(paper_workflow_root, violations, checked_paths)
    _scan_notebook_utils(notebook_utils_root, violations, checked_paths)
    _scan_colab_utils(colab_utils_root, violations, checked_paths)

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_notebook_naming_contract",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the notebook naming contract audit as a CLI.

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
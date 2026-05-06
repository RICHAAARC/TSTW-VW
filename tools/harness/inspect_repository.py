"""
文件用途：提供仓库 intake 检查与空仓库分类能力。
File purpose: Provide repository intake inspection and empty bootstrap classification.
Module type: General module
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_DIRECTORIES = [
    "configs",
    "docs",
    "tools",
    "tests",
    "main",
    "paper_workflow",
    "outputs",
]


def inspect_repository(root: str | Path) -> dict[str, Any]:
    """Inspect repository structure and classify bootstrap status.

    Args:
        root: Repository root path.

    Returns:
        A structure summary with repository mode and governed directory status.
    """
    root_path = Path(root)
    directory_status: dict[str, dict[str, Any]] = {}
    present_count = 0
    for directory_name in EXPECTED_DIRECTORIES:
        directory_path = root_path / directory_name
        exists = directory_path.exists()
        if exists:
            present_count += 1
        directory_status[directory_name] = {
            "exists": exists,
            "path": str(directory_path),
        }

    project_stage = None
    contract_path = root_path / "configs" / "project" / "project_contract.json"
    if contract_path.exists():
        try:
            project_stage = json.loads(contract_path.read_text(encoding="utf-8")).get(
                "project_stage"
            )
        except json.JSONDecodeError:
            project_stage = "unreadable"

    repository_mode = (
        "empty_repository_bootstrap" if present_count == 0 else "governed_repository"
    )
    return {
        "repository_mode": repository_mode,
        "directory_status": directory_status,
        "project_stage": project_stage,
    }


def main(argv: list[str] | None = None) -> None:
    """Run the repository intake inspector as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    print(json.dumps(inspect_repository(root), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)

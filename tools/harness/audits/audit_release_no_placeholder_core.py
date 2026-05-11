"""
文件用途：审计 main 与顶层 configs 不得保留 placeholder 或 random core 资产。
File purpose: Audit that main and top-level configs do not retain placeholder or random core assets.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.file_scanner import iter_text_files
from tools.harness.lib.json_report import build_report, exit_with_report


def _is_top_level_config(candidate: Path, root_path: Path) -> bool:
    try:
        relative_parts = candidate.relative_to(root_path).parts
    except ValueError:
        return False
    return len(relative_parts) >= 3 and relative_parts[0] == "configs"


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the placeholder-core audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized audit report.
    """
    root_path = Path(root)
    violations: list[dict[str, Any]] = []
    checked_paths: list[str] = []

    main_root = root_path / "main"
    if main_root.exists():
        for file_path in iter_text_files(main_root):
            checked_paths.append(str(file_path))
            lowered_name = file_path.name.lower()
            if "placeholder" in lowered_name or "random" in lowered_name:
                violations.append(
                    {
                        "path": str(file_path),
                        "reason": "placeholder_or_random_file_must_not_remain_in_main",
                    }
                )

    configs_root = root_path / "configs"
    if configs_root.exists():
        for file_path in iter_text_files(configs_root):
            if not _is_top_level_config(file_path, root_path):
                continue
            checked_paths.append(str(file_path))
            lowered_name = file_path.name.lower()
            if "placeholder" in lowered_name or "random" in lowered_name:
                violations.append(
                    {
                        "path": str(file_path),
                        "reason": "placeholder_or_random_config_must_move_to_experiments",
                    }
                )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_release_no_placeholder_core",
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
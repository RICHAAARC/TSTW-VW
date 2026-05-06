"""
文件用途：执行正式命名治理审计。
File purpose: Audit governed naming conventions for the protocol_skeleton stage.
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

from tools.harness.lib.file_scanner import (
    BINARY_SUFFIXES,
    iter_text_files,
    read_text,
    should_skip_path,
)
from tools.harness.lib.json_report import build_report, exit_with_report
from tools.harness.lib.naming_rules import (
    contains_encoded_or_escaped_name_fragment,
    find_forbidden_method_variant,
    has_forbidden_stage_suffix,
    is_allowed_formal_directory_name,
    is_allowed_formal_file_name,
    is_snake_case_name,
)


PROJECT_STAGE_PATTERN = re.compile(
    r"(?im)['\"]?project_stage['\"]?\s*:\s*['\"]?(stage_0|stage_1)['\"]?"
)
CONFIG_KEY_PATTERN = re.compile(r"['\"]?([A-Za-z][A-Za-z0-9_]*)['\"]?\s*:")
STALE_YAML_CONFIG_REFERENCE_PARTS = (
    ("configs/project/", "project_contract", ".yaml"),
    ("configs/protocol/", "protocol_skeleton", ".yaml"),
    ("configs/method/", "method_placeholder", ".yaml"),
    ("configs/ablation/", "ablation_placeholder", ".yaml"),
)


def _check_path_name_rules(path: Path, violations: list[dict[str, Any]]) -> None:
    """Apply governed file and directory naming checks.

    Args:
        path: Candidate repository path.
        violations: Mutable violation list.

    Returns:
        None.
    """
    if contains_encoded_or_escaped_name_fragment(path.name):
        violations.append(
            {
                "path": str(path),
                "reason": "encoded_or_escaped_file_name_not_allowed",
            }
        )
        return

    if path.is_dir():
        if not is_allowed_formal_directory_name(path.name):
            violations.append(
                {
                    "path": str(path),
                    "reason": "directory_name_not_snake_case",
                    "value": path.name,
                }
            )
        return

    if path.suffix.lower() in {".yaml", ".yml"} and "configs" in path.parts:
        violations.append(
            {
                "path": str(path),
                "reason": "formal_config_must_use_json_suffix",
            }
        )
        return

    if not is_allowed_formal_file_name(path.name):
        violations.append(
            {
                "path": str(path),
                "reason": "file_name_not_allowed_by_governance",
                "value": path.name,
            }
        )
        return

    if has_forbidden_stage_suffix(path.name):
        violations.append(
            {
                "path": str(path),
                "reason": "file_name_uses_forbidden_version_like_suffix",
            }
        )


def _scan_for_stale_yaml_references(
    file_path: Path,
    text: str,
    violations: list[dict[str, Any]],
) -> None:
    """Find stale formal `.yaml` config references in governed text files.

    Args:
        file_path: Candidate text file path.
        text: File content.
        violations: Mutable violation list.

    Returns:
        None.
    """
    for prefix, stem, suffix in STALE_YAML_CONFIG_REFERENCE_PARTS:
        stale_reference = prefix + stem + suffix
        if stale_reference in text:
            violations.append(
                {
                    "path": str(file_path),
                    "reason": "stale_yaml_config_reference",
                    "value": stale_reference,
                }
            )


def _iter_governed_config_files(root: Path) -> list[Path]:
    """Collect governed configuration files for naming inspection.

    Args:
        root: Repository root path.

    Returns:
        A list of configuration files under `configs/`.
    """
    config_root = root / "configs"
    return list(iter_text_files(config_root)) if config_root.exists() else []


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the naming governance audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized naming audit report.
    """
    root_path = Path(root)
    violations: list[dict[str, Any]] = []
    checked_paths: list[str] = []

    governed_files = [
        root_path / "AGENTS.md",
        root_path / "README.md",
        root_path / ".gitignore",
        root_path / "pyproject.toml",
    ]
    governed_directories = [
        root_path / ".codex",
        root_path / "configs",
        root_path / "docs",
        root_path / "tools",
        root_path / "tests",
    ]

    for governed_file in governed_files:
        if not governed_file.exists() or should_skip_path(governed_file):
            continue
        checked_paths.append(str(governed_file))
        _check_path_name_rules(governed_file, violations)
        _scan_for_stale_yaml_references(
            governed_file,
            read_text(governed_file),
            violations,
        )

    for governed_directory in governed_directories:
        if not governed_directory.exists():
            continue

        if not should_skip_path(governed_directory):
            _check_path_name_rules(governed_directory, violations)

        for path in governed_directory.rglob("*"):
            if should_skip_path(path):
                continue
            _check_path_name_rules(path, violations)
            if path.is_file():
                checked_paths.append(str(path))
                if path.suffix.lower() not in BINARY_SUFFIXES:
                    _scan_for_stale_yaml_references(
                        path,
                        read_text(path),
                        violations,
                    )

    for config_file in _iter_governed_config_files(root_path):
        text = read_text(config_file)
        for variant in find_forbidden_method_variant(text):
            violations.append(
                {
                    "path": str(config_file),
                    "reason": "forbidden_method_variant",
                    "value": variant,
                }
            )

        for match in PROJECT_STAGE_PATTERN.finditer(text):
            violations.append(
                {
                    "path": str(config_file),
                    "reason": "forbidden_project_stage_name",
                    "value": match.group(1),
                }
            )

        for key_name in CONFIG_KEY_PATTERN.findall(text):
            if not is_snake_case_name(key_name):
                violations.append(
                    {
                        "path": str(config_file),
                        "reason": "config_key_not_snake_case",
                        "value": key_name,
                    }
                )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_naming_conventions",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the naming governance audit as a CLI.

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

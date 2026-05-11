"""
文件用途：执行正式命名治理审计。File purpose: Audit governed naming conventions for the protocol_skeleton stage.
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
    find_forbidden_weak_stage_names,
    find_forbidden_method_variant,
    find_forbidden_version_like_names,
    has_forbidden_stage_suffix,
    is_allowed_formal_directory_name,
    is_allowed_formal_file_name,
    is_snake_case_name,
    validate_path_name_semantics,
)


PROJECT_STAGE_PATTERN = re.compile(
    r"(?im)['\"]?project_stage['\"]?\s*:\s*['\"]?(stage[0-9]+(?:[_-]?[0-9]+)?|stage_[0-9]+|stage-[0-9]+|protocol_skeleton|synthetic_tubelet_sync_probe|real_video_vae_latent_probe)['\"]?"
)
WEAK_PROJECT_STAGE_PATTERN = re.compile(
    r"(?im)['\"]?project_stage['\"]?\s*:\s*['\"]?(stage[0-9]+|stage_[0-9]+|stage-[0-9]+)['\"]?"
)
CONFIG_KEY_PATTERN = re.compile(r"['\"]?([A-Za-z][A-Za-z0-9_]*)['\"]?\s*:")
GOVERNED_TEXT_ROOTS = [
    "AGENTS.md",
    "README.md",
    ".codex",
    "configs",
    "docs",
    "main",
    "tests",
    "tools",
]


def _suggest_replacement(value: str) -> str | None:
    lowered = value.lower()
    if re.search(r"stage[_-]?2\b|stage2|stage-2|stage_2", lowered):
        return "real_video_vae_latent_probe"
    if re.search(r"stage[_-]?1\b|stage1|stage-1|stage_1", lowered):
        return "synthetic_tubelet_sync_probe"
    if re.search(r"stage[_-]?0\b|stage0|stage-0|stage_0", lowered):
        return "protocol_skeleton"
    if re.search(r"_v[0-9]+\b|_p[0-9]+\b", lowered):
        return "use semantic mechanism name"
    return None


def _line_number_for_value(text: str, value: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if value in line:
            return index
    return None


def _scan_text_weak_names(file_path: Path, text: str, violations: list[dict[str, Any]]) -> None:
    def _is_allowed_reference_line(line_number: int | None) -> bool:
        if line_number is None:
            return False
        line_text = text.splitlines()[line_number - 1].lower()
        normalized_path = str(file_path).replace('\\', '/')
        allow_tokens = (
            'forbidden',
            'blocked',
            'reject',
            'allow',
            'weak naming',
            'forbidden_weak_name_patterns',
            '禁止',
            '阻断',
            '示例',
            'assert',
        )
        if any(token in line_text for token in allow_tokens):
            return True
        if normalized_path.startswith(str(ROOT / 'tests').replace('\\', '/')):
            return True
        if normalized_path.endswith('configs/project/project_contract.json'):
            return True
        if normalized_path.endswith('tools/harness/audits/audit_naming_conventions.py'):
            return True
        if normalized_path.endswith('tools/harness/lib/naming_rules.py'):
            return True
        return False

    for value in find_forbidden_weak_stage_names(text):
        line_number = _line_number_for_value(text, value)
        if _is_allowed_reference_line(line_number):
            continue
        violations.append(
            {
                "path": str(file_path),
                "line": line_number,
                "reason": "forbidden_weak_stage_name_in_text",
                "value": value,
                "suggested_replacement": _suggest_replacement(value),
            }
        )
    for value in find_forbidden_version_like_names(text):
        line_number = _line_number_for_value(text, value)
        if _is_allowed_reference_line(line_number):
            continue
        violations.append(
            {
                "path": str(file_path),
                "line": line_number,
                "reason": "forbidden_version_like_name_in_text",
                "value": value,
                "suggested_replacement": _suggest_replacement(value),
            }
        )
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

    violations.extend(validate_path_name_semantics(path))

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

    for relative_root in GOVERNED_TEXT_ROOTS:
        candidate = root_path / relative_root
        if not candidate.exists():
            continue
        if candidate.is_file():
            if should_skip_path(candidate):
                continue
            checked_paths.append(str(candidate))
            _check_path_name_rules(candidate, violations)
            text = read_text(candidate)
            _scan_for_stale_yaml_references(candidate, text, violations)
            _scan_text_weak_names(candidate, text, violations)
            continue
        if should_skip_path(candidate):
            continue
        _check_path_name_rules(candidate, violations)
        for path in candidate.rglob("*"):
            if should_skip_path(path):
                continue
            _check_path_name_rules(path, violations)
            if not path.is_file():
                continue
            checked_paths.append(str(path))
            if path.suffix.lower() in BINARY_SUFFIXES:
                continue
            text = read_text(path)
            _scan_for_stale_yaml_references(path, text, violations)
            _scan_text_weak_names(path, text, violations)

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

        for match in WEAK_PROJECT_STAGE_PATTERN.finditer(text):
            stage_value = match.group(1)
            violations.append(
                {
                    "path": str(config_file),
                    "reason": "forbidden_project_stage_name",
                    "value": stage_value,
                }
            )
        
        for match in PROJECT_STAGE_PATTERN.finditer(text):
            stage_value = match.group(1)
            normalized_path = str(config_file).replace('\\', '/')
            if stage_value == 'protocol_skeleton' and '/configs/project/' not in normalized_path:
                continue
            if stage_value not in {'protocol_skeleton', 'synthetic_tubelet_sync_probe', 'real_video_vae_latent_probe'}:
                continue
            if stage_value == 'protocol_skeleton':
                violations.append(
                    {
                        "path": str(config_file),
                        "reason": "forbidden_project_stage_name",
                        "value": stage_value,
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

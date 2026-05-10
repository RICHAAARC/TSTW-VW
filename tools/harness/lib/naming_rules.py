"""
File purpose: Provide reusable naming governance rules for harness audits and tests.
Module type: General module
"""

from __future__ import annotations

import re
from pathlib import Path


FORBIDDEN_WEAK_NAME_PATTERNS = (
    r"\bstage[0-9]+\b",
    r"\bstage_[0-9]+\b",
    r"\bstage-[0-9]+\b",
    r"\btest_stage[0-9]+_[a-z0-9_]*\b",
    r"\brun_stage[0-9]+_[a-z0-9_]*\b",
    r"\b_v[0-9]+\b",
    r"\b_p[0-9]+\b",
)
FORBIDDEN_METHOD_VARIANTS = (
    "full",
    "default",
    "new",
    "old",
    "best",
    "final_method",
)

SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ENCODED_NAME_PATTERN = re.compile(r"(#U|%[0-9A-Fa-f]{2}|\\u[0-9A-Fa-f]{4})")
FORBIDDEN_METHOD_VARIANT_PATTERN = re.compile(
    r"(?im)(?<![\w])['\"]?method_variant['\"]?\s*[:=]\s*['\"]?(full|default|new|old|best|final_method)['\"]?"
)
VERSION_LIKE_NAME_PATTERN = re.compile(
    r"\b[a-z0-9]+(?:_[a-z0-9]+)*(?:_v[0-9]+|_p[0-9]+)\b",
    re.IGNORECASE,
)
TECHNICAL_VERSION_CONTEXT_PATTERN = re.compile(
    r"(python\s*[0-9]+\.[0-9]+|cuda\s*[0-9]+\.[0-9]+|diffusers==[0-9]+\.[0-9]+\.[0-9]+)",
    re.IGNORECASE,
)
FORBIDDEN_PATH_SEGMENTS = {
    "stage2_runner",
    "stage2_paths",
    "stage2_artifacts",
    "test_stage1_records_schema",
    "test_stage2_records_schema",
    "run_stage1_profile",
}
WEAK_STAGE_PATTERN = re.compile("|".join(FORBIDDEN_WEAK_NAME_PATTERNS), re.IGNORECASE)

ALLOWED_LITERAL_FILE_NAMES = {
    "README.md",
    "AGENTS.md",
    ".gitignore",
    "pyproject.toml",
    "__init__.py",
}
ALLOWED_FILE_SUFFIXES = {".md", ".py", ".json", ".toml"}
ALLOWED_DIRECTORY_EXCEPTIONS = {".codex", ".git", ".pytest_cache", "__pycache__"}


def is_snake_case_name(name: str) -> bool:
    return bool(SNAKE_CASE_PATTERN.fullmatch(name))


def has_forbidden_stage_suffix(name: str) -> bool:
    stem = name.rsplit(".", 1)[0]
    return bool(re.search(r"(?:_v[0-9]+|_p[0-9]+)$", stem, flags=re.IGNORECASE))


def find_forbidden_weak_stage_names(text: str) -> list[str]:
    return [match.group(0) for match in WEAK_STAGE_PATTERN.finditer(text)]


def find_forbidden_method_variant(text: str) -> list[str]:
    return [match.group(1) for match in FORBIDDEN_METHOD_VARIANT_PATTERN.finditer(text)]


def find_forbidden_version_like_names(text: str) -> list[str]:
    values: list[str] = []
    for match in VERSION_LIKE_NAME_PATTERN.finditer(text):
        value = match.group(0)
        if is_allowed_technical_version_context(value, text):
            continue
        values.append(value)
    return values


def is_allowed_technical_version_context(value: str, surrounding_text: str) -> bool:
    lowered_value = value.lower()
    if lowered_value in {"schema_version", "compatibility_version", "legacy_stage_id"}:
        return True
    return bool(TECHNICAL_VERSION_CONTEXT_PATTERN.search(surrounding_text))


def validate_path_name_semantics(path: Path) -> list[dict]:
    violations: list[dict] = []
    normalized = path.as_posix().lower()
    if "docs/builds/" in normalized or normalized.endswith("docs/builds"):
        return violations
    stem = path.stem.lower()
    if stem in FORBIDDEN_PATH_SEGMENTS:
        violations.append(
            {
                "path": str(path),
                "reason": "path_uses_forbidden_weak_stage_name",
                "value": stem,
            }
        )
    for part in path.parts:
        lowered = str(part).lower()
        if WEAK_STAGE_PATTERN.search(lowered):
            violations.append(
                {
                    "path": str(path),
                    "reason": "path_contains_weak_stage_token",
                    "value": part,
                }
            )
    return violations


def contains_encoded_or_escaped_name_fragment(name: str) -> bool:
    return bool(ENCODED_NAME_PATTERN.search(name))


def is_allowed_formal_directory_name(name: str) -> bool:
    return name in ALLOWED_DIRECTORY_EXCEPTIONS or is_snake_case_name(name)


def is_allowed_formal_file_name(name: str) -> bool:
    if name in ALLOWED_LITERAL_FILE_NAMES:
        return True
    if name.endswith(".skill.md"):
        return is_snake_case_name(name[: -len(".skill.md")])
    candidate = Path(name)
    if candidate.suffix not in ALLOWED_FILE_SUFFIXES:
        return False
    return is_snake_case_name(candidate.stem)

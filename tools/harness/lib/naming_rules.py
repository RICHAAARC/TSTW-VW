"""
文件用途：提供命名治理的规则函数。
File purpose: Provide reusable naming governance rules for harness audits and tests.
Module type: General module
"""

from __future__ import annotations

import re
from pathlib import Path


FORBIDDEN_STAGE_SUFFIXES = ("_v1", "_v2", "_p0", "_p1")
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
    r"\b[a-z0-9]+(?:_[a-z0-9]+)*(?:_v[12]|_p[01])\b",
    re.IGNORECASE,
)

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
    """Check whether a name follows the repository snake_case convention.

    Args:
        name: Candidate identifier.

    Returns:
        True when the name matches the governed snake_case pattern.
    """
    return bool(SNAKE_CASE_PATTERN.fullmatch(name))


def has_forbidden_stage_suffix(name: str) -> bool:
    """Check whether a name ends with a blocked version-like stage suffix.

    Args:
        name: Candidate file name, directory name, or identifier.

    Returns:
        True when the name ends with a blocked suffix.
    """
    stem = name.rsplit(".", 1)[0]
    return any(stem.endswith(suffix) for suffix in FORBIDDEN_STAGE_SUFFIXES)


def find_forbidden_method_variant(text: str) -> list[str]:
    """Find forbidden formal `method_variant` values inside text.

    Args:
        text: Candidate text from a governed configuration surface.

    Returns:
        A list of forbidden variant values discovered in the text.
    """
    return [match.group(1) for match in FORBIDDEN_METHOD_VARIANT_PATTERN.finditer(text)]


def find_forbidden_version_like_names(text: str) -> list[str]:
    """Find version-like names that violate semantic naming governance.

    Args:
        text: Candidate text to inspect.

    Returns:
        A list of version-like names that match blocked suffix patterns.
    """
    return [match.group(0) for match in VERSION_LIKE_NAME_PATTERN.finditer(text)]


def contains_encoded_or_escaped_name_fragment(name: str) -> bool:
    """Check whether a name contains encoded or escaped fragments.

    Args:
        name: Candidate file or directory name.

    Returns:
        True when the name contains `#U`, percent-encoding, or escaped Unicode.
    """
    return bool(ENCODED_NAME_PATTERN.search(name))


def is_allowed_formal_directory_name(name: str) -> bool:
    """Check whether a governed directory name is allowed.

    Args:
        name: Candidate directory name.

    Returns:
        True when the directory name is snake_case or an approved exception.
    """
    return name in ALLOWED_DIRECTORY_EXCEPTIONS or is_snake_case_name(name)


def is_allowed_formal_file_name(name: str) -> bool:
    """Check whether a governed file name is allowed.

    Args:
        name: Candidate file name.

    Returns:
        True when the file name follows the governed literal or snake_case rules.
    """
    if name in ALLOWED_LITERAL_FILE_NAMES:
        return True

    if name.endswith(".skill.md"):
        return is_snake_case_name(name[: -len(".skill.md")])

    candidate = Path(name)
    if candidate.suffix not in ALLOWED_FILE_SUFFIXES:
        return False
    return is_snake_case_name(candidate.stem)

"""
文件用途：提供仓库文本文件扫描与跳过规则。
File purpose: Provide repository text scanning helpers and skip policies for harness audits.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator


SKIP_DIRECTORY_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "outputs",
    "dist",
    "build",
    "audit_reports",
}

BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".pyc",
    ".pyd",
}


def _is_docs_builds_path(candidate: Path) -> bool:
    """Check whether a path belongs to the excluded `docs/builds` subtree.

    Args:
        candidate: File or directory path to evaluate.

    Returns:
        True when the path is `docs/builds` or any descendant beneath it.
    """
    normalized = candidate.as_posix()
    return (
        normalized == "docs/builds"
        or normalized.startswith("docs/builds/")
        or normalized.endswith("/docs/builds")
        or "/docs/builds/" in normalized
    )


def should_skip_path(path: str | Path) -> bool:
    """Determine whether a path should be skipped by harness scanners.

    Args:
        path: File or directory path to evaluate.

    Returns:
        True when the path belongs to a skipped runtime or cache location.
    """
    candidate = Path(path)
    if any(part in SKIP_DIRECTORY_NAMES for part in candidate.parts):
        return True
    return _is_docs_builds_path(candidate)


def iter_text_files(root: str | Path) -> Iterator[Path]:
    """Iterate over text-like files beneath a repository root.

    Args:
        root: Repository root or subdirectory root.

    Returns:
        An iterator of candidate text file paths.
    """
    root_path = Path(root)
    if not root_path.exists():
        return

    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if should_skip_path(path):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        yield path


def read_text(path: str | Path) -> str:
    """Read a text file using a tolerant UTF-8 decoding policy.

    Args:
        path: Target file path.

    Returns:
        Decoded file content.
    """
    file_path = Path(path)
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="utf-8", errors="ignore")

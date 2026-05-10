"""
File purpose: Provide digest helpers used by governed protocol runtime flows.
Module type: General module
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def compute_sha256_text(text: str) -> str:
    """Compute a SHA-256 digest for UTF-8 text content.

    Args:
        text: Input text payload.

    Returns:
        The hexadecimal SHA-256 digest.

    Raises:
        TypeError: If text is not a string.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_object_digest(payload: Any) -> str:
    """Compute a stable digest for a JSON-serializable object.

    Args:
        payload: JSON-serializable Python object.

    Returns:
        The hexadecimal SHA-256 digest.
    """
    normalized_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return compute_sha256_text(normalized_payload)


def compute_file_digest(path: str | Path) -> str:
    """Compute a SHA-256 digest for a file.

    Args:
        path: Target file path.

    Returns:
        The hexadecimal SHA-256 digest.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"file does not exist: {file_path}")
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def compute_path_collection_digest(paths: Iterable[str | Path]) -> str:
    """Compute a stable digest for a collection of file paths.

    Args:
        paths: Iterable of file paths.

    Returns:
        The hexadecimal SHA-256 digest of the file-digest sequence.

    Raises:
        ValueError: If paths is empty.
    """
    normalized_paths = [str(Path(path)) for path in paths]
    if not normalized_paths:
        raise ValueError("paths must contain at least one file path")
    file_digests = [compute_file_digest(path) for path in sorted(normalized_paths)]
    return compute_object_digest(file_digests)

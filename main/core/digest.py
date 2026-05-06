"""
文件用途：提供阶段 0 协议骨架所需的 digest 计算工具。
File purpose: Provide digest helpers for the stage-0 protocol skeleton.
Module type: General module
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def compute_sha256_text(text: str) -> str:
    """功能：计算 UTF-8 文本的 SHA-256 摘要。

    Compute a SHA-256 digest for UTF-8 text content.

    Args:
        text: Input text payload.

    Returns:
        The hexadecimal SHA-256 digest.
    """
    if not isinstance(text, str):
        # 中文注释：digest 输入必须是字符串，避免隐式编码差异。
        raise TypeError("text must be a string")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_object_digest(payload: Any) -> str:
    """功能：计算可 JSON 序列化对象的稳定摘要。

    Compute a stable digest for a JSON-serializable object.

    Args:
        payload: JSON-serializable Python object.

    Returns:
        The hexadecimal SHA-256 digest.
    """
    normalized_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return compute_sha256_text(normalized_payload)


def compute_file_digest(path: str | Path) -> str:
    """功能：计算文件内容摘要。

    Compute a SHA-256 digest for a file.

    Args:
        path: Target file path.

    Returns:
        The hexadecimal SHA-256 digest.
    """
    file_path = Path(path)
    if not file_path.exists():
        # 中文注释：文件必须存在，才能形成可追溯的产物摘要。
        raise FileNotFoundError(f"file does not exist: {file_path}")
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def compute_path_collection_digest(paths: Iterable[str | Path]) -> str:
    """功能：计算文件路径集合的组合摘要。

    Compute a stable digest for a collection of file paths.

    Args:
        paths: Iterable of file paths.

    Returns:
        The hexadecimal SHA-256 digest of the file-digest sequence.
    """
    normalized_paths = [str(Path(path)) for path in paths]
    if not normalized_paths:
        # 中文注释：组合摘要至少需要一个文件，否则无法代表具体产物集合。
        raise ValueError("paths must contain at least one file path")
    file_digests = [compute_file_digest(path) for path in sorted(normalized_paths)]
    return compute_object_digest(file_digests)
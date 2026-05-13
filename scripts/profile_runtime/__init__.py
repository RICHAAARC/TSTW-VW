"""
文件用途：提供 runtime profiling 脚本的共享路径与写盘 helper。
File purpose: Provide shared path and persistence helpers for runtime profiling scripts.
Module type: General module
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_PROFILE_DIRNAME = "runtime_profile"


def ensure_runtime_profile_dir(run_root: str | Path) -> Path:
    """功能：确保 run_root 下的 runtime_profile 目录存在。

    Ensure that the runtime_profile directory exists under the provided run root.

    Args:
        run_root: Run-root path.

    Returns:
        The runtime_profile directory path.
    """
    runtime_profile_dir = Path(run_root) / RUNTIME_PROFILE_DIRNAME
    runtime_profile_dir.mkdir(parents=True, exist_ok=True)
    return runtime_profile_dir


def iso_timestamp_utc() -> str:
    """功能：生成 ISO-8601 UTC 时间戳。

    Generate an ISO-8601 timestamp in UTC.

    Args:
        None.

    Returns:
        The normalized UTC timestamp string.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json_file(path: str | Path, payload: dict[str, Any]) -> Path:
    """功能：以 UTF-8 编码写出 JSON 文件。

    Write a JSON file using UTF-8 encoding.

    Args:
        path: Output JSON path.
        payload: JSON payload.

    Returns:
        The resolved output path.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_markdown_file(path: str | Path, text: str) -> Path:
    """功能：以 UTF-8 编码写出 Markdown 文件。

    Write a Markdown file using UTF-8 encoding.

    Args:
        path: Output Markdown path.
        text: Markdown body.

    Returns:
        The resolved output path.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_text = text if text.endswith("\n") else text + "\n"
    output_path.write_text(normalized_text, encoding="utf-8")
    return output_path


def read_json_file(path: str | Path) -> dict[str, Any]:
    """功能：读取 JSON 文件。

    Read a JSON file from disk.

    Args:
        path: Input JSON path.

    Returns:
        The parsed JSON object.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))

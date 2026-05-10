"""
文件用途：提供阶段 2 本地数据集根目录与配置定位工具。
File purpose: Provide local dataset-root and runtime-config localization helpers for stage-two runtime.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_runtime_dataset_config(runtime_config_path: str | Path) -> dict[str, Any]:
    """功能：加载 notebook 生成的 runtime config。

    Load notebook-generated runtime configuration payload.

    Args:
        runtime_config_path: Runtime config JSON path.

    Returns:
        Parsed runtime config payload.
    """
    config_path = Path(runtime_config_path)
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime config must be a JSON object")
    return payload


def resolve_local_dataset_root(runtime_config: dict[str, Any]) -> Path:
    """功能：解析并校验本地数据集根目录。

    Resolve and validate local dataset root from runtime config.

    Args:
        runtime_config: Parsed runtime config payload.

    Returns:
        A resolved dataset-root path.
    """
    if not isinstance(runtime_config, dict):
        raise TypeError("runtime_config must be a dictionary")
    dataset_root_text = str(runtime_config.get("local_dataset_root", "")).strip()
    if not dataset_root_text:
        raise KeyError("local_dataset_root is required in runtime config")
    dataset_root = Path(dataset_root_text)
    if not dataset_root.exists():
        raise FileNotFoundError(dataset_root)
    return dataset_root


def resolve_runtime_dataset_manifest_path(runtime_config: dict[str, Any]) -> Path:
    """功能：解析 runtime 配置中的数据集 manifest 路径。

    Resolve dataset manifest path from runtime configuration.

    Args:
        runtime_config: Parsed runtime config payload.

    Returns:
        A resolved manifest path.
    """
    dataset_root = resolve_local_dataset_root(runtime_config)
    manifest_path_text = str(runtime_config.get("dataset_manifest_path", "")).strip()
    if manifest_path_text:
        manifest_path = Path(manifest_path_text)
    else:
        manifest_path = dataset_root / "dataset_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    return manifest_path

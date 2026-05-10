"""
文件用途：提供阶段 2 VAE 本地模型定位与摘要工具。
File purpose: Provide local model resolution and digest helpers for stage-two VAE runtime.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from main.core.digest import compute_object_digest


def resolve_vae_model_root(config: dict[str, Any], required: bool) -> Path | None:
    """功能：从 backend 配置解析本地 VAE 模型目录。

    Resolve local VAE model root from backend config.

    Args:
        config: Backend configuration payload.
        required: Whether the model root is mandatory.

    Returns:
        A resolved model-root path, or `None` when optional and unset.
    """
    if not isinstance(config, dict):
        raise TypeError("config must be a dictionary")
    model_root_text = str(
        config.get("vae_model_local_path", config.get("local_model_root", ""))
    ).strip()
    if not model_root_text:
        if required:
            raise KeyError("vae_model_local_path is required")
        return None

    model_root = Path(model_root_text)
    if required and not model_root.exists():
        # 中文注释：formal 模式下模型目录缺失必须立即失败。
        raise FileNotFoundError(model_root)
    return model_root


def compute_model_root_digest(model_root: Path | None) -> str:
    """功能：计算模型目录的可重建摘要。

    Compute a reproducible digest for model root contents.

    Args:
        model_root: Local model root path.

    Returns:
        A digest string representing the model root snapshot.
    """
    if model_root is None:
        return "model_root_missing_placeholder"
    if not model_root.exists():
        return "model_root_unavailable_placeholder"

    file_entries: list[dict[str, object]] = []
    for file_path in sorted(path for path in model_root.rglob("*") if path.is_file()):
        file_entries.append(
            {
                "relpath": str(file_path.relative_to(model_root)).replace("\\", "/"),
                "size": int(file_path.stat().st_size),
            }
        )
    return compute_object_digest(file_entries)

"""
文件用途：提供 runtime config bundle 的通用加载能力。
File purpose: Provide generic runtime config bundle loading utilities.
Module type: General module
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeConfigBundle:
    """功能：定义 runtime 所需的正式配置集合。

    Runtime config bundle.

    Args:
        project_contract_path: Project contract config path.
        protocol_config_path: Protocol config path.
        artifact_schema_path: Artifact schema config path.
        ablation_config_path: Ablation runtime config path.
        attack_config_path: Attack config path.
        method_config_paths: Method config paths keyed by method variant.

    Returns:
        None.
    """

    project_contract_path: Path
    protocol_config_path: Path
    artifact_schema_path: Path
    ablation_config_path: Path
    attack_config_path: Path
    method_config_paths: dict[str, Path]


def load_json_config(path: str | Path) -> dict[str, Any]:
    """功能：加载 JSON 配置文件。

    Load a JSON config file.

    Args:
        path: Config file path.

    Returns:
        The parsed JSON object.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_method_config_paths(
    root_path: Path,
    method_variants: list[str],
    method_root: Path | None = None,
) -> dict[str, Path]:
    """功能：根据 method variant 列表构建配置路径映射。

    Build method-config paths from a validated method-variant list.

    Args:
        root_path: Repository root path.
        method_variants: Ordered method-variant names.
        method_root: Optional override for the method-config root.

    Returns:
        A dictionary keyed by method variant.
    """
    method_config_paths: dict[str, Path] = {}
    for method_variant in method_variants:
        if not isinstance(method_variant, str) or not method_variant:
            raise ValueError("method_variant entries must be non-empty strings")
        method_config_paths[method_variant] = (
            (method_root or (root_path / "configs" / "method")) / f"{method_variant}.json"
        )
    return method_config_paths


def load_runtime_configs(config_bundle: RuntimeConfigBundle) -> dict[str, Any]:
    """功能：根据 bundle 加载全部正式配置内容。

    Load governed config payloads from a resolved config bundle.

    Args:
        config_bundle: Resolved runtime config bundle.

    Returns:
        A dictionary containing loaded config payloads and their paths.
    """
    return {
        "bundle": config_bundle,
        "project_contract": load_json_config(config_bundle.project_contract_path),
        "protocol_config": load_json_config(config_bundle.protocol_config_path),
        "artifact_schema": load_json_config(config_bundle.artifact_schema_path),
        "ablation_config": load_json_config(config_bundle.ablation_config_path),
        "attack_config": load_json_config(config_bundle.attack_config_path),
        "method_configs": {
            method_variant: load_json_config(config_path)
            for method_variant, config_path in config_bundle.method_config_paths.items()
        },
    }
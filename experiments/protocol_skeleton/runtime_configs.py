"""
文件用途：装配 protocol_skeleton experiment 的正式配置路径集合。
File purpose: Build the governed runtime config bundle for the protocol_skeleton experiment.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from main.core.registry import (
    RuntimeConfigBundle,
    build_method_config_paths,
    load_json_config,
    load_runtime_configs,
)


def _resolve_method_variants(ablation_config_path: Path) -> list[str]:
    """功能：读取并校验 protocol_skeleton 的 method variant 列表。

    Read and validate the protocol-skeleton method-variant list.

    Args:
        ablation_config_path: Protocol-skeleton ablation config path.

    Returns:
        A non-empty ordered method-variant list.
    """
    ablation_config = load_json_config(ablation_config_path)
    method_variants = ablation_config.get("method_variants", [])
    if not isinstance(method_variants, list) or not method_variants:
        raise ValueError("ablation method_variants must be a non-empty list")
    for method_variant in method_variants:
        if not isinstance(method_variant, str) or not method_variant:
            raise ValueError("method_variant entries must be non-empty strings")
    return method_variants


def build_protocol_skeleton_config_bundle(
    repository_root: str | Path,
) -> RuntimeConfigBundle:
    """功能：构建 protocol_skeleton experiment 的配置路径集合。

    Build the config bundle for the protocol_skeleton experiment.

    Args:
        repository_root: Repository root path.

    Returns:
        A resolved runtime config bundle.
    """
    root_path = Path(repository_root)
    experiment_config_root = root_path / "experiments" / "protocol_skeleton" / "configs"
    ablation_config_path = (
        experiment_config_root / "ablation" / "protocol_skeleton_methods.json"
    )
    method_variants = _resolve_method_variants(ablation_config_path)
    return RuntimeConfigBundle(
        project_contract_path=root_path / "configs" / "project" / "project_contract.json",
        protocol_config_path=experiment_config_root / "protocol" / "protocol_skeleton.json",
        artifact_schema_path=(
            root_path / "configs" / "schema" / "protocol_artifact_schema.json"
        ),
        ablation_config_path=ablation_config_path,
        attack_config_path=(
            experiment_config_root / "attacks" / "identity_attack_placeholder.json"
        ),
        method_config_paths=build_method_config_paths(
            root_path,
            method_variants,
            experiment_config_root / "method",
        ),
    )


def load_protocol_skeleton_runtime_configs(
    repository_root: str | Path,
) -> dict[str, Any]:
    """功能：加载 protocol_skeleton experiment 的全部正式配置内容。

    Load all governed config payloads for the protocol_skeleton experiment.

    Args:
        repository_root: Repository root path.

    Returns:
        A dictionary containing loaded config payloads and their paths.
    """
    return load_runtime_configs(build_protocol_skeleton_config_bundle(repository_root))
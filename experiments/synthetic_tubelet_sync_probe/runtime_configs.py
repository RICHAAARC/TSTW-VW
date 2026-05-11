"""
文件用途：装配 synthetic_tubelet_sync_probe experiment 的正式配置路径集合。
File purpose: Build the governed runtime config bundle for the synthetic_tubelet_sync_probe experiment.
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


CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"


def _resolve_method_variants(ablation_config_path: Path) -> list[str]:
    """功能：读取并校验 synthetic_tubelet_sync_probe 的 method variant 列表。

    Read and validate the synthetic_tubelet_sync_probe method-variant list.

    Args:
        ablation_config_path: Synthetic-tubelet-sync ablation config path.

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


def build_synthetic_tubelet_sync_probe_config_bundle(
    repository_root: str | Path,
) -> RuntimeConfigBundle:
    """功能：构建 synthetic_tubelet_sync_probe experiment 的配置路径集合。

    Build the config bundle for the synthetic_tubelet_sync_probe experiment.

    Args:
        repository_root: Repository root path.

    Returns:
        A resolved runtime config bundle.

    Raises:
        ValueError: Raised when the governed construction phase does not match.
    """
    root_path = Path(repository_root)
    project_contract_path = root_path / "configs" / "project" / "project_contract.json"
    project_contract = load_json_config(project_contract_path)
    construction_phase = project_contract.get("construction_phase")
    if construction_phase != CONSTRUCTION_PHASE:
        raise ValueError(f"unsupported construction_phase: {construction_phase}")

    experiment_config_root = (
        root_path / "experiments" / "synthetic_tubelet_sync_probe" / "configs"
    )
    ablation_config_path = (
        experiment_config_root / "ablation" / "synthetic_tubelet_sync_ablation.json"
    )
    method_variants = _resolve_method_variants(ablation_config_path)
    return RuntimeConfigBundle(
        project_contract_path=project_contract_path,
        protocol_config_path=(
            experiment_config_root / "protocol" / "synthetic_tubelet_sync_probe.json"
        ),
        artifact_schema_path=(
            root_path / "configs" / "schema" / "protocol_artifact_schema.json"
        ),
        ablation_config_path=ablation_config_path,
        attack_config_path=(
            experiment_config_root / "attacks" / "temporal_attack_matrix.json"
        ),
        method_config_paths=build_method_config_paths(root_path, method_variants),
    )


def load_synthetic_tubelet_sync_probe_runtime_configs(
    repository_root: str | Path,
) -> dict[str, Any]:
    """功能：加载 synthetic_tubelet_sync_probe experiment 的全部正式配置内容。

    Load all governed config payloads for the synthetic_tubelet_sync_probe experiment.

    Args:
        repository_root: Repository root path.

    Returns:
        A dictionary containing loaded config payloads and their paths.
    """
    return load_runtime_configs(
        build_synthetic_tubelet_sync_probe_config_bundle(repository_root)
    )
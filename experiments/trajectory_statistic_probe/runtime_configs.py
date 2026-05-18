"""
文件用途：装配 trajectory_statistic_probe experiment 的正式配置路径集合。
File purpose: Build the governed runtime config bundle for the trajectory_statistic_probe experiment.
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


CONSTRUCTION_PHASE = "trajectory_statistic_probe"


def build_trajectory_statistic_probe_config_bundle(
    repository_root: str | Path,
) -> RuntimeConfigBundle:
    """功能：构建 trajectory_statistic_probe experiment 的配置 bundle。

    Build the config bundle for the trajectory_statistic_probe experiment.

    Args:
        repository_root: Repository root path.

    Returns:
        A resolved runtime config bundle.
    """
    root_path = Path(repository_root)
    ablation_config_path = (
        root_path / "configs" / "ablation" / "trajectory_statistic_ablation.json"
    )
    ablation_config = load_json_config(ablation_config_path)
    method_variants = ablation_config.get("method_variants", [])
    if not isinstance(method_variants, list) or not method_variants:
        raise ValueError("trajectory_statistic_ablation.method_variants must be non-empty")
    return RuntimeConfigBundle(
        project_contract_path=root_path / "configs" / "project" / "project_contract.json",
        protocol_config_path=(
            root_path / "configs" / "protocol" / "trajectory_statistic_probe.json"
        ),
        artifact_schema_path=(
            root_path / "configs" / "schema" / "protocol_artifact_schema.json"
        ),
        ablation_config_path=ablation_config_path,
        attack_config_path=(
            root_path / "configs" / "attacks" / "trajectory_probe_attack_matrix.json"
        ),
        method_config_paths=build_method_config_paths(root_path, method_variants),
    )


def load_trajectory_statistic_probe_runtime_configs(
    repository_root: str | Path,
) -> dict[str, Any]:
    """功能：加载 trajectory_statistic_probe experiment 的全部正式配置内容。

    Load all governed config payloads for the trajectory_statistic_probe experiment.

    Args:
        repository_root: Repository root path.

    Returns:
        A dictionary containing loaded config payloads and their paths.
    """
    root_path = Path(repository_root)
    runtime_configs = load_runtime_configs(
        build_trajectory_statistic_probe_config_bundle(root_path)
    )
    runtime_configs["trajectory_backend_config"] = load_json_config(
        root_path / "configs" / "backend" / "trajectory_reconstruction.json"
    )
    return runtime_configs
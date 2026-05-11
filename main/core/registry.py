"""
文件用途：加载阶段 0 runtime 所需的正式配置集合。
File purpose: Load the governed config bundle required by the protocol skeleton runtime runtime skeleton.
Module type: General module
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StageZeroConfigBundle:
    """功能：定义阶段 0 runtime 的正式配置集合。

    Protocol Skeleton runtime config bundle.

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


ACTIVE_STAGE_CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"


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


def load_stage_zero_config_bundle(repository_root: str | Path) -> StageZeroConfigBundle:
    """功能：构建阶段 0 runtime 的配置路径集合。

    Build the config bundle for the protocol skeleton runtime runtime skeleton.

    Args:
        repository_root: Repository root path.

    Returns:
        A `StageZeroConfigBundle` instance.
    """
    root_path = Path(repository_root)
    ablation_config_path = (
        root_path
        / "experiments"
        / "protocol_skeleton"
        / "configs"
        / "ablation"
        / "protocol_skeleton_methods.json"
    )
    ablation_config = load_json_config(ablation_config_path)
    method_variants = ablation_config.get("method_variants", [])
    if not isinstance(method_variants, list) or not method_variants:
        raise ValueError("ablation method_variants must be a non-empty list")

    method_config_paths: dict[str, Path] = {}
    for method_variant in method_variants:
        if not isinstance(method_variant, str) or not method_variant:
            raise ValueError("method_variant entries must be non-empty strings")
        method_config_paths[method_variant] = (
            root_path
            / "experiments"
            / "protocol_skeleton"
            / "configs"
            / "method"
            / f"{method_variant}.json"
        )

    return StageZeroConfigBundle(
        project_contract_path=root_path / "configs" / "project" / "project_contract.json",
        protocol_config_path=(
            root_path
            / "experiments"
            / "protocol_skeleton"
            / "configs"
            / "protocol"
            / "protocol_skeleton.json"
        ),
        artifact_schema_path=(
            root_path / "configs" / "schema" / "protocol_artifact_schema.json"
        ),
        ablation_config_path=ablation_config_path,
        attack_config_path=(
            root_path
            / "experiments"
            / "protocol_skeleton"
            / "configs"
            / "attacks"
            / "identity_attack_placeholder.json"
        ),
        method_config_paths=method_config_paths,
    )


def load_stage_zero_runtime_configs(repository_root: str | Path) -> dict[str, Any]:
    """功能：加载阶段 0 runtime 的全部正式配置内容。

    Load all governed config payloads for the protocol skeleton runtime runtime skeleton.

    Args:
        repository_root: Repository root path.

    Returns:
        A dictionary containing loaded config payloads and their paths.
    """
    config_bundle = load_stage_zero_config_bundle(repository_root)
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


def _build_method_config_paths(
    root_path: Path,
    method_variants: list[str],
    method_root: Path | None = None,
) -> dict[str, Path]:
    method_config_paths: dict[str, Path] = {}
    for method_variant in method_variants:
        if not isinstance(method_variant, str) or not method_variant:
            raise ValueError("method_variant entries must be non-empty strings")
        method_config_paths[method_variant] = (
            (method_root or (root_path / "configs" / "method")) / f"{method_variant}.json"
        )
    return method_config_paths


def load_active_runtime_config_bundle(repository_root: str | Path) -> StageZeroConfigBundle:
    """功能：根据正式 construction phase 选择 active runtime 配置集合。

    Build the active runtime config bundle for the current formal construction phase.

    Args:
        repository_root: Repository root path.

    Returns:
        A config bundle aligned with the active formal stage.
    """
    root_path = Path(repository_root)
    project_contract_path = root_path / "configs" / "project" / "project_contract.json"
    project_contract = load_json_config(project_contract_path)
    construction_phase = project_contract.get("construction_phase")

    if construction_phase == "protocol_skeleton":
        return load_stage_zero_config_bundle(root_path)
    if construction_phase != ACTIVE_STAGE_CONSTRUCTION_PHASE:
        raise ValueError(f"unsupported active construction_phase: {construction_phase}")

    ablation_config_path = (
        root_path
        / "experiments"
        / "synthetic_tubelet_sync_probe"
        / "configs"
        / "ablation"
        / "synthetic_tubelet_sync_ablation.json"
    )
    ablation_config = load_json_config(ablation_config_path)
    method_variants = ablation_config.get("method_variants", [])
    if not isinstance(method_variants, list) or not method_variants:
        raise ValueError("ablation method_variants must be a non-empty list")

    return StageZeroConfigBundle(
        project_contract_path=project_contract_path,
        protocol_config_path=(
            root_path
            / "experiments"
            / "synthetic_tubelet_sync_probe"
            / "configs"
            / "protocol"
            / "synthetic_tubelet_sync_probe.json"
        ),
        artifact_schema_path=(
            root_path / "configs" / "schema" / "protocol_artifact_schema.json"
        ),
        ablation_config_path=ablation_config_path,
        attack_config_path=(
            root_path
            / "experiments"
            / "synthetic_tubelet_sync_probe"
            / "configs"
            / "attacks"
            / "temporal_attack_matrix.json"
        ),
        method_config_paths=_build_method_config_paths(root_path, method_variants),
    )


def load_active_runtime_configs(repository_root: str | Path) -> dict[str, Any]:
    """功能：加载当前 formal stage 的全部 active runtime 配置内容。

    Load the governed config payloads for the active formal runtime.

    Args:
        repository_root: Repository root path.

    Returns:
        A dictionary containing loaded config payloads and their paths.
    """
    config_bundle = load_active_runtime_config_bundle(repository_root)
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
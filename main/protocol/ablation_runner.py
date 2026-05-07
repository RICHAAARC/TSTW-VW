"""
文件用途：提供当前 formal stage 的 ablation runner 骨架。
File purpose: Provide the active formal-stage ablation runner scaffold.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from main.analysis.table_builder import TableBuilder
from main.attacks.attack_registry import build_attack_registry
from main.backends.synthetic_video_latent import (
    LATENT_BACKEND_NAME as SYNTHETIC_VIDEO_LATENT_BACKEND_NAME,
    build_synthetic_video_latent_backend_from_support_config,
)
from main.core.manifest import ManifestBuilder
from main.core.records import RecordWriter
from main.core.registry import load_active_runtime_configs
from main.protocol.detector_runner import ProtocolRunner
from main.protocol.event_builder import build_event_plan
from main.protocol.split_builder import build_split_plan


@dataclass(frozen=True)
class AblationRunResult:
    """功能：定义 active stage 运行结果载体。

    Active-stage run result payload.

    Args:
        run_id: Stable run identifier.
        output_root: Run root path.
        event_score_records: Persisted event score records.
        threshold_records: Persisted threshold records.
        run_manifest: Persisted run manifest.

    Returns:
        None.
    """

    run_id: str
    output_root: Path
    event_score_records: list[dict[str, Any]]
    threshold_records: list[dict[str, Any]]
    run_manifest: dict[str, Any]


class AblationRunner:
    """功能：执行当前 formal stage 的共享 ablation protocol。

    Active-stage ablation runner that executes all governed method variants under one protocol.

    Args:
        repository_root: Repository root path.

    Returns:
        None.
    """

    def __init__(self, repository_root: str | Path) -> None:
        self._repository_root = Path(repository_root)
        if not self._repository_root.exists():
            raise FileNotFoundError(self._repository_root)
        self._runtime_configs = load_active_runtime_configs(self._repository_root)
        self._protocol_runner = ProtocolRunner(
            latent_backend=self._resolve_latent_backend(self._runtime_configs["protocol_config"])
        )
        self._table_builder = TableBuilder()
        self._manifest_builder = ManifestBuilder()

    def run(self, output_root: str | Path, samples_per_role: int = 2) -> AblationRunResult:
        """功能：运行当前 formal stage 的完整共享协议。

        Run the complete shared protocol for the active formal stage.

        Args:
            output_root: Run root path.
            samples_per_role: Sample count per split-role pair.

        Returns:
            A `StageZeroRunResult` instance.
        """
        if not isinstance(samples_per_role, int) or samples_per_role < 1:
            raise ValueError("samples_per_role must be a positive integer")

        output_root_path = Path(output_root)
        run_id = output_root_path.name
        split_plan = build_split_plan(samples_per_role=samples_per_role)
        attack_registry = build_attack_registry(self._runtime_configs["attack_config"])
        event_plan = build_event_plan(split_plan, attack_registry)
        event_score_records: list[dict[str, Any]] = []
        threshold_records: list[dict[str, Any]] = []

        ablation_config = self._runtime_configs["ablation_config"]
        method_configs = self._runtime_configs["method_configs"]
        for method_variant in ablation_config["method_variants"]:
            method_config = method_configs[method_variant]
            variant_event_records, threshold_record = self._protocol_runner.run_method_variant(
                run_id,
                event_plan,
                method_config,
                self._runtime_configs["protocol_config"],
                output_root=output_root_path,
            )
            event_score_records.extend(variant_event_records)
            threshold_records.append(threshold_record)

        record_writer = RecordWriter(output_root_path)
        record_writer.write_event_score_records(event_score_records)
        record_writer.write_threshold_records(threshold_records)
        self._table_builder.build_tables(event_score_records, threshold_records, output_root_path)
        run_manifest = self._manifest_builder.build_run_manifest(
            run_id=run_id,
            method_config_paths=list(
                self._runtime_configs["bundle"].method_config_paths.values()
            ),
            protocol_config_path=self._runtime_configs["bundle"].protocol_config_path,
            attack_config_path=self._runtime_configs["bundle"].attack_config_path,
            ablation_config_path=self._runtime_configs["bundle"].ablation_config_path,
            event_score_records=event_score_records,
            threshold_records=threshold_records,
            output_paths=record_writer.output_paths,
        )
        record_writer.write_run_manifest(run_manifest)
        return AblationRunResult(
            run_id=run_id,
            output_root=output_root_path,
            event_score_records=event_score_records,
            threshold_records=threshold_records,
            run_manifest=run_manifest,
        )

    def _resolve_latent_backend(self, protocol_config: dict[str, Any]) -> Any | None:
        if not isinstance(protocol_config, dict):
            raise TypeError("protocol_config must be a dictionary")
        if protocol_config.get("latent_backend_name") != SYNTHETIC_VIDEO_LATENT_BACKEND_NAME:
            return None
        return build_synthetic_video_latent_backend_from_support_config(protocol_config)
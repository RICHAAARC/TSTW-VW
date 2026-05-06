"""
文件用途：提供阶段 0 的 ablation runner 骨架。
File purpose: Provide the stage-0 ablation runner scaffold.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from main.analysis.table_builder import TableBuilder
from main.attacks.attack_registry import build_attack_registry
from main.core.manifest import ManifestBuilder
from main.core.records import RecordWriter
from main.core.registry import load_stage_zero_runtime_configs
from main.protocol.detector_runner import ProtocolRunner
from main.protocol.event_builder import build_event_plan
from main.protocol.split_builder import build_split_plan


@dataclass(frozen=True)
class StageZeroRunResult:
    """功能：定义阶段 0 运行结果载体。

    Stage-0 run result payload.

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
    """功能：执行阶段 0 的共享 ablation protocol。

    Stage-0 ablation runner that executes both required method variants under one protocol.

    Args:
        repository_root: Repository root path.

    Returns:
        None.
    """

    def __init__(self, repository_root: str | Path) -> None:
        self._repository_root = Path(repository_root)
        if not self._repository_root.exists():
            raise FileNotFoundError(self._repository_root)
        self._runtime_configs = load_stage_zero_runtime_configs(self._repository_root)
        self._protocol_runner = ProtocolRunner()
        self._table_builder = TableBuilder()
        self._manifest_builder = ManifestBuilder()

    def run(self, output_root: str | Path, samples_per_role: int = 2) -> StageZeroRunResult:
        """功能：运行阶段 0 的完整 protocol skeleton。

        Run the complete stage-0 protocol skeleton.

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
        return StageZeroRunResult(
            run_id=run_id,
            output_root=output_root_path,
            event_score_records=event_score_records,
            threshold_records=threshold_records,
            run_manifest=run_manifest,
        )
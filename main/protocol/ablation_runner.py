"""
文件用途：提供当前 formal stage 的 ablation runner 骨架。
File purpose: Provide the active formal-stage ablation runner scaffold.
Module type: General module
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from main.analysis.table_builder import TableBuilder
from main.attacks.attack_registry import build_attack_registry
from main.backends.synthetic_video_latent import (
    LATENT_BACKEND_NAME as SYNTHETIC_VIDEO_LATENT_BACKEND_NAME,
    SUPPORTED_RUNTIME_PROFILES,
    build_synthetic_video_latent_backend_from_support_config,
)
from main.core.manifest import ManifestBuilder
from main.core.records import RecordWriter
from main.core.registry import load_active_runtime_configs
from main.core.schema import (
    validate_event_score_record,
    validate_threshold_record,
)
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
        self._table_builder = TableBuilder()
        self._manifest_builder = ManifestBuilder()

    def run(
        self,
        output_root: str | Path,
        samples_per_role: int = 2,
        runtime_profile_override: str | None = None,
    ) -> AblationRunResult:
        """功能：运行当前 formal stage 的完整共享协议。

        Run the complete shared protocol for the active formal stage.

        Args:
            output_root: Run root path.
            samples_per_role: Sample count per split-role pair.
            runtime_profile_override: Optional runtime profile override
                (one of ``tiny``/``smoke``/``formal``) used to drive the
                latent backend shape selection and tubelet sweep tier.

        Returns:
            A `StageZeroRunResult` instance.
        """
        if not isinstance(samples_per_role, int) or samples_per_role < 1:
            raise ValueError("samples_per_role must be a positive integer")

        protocol_config = self._resolve_protocol_config(runtime_profile_override)
        runtime_profile = protocol_config.get("runtime_profile")
        protocol_runner = ProtocolRunner(
            latent_backend=self._resolve_latent_backend(protocol_config)
        )

        output_root_path = Path(output_root)
        run_id = output_root_path.name
        split_plan = build_split_plan(samples_per_role=samples_per_role)
        attack_registry = build_attack_registry(self._runtime_configs["attack_config"])
        event_plan = build_event_plan(split_plan, attack_registry)
        event_score_records: list[dict[str, Any]] = []
        threshold_records: list[dict[str, Any]] = []

        ablation_config = self._runtime_configs["ablation_config"]
        method_configs = self._runtime_configs["method_configs"]
        record_writer = RecordWriter(output_root_path)
        # 中文注释：在阶段 1 性能收口阶段，我们要求 records 与 thresholds
        # 在每个 method variant 完成后立即增量落盘，避免完整 ablation 中途
        # 终止时无任何正式 records / thresholds 可用作可重建证据。
        self._reset_incremental_outputs(record_writer)
        for method_config in self._build_runtime_method_configs(
            ablation_config,
            method_configs,
            runtime_profile,
        ):
            variant_event_records, threshold_record = protocol_runner.run_method_variant(
                run_id,
                event_plan,
                method_config,
                protocol_config,
                output_root=output_root_path,
            )
            event_score_records.extend(variant_event_records)
            threshold_records.append(threshold_record)
            self._append_event_score_records(record_writer, variant_event_records)
            self._rewrite_threshold_records(record_writer, threshold_records)

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

    def _resolve_protocol_config(
        self,
        runtime_profile_override: str | None,
    ) -> dict[str, Any]:
        protocol_config = self._runtime_configs["protocol_config"]
        if runtime_profile_override is None:
            return protocol_config
        if runtime_profile_override not in SUPPORTED_RUNTIME_PROFILES:
            raise ValueError(
                f"unsupported runtime_profile_override: {runtime_profile_override}"
            )
        overridden_protocol_config = copy.deepcopy(protocol_config)
        overridden_protocol_config["runtime_profile"] = runtime_profile_override
        return overridden_protocol_config

    def _reset_incremental_outputs(self, record_writer: RecordWriter) -> None:
        event_scores_path = record_writer.output_paths.event_scores_path
        thresholds_path = record_writer.output_paths.thresholds_path
        event_scores_path.parent.mkdir(parents=True, exist_ok=True)
        thresholds_path.parent.mkdir(parents=True, exist_ok=True)
        if event_scores_path.exists():
            event_scores_path.unlink()
        if thresholds_path.exists():
            thresholds_path.unlink()

    def _append_event_score_records(
        self,
        record_writer: RecordWriter,
        variant_event_records: list[dict[str, Any]],
    ) -> None:
        if not variant_event_records:
            return
        event_scores_path = record_writer.output_paths.event_scores_path
        with event_scores_path.open("a", encoding="utf-8") as handle:
            for event_score_record in variant_event_records:
                validate_event_score_record(event_score_record)
                handle.write(json.dumps(event_score_record, ensure_ascii=False) + "\n")

    def _rewrite_threshold_records(
        self,
        record_writer: RecordWriter,
        threshold_records: list[dict[str, Any]],
    ) -> None:
        for threshold_record in threshold_records:
            validate_threshold_record(threshold_record)
        record_writer.output_paths.thresholds_path.write_text(
            json.dumps(threshold_records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _build_runtime_method_configs(
        self,
        ablation_config: dict[str, Any],
        method_configs: dict[str, dict[str, Any]],
        runtime_profile: str | None,
    ) -> list[dict[str, Any]]:
        runtime_method_configs = [
            dict(method_configs[method_variant])
            for method_variant in ablation_config["method_variants"]
        ]
        sweep_variant = ablation_config.get("tubelet_length_sweep_variant")
        sweep_lengths = self._resolve_tubelet_length_sweep(ablation_config, runtime_profile)
        if (
            isinstance(sweep_variant, str)
            and sweep_variant in method_configs
            and isinstance(sweep_lengths, list)
            and sweep_lengths
        ):
            base_config = method_configs[sweep_variant]
            default_length = int(base_config["tubelet_length"])
            for tubelet_length in sweep_lengths:
                if not isinstance(tubelet_length, int) or tubelet_length < 1:
                    raise ValueError("tubelet_length_sweep entries must be positive integers")
                if tubelet_length == default_length:
                    continue
                derived_method_config = dict(base_config)
                derived_method_config["base_method_variant"] = sweep_variant
                derived_method_config["method_variant"] = (
                    f"{sweep_variant}_lt{int(tubelet_length):02d}"
                )
                derived_method_config["tubelet_length"] = int(tubelet_length)
                runtime_method_configs.append(derived_method_config)
        return runtime_method_configs

    def _resolve_tubelet_length_sweep(
        self,
        ablation_config: dict[str, Any],
        runtime_profile: str | None,
    ) -> list[int]:
        # 中文注释：smoke 与 tiny 仅跑 {1,4} 加速 CI 闭环；formal 走完整 {1,2,4,8,16}。
        profile_keyed = {
            "tiny": ablation_config.get("tubelet_length_sweep_tiny"),
            "smoke": ablation_config.get("tubelet_length_sweep_smoke"),
            "formal": ablation_config.get("tubelet_length_sweep_formal"),
        }
        candidate = profile_keyed.get(runtime_profile)
        if isinstance(candidate, list) and candidate:
            return list(candidate)
        return list(ablation_config.get("tubelet_length_sweep", []))

    def _resolve_latent_backend(self, protocol_config: dict[str, Any]) -> Any | None:
        if not isinstance(protocol_config, dict):
            raise TypeError("protocol_config must be a dictionary")
        if protocol_config.get("latent_backend_name") != SYNTHETIC_VIDEO_LATENT_BACKEND_NAME:
            return None
        return build_synthetic_video_latent_backend_from_support_config(protocol_config)
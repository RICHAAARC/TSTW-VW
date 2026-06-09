"""
文件用途：运行阶段 3 trajectory statistic probe 的受治理 runtime 闭环。
File purpose: Run the governed stage-three trajectory statistic probe runtime.
Module type: General module
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.synthetic_tubelet_sync_probe.synthetic_video_latent import (
    build_synthetic_video_latent_backend_from_support_config,
)
from experiments.trajectory_statistic_probe.artifact_builder import (
    TrajectoryStatisticArtifactBuilder,
)
from experiments.trajectory_statistic_probe.mechanism_audit import (
    build_stage3_mechanism_decision,
)
from experiments.trajectory_statistic_probe.method_factory import (
    build_trajectory_probe_method_factory,
)
from experiments.trajectory_statistic_probe.output_layout import (
    build_trajectory_statistic_probe_output_paths,
)
from experiments.trajectory_statistic_probe.real_video_vae_latent_frozen_baseline_loader import (
    FrozenBaselinePackage,
    load_real_video_vae_latent_frozen_baseline,
)
from experiments.trajectory_statistic_probe.runtime_configs import (
    load_trajectory_statistic_probe_runtime_configs,
)
from main.attacks.attack_registry import build_attack_registry
from main.core.digest import (
    compute_file_digest,
    compute_object_digest,
    compute_path_collection_digest,
)
from main.core.records import RecordWriter
from main.protocol.detector_runner import ProtocolRunner
from main.protocol.event_builder import build_event_plan
from main.protocol.split_builder import build_split_plan


@dataclass(frozen=True)
class TrajectoryStatisticProbeRunResult:
    """功能：定义阶段 3 运行结果载体。

    Stage-three run result payload.

    Args:
        run_id: Stable run identifier.
        output_root: Run root path.
        event_score_records: Persisted event score records.
        threshold_records: Persisted threshold records.
        run_manifest: Persisted run manifest.
        mechanism_decision: Persisted mechanism-decision payload.

    Returns:
        None.
    """

    run_id: str
    output_root: Path
    event_score_records: list[dict[str, Any]]
    threshold_records: list[dict[str, Any]]
    run_manifest: dict[str, Any]
    mechanism_decision: dict[str, Any]


class TrajectoryStatisticProbeRunner:
    """功能：执行阶段 3 受治理协议闭环。

    Execute the governed stage-three protocol loop.

    Args:
        repository_root: Repository root path.

    Returns:
        None.
    """

    def __init__(self, repository_root: str | Path) -> None:
        self._repository_root = Path(repository_root)
        if not self._repository_root.exists():
            raise FileNotFoundError(self._repository_root)
        self._runtime_configs = load_trajectory_statistic_probe_runtime_configs(
            self._repository_root
        )
        self._artifact_builder = TrajectoryStatisticArtifactBuilder()

    def run(
        self,
        output_root: str | Path,
        samples_per_role: int = 2,
        runtime_profile_override: str | None = None,
        method_variants: list[str] | None = None,
        frozen_baseline_root: str | Path | None = None,
    ) -> TrajectoryStatisticProbeRunResult:
        """功能：运行阶段 3 受治理协议并写出 records、tables 与 manifests。

        Run the governed stage-three protocol and persist its artifacts.

        Args:
            output_root: Run root path.
            samples_per_role: Sample count per split-role pair.
            runtime_profile_override: Optional runtime profile override.
            method_variants: Optional method-variant allowlist.
            frozen_baseline_root: Optional frozen baseline output root.

        Returns:
            A `TrajectoryStatisticProbeRunResult` instance.
        """
        if not isinstance(samples_per_role, int) or samples_per_role < 1:
            raise ValueError("samples_per_role must be a positive integer")

        protocol_config = self._resolve_protocol_config(runtime_profile_override)
        frozen_baseline_package = self._load_frozen_baseline_if_available(
            frozen_baseline_root
        )
        trajectory_backend_config = self._resolve_trajectory_backend_config(
            frozen_baseline_package
        )
        attack_registry = build_attack_registry(self._runtime_configs["attack_config"])
        split_plan = build_split_plan(samples_per_role=samples_per_role)
        event_plan = build_event_plan(split_plan, attack_registry)
        runtime_method_configs = self._build_runtime_method_configs(
            method_variants,
            frozen_baseline_package,
        )
        protocol_runner = ProtocolRunner(
            latent_backend=build_synthetic_video_latent_backend_from_support_config(
                protocol_config
            ),
            method_factory=build_trajectory_probe_method_factory(
                trajectory_backend_config
            ),
        )

        output_root_path = Path(output_root)
        output_paths = build_trajectory_statistic_probe_output_paths(output_root_path)
        run_id = output_root_path.name
        event_score_records: list[dict[str, Any]] = []
        threshold_records: list[dict[str, Any]] = []

        for method_config in runtime_method_configs:
            variant_event_records, threshold_record = protocol_runner.run_method_variant(
                run_id,
                event_plan,
                method_config,
                protocol_config,
                output_root=output_root_path,
            )
            for event_score_record in variant_event_records:
                event_score_record["mechanism_trace"][
                    "construction_phase"
                ] = "trajectory_statistic_probe"
            event_score_records.extend(variant_event_records)
            threshold_records.append(threshold_record)

        record_writer = RecordWriter(output_root_path)
        record_writer.write_event_score_records(event_score_records)
        record_writer.write_threshold_records(threshold_records)
        self._artifact_builder.build_artifacts(
            event_score_records,
            threshold_records,
            output_root_path,
        )
        mechanism_decision = build_stage3_mechanism_decision(
            event_score_records,
            threshold_records,
            runtime_method_configs,
            frozen_baseline_manifest=(
                frozen_baseline_package.frozen_baseline_manifest
                if frozen_baseline_package is not None
                else None
            ),
            trajectory_backend_config=trajectory_backend_config,
        )
        output_paths.trajectory_mechanism_decision_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.trajectory_mechanism_decision_path.write_text(
            json.dumps(mechanism_decision, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        run_manifest = self._build_run_manifest(
            run_id,
            runtime_method_configs,
            output_paths,
            event_score_records,
            threshold_records,
        )
        output_paths.run_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.run_manifest_path.write_text(
            json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output_paths.runtime_config_path.parent.mkdir(parents=True, exist_ok=True)
        output_paths.runtime_config_path.write_text(
            json.dumps(
                {
                    "runtime_profile": protocol_config["runtime_profile"],
                    "method_variants": [
                        method_config["method_variant"]
                        for method_config in runtime_method_configs
                    ],
                    "trajectory_backend_config": self._runtime_configs[
                        "trajectory_backend_config"
                    ]
                    if frozen_baseline_package is None
                    else trajectory_backend_config,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if frozen_baseline_package is not None:
            output_paths.stage2_frozen_baseline_manifest_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            output_paths.stage2_frozen_baseline_manifest_path.write_text(
                json.dumps(
                    frozen_baseline_package.frozen_baseline_manifest,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        return TrajectoryStatisticProbeRunResult(
            run_id=run_id,
            output_root=output_root_path,
            event_score_records=event_score_records,
            threshold_records=threshold_records,
            run_manifest=run_manifest,
            mechanism_decision=mechanism_decision,
        )

    def _resolve_protocol_config(
        self,
        runtime_profile_override: str | None,
    ) -> dict[str, Any]:
        protocol_config = copy.deepcopy(self._runtime_configs["protocol_config"])
        if runtime_profile_override is not None:
            protocol_config["runtime_profile"] = runtime_profile_override
        return protocol_config

    def _load_frozen_baseline_if_available(
        self,
        frozen_baseline_root: str | Path | None,
    ) -> FrozenBaselinePackage | None:
        """功能：按需读取阶段 3 的冻结 baseline 前置依赖。

        这是项目特定的治理入口。通用工程写法是让 runner 接受可选的只读依赖,
        并把依赖校验放在主循环之前, 避免已失败的前置输入污染后续 records。
        """
        if frozen_baseline_root is None:
            return None
        return load_real_video_vae_latent_frozen_baseline(frozen_baseline_root)

    def _resolve_trajectory_backend_config(
        self,
        frozen_baseline_package: FrozenBaselinePackage | None,
    ) -> dict[str, Any]:
        """功能：根据冻结 baseline 依赖决定 trajectory source 配置。

        通用工程写法是先复制静态配置, 再把只读依赖的 digest 作为 provenance 注入运行时配置。
        项目特定设计在于: 只有当阶段 2 frozen baseline 通过 loader 后, 才允许把 source 从
        `latent_interpolation_surrogate` 推进为 `stage2_frozen_endpoint_replay`。
        """
        trajectory_backend_config = dict(
            self._runtime_configs["trajectory_backend_config"]
        )
        if frozen_baseline_package is None:
            return trajectory_backend_config
        trajectory_backend_config["trajectory_source_kind"] = (
            "stage2_frozen_endpoint_replay"
        )
        trajectory_backend_config["formal_trajectory_source_status"] = "candidate_ready"
        trajectory_backend_config["stage2_frozen_baseline_manifest_digest"] = (
            compute_object_digest(frozen_baseline_package.frozen_baseline_manifest)
        )
        trajectory_backend_config["stage2_frozen_baseline_record_count"] = (
            frozen_baseline_package.frozen_baseline_manifest.get(
                "baseline_record_count"
            )
        )
        trajectory_backend_config["stage2_frozen_baseline_threshold_count"] = (
            frozen_baseline_package.frozen_baseline_manifest.get(
                "baseline_threshold_count"
            )
        )
        return trajectory_backend_config

    def _build_runtime_method_configs(
        self,
        method_variants: list[str] | None,
        frozen_baseline_package: FrozenBaselinePackage | None = None,
    ) -> list[dict[str, Any]]:
        ablation_config = self._runtime_configs["ablation_config"]
        method_configs = self._runtime_configs["method_configs"]
        configured_variants = list(ablation_config.get("method_variants", []))
        if method_variants is None:
            selected_variants = configured_variants
        else:
            missing_variants = [
                method_variant
                for method_variant in method_variants
                if method_variant not in configured_variants
            ]
            if missing_variants:
                raise ValueError(
                    f"unsupported method_variants: {', '.join(sorted(missing_variants))}"
                )
            selected_variants = list(method_variants)
        runtime_method_configs = [
            dict(method_configs[method_variant])
            for method_variant in selected_variants
        ]
        if frozen_baseline_package is not None:
            for method_config in runtime_method_configs:
                if bool(method_config.get("enable_trajectory", False)):
                    method_config["trajectory_source_kind"] = (
                        "stage2_frozen_endpoint_replay"
                    )
        return runtime_method_configs

    def _build_run_manifest(
        self,
        run_id: str,
        runtime_method_configs: list[dict[str, Any]],
        output_paths: Any,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        method_config_paths = self._runtime_configs["bundle"].method_config_paths
        selected_method_config_paths = [
            method_config_paths[method_config["method_variant"]]
            for method_config in runtime_method_configs
        ]
        placeholder_fields = sorted(
            {
                field_name
                for record in event_score_records
                for field_name in record.get("placeholder_fields", [])
            }
        )
        random_fields = sorted(
            {
                field_name
                for record in event_score_records
                for field_name in record.get("random_fields", [])
            }
        )
        return {
            "run_id": run_id,
            "created_at": threshold_records[0]["created_at"],
            "construction_phase": "trajectory_statistic_probe",
            "protocol_name": "fixed_low_fpr_calibrated_detection",
            "method_config_digest": compute_object_digest(
                [compute_file_digest(path) for path in selected_method_config_paths]
            ),
            "protocol_config_digest": compute_file_digest(
                self._runtime_configs["bundle"].protocol_config_path
            ),
            "attack_matrix_digest": compute_file_digest(
                self._runtime_configs["bundle"].attack_config_path
            ),
            "ablation_config_digest": compute_file_digest(
                self._runtime_configs["bundle"].ablation_config_path
            ),
            "records_digest": compute_object_digest(event_score_records),
            "thresholds_digest": compute_object_digest(threshold_records),
            "tables_digest": compute_path_collection_digest(output_paths.table_paths()),
            "figures_digest": None,
            "placeholder_fields": placeholder_fields,
            "random_fields": random_fields,
            "stage2_frozen_baseline_manifest_path": (
                str(output_paths.stage2_frozen_baseline_manifest_path)
            ),
        }

"""
文件用途: 运行 trajectory-aware sampling probe 的最小 CPU scaffold 闭环。
Module type: General module
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.trajectory_aware_sampling_probe.artifact_builder import (
    build_trajectory_aware_sampling_artifacts,
)
from experiments.trajectory_aware_sampling_probe.gpu_validation_contract import (
    build_trajectory_aware_sampling_gpu_validation_contract,
)
from experiments.trajectory_aware_sampling_probe.output_layout import (
    build_trajectory_aware_sampling_probe_output_paths,
)
from main.core.digest import compute_file_digest, compute_object_digest
from main.core.records import RecordWriter

DEFAULT_SAMPLING_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_probe.json"
)
DEFAULT_GPU_VALIDATION_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_gpu_validation_contract.json"
)


@dataclass(frozen=True)
class TrajectoryAwareSamplingProbeRunResult:
    """功能: 记录 trajectory-aware sampling scaffold 的运行结果。

    该对象只承载本地 CPU scaffold 结果路径和 payload。它不代表真实采样已经执行,
    也不代表真实视频生成或真实 watermark 集成已经被允许。
    """

    run_id: str
    output_root: Path
    readiness_decision: dict[str, Any]
    selection_plan: dict[str, Any]
    policy_manifest: dict[str, Any]
    gpu_validation_contract: dict[str, Any]
    artifact_paths: dict[str, Path]


class TrajectoryAwareSamplingProbeRunner:
    """功能: 从阶段 3 输出根目录构建 sampling scaffold 产物。

    该 runner 属于项目特定写法。它的输入是已经通过阶段 3 formal replay 的只读输出目录,
    输出是下一阶段的 selection plan 和报告。通用工程价值在于: 把读取上游 records、读取机制决策、
    读取配置、写出下游 scaffold 产物这些步骤集中到一个可测试入口中, 避免 notebook 直接拼装正式产物。
    """

    def __init__(self, repository_root: str | Path) -> None:
        self._repository_root = Path(repository_root)
        if not self._repository_root.exists():
            raise FileNotFoundError(self._repository_root)

    def run(
        self,
        upstream_trajectory_root: str | Path,
        output_root: str | Path,
        sampling_config_path: str | Path | None = None,
    ) -> TrajectoryAwareSamplingProbeRunResult:
        """功能: 执行 sampling scaffold 的本地 CPU 闭环。

        Args:
            upstream_trajectory_root: 阶段 3 trajectory statistic probe 输出根目录。
            output_root: sampling scaffold 输出根目录。
            sampling_config_path: 可选 sampling 配置路径, 默认使用仓库受治理配置。

        Returns:
            `TrajectoryAwareSamplingProbeRunResult` 实例。
        """
        upstream_root_path = Path(upstream_trajectory_root)
        output_root_path = Path(output_root)
        event_score_records = RecordWriter(upstream_root_path).read_event_score_records()
        mechanism_decision = self._read_trajectory_mechanism_decision(upstream_root_path)
        sampling_config = self._read_sampling_config(sampling_config_path)

        artifact_paths = build_trajectory_aware_sampling_artifacts(
            event_score_records,
            mechanism_decision,
            sampling_config,
            output_root_path,
        )
        readiness_decision = json.loads(
            artifact_paths["sampling_readiness_decision_path"].read_text(
                encoding="utf-8"
            )
        )
        selection_plan = json.loads(
            artifact_paths["sampling_selection_plan_path"].read_text(
                encoding="utf-8"
            )
        )
        policy_manifest = json.loads(
            artifact_paths["sampling_policy_manifest_path"].read_text(
                encoding="utf-8"
            )
        )
        handoff_manifest = self._write_run_handoff_manifest(
            output_root_path,
            upstream_root_path,
            sampling_config_path,
            readiness_decision,
            selection_plan,
            policy_manifest,
        )
        gpu_validation_contract = self._write_gpu_validation_contract(
            output_root_path,
            policy_manifest,
            handoff_manifest,
            self._read_gpu_validation_config(),
        )
        output_paths = build_trajectory_aware_sampling_probe_output_paths(output_root_path)
        artifact_paths["sampling_handoff_manifest_path"] = (
            output_paths.sampling_handoff_manifest_path
        )
        artifact_paths["gpu_validation_contract_path"] = (
            output_paths.gpu_validation_contract_path
        )
        return TrajectoryAwareSamplingProbeRunResult(
            run_id=output_root_path.name,
            output_root=output_root_path,
            readiness_decision=readiness_decision,
            selection_plan=selection_plan,
            policy_manifest=policy_manifest,
            gpu_validation_contract=gpu_validation_contract,
            artifact_paths=artifact_paths,
        )

    def _read_trajectory_mechanism_decision(
        self,
        upstream_root_path: Path,
    ) -> dict[str, Any]:
        decision_path = upstream_root_path / "artifacts" / "trajectory_mechanism_decision.json"
        if not decision_path.exists():
            raise FileNotFoundError(decision_path)
        return json.loads(decision_path.read_text(encoding="utf-8"))

    def _read_sampling_config(
        self,
        sampling_config_path: str | Path | None,
    ) -> dict[str, Any]:
        config_path = self._resolve_sampling_config_path(sampling_config_path)
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _resolve_sampling_config_path(
        self,
        sampling_config_path: str | Path | None,
    ) -> Path:
        if sampling_config_path is None:
            return self._repository_root / DEFAULT_SAMPLING_CONFIG_RELATIVE_PATH
        config_path = Path(sampling_config_path)
        if config_path.is_absolute():
            return config_path
        return self._repository_root / config_path

    def _read_gpu_validation_config(self) -> dict[str, Any]:
        config_path = self._repository_root / DEFAULT_GPU_VALIDATION_CONFIG_RELATIVE_PATH
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _write_run_handoff_manifest(
        self,
        output_root_path: Path,
        upstream_root_path: Path,
        sampling_config_path: str | Path | None,
        readiness_decision: dict[str, Any],
        selection_plan: dict[str, Any],
        policy_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        """功能: 写出只读 handoff manifest, 便于后续检查输入来源。"""
        resolved_config_path = self._resolve_sampling_config_path(sampling_config_path)
        upstream_decision_path = (
            upstream_root_path / "artifacts" / "trajectory_mechanism_decision.json"
        )
        upstream_records_path = upstream_root_path / "records" / "event_scores.jsonl"
        handoff_manifest = {
            "handoff_kind": "trajectory_aware_sampling_scaffold",
            "construction_phase": "trajectory_aware_sampling_probe",
            "upstream_trajectory_root": str(upstream_root_path),
            "upstream_trajectory_records_digest": compute_file_digest(upstream_records_path),
            "upstream_trajectory_mechanism_decision_digest": compute_file_digest(
                upstream_decision_path
            ),
            "sampling_config_digest": compute_file_digest(resolved_config_path),
            "SamplingReadinessDecision": readiness_decision.get(
                "SamplingReadinessDecision"
            ),
            "SamplingSelectionPlanDecision": selection_plan.get(
                "SamplingSelectionPlanDecision"
            ),
            "selected_record_count": selection_plan.get("selected_record_count", 0),
            "selection_plan_digest": selection_plan.get("selection_plan_digest"),
            "policy_manifest_digest": compute_object_digest(policy_manifest),
            "requires_real_gpu_validation": False,
            "next_step_requires_real_gpu_validation": policy_manifest.get(
                "next_step_requires_real_gpu_validation",
                False,
            ),
            "NextRequiredValidationBySampling": policy_manifest.get(
                "NextRequiredValidationBySampling",
                "finish_trajectory_aware_sampling_probe",
            ),
            "real_generation_allowed": False,
            "real_watermark_integration_allowed": False,
        }
        manifest_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).sampling_handoff_manifest_path
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(handoff_manifest, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return handoff_manifest

    def _write_gpu_validation_contract(
        self,
        output_root_path: Path,
        policy_manifest: dict[str, Any],
        handoff_manifest: dict[str, Any],
        gpu_validation_config: dict[str, Any],
    ) -> dict[str, Any]:
        contract_payload = build_trajectory_aware_sampling_gpu_validation_contract(
            policy_manifest,
            handoff_manifest,
            gpu_validation_config,
        )
        contract_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).gpu_validation_contract_path
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(
            json.dumps(contract_payload, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return contract_payload

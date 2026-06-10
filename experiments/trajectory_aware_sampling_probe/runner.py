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
from experiments.trajectory_aware_sampling_probe.backend_transition_guard import (
    build_trajectory_aware_sampling_backend_transition_guard,
)
from experiments.trajectory_aware_sampling_probe.backend_transition_decision import (
    build_trajectory_aware_sampling_backend_transition_decision,
)
from experiments.trajectory_aware_sampling_probe.backend_integration_decision import (
    build_trajectory_aware_sampling_backend_integration_decision,
)
from experiments.trajectory_aware_sampling_probe.backend_adapter_scaffold import (
    build_trajectory_aware_sampling_backend_adapter_scaffold,
)
from experiments.trajectory_aware_sampling_probe.backend_connection_contract import (
    build_trajectory_aware_sampling_backend_connection_contract,
)
from experiments.trajectory_aware_sampling_probe.real_backend_connection_smoke import (
    build_trajectory_aware_sampling_real_backend_connection_smoke,
)
from experiments.trajectory_aware_sampling_probe.gpu_validation_contract import (
    build_trajectory_aware_sampling_gpu_validation_contract,
)
from experiments.trajectory_aware_sampling_probe.output_layout import (
    build_trajectory_aware_sampling_probe_output_paths,
)
from experiments.trajectory_aware_sampling_probe.runtime_interface_implementation import (
    build_trajectory_aware_sampling_runtime_interface_implementation,
)
from experiments.trajectory_aware_sampling_probe.runtime_interface_scaffold import (
    build_trajectory_aware_sampling_runtime_interface_scaffold,
)
from main.core.digest import compute_file_digest, compute_object_digest
from main.core.records import RecordWriter

DEFAULT_SAMPLING_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_probe.json"
)
DEFAULT_GPU_VALIDATION_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_gpu_validation_contract.json"
)
DEFAULT_BACKEND_TRANSITION_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_backend_transition_guard.json"
)
DEFAULT_BACKEND_TRANSITION_DECISION_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_backend_transition_decision.json"
)
DEFAULT_RUNTIME_INTERFACE_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_runtime_interface_scaffold.json"
)
DEFAULT_RUNTIME_INTERFACE_IMPLEMENTATION_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_runtime_interface_implementation.json"
)
DEFAULT_BACKEND_INTEGRATION_DECISION_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_backend_integration_decision.json"
)
DEFAULT_BACKEND_ADAPTER_SCAFFOLD_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_backend_adapter_scaffold.json"
)
DEFAULT_BACKEND_CONNECTION_CONTRACT_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_backend_connection_contract.json"
)
DEFAULT_REAL_BACKEND_CONNECTION_SMOKE_CONFIG_RELATIVE_PATH = Path(
    "configs/protocol/trajectory_aware_sampling_real_backend_connection_smoke.json"
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
    backend_transition_guard: dict[str, Any]
    backend_transition_decision: dict[str, Any]
    runtime_interface_scaffold: dict[str, Any]
    runtime_interface_implementation: dict[str, Any]
    backend_integration_decision: dict[str, Any]
    backend_adapter_scaffold: dict[str, Any]
    backend_connection_contract: dict[str, Any]
    real_backend_connection_smoke: dict[str, Any]
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
        backend_transition_guard = self._write_backend_transition_guard(
            output_root_path,
            gpu_validation_contract,
            self._read_backend_transition_config(),
        )
        backend_transition_decision = self._write_backend_transition_decision(
            output_root_path,
            backend_transition_guard,
            self._read_backend_transition_decision_config(),
        )
        runtime_interface_scaffold = self._write_runtime_interface_scaffold(
            output_root_path,
            selection_plan,
            backend_transition_decision,
            self._read_runtime_interface_config(),
        )
        runtime_interface_implementation = (
            self._write_runtime_interface_implementation(
                output_root_path,
                runtime_interface_scaffold,
                self._read_runtime_interface_implementation_config(),
            )
        )
        backend_integration_decision = self._write_backend_integration_decision(
            output_root_path,
            runtime_interface_implementation,
            self._read_backend_integration_decision_config(),
        )
        backend_adapter_scaffold = self._write_backend_adapter_scaffold(
            output_root_path,
            backend_integration_decision,
            self._read_backend_adapter_scaffold_config(),
        )
        backend_connection_contract = self._write_backend_connection_contract(
            output_root_path,
            backend_adapter_scaffold,
            self._read_backend_connection_contract_config(),
        )
        real_backend_connection_smoke = self._write_real_backend_connection_smoke(
            output_root_path,
            backend_connection_contract,
            self._read_real_backend_connection_smoke_config(),
        )
        output_paths = build_trajectory_aware_sampling_probe_output_paths(output_root_path)
        artifact_paths["sampling_handoff_manifest_path"] = (
            output_paths.sampling_handoff_manifest_path
        )
        artifact_paths["gpu_validation_contract_path"] = (
            output_paths.gpu_validation_contract_path
        )
        artifact_paths["backend_transition_guard_path"] = (
            output_paths.backend_transition_guard_path
        )
        artifact_paths["backend_transition_decision_path"] = (
            output_paths.backend_transition_decision_path
        )
        artifact_paths["runtime_interface_scaffold_path"] = (
            output_paths.runtime_interface_scaffold_path
        )
        artifact_paths["runtime_interface_implementation_path"] = (
            output_paths.runtime_interface_implementation_path
        )
        artifact_paths["backend_integration_decision_path"] = (
            output_paths.backend_integration_decision_path
        )
        artifact_paths["backend_adapter_scaffold_path"] = (
            output_paths.backend_adapter_scaffold_path
        )
        artifact_paths["backend_connection_contract_path"] = (
            output_paths.backend_connection_contract_path
        )
        artifact_paths["real_backend_connection_smoke_path"] = (
            output_paths.real_backend_connection_smoke_path
        )
        return TrajectoryAwareSamplingProbeRunResult(
            run_id=output_root_path.name,
            output_root=output_root_path,
            readiness_decision=readiness_decision,
            selection_plan=selection_plan,
            policy_manifest=policy_manifest,
            gpu_validation_contract=gpu_validation_contract,
            backend_transition_guard=backend_transition_guard,
            backend_transition_decision=backend_transition_decision,
            runtime_interface_scaffold=runtime_interface_scaffold,
            runtime_interface_implementation=runtime_interface_implementation,
            backend_integration_decision=backend_integration_decision,
            backend_adapter_scaffold=backend_adapter_scaffold,
            backend_connection_contract=backend_connection_contract,
            real_backend_connection_smoke=real_backend_connection_smoke,
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

    def _read_backend_transition_config(self) -> dict[str, Any]:
        config_path = self._repository_root / DEFAULT_BACKEND_TRANSITION_CONFIG_RELATIVE_PATH
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _read_backend_transition_decision_config(self) -> dict[str, Any]:
        config_path = (
            self._repository_root
            / DEFAULT_BACKEND_TRANSITION_DECISION_CONFIG_RELATIVE_PATH
        )
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _read_runtime_interface_config(self) -> dict[str, Any]:
        config_path = self._repository_root / DEFAULT_RUNTIME_INTERFACE_CONFIG_RELATIVE_PATH
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _read_runtime_interface_implementation_config(self) -> dict[str, Any]:
        config_path = (
            self._repository_root
            / DEFAULT_RUNTIME_INTERFACE_IMPLEMENTATION_CONFIG_RELATIVE_PATH
        )
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _read_backend_integration_decision_config(self) -> dict[str, Any]:
        config_path = (
            self._repository_root
            / DEFAULT_BACKEND_INTEGRATION_DECISION_CONFIG_RELATIVE_PATH
        )
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _read_backend_adapter_scaffold_config(self) -> dict[str, Any]:
        config_path = (
            self._repository_root
            / DEFAULT_BACKEND_ADAPTER_SCAFFOLD_CONFIG_RELATIVE_PATH
        )
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _read_backend_connection_contract_config(self) -> dict[str, Any]:
        config_path = (
            self._repository_root
            / DEFAULT_BACKEND_CONNECTION_CONTRACT_CONFIG_RELATIVE_PATH
        )
        return json.loads(config_path.read_text(encoding="utf-8"))

    def _read_real_backend_connection_smoke_config(self) -> dict[str, Any]:
        config_path = (
            self._repository_root
            / DEFAULT_REAL_BACKEND_CONNECTION_SMOKE_CONFIG_RELATIVE_PATH
        )
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

    def _write_backend_transition_guard(
        self,
        output_root_path: Path,
        gpu_validation_contract: dict[str, Any],
        backend_transition_config: dict[str, Any],
    ) -> dict[str, Any]:
        guard_payload = build_trajectory_aware_sampling_backend_transition_guard(
            gpu_validation_contract,
            backend_transition_config,
        )
        guard_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).backend_transition_guard_path
        guard_path.parent.mkdir(parents=True, exist_ok=True)
        guard_path.write_text(
            json.dumps(guard_payload, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return guard_payload

    def _write_backend_transition_decision(
        self,
        output_root_path: Path,
        backend_transition_guard: dict[str, Any],
        backend_transition_decision_config: dict[str, Any],
    ) -> dict[str, Any]:
        decision_payload = build_trajectory_aware_sampling_backend_transition_decision(
            backend_transition_guard,
            backend_transition_decision_config,
        )
        decision_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).backend_transition_decision_path
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        decision_path.write_text(
            json.dumps(decision_payload, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return decision_payload

    def _write_runtime_interface_scaffold(
        self,
        output_root_path: Path,
        selection_plan: dict[str, Any],
        backend_transition_decision: dict[str, Any],
        runtime_interface_config: dict[str, Any],
    ) -> dict[str, Any]:
        scaffold_payload = build_trajectory_aware_sampling_runtime_interface_scaffold(
            selection_plan,
            backend_transition_decision,
            runtime_interface_config,
        )
        scaffold_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).runtime_interface_scaffold_path
        scaffold_path.parent.mkdir(parents=True, exist_ok=True)
        scaffold_path.write_text(
            json.dumps(scaffold_payload, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        return scaffold_payload

    def _write_runtime_interface_implementation(
        self,
        output_root_path: Path,
        runtime_interface_scaffold: dict[str, Any],
        runtime_interface_implementation_config: dict[str, Any],
    ) -> dict[str, Any]:
        implementation_payload = (
            build_trajectory_aware_sampling_runtime_interface_implementation(
                runtime_interface_scaffold,
                runtime_interface_implementation_config,
            )
        )
        implementation_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).runtime_interface_implementation_path
        implementation_path.parent.mkdir(parents=True, exist_ok=True)
        implementation_path.write_text(
            json.dumps(
                implementation_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return implementation_payload


    def _write_backend_integration_decision(
        self,
        output_root_path: Path,
        runtime_interface_implementation: dict[str, Any],
        backend_integration_decision_config: dict[str, Any],
    ) -> dict[str, Any]:
        decision_payload = build_trajectory_aware_sampling_backend_integration_decision(
            runtime_interface_implementation,
            backend_integration_decision_config,
        )
        decision_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).backend_integration_decision_path
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        decision_path.write_text(
            json.dumps(
                decision_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return decision_payload

    def _write_backend_adapter_scaffold(
        self,
        output_root_path: Path,
        backend_integration_decision: dict[str, Any],
        backend_adapter_scaffold_config: dict[str, Any],
    ) -> dict[str, Any]:
        scaffold_payload = build_trajectory_aware_sampling_backend_adapter_scaffold(
            backend_integration_decision,
            backend_adapter_scaffold_config,
        )
        scaffold_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).backend_adapter_scaffold_path
        scaffold_path.parent.mkdir(parents=True, exist_ok=True)
        scaffold_path.write_text(
            json.dumps(
                scaffold_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return scaffold_payload

    def _write_backend_connection_contract(
        self,
        output_root_path: Path,
        backend_adapter_scaffold: dict[str, Any],
        backend_connection_contract_config: dict[str, Any],
    ) -> dict[str, Any]:
        contract_payload = build_trajectory_aware_sampling_backend_connection_contract(
            backend_adapter_scaffold,
            backend_connection_contract_config,
        )
        contract_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).backend_connection_contract_path
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(
            json.dumps(
                contract_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return contract_payload

    def _write_real_backend_connection_smoke(
        self,
        output_root_path: Path,
        backend_connection_contract: dict[str, Any],
        real_backend_connection_smoke_config: dict[str, Any],
    ) -> dict[str, Any]:
        smoke_payload = build_trajectory_aware_sampling_real_backend_connection_smoke(
            backend_connection_contract,
            real_backend_connection_smoke_config,
        )
        smoke_path = build_trajectory_aware_sampling_probe_output_paths(
            output_root_path
        ).real_backend_connection_smoke_path
        smoke_path.parent.mkdir(parents=True, exist_ok=True)
        smoke_path.write_text(
            json.dumps(
                smoke_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return smoke_payload

"""
文件用途：定义 trajectory-aware sampling probe 的输出布局。
File purpose: Define the governed output layout for the trajectory-aware sampling probe.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from main.protocol.output_layout import BaseRunOutputPaths, build_base_run_output_paths


@dataclass(frozen=True)
class TrajectoryAwareSamplingProbeOutputPaths(BaseRunOutputPaths):
    """功能：记录下一阶段 decision-only scaffold 的固定输出路径。

    该布局属于项目特定写法。它只为后续构建预留受治理的决策与报告位置,
    不表示当前已经允许真实生成、真实采样调度或真实 watermark 集成。
    """

    sampling_readiness_decision_path: Path
    sampling_policy_manifest_path: Path
    sampling_selection_plan_path: Path
    sampling_handoff_manifest_path: Path
    gpu_validation_contract_path: Path
    backend_transition_guard_path: Path
    backend_transition_decision_path: Path
    runtime_interface_scaffold_path: Path
    runtime_interface_implementation_path: Path
    backend_integration_decision_path: Path
    backend_adapter_scaffold_path: Path
    backend_connection_contract_path: Path
    real_backend_connection_smoke_path: Path
    real_backend_connection_smoke_handoff_path: Path
    real_gpu_backend_connection_smoke_result_gate_path: Path
    real_backend_runtime_validation_gate_path: Path
    explicit_real_generation_transition_decision_path: Path
    controlled_single_real_generation_request_scaffold_path: Path
    manual_controlled_single_request_result_gate_path: Path
    governed_real_generation_execution_authorization_decision_path: Path
    sampling_probe_report_path: Path

    def table_paths(self) -> list[Path]:
        return []

    def figure_paths(self) -> list[Path]:
        return []


def build_trajectory_aware_sampling_probe_output_paths(
    output_root: str | Path,
) -> TrajectoryAwareSamplingProbeOutputPaths:
    """功能：构建 trajectory-aware sampling probe 的固定输出布局。

    此处复用通用 `BaseRunOutputPaths`, 使未来真正写出 records / thresholds 时仍能保持
    与现有协议布局一致；当前 scaffold 只使用 artifacts 与 reports 下的决策文件。
    """
    output_root_path = Path(output_root)
    base_paths = build_base_run_output_paths(output_root_path)
    return TrajectoryAwareSamplingProbeOutputPaths(
        root_path=base_paths.root_path,
        event_scores_path=base_paths.event_scores_path,
        thresholds_path=base_paths.thresholds_path,
        run_manifest_path=base_paths.run_manifest_path,
        artifact_manifest_path=base_paths.artifact_manifest_path,
        runtime_manifest_path=base_paths.runtime_manifest_path,
        runtime_config_path=base_paths.runtime_config_path,
        sampling_readiness_decision_path=(
            output_root_path / "artifacts" / "sampling_readiness_decision.json"
        ),
        sampling_policy_manifest_path=(
            output_root_path / "artifacts" / "sampling_policy_manifest.json"
        ),
        sampling_selection_plan_path=(
            output_root_path / "artifacts" / "sampling_selection_plan.json"
        ),
        sampling_handoff_manifest_path=(
            output_root_path / "artifacts" / "sampling_handoff_manifest.json"
        ),
        gpu_validation_contract_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_gpu_validation_contract.json"
        ),
        backend_transition_guard_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_backend_transition_guard.json"
        ),
        backend_transition_decision_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_backend_transition_decision.json"
        ),
        runtime_interface_scaffold_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_runtime_interface_scaffold.json"
        ),
        runtime_interface_implementation_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_runtime_interface_implementation.json"
        ),
        backend_integration_decision_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_backend_integration_decision.json"
        ),
        backend_adapter_scaffold_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_backend_adapter_scaffold.json"
        ),
        backend_connection_contract_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_backend_connection_contract.json"
        ),
        real_backend_connection_smoke_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_real_backend_connection_smoke.json"
        ),
        real_backend_connection_smoke_handoff_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_real_backend_connection_smoke_handoff.json"
        ),
        real_gpu_backend_connection_smoke_result_gate_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_real_gpu_backend_connection_smoke_result_gate.json"
        ),
        real_backend_runtime_validation_gate_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_real_backend_runtime_validation_gate.json"
        ),
        explicit_real_generation_transition_decision_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_explicit_real_generation_transition_decision.json"
        ),
        controlled_single_real_generation_request_scaffold_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_controlled_single_real_generation_request_scaffold.json"
        ),
        manual_controlled_single_request_result_gate_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_manual_controlled_single_request_result_gate.json"
        ),
        governed_real_generation_execution_authorization_decision_path=(
            output_root_path
            / "artifacts"
            / "trajectory_aware_sampling_governed_real_generation_execution_authorization_decision.json"
        ),
        sampling_probe_report_path=(
            output_root_path / "reports" / "trajectory_aware_sampling_probe_report.md"
        ),
    )

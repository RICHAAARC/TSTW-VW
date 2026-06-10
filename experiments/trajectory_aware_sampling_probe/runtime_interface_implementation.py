"""
文件用途: 构建 trajectory-aware sampling 的非后端连接版 runtime interface implementation。
Module type: General module
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any

from main.core.digest import compute_object_digest


_READY_SCAFFOLD_DECISION = "READY_FOR_REAL_GPU_RUNTIME_INTERFACE_IMPLEMENTATION"
_READY_IMPLEMENTATION_DECISION = "READY_FOR_BACKEND_INTEGRATION_DECISION"


def build_trajectory_aware_sampling_runtime_interface_implementation(
    runtime_interface_scaffold: dict[str, Any],
    runtime_interface_implementation_config: dict[str, Any],
    gpu_environment_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """功能: 生成非后端连接版 runtime interface implementation 产物。

    该函数属于项目特定写法。它把已经冻结的 request prototype 转换为 dry-run request 和 result manifest,
    并记录 GPU preflight 摘要。此处只验证接口形状和治理边界, 不连接真实 DiT / Flow Matching 后端,
    不生成视频, 不执行真实 watermark 嵌入或检测。其通用价值在于: 在高成本真实后端接入之前,
    先让后续 runtime 的输入、输出、失败路径和环境检查具备可审计的稳定格式。
    """
    blocking_reasons: list[str] = []

    if (
        runtime_interface_scaffold.get(
            "TrajectoryAwareSamplingRuntimeInterfaceScaffoldDecision"
        )
        != runtime_interface_implementation_config.get(
            "required_runtime_interface_scaffold_decision",
            _READY_SCAFFOLD_DECISION,
        )
    ):
        blocking_reasons.append("runtime_interface_scaffold_not_ready")

    if (
        runtime_interface_scaffold.get(
            "NextAllowedConstructionAfterRuntimeInterfaceScaffold"
        )
        != runtime_interface_implementation_config.get(
            "required_next_allowed_construction_after_scaffold",
            "real_gpu_runtime_interface_implementation",
        )
    ):
        blocking_reasons.append("runtime_interface_scaffold_next_construction_mismatch")

    if runtime_interface_scaffold.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("scaffold_enabled_runtime_backend_connection")
    if runtime_interface_scaffold.get("real_generation_allowed") is not False:
        blocking_reasons.append("scaffold_enabled_real_generation")
    if runtime_interface_scaffold.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("scaffold_enabled_real_watermark")

    request_prototypes = runtime_interface_scaffold.get("request_prototypes", [])
    if not isinstance(request_prototypes, list):
        request_prototypes = []
    minimum_request_count = int(
        runtime_interface_implementation_config.get("minimum_request_prototype_count", 1)
    )
    if len(request_prototypes) < minimum_request_count:
        blocking_reasons.append("request_prototype_count_below_minimum")

    if (
        runtime_interface_implementation_config.get(
            "runtime_interface_implementation_allowed"
        )
        is not True
    ):
        blocking_reasons.append("config_runtime_interface_implementation_not_allowed")
    if runtime_interface_implementation_config.get("runtime_backend_connection_allowed") is not False:
        blocking_reasons.append("config_enabled_runtime_backend_connection")
    if runtime_interface_implementation_config.get("real_generation_allowed") is not False:
        blocking_reasons.append("config_enabled_real_generation")
    if runtime_interface_implementation_config.get("real_watermark_integration_allowed") is not False:
        blocking_reasons.append("config_enabled_real_watermark")

    gpu_preflight_summary = _build_gpu_preflight_summary(gpu_environment_override)
    if (
        runtime_interface_implementation_config.get("gpu_preflight_required_for_decision")
        is True
        and gpu_preflight_summary["preflight_status"] != "available"
    ):
        blocking_reasons.append("gpu_preflight_not_available")

    decision = _READY_IMPLEMENTATION_DECISION if not blocking_reasons else "INCONCLUSIVE"
    dry_run_requests = [
        _build_dry_run_request(request_prototype, index)
        for index, request_prototype in enumerate(request_prototypes)
        if isinstance(request_prototype, dict)
    ]
    dry_run_result_manifests = [
        _build_dry_run_result_manifest(
            request,
            runtime_interface_implementation_config,
        )
        for request in dry_run_requests
    ]
    payload: dict[str, Any] = {
        "TrajectoryAwareSamplingRuntimeInterfaceImplementationDecision": decision,
        "TrajectoryAwareSamplingRuntimeInterfaceImplementationBlockingReasons": (
            blocking_reasons
        ),
        "project_stage": runtime_interface_implementation_config.get("project_stage"),
        "construction_phase": runtime_interface_implementation_config.get(
            "construction_phase"
        ),
        "target_construction_phase": runtime_interface_implementation_config.get(
            "target_construction_phase"
        ),
        "runtime_mode": runtime_interface_implementation_config.get("runtime_mode"),
        "runtime_interface_implementation_allowed": decision == _READY_IMPLEMENTATION_DECISION,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "gpu_preflight_summary": gpu_preflight_summary,
        "dry_run_request_count": len(dry_run_requests),
        "dry_run_result_manifest_count": len(dry_run_result_manifests),
        "dry_run_requests": dry_run_requests,
        "dry_run_result_manifests": dry_run_result_manifests,
        "runtime_interface_scaffold_digest": runtime_interface_scaffold.get(
            "runtime_interface_scaffold_digest"
        ),
        "runtime_interface_scaffold_payload_digest": compute_object_digest(
            runtime_interface_scaffold
        ),
        "forbidden_runtime_capabilities_until_backend_integration_decision": list(
            runtime_interface_implementation_config.get(
                "forbidden_runtime_capabilities_until_backend_integration_decision",
                [],
            )
        ),
        "NextAllowedConstructionAfterRuntimeInterfaceImplementation": (
            runtime_interface_implementation_config.get(
                "approved_next_construction",
                "backend_integration_decision",
            )
            if decision == _READY_IMPLEMENTATION_DECISION
            else "finish_trajectory_aware_sampling_probe"
        ),
    }
    payload["runtime_interface_implementation_digest"] = compute_object_digest(
        {
            key: value
            for key, value in payload.items()
            if key != "runtime_interface_implementation_digest"
        }
    )
    return payload


def _build_gpu_preflight_summary(
    gpu_environment_override: dict[str, Any] | None,
) -> dict[str, Any]:
    if gpu_environment_override is not None:
        return _normalize_gpu_preflight_summary(gpu_environment_override)

    torch_cuda_available = False
    cuda_device_name = ""
    try:
        import torch  # type: ignore

        torch_cuda_available = bool(torch.cuda.is_available())
        if torch_cuda_available:
            cuda_device_name = str(torch.cuda.get_device_name(0))
    except Exception:
        torch_cuda_available = False
        cuda_device_name = ""

    nvidia_smi_path = shutil.which("nvidia-smi")
    nvidia_smi_visible = nvidia_smi_path is not None
    driver_version = ""
    if nvidia_smi_path:
        try:
            completed = subprocess.run(
                [
                    nvidia_smi_path,
                    "--query-gpu=driver_version",
                    "--format=csv,noheader",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            driver_version = completed.stdout.splitlines()[0].strip() if completed.stdout else ""
        except Exception:
            driver_version = ""

    gpu_available = torch_cuda_available or nvidia_smi_visible
    return {
        "gpu_available": gpu_available,
        "cuda_available": torch_cuda_available,
        "device_name": cuda_device_name,
        "driver_version": driver_version,
        "preflight_status": "available" if gpu_available else "unavailable",
        "nvidia_smi_visible": nvidia_smi_visible,
        "python_platform": platform.platform(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
    }


def _normalize_gpu_preflight_summary(payload: dict[str, Any]) -> dict[str, Any]:
    gpu_available = bool(payload.get("gpu_available", False))
    cuda_available = bool(payload.get("cuda_available", gpu_available))
    preflight_status = str(
        payload.get("preflight_status", "available" if gpu_available else "unavailable")
    )
    return {
        "gpu_available": gpu_available,
        "cuda_available": cuda_available,
        "device_name": str(payload.get("device_name", "")),
        "driver_version": str(payload.get("driver_version", "")),
        "preflight_status": preflight_status,
        "nvidia_smi_visible": bool(payload.get("nvidia_smi_visible", gpu_available)),
        "python_platform": str(payload.get("python_platform", platform.platform())),
        "cuda_visible_devices": str(payload.get("cuda_visible_devices", "")),
    }


def _build_dry_run_request(
    request_prototype: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    request_payload = {
        "request_id": str(request_prototype.get("request_id", f"dry_run_request_{index:04d}")),
        "selected_record_digest": str(request_prototype.get("selected_record_digest", "")),
        "event_id": str(request_prototype.get("event_id", "")),
        "sample_id": str(request_prototype.get("sample_id", "")),
        "method_variant": str(request_prototype.get("method_variant", "")),
        "attack_name": str(request_prototype.get("attack_name", "")),
        "selection_policy_kind": str(request_prototype.get("selection_policy_kind", "")),
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "dry_run_only": True,
    }
    request_payload["dry_run_request_digest"] = compute_object_digest(request_payload)
    return request_payload


def _build_dry_run_result_manifest(
    dry_run_request: dict[str, Any],
    runtime_interface_implementation_config: dict[str, Any],
) -> dict[str, Any]:
    manifest_payload = {
        "request_id": dry_run_request["request_id"],
        "runtime_status": runtime_interface_implementation_config.get(
            "dry_run_runtime_status",
            "interface_dry_run_only",
        ),
        "backend_status": runtime_interface_implementation_config.get(
            "dry_run_backend_status",
            "not_connected_by_governance",
        ),
        "result_artifact_digest": None,
        "runtime_error_message": None,
        "runtime_backend_connection_allowed": False,
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "dry_run_request_digest": dry_run_request["dry_run_request_digest"],
    }
    manifest_payload["dry_run_result_manifest_digest"] = compute_object_digest(
        manifest_payload
    )
    return manifest_payload

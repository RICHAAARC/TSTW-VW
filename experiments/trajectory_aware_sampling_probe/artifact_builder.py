"""
文件用途: 写出 trajectory-aware sampling probe 的最小可重建 scaffold 产物。
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.trajectory_aware_sampling_probe.output_layout import (
    build_trajectory_aware_sampling_probe_output_paths,
)
from experiments.trajectory_aware_sampling_probe.readiness_audit import (
    build_trajectory_aware_sampling_readiness_decision,
)
from experiments.trajectory_aware_sampling_probe.selection_plan_builder import (
    build_record_digest_selection_plan,
)


def build_trajectory_aware_sampling_artifacts(
    event_score_records: list[dict[str, Any]],
    trajectory_mechanism_decision: dict[str, Any],
    sampling_probe_config: dict[str, Any],
    output_root: str | Path,
) -> dict[str, Path]:
    """功能: 从阶段 3 records 和机制决策写出 sampling scaffold 产物。

    此处设计的主要考虑在于让下一阶段的最小闭环可以被本地 CPU 测试验证: readiness、selection plan、
    policy manifest 和报告都由受治理输入生成。该函数不写 `records/` 或 `thresholds/`, 不生成视频,
    不调用真实模型, 因此仍属于 transition preparation, 不属于真实采样运行。
    """
    output_paths = build_trajectory_aware_sampling_probe_output_paths(output_root)
    readiness_decision = build_trajectory_aware_sampling_readiness_decision(
        trajectory_mechanism_decision,
        sampling_probe_config,
    )
    selection_plan = build_record_digest_selection_plan(
        event_score_records,
        trajectory_mechanism_decision,
        sampling_probe_config,
    )
    policy_manifest = build_sampling_policy_manifest(
        readiness_decision,
        selection_plan,
        sampling_probe_config,
    )

    _write_json(output_paths.sampling_readiness_decision_path, readiness_decision)
    _write_json(output_paths.sampling_selection_plan_path, selection_plan)
    _write_json(output_paths.sampling_policy_manifest_path, policy_manifest)
    output_paths.sampling_probe_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.sampling_probe_report_path.write_text(
        build_trajectory_aware_sampling_report_text(
            readiness_decision,
            selection_plan,
            policy_manifest,
        ),
        encoding="utf-8",
    )
    return {
        "sampling_readiness_decision_path": output_paths.sampling_readiness_decision_path,
        "sampling_selection_plan_path": output_paths.sampling_selection_plan_path,
        "sampling_policy_manifest_path": output_paths.sampling_policy_manifest_path,
        "sampling_probe_report_path": output_paths.sampling_probe_report_path,
    }


def build_sampling_policy_manifest(
    readiness_decision: dict[str, Any],
    selection_plan: dict[str, Any],
    sampling_probe_config: dict[str, Any],
) -> dict[str, Any]:
    """功能: 汇总 sampling scaffold 的策略 manifest。

    该 manifest 只描述如何从已有 records 中选择摘要记录。它显式保留禁用真实生成和真实 watermark 的布尔值,
    便于后续 notebook 或 CLI 在读取该文件时先执行边界检查。
    """
    outputs = sampling_probe_config.get("outputs", {})
    if not isinstance(outputs, dict):
        outputs = {}
    return {
        "construction_phase": sampling_probe_config.get("construction_phase"),
        "selection_output_kind": selection_plan.get("selection_output_kind"),
        "SamplingReadinessDecision": readiness_decision.get("SamplingReadinessDecision"),
        "SamplingSelectionPlanDecision": selection_plan.get(
            "SamplingSelectionPlanDecision"
        ),
        "SamplingSelectionBlockingReasons": selection_plan.get(
            "SamplingSelectionBlockingReasons",
            [],
        ),
        "selected_sampling_policy_kind": selection_plan.get(
            "selected_sampling_policy_kind"
        ),
        "allowed_sampling_policy_kinds": selection_plan.get(
            "allowed_sampling_policy_kinds",
            [],
        ),
        "selected_record_count": selection_plan.get("selected_record_count", 0),
        "source_record_count": selection_plan.get("source_record_count", 0),
        "selection_plan_digest": selection_plan.get("selection_plan_digest"),
        "upstream_trajectory_decision_digest": selection_plan.get(
            "upstream_trajectory_decision_digest"
        ),
        "sampling_readiness_decision_path": outputs.get(
            "sampling_readiness_decision_path",
            "artifacts/sampling_readiness_decision.json",
        ),
        "sampling_selection_plan_path": outputs.get(
            "sampling_selection_plan_path",
            "artifacts/sampling_selection_plan.json",
        ),
        "sampling_probe_report_path": outputs.get(
            "sampling_probe_report_path",
            "reports/trajectory_aware_sampling_probe_report.md",
        ),
        "real_generation_allowed": False,
        "real_watermark_integration_allowed": False,
        "requires_real_gpu_validation": False,
    }


def build_trajectory_aware_sampling_report_text(
    readiness_decision: dict[str, Any],
    selection_plan: dict[str, Any],
    policy_manifest: dict[str, Any],
) -> str:
    """功能: 生成人可读 sampling scaffold 报告文本。"""
    return "\n".join(
        [
            "# Trajectory-Aware Sampling Probe Report",
            "",
            f"sampling_readiness_decision: {readiness_decision.get('SamplingReadinessDecision')}",
            f"sampling_selection_plan_decision: {selection_plan.get('SamplingSelectionPlanDecision')}",
            f"selected_sampling_policy_kind: {selection_plan.get('selected_sampling_policy_kind')}",
            f"selected_record_count: {selection_plan.get('selected_record_count')}",
            f"source_record_count: {selection_plan.get('source_record_count')}",
            f"selection_plan_digest: {selection_plan.get('selection_plan_digest')}",
            f"requires_real_gpu_validation: {policy_manifest.get('requires_real_gpu_validation')}",
            f"real_generation_allowed: {policy_manifest.get('real_generation_allowed')}",
            f"real_watermark_integration_allowed: {policy_manifest.get('real_watermark_integration_allowed')}",
            "",
            (
                "This report is generated from governed trajectory records, the upstream "
                "trajectory mechanism decision, and the sampling probe config. It does not "
                "execute real generation or real watermark integration."
            ),
            "",
        ]
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

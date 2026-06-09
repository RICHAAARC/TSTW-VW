"""
文件用途：读取并校验 real_video_vae_latent_probe 冻结 baseline 包。
File purpose: Load and validate the frozen real-video VAE-latent baseline package.
Module type: General module
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from main.core.digest import compute_file_digest, compute_object_digest
from main.core.records import RecordWriter


REQUIRED_STAGE_TWO_PROTOCOL = "aligned_payload_safety"
REQUIRED_NEXT_PHASE = "trajectory_statistic_probe"


@dataclass(frozen=True)
class FrozenBaselinePackage:
    """功能：保存已校验的冻结 baseline 输入。

    该结构属于项目特定写法, 用于把前一语义阶段的 records、thresholds、decision
    与 manifest 固定为阶段 3 的只读依赖。其他项目可以复用这种“先校验再运行”的
    loader 结构, 但字段名需要替换为各自协议中的 gate 名称。
    """

    baseline_root: Path
    event_score_records: list[dict[str, Any]]
    threshold_records: list[dict[str, Any]]
    run_manifest: dict[str, Any]
    mechanism_decision: dict[str, Any]
    frozen_baseline_manifest: dict[str, Any]


def load_real_video_vae_latent_frozen_baseline(
    baseline_root: str | Path,
) -> FrozenBaselinePackage:
    """功能：读取并校验阶段 3 所需的冻结 baseline 包。

    Args:
        baseline_root: real_video_vae_latent_probe 输出根目录。

    Returns:
        已校验的 `FrozenBaselinePackage`。
    """
    root_path = Path(baseline_root)
    if not root_path.exists():
        raise FileNotFoundError(root_path)

    record_writer = RecordWriter(root_path)
    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    run_manifest = record_writer.read_run_manifest()
    mechanism_decision_path = root_path / "artifacts" / "stage2_mechanism_decision.json"
    if not mechanism_decision_path.exists():
        raise FileNotFoundError(mechanism_decision_path)
    mechanism_decision = json.loads(mechanism_decision_path.read_text(encoding="utf-8"))

    blocking_reasons = validate_real_video_vae_latent_frozen_baseline_payload(
        event_score_records,
        threshold_records,
        run_manifest,
        mechanism_decision,
    )
    if blocking_reasons:
        raise ValueError(
            "frozen baseline did not pass trajectory dependency gate: "
            + ", ".join(blocking_reasons)
        )

    frozen_manifest = build_stage2_frozen_baseline_manifest(
        root_path,
        event_score_records,
        threshold_records,
        run_manifest,
        mechanism_decision,
        mechanism_decision_path,
    )
    return FrozenBaselinePackage(
        baseline_root=root_path,
        event_score_records=event_score_records,
        threshold_records=threshold_records,
        run_manifest=run_manifest,
        mechanism_decision=mechanism_decision,
        frozen_baseline_manifest=frozen_manifest,
    )


def validate_real_video_vae_latent_frozen_baseline_payload(
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
    run_manifest: dict[str, Any],
    mechanism_decision: dict[str, Any],
) -> list[str]:
    """功能：返回冻结 baseline 是否可作为 trajectory probe 前置依赖。

    Args:
        event_score_records: baseline event records。
        threshold_records: baseline threshold records。
        run_manifest: baseline run manifest。
        mechanism_decision: baseline mechanism decision。

    Returns:
        blocking reason 列表, 空列表表示依赖通过。
    """
    blocking_reasons: list[str] = []
    if not event_score_records:
        blocking_reasons.append("baseline_event_score_records_missing")
    if not threshold_records:
        blocking_reasons.append("baseline_threshold_records_missing")
    if not run_manifest:
        blocking_reasons.append("baseline_run_manifest_missing")

    if mechanism_decision.get("Stage2ImplementationDecision") != "PASS":
        blocking_reasons.append("stage2_implementation_not_passed")
    if mechanism_decision.get("Stage2MechanismDecision") != "PASS":
        blocking_reasons.append("stage2_mechanism_not_passed")
    if mechanism_decision.get("Stage2MechanismBlockingReasons", []) != []:
        blocking_reasons.append("stage2_mechanism_blocking_reasons_not_empty")
    if mechanism_decision.get("stage2_mechanism_protocol") != REQUIRED_STAGE_TWO_PROTOCOL:
        blocking_reasons.append("stage2_mechanism_protocol_not_aligned_payload_safety")
    if mechanism_decision.get("sync_confidence_gate_rule") != "aligned_payload_safety_gate":
        blocking_reasons.append("sync_confidence_gate_rule_not_aligned_payload_safety_gate")
    negative_rescue_count = mechanism_decision.get(
        "negative_rescue_over_threshold_count",
        -1,
    )
    if not isinstance(negative_rescue_count, int) or negative_rescue_count != 0:
        blocking_reasons.append("negative_rescue_over_threshold_count_not_zero")
    if mechanism_decision.get("NextAllowedStageByMechanism") != REQUIRED_NEXT_PHASE:
        blocking_reasons.append("next_allowed_stage_not_trajectory_statistic_probe")

    if _any_baseline_record_has_trajectory_score(event_score_records):
        blocking_reasons.append("baseline_s_traj_must_be_null")
    return blocking_reasons


def build_stage2_frozen_baseline_manifest(
    baseline_root: Path,
    event_score_records: list[dict[str, Any]],
    threshold_records: list[dict[str, Any]],
    run_manifest: dict[str, Any],
    mechanism_decision: dict[str, Any],
    mechanism_decision_path: Path,
) -> dict[str, Any]:
    """功能：生成冻结 baseline manifest。

    Args:
        baseline_root: baseline 输出根目录。
        event_score_records: baseline event records。
        threshold_records: baseline threshold records。
        run_manifest: baseline run manifest。
        mechanism_decision: baseline mechanism decision。
        mechanism_decision_path: mechanism decision 文件路径。

    Returns:
        可写入阶段 3 artifacts 的 manifest 字典。
    """
    return {
        "Stage2FrozenBaselineManifest": "PASSED",
        "baseline_construction_phase": run_manifest.get("construction_phase"),
        "baseline_root": str(baseline_root),
        "baseline_run_id": run_manifest.get("run_id"),
        "stage2_mechanism_protocol": mechanism_decision.get("stage2_mechanism_protocol"),
        "Stage2ImplementationDecision": mechanism_decision.get("Stage2ImplementationDecision"),
        "Stage2MechanismDecision": mechanism_decision.get("Stage2MechanismDecision"),
        "Stage2DependencyStatus": "PASSED",
        "baseline_records_digest": compute_object_digest(event_score_records),
        "baseline_thresholds_digest": compute_object_digest(threshold_records),
        "baseline_run_manifest_digest": compute_object_digest(run_manifest),
        "baseline_mechanism_decision_digest": compute_file_digest(mechanism_decision_path),
        "baseline_record_count": len(event_score_records),
        "baseline_threshold_count": len(threshold_records),
    }


def _any_baseline_record_has_trajectory_score(
    event_score_records: list[dict[str, Any]],
) -> bool:
    for record in event_score_records:
        evidence_scores = record.get("evidence_scores", {})
        if evidence_scores.get("S_traj") is not None:
            return True
    return False

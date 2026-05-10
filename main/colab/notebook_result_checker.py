"""
文件用途：检查阶段 2 scaffold 输出完整性。
File purpose: Check the completeness of stage-two scaffold outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from main.core.records import RecordWriter
from main.protocol.real_video_vae_latent_paths import build_real_video_vae_latent_output_paths


def check_real_video_vae_latent_outputs(
    run_root: str | Path,
    construction_phase: str = "real_video_vae_latent_probe",
    run_mode: str = "smoke",
    require_formal_pass_criteria: bool = False,
) -> dict[str, Any]:
    """功能：检查阶段 2 运行目录中的关键产物与约束。

    Check the required artifacts and constraints for a stage-two run directory.

    Args:
        run_root: Run root path.
        construction_phase: Expected construction phase.
        run_mode: Runtime mode label.
        require_formal_pass_criteria: Whether to require a formal PASS decision.

    Returns:
        A dictionary containing the check results.
    """
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    record_writer = RecordWriter(run_root)
    event_score_records = record_writer.read_event_score_records()
    threshold_records = record_writer.read_threshold_records()
    report_fields = _parse_report_fields(output_paths.report_path.read_text(encoding="utf-8"))
    required_paths = {
        "event_scores": output_paths.event_scores_path.exists(),
        "thresholds": output_paths.thresholds_path.exists(),
        "main_tpr_fpr_table": output_paths.main_tpr_fpr_table_path.exists(),
        "real_video_attack_breakdown": output_paths.real_video_attack_breakdown_path.exists(),
        "quality_table": output_paths.quality_table_path.exists(),
        "temporal_consistency_table": output_paths.temporal_consistency_table_path.exists(),
        "real_video_vae_latent_governance_summary": output_paths.real_video_vae_latent_governance_summary_path.exists(),
        "report": output_paths.report_path.exists(),
        "colab_runtime_manifest": output_paths.colab_runtime_manifest_path.exists(),
        "artifact_manifest": output_paths.artifact_manifest_path.exists(),
    }
    real_video_vae_latent_decision = report_fields.get("RealVideoVaeLatentDecision", "INCONCLUSIVE")
    blocking_reasons = [
        reason.strip()
        for reason in report_fields.get("BlockingReasons", "").replace(";", ",").split(",")
        if reason.strip()
    ]
    next_allowed_stage = report_fields.get(
        "NextAllowedStage",
        "remain_in_real_video_vae_latent_probe",
    )
    all_s_traj_null = all(
        record["evidence_scores"].get("S_traj") is None
        for record in event_score_records
    )
    construction_phase_matches = all(
        record.get("mechanism_trace", {}).get("construction_phase") == construction_phase
        for record in event_score_records
    )
    status = all(required_paths.values()) and bool(event_score_records) and bool(threshold_records)
    status = status and all_s_traj_null and construction_phase_matches
    if require_formal_pass_criteria:
        status = status and run_mode == "formal" and real_video_vae_latent_decision == "PASS"
    return {
        "status": status,
        "required_paths": required_paths,
        "record_count": len(event_score_records),
        "threshold_count": len(threshold_records),
        "all_s_traj_null": all_s_traj_null,
        "construction_phase_matches": construction_phase_matches,
        "RealVideoVaeLatentDecision": real_video_vae_latent_decision,
        "BlockingReasons": blocking_reasons,
        "NextAllowedStage": next_allowed_stage,
    }


def _parse_report_fields(report_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in report_text.splitlines():
        if not line.startswith("- ") or ": " not in line:
            continue
        field_name, field_value = line[2:].split(": ", 1)
        fields[field_name] = field_value
    return fields


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Check the governed placeholder stage-two outputs.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--construction-phase", default="real_video_vae_latent_probe")
    parser.add_argument("--run-mode", default="smoke")
    parser.add_argument("--require-formal-pass-criteria", action="store_true")
    parser.add_argument("--output-path", default=None)
    args = parser.parse_args(argv)
    result = check_real_video_vae_latent_outputs(
        run_root=args.run_root,
        construction_phase=args.construction_phase,
        run_mode=args.run_mode,
        require_formal_pass_criteria=args.require_formal_pass_criteria,
    )
    if args.output_path:
        output_path = Path(args.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
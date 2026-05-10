"""
File purpose: Run governed stage-one synthetic tubelet-sync profiles.
Module type: General module
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main.core.records import RecordWriter
from main.protocol.ablation_runner import AblationRunner


PROFILE_SAMPLE_DEFAULTS = {
    "tiny": 1,
    "smoke": 2,
    "proof": 2,
    "formal": 2,
}
KEY_REPORT_FIELDS = (
    "closure_target_pass",
    "validation_target_fpr_pass",
    "strict_target_fpr_pass",
    "primary_stage1_completion_pass",
    "primary_strict_target_fpr_pass",
    "derived_sweep_strict_target_fpr_pass",
    "overall_stage1_audit_pass",
    "tubelet_only_beats_frame_prc_under_some_attack",
    "tubelet_sync_beats_tubelet_only_under_temporal_crop_or_local_clip",
    "tubelet_sync_beats_tubelet_only_under_speed_change",
    "speed_change_in_primary_completion_scope",
    "records_to_tables",
    "records_to_curves",
    "records_to_report",
)


def run_synthetic_tubelet_sync_profile(
    profile: str,
    output_root: str | Path | None = None,
    samples_per_role: int | None = None,
) -> Path:
    if profile not in PROFILE_SAMPLE_DEFAULTS:
        raise ValueError(f"unsupported profile: {profile}")
    resolved_output_root = (
        _build_default_output_root(profile)
        if output_root is None
        else Path(output_root)
    )
    resolved_samples_per_role = (
        PROFILE_SAMPLE_DEFAULTS[profile]
        if samples_per_role is None
        else int(samples_per_role)
    )
    AblationRunner(ROOT).run(
        resolved_output_root,
        samples_per_role=resolved_samples_per_role,
        runtime_profile_override=profile,
    )
    _print_report_gate_summary(resolved_output_root)
    return resolved_output_root


def _build_default_output_root(profile: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "outputs" / "runs" / f"synthetic_tubelet_sync_{profile}_{timestamp}"


def _print_report_gate_summary(output_root: Path) -> None:
    report_path = RecordWriter(output_root).output_paths.report_path
    report_fields = _parse_report_fields(report_path.read_text(encoding="utf-8"))
    print(f"output_root: {output_root}")
    print(f"method_validation_report: {report_path}")
    for field_name in KEY_REPORT_FIELDS:
        field_value = report_fields.get(field_name, "missing")
        print(f"{field_name}: {field_value}")


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
        description="Run governed stage-one synthetic tubelet-sync profiles.",
    )
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILE_SAMPLE_DEFAULTS.keys()),
        required=True,
    )
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--samples-per-role", type=int, default=None)
    args = parser.parse_args(argv)
    run_synthetic_tubelet_sync_profile(
        args.profile,
        output_root=args.output_root,
        samples_per_role=args.samples_per_role,
    )


if __name__ == "__main__":
    main()

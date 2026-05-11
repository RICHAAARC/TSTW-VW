"""
文件用途：审计 main 目录不得保留阶段专用 runner、artifact builder 或路径布局文件。
File purpose: Audit that main does not retain stage-specific runner, artifact-builder, or output-layout files.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.json_report import build_report, exit_with_report


FORBIDDEN_STAGE_FILES = {
    "main/protocol/real_video_vae_latent_runner.py": "stage_two_runner_must_move_to_experiments",
    "main/analysis/real_video_vae_latent_artifacts.py": "stage_two_artifact_builder_must_move_to_experiments",
    "main/protocol/real_video_vae_latent_paths.py": "stage_two_output_layout_must_move_to_experiments_or_main_protocol_output_layout",
    "main/protocol/ablation_runner.py": "stage_one_ablation_runner_must_move_to_experiments",
}


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the main stage-specific runner audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized audit report.
    """
    root_path = Path(root)
    violations: list[dict[str, Any]] = []
    checked_paths = [str(root_path / relative_path) for relative_path in FORBIDDEN_STAGE_FILES]

    for relative_path, reason in FORBIDDEN_STAGE_FILES.items():
        candidate = root_path / relative_path
        if not candidate.exists():
            continue
        violations.append(
            {
                "path": str(candidate),
                "reason": reason,
            }
        )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_main_no_stage_specific_runner",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the audit as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    exit_with_report(run_audit(root))


if __name__ == "__main__":
    main(sys.argv)
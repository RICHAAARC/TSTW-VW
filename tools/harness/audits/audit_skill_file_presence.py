"""
文件用途：执行 skill 文件存在性与结构一致性审计。
File purpose: Audit required skill file presence and section consistency.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.file_scanner import read_text
from tools.harness.lib.json_report import build_report, exit_with_report


REQUIRED_SKILL_FILES = [
    "repository_intake.skill.md",
    "stage_progression_guard.skill.md",
    "naming_governance.skill.md",
    "placeholder_random_field_governance.skill.md",
    "protocol_records.skill.md",
    "threshold_calibration.skill.md",
    "ablation_consistency.skill.md",
    "notebook_entrypoint.skill.md",
    "artifact_rebuild.skill.md",
    "claim_audit.skill.md",
    "minimal_release.skill.md",
]
REQUIRED_SECTIONS = [
    "## Purpose",
    "## Scope",
    "## Required Inputs",
    "## Required Outputs",
    "## Blocking Rules",
    "## Allowed Changes",
    "## Forbidden Changes",
    "## Required Tests",
    "## Required Audit Hooks",
]
REQUIRED_SKILL_CONTENT = {
    "repository_intake.skill.md": [
        "docs/file_organization.md",
        "`scripts`",
        "`experiments`",
        "`audit_reports`",
        "`.codex`",
        "`examples`",
        "`release`",
    ],
    "stage_progression_guard.skill.md": [
        "allowed semantic stage names",
        "`synthetic_tubelet_sync_probe`",
        "`real_video_vae_latent_probe`",
    ],
    "minimal_release.skill.md": [
        "`minimal_release/`",
        "`release/`",
    ],
    "notebook_entrypoint.skill.md": [
        "`paper_workflow/colab_utils/`",
        "`paper_workflow/notebook_utils/`",
        "Stage2_Real_Video_VAE_Latent_Probe.ipynb",
        "audit_notebook_naming_contract.py",
        "`scripts/`",
    ],
    "repository_intake.skill.md": [
        "`outputs/` is an ephemeral runtime root",
        "paper_workflow/notebook_utils/",
    ],
    "naming_governance.skill.md": [
        "Stage2_Real_Video_VAE_Latent_Probe.ipynb",
        "paper_workflow/notebook_utils/",
    ],
}


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the skill presence and section audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized skill file audit report.
    """
    root_path = Path(root)
    skills_root = root_path / ".codex" / "skills"
    checked_paths: list[str] = []
    violations: list[dict[str, Any]] = []

    for file_name in REQUIRED_SKILL_FILES:
        skill_path = skills_root / file_name
        checked_paths.append(str(skill_path))
        if not skill_path.exists():
            violations.append(
                {
                    "path": str(skill_path),
                    "reason": "missing_skill_file",
                }
            )
            continue
        text = read_text(skill_path)
        normalized_text = text.lower()
        for required_section in REQUIRED_SECTIONS:
            if required_section not in text:
                violations.append(
                    {
                        "path": str(skill_path),
                        "reason": "missing_required_skill_section",
                        "value": required_section,
                    }
                )
        for required_content in REQUIRED_SKILL_CONTENT.get(file_name, []):
            if required_content.lower() in normalized_text:
                continue
            violations.append(
                {
                    "path": str(skill_path),
                    "reason": "missing_required_skill_content",
                    "value": required_content,
                }
            )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_skill_file_presence",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the skill presence audit as a CLI.

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

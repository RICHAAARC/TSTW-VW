"""
文件用途：执行阶段 0 support config 骨架审计。
File purpose: Audit the governed stage-0 support config skeletons.
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
from tools.harness.validate_project_contract import (
    load_json_config,
    validate_ablation_placeholder_data,
    validate_attack_placeholder_data,
)


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the stage-0 support config audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized support config audit report.
    """
    root_path = Path(root)
    ablation_path = root_path / "configs" / "ablation" / "ablation_placeholder.json"
    attack_path = root_path / "configs" / "attacks" / "identity_attack_placeholder.json"
    checked_paths = [str(ablation_path), str(attack_path)]
    violations: list[dict[str, Any]] = []

    if not ablation_path.exists():
        violations.append(
            {
                "path": str(ablation_path),
                "reason": "missing_ablation_placeholder_config",
            }
        )
    else:
        for violation in validate_ablation_placeholder_data(
            load_json_config(ablation_path)
        ):
            violation["path"] = str(ablation_path)
            violations.append(violation)

    if not attack_path.exists():
        violations.append(
            {
                "path": str(attack_path),
                "reason": "missing_attack_placeholder_config",
            }
        )
    else:
        for violation in validate_attack_placeholder_data(load_json_config(attack_path)):
            violation["path"] = str(attack_path)
            violations.append(violation)

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_protocol_support_configs",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the stage-0 support config audit as a CLI.

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
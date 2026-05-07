"""
文件用途：执行阶段 0 与阶段 1 入口 support config 骨架审计。
File purpose: Audit the governed stage-0 support configs and the reserved stage-1 entry configs.
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
    validate_synthetic_tubelet_sync_ablation_support_data,
    validate_synthetic_tubelet_sync_method_config_data,
    validate_synthetic_tubelet_sync_protocol_support_data,
    validate_temporal_attack_matrix_support_data,
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
    stage_one_protocol_path = (
        root_path / "configs" / "protocol" / "synthetic_tubelet_sync_probe.json"
    )
    temporal_attack_path = (
        root_path / "configs" / "attacks" / "temporal_attack_matrix.json"
    )
    stage_one_ablation_path = (
        root_path / "configs" / "ablation" / "synthetic_tubelet_sync_ablation.json"
    )
    stage_one_method_paths = [
        root_path / "configs" / "method" / "frame_prc.json",
        root_path / "configs" / "method" / "tubelet_only.json",
        root_path / "configs" / "method" / "tubelet_sync.json",
    ]
    checked_paths = [
        str(ablation_path),
        str(attack_path),
        str(stage_one_protocol_path),
        str(temporal_attack_path),
        str(stage_one_ablation_path),
        *(str(method_path) for method_path in stage_one_method_paths),
    ]
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

    if not stage_one_protocol_path.exists():
        violations.append(
            {
                "path": str(stage_one_protocol_path),
                "reason": "missing_stage_one_protocol_support_config",
            }
        )
    else:
        for violation in validate_synthetic_tubelet_sync_protocol_support_data(
            load_json_config(stage_one_protocol_path)
        ):
            violation["path"] = str(stage_one_protocol_path)
            violations.append(violation)

    if not temporal_attack_path.exists():
        violations.append(
            {
                "path": str(temporal_attack_path),
                "reason": "missing_temporal_attack_matrix_support_config",
            }
        )
    else:
        for violation in validate_temporal_attack_matrix_support_data(
            load_json_config(temporal_attack_path)
        ):
            violation["path"] = str(temporal_attack_path)
            violations.append(violation)

    if not stage_one_ablation_path.exists():
        violations.append(
            {
                "path": str(stage_one_ablation_path),
                "reason": "missing_stage_one_ablation_support_config",
            }
        )
    else:
        for violation in validate_synthetic_tubelet_sync_ablation_support_data(
            load_json_config(stage_one_ablation_path)
        ):
            violation["path"] = str(stage_one_ablation_path)
            violations.append(violation)

    for method_path in stage_one_method_paths:
        if not method_path.exists():
            violations.append(
                {
                    "path": str(method_path),
                    "reason": "missing_stage_one_method_support_config",
                }
            )
            continue
        for violation in validate_synthetic_tubelet_sync_method_config_data(
            load_json_config(method_path)
        ):
            violation["path"] = str(method_path)
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
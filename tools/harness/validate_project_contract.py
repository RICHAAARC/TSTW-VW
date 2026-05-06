"""
文件用途：提供项目契约与阈值协议配置的校验逻辑。
File purpose: Provide reusable validators for the project contract and threshold protocol skeleton.
Module type: General module
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SAMPLE_ROLES = {
    "clean_negative",
    "attacked_negative",
    "watermarked_positive",
    "attacked_positive",
}
REQUIRED_SPLITS = {"dev", "calibration", "test"}
REQUIRED_METHOD_OBJECTS = {
    "temporal_synchronized_tubelet_code",
    "flow_matching_trajectory_statistic",
    "fixed_low_fpr_calibrated_detector",
}
REQUIRED_EVIDENCE_NAMES = {
    "tubelet_evidence",
    "sync_evidence",
    "trajectory_evidence",
    "final_evidence",
}


def load_json_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON configuration file using only the Python standard library.

    Args:
        path: Target JSON configuration file path.

    Returns:
        Parsed dictionary content.

    Raises:
        FileNotFoundError: Raised when the file does not exist.
        json.JSONDecodeError: Raised when the file is not valid JSON.
    """
    file_path = Path(path)
    return json.loads(file_path.read_text(encoding="utf-8"))


def validate_project_contract_data(data: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the `project_contract.json` data structure.

    Args:
        data: Parsed project contract data.

    Returns:
        A list of contract validation violations.
    """
    violations: list[dict[str, str]] = []

    if data.get("project_stage") != "protocol_skeleton":
        violations.append(
            {
                "field": "project_stage",
                "reason": "project_stage_must_equal_protocol_skeleton",
            }
        )

    if not REQUIRED_SAMPLE_ROLES.issubset(set(data.get("sample_roles", []))):
        violations.append(
            {
                "field": "sample_roles",
                "reason": "missing_required_sample_roles",
            }
        )

    if not REQUIRED_SPLITS.issubset(set(data.get("splits", []))):
        violations.append(
            {
                "field": "splits",
                "reason": "missing_required_splits",
            }
        )

    if not REQUIRED_METHOD_OBJECTS.issubset(set(data.get("method_objects", []))):
        violations.append(
            {
                "field": "method_objects",
                "reason": "missing_required_method_objects",
            }
        )

    if not REQUIRED_EVIDENCE_NAMES.issubset(set(data.get("evidence_names", []))):
        violations.append(
            {
                "field": "evidence_names",
                "reason": "missing_required_evidence_names",
            }
        )

    return violations


def validate_protocol_config_data(data: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the `protocol_skeleton.json` threshold protocol fields.

    Args:
        data: Parsed protocol skeleton data.

    Returns:
        A list of threshold protocol validation violations.
    """
    violations: list[dict[str, str]] = []
    threshold_protocol = data.get("threshold_protocol", {})

    if threshold_protocol.get("calibration_split") != "calibration":
        violations.append(
            {
                "field": "threshold_protocol.calibration_split",
                "reason": "calibration_split_must_equal_calibration",
            }
        )

    calibration_negative_roles = set(
        threshold_protocol.get("calibration_negative_roles", [])
    )
    if not {"clean_negative", "attacked_negative"}.issubset(
        calibration_negative_roles
    ):
        violations.append(
            {
                "field": "threshold_protocol.calibration_negative_roles",
                "reason": "missing_required_calibration_negative_roles",
            }
        )

    if threshold_protocol.get("test_threshold_update_allowed") is not False:
        violations.append(
            {
                "field": "threshold_protocol.test_threshold_update_allowed",
                "reason": "test_threshold_updates_must_be_disabled",
            }
        )

    if threshold_protocol.get("score_name") != "S_final":
        violations.append(
            {
                "field": "threshold_protocol.score_name",
                "reason": "score_name_must_equal_s_final",
            }
        )

    return violations


def main(argv: list[str] | None = None) -> None:
    """Run the project contract validator as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    project_contract_path = root / "configs" / "project" / "project_contract.json"
    protocol_path = root / "configs" / "protocol" / "protocol_skeleton.json"

    payload = {
        "project_contract_violations": validate_project_contract_data(
            load_json_config(project_contract_path)
        ),
        "protocol_threshold_violations": validate_protocol_config_data(
            load_json_config(protocol_path)
        ),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv)

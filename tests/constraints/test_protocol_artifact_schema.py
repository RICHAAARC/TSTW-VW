"""
文件用途：验证 stage-one protocol artifact schema 配置。
File purpose: Validate the governed stage-one protocol artifact schema configuration.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

from copy import deepcopy
from pathlib import Path

from tools.harness.validate_project_contract import (
    load_json_config,
    validate_protocol_artifact_schema_data,
)


ROOT = Path(__file__).resolve().parents[2]


def test_protocol_artifact_schema_passes() -> None:
    """Validate that the checked-in artifact schema satisfies stage-one rules.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    assert validate_protocol_artifact_schema_data(data) == []


def test_missing_placeholder_and_random_fields_fails() -> None:
    """Validate that record governance fields cannot be omitted from the schema.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    broken = deepcopy(data)
    broken["event_score_record"]["required_top_level_fields"] = [
        field_name
        for field_name in broken["event_score_record"]["required_top_level_fields"]
        if field_name not in {"placeholder_fields", "random_fields"}
    ]
    violations = validate_protocol_artifact_schema_data(broken)
    assert any(
        violation["reason"] == "missing_required_event_score_fields"
        for violation in violations
    )


def test_missing_latent_trace_fields_fails() -> None:
    """Validate that latent trace fields cannot be omitted from the schema.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    broken = deepcopy(data)
    broken["event_score_record"]["required_top_level_fields"] = [
        field_name
        for field_name in broken["event_score_record"]["required_top_level_fields"]
        if field_name
        not in {
            "latent_backend_name",
            "latent_backend_status",
            "latent_tensor_digest_random",
            "latent_generation_seed_random",
        }
    ]
    violations = validate_protocol_artifact_schema_data(broken)
    assert any(
        violation["reason"] == "missing_required_event_score_fields"
        for violation in violations
    )


def test_missing_input_artifact_trace_fields_fails() -> None:
    """Validate that input artifact trace fields cannot be omitted from the schema.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    broken = deepcopy(data)
    broken["event_score_record"]["required_input_artifact_trace_fields"] = [
        field_name
        for field_name in broken["event_score_record"][
            "required_input_artifact_trace_fields"
        ]
        if field_name != "artifact_digest"
    ]
    violations = validate_protocol_artifact_schema_data(broken)
    assert any(
        violation["reason"] == "missing_required_input_artifact_trace_fields"
        for violation in violations
    )


def test_threshold_source_record_digest_is_required() -> None:
    """Validate that threshold traceability remains part of the schema skeleton.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    broken = deepcopy(data)
    broken["threshold_record"]["required_fields"] = [
        field_name
        for field_name in broken["threshold_record"]["required_fields"]
        if field_name != "threshold_source_record_digest"
    ]
    violations = validate_protocol_artifact_schema_data(broken)
    assert any(
        violation["reason"] == "missing_required_threshold_record_fields"
        for violation in violations
    )


def test_protocol_artifact_output_layout_is_frozen() -> None:
    """Validate that the governed relative output layout stays fixed.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    broken = deepcopy(data)
    broken["output_layout"]["main_metrics_path"] = "tables/main_tpr_fpr_table_v1.csv"
    violations = validate_protocol_artifact_schema_data(broken)
    assert any(
        violation["reason"] == "unexpected_protocol_artifact_output_path"
        for violation in violations
    )


def test_missing_mechanism_trace_fields_fail() -> None:
    """Validate that stage-one mechanism trace fields cannot be omitted from the schema.

    Args:
        None.

    Returns:
        None.
    """
    data = load_json_config(
        ROOT / "configs" / "schema" / "protocol_artifact_schema.json"
    )
    broken = deepcopy(data)
    broken["event_score_record"]["required_mechanism_trace_fields"] = [
        field_name
        for field_name in broken["event_score_record"]["required_mechanism_trace_fields"]
        if field_name != "partition_digest"
    ]
    violations = validate_protocol_artifact_schema_data(broken)
    assert any(
        violation["reason"] == "missing_required_mechanism_trace_fields"
        for violation in violations
    )
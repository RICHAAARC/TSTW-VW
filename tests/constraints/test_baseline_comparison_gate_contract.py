"""验证阶段三 baseline comparison gate 的配置和记录契约。"""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.record_schema import validate_baseline_record
from experiments.baseline_comparison_gate.source_intake import (
    REQUIRED_BASELINE_NAMES,
    build_source_intake_summary,
    load_all_source_manifests,
    validate_source_manifest,
)
from tools.harness.validate_project_contract import load_json_config

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]
BASELINE_CONFIG_DIR = ROOT / "configs" / "baselines"


def test_baseline_source_manifests_pass_minimum_intake_contract() -> None:
    """确认三个固定 baseline 都完成最小 source intake 字段登记。"""
    manifests = load_all_source_manifests(BASELINE_CONFIG_DIR)

    assert tuple(manifests) == REQUIRED_BASELINE_NAMES
    for baseline_name, manifest in manifests.items():
        assert manifest["baseline_name"] == baseline_name
        assert validate_source_manifest(manifest) == []


def test_baseline_source_manifest_requires_full_upstream_commit() -> None:
    """确认 source manifest 不能使用短 commit 或未固定来源。"""
    manifest = load_json_config(BASELINE_CONFIG_DIR / "external_videoseal_source.json")
    manifest["upstream_commit"] = "e00b98c"

    violations = validate_source_manifest(manifest)

    assert any(
        violation["field"] == "upstream_commit"
        and violation["reason"] == "must_be_full_git_sha"
        for violation in violations
    )


def test_baseline_source_intake_summary_is_stage_scoped() -> None:
    """确认 source intake 摘要只声明阶段三来源状态, 不伪造实验结果。"""
    manifests = load_all_source_manifests(BASELINE_CONFIG_DIR)
    summary = build_source_intake_summary(manifests)

    assert summary["project_stage"] == "baseline_comparison_gate"
    assert summary["baseline_count"] == 3
    assert {entry["baseline_name"] for entry in summary["entries"]} == set(
        REQUIRED_BASELINE_NAMES
    )
    assert all(entry["violation_count"] == 0 for entry in summary["entries"])


def test_baseline_comparison_protocol_config_declares_fixed_fpr_gate() -> None:
    """确认阶段三总配置冻结 calibration-only fixed-FPR 协议。"""
    config = load_json_config(BASELINE_CONFIG_DIR / "baseline_comparison_gate.json")
    threshold_protocol = config["threshold_protocol"]

    assert config["project_stage"] == "baseline_comparison_gate"
    assert config["baselines"] == list(REQUIRED_BASELINE_NAMES)
    assert threshold_protocol["calibration_split"] == "calibration"
    assert set(threshold_protocol["calibration_negative_roles"]) == {
        "clean_negative",
        "attacked_negative",
    }
    assert threshold_protocol["test_threshold_update_allowed"] is False
    assert threshold_protocol["allow_attack_specific_threshold"] is False
    assert threshold_protocol["target_fprs"] == [0.001]


def test_baseline_record_schema_accepts_complete_record() -> None:
    """确认完整 baseline record 可以通过阶段三最小字段校验。"""
    record = {
        "workflow_key": "baseline_comparison_gate",
        "run_id": "baseline_comparison_formal_20260611T034500Z_abcdef0",
        "sample_id": "sample_000001",
        "split": "test",
        "sample_role": "attacked_positive",
        "baseline_name": "external_videoseal",
        "baseline_family": "external_video_watermark",
        "method_name": "external_videoseal",
        "method_family": "external_video_watermark",
        "payload_length_bits": 128,
        "payload_digest": "sha256:payload",
        "attack_name": "h264_crf_28",
        "attack_family": "compression",
        "attack_config_digest": "sha256:attack",
        "baseline_score": 0.75,
        "baseline_raw_detector_output": {"score": 0.75},
        "threshold": 0.5,
        "target_fpr": 0.001,
        "decision": "positive",
        "bit_accuracy": 0.95,
        "ber": 0.05,
        "quality_metrics": {"lpips": 0.02, "clip_similarity": 0.94},
        "temporal_metrics": {"frame_count": 32},
        "runtime_metrics": {"detect_seconds": 1.0},
        "baseline_trace": {
            "source_digest": "sha256:source",
            "model_digest": "sha256:model",
            "adapter_version": "adapter_skeleton",
            "score_mapping_rule": "native_score",
            "license_status": "reviewed",
        },
        "failure_reason": None,
    }

    assert validate_baseline_record(record) == []


def test_baseline_record_schema_requires_trace_provenance() -> None:
    """确认 baseline record 必须保留 source、model 和 adapter trace。"""
    record = {
        "workflow_key": "baseline_comparison_gate",
        "run_id": "baseline_comparison_formal_20260611T034500Z_abcdef0",
        "sample_id": "sample_000001",
        "split": "test",
        "sample_role": "attacked_positive",
        "baseline_name": "external_videoseal",
        "baseline_family": "external_video_watermark",
        "method_name": "external_videoseal",
        "method_family": "external_video_watermark",
        "payload_length_bits": 128,
        "payload_digest": "sha256:payload",
        "attack_name": "clean",
        "attack_family": "clean",
        "attack_config_digest": "sha256:attack",
        "baseline_score": None,
        "baseline_raw_detector_output": {},
        "threshold": None,
        "target_fpr": 0.001,
        "decision": "failed",
        "bit_accuracy": None,
        "ber": None,
        "quality_metrics": {},
        "temporal_metrics": {},
        "runtime_metrics": {},
        "baseline_trace": {},
        "failure_reason": "external_baseline_not_integrated",
    }

    violations = validate_baseline_record(record)

    assert any(
        violation["field"] == "baseline_trace.source_digest"
        for violation in violations
    )
    assert any(
        violation["field"] == "baseline_trace.model_digest"
        for violation in violations
    )
    assert any(
        violation["field"] == "baseline_trace.adapter_version"
        for violation in violations
    )

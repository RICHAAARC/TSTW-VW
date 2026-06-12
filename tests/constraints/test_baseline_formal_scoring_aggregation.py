"""验证 baseline score records 聚合层。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.formal_scoring_aggregation import run_baseline_score_aggregation
from experiments.baseline_comparison_gate.formal_scoring_runner import materialize_formal_scoring_execution_run

pytestmark = [pytest.mark.constraint, pytest.mark.unit]
ROOT = Path(__file__).resolve().parents[2]


def write_jsonl(path: Path, rows: list[dict]) -> Path:
    """写出测试 JSONL。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def make_record(split: str, role: str, score: float, attack: str = "no_attack") -> dict:
    """构造最小 score record。"""
    return {
        "workflow_key": "baseline_comparison_gate",
        "run_id": "run",
        "sample_id": f"{split}_{role}_{attack}",
        "split": split,
        "sample_role": role,
        "baseline_name": "external_videoseal",
        "baseline_family": "external_video_watermark",
        "method_name": "external_videoseal",
        "method_family": "external_video_watermark",
        "payload_length_bits": 32,
        "payload_digest": "payload",
        "attack_name": attack,
        "attack_family": "clean",
        "attack_config_digest": "attack",
        "baseline_score": score,
        "baseline_raw_detector_output": {"bit_accuracy": score},
        "threshold": None,
        "target_fpr": 0.001,
        "decision": "pending_threshold_calibration",
        "bit_accuracy": score,
        "ber": 1.0 - score,
        "quality_metrics": {},
        "temporal_metrics": {},
        "runtime_metrics": {"detect_seconds": 0.1},
        "baseline_trace": {"source_digest": "s", "model_digest": "m", "adapter_version": "a", "score_mapping_rule": "r", "license_status": "recorded"},
        "failure_reason": None,
    }


def test_score_aggregation_writes_fixed_fpr_tables(tmp_path: Path) -> None:
    """确认聚合层能从 score records 生成阈值表、主表、攻击分解表和 claim audit。"""
    records = [
        make_record("calibration", "clean_negative", 0.1),
        make_record("calibration", "attacked_negative", 0.2),
        make_record("test", "clean_negative", 0.1),
        make_record("test", "watermarked_positive", 0.9),
        make_record("test", "attacked_positive", 0.8, "blur"),
    ]
    record_path = write_jsonl(tmp_path / "input" / "records.jsonl", records)
    summary = run_baseline_score_aggregation(run_root=tmp_path / "agg", record_paths=[record_path])

    assert summary["formal_fixed_fpr_complete"] is True
    assert (tmp_path / "agg" / "thresholds" / "baseline_threshold_table.csv").exists()
    assert (tmp_path / "agg" / "tables" / "baseline_comparison_table.csv").exists()
    assert (tmp_path / "agg" / "claim_audit" / "baseline_claim_audit.csv").exists()


def test_execution_materialization_excludes_large_checkpoint_cache(tmp_path: Path) -> None:
    """确认正式 execution 复制到 Drive 风格目录时默认排除大型权重缓存。"""
    run_root = tmp_path / "run"
    write_jsonl(run_root / "records" / "baseline_formal_score_records.jsonl", [make_record("dev", "attacked_negative", 0.5)])
    manifest = run_root / "artifacts" / "baseline_comparison_formal_scoring_execution_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}", encoding="utf-8")
    ckpt = run_root / "work" / "external_videoseal" / "worker_00" / "ckpts" / "model.pth"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    ckpt.write_bytes(b"large")

    dest = materialize_formal_scoring_execution_run(run_root=run_root, result_root=tmp_path / "results", run_id="execution_run")

    assert (dest / "records" / "baseline_formal_score_records.jsonl").exists()
    assert not (dest / "work" / "external_videoseal" / "worker_00" / "ckpts" / "model.pth").exists()


def test_execution_materialization_can_require_gpu_profile_files(tmp_path: Path) -> None:
    """验证 formal execution 物化时可以强制检查 GPU profiling 产物。"""
    run_root = tmp_path / "run"
    write_jsonl(run_root / "records" / "baseline_formal_score_records.jsonl", [make_record("dev", "attacked_negative", 0.5)])
    manifest = run_root / "artifacts" / "baseline_comparison_formal_scoring_execution_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}", encoding="utf-8")
    profile_dir = run_root / "runtime_profile" / "baseline_gpu_profiles" / "formal_scoring_execution"
    profile_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "gpu_runtime_trace.csv",
        "gpu_runtime_summary.json",
        "gpu_runtime_report.md",
        "gpu_runtime_profile_manifest.json",
    ):
        (profile_dir / name).write_text("ok\n", encoding="utf-8")

    dest = materialize_formal_scoring_execution_run(
        run_root=run_root,
        result_root=tmp_path / "results",
        run_id="execution_run",
        required_relative_paths=[
            "runtime_profile/baseline_gpu_profiles/formal_scoring_execution/gpu_runtime_trace.csv",
            "runtime_profile/baseline_gpu_profiles/formal_scoring_execution/gpu_runtime_summary.json",
            "runtime_profile/baseline_gpu_profiles/formal_scoring_execution/gpu_runtime_report.md",
            "runtime_profile/baseline_gpu_profiles/formal_scoring_execution/gpu_runtime_profile_manifest.json",
        ],
    )

    assert (
        dest
        / "runtime_profile"
        / "baseline_gpu_profiles"
        / "formal_scoring_execution"
        / "gpu_runtime_summary.json"
    ).exists()


def test_baseline_notebook_defines_score_aggregation_config_before_use() -> None:
    """验证 baseline shard 聚合配置位于独立聚合 Notebook 中。"""
    run_notebook_path = ROOT / "paper_workflow" / "run_baseline_comparison_gate.ipynb"
    aggregate_notebook_path = ROOT / "paper_workflow" / "aggregate_baseline_comparison_gate_shards.ipynb"
    run_source = run_notebook_path.read_text(encoding="utf-8")
    aggregate_payload = json.loads(aggregate_notebook_path.read_text(encoding="utf-8"))
    aggregate_source = "\n".join(
        "".join(cell.get("source", []))
        for cell in aggregate_payload.get("cells", [])
        if cell.get("cell_type") == "code"
    )

    assert "RUN_BASELINE_SCORE_RECORDS_AGGREGATION" not in run_source
    assert "BASELINE_SCORE_RECORD_PATHS = []" in aggregate_source
    assert "BASELINE_SCORE_AGGREGATION_RUN_ROOT =" in aggregate_source
    assert "aggregate_baseline_score_records.py" in aggregate_source
    assert "--baseline-name" in aggregate_source
    assert re.search(r"BASELINE_FORMAL_SCORING_EXECUTION_MAX_WORK_ITEMS = (None|\d+)", run_source)
    assert re.search(r"BASELINE_FORMAL_SCORING_WORKER_COUNT = \d+", run_source)
    assert "BASELINE_FORMAL_SCORING_EXECUTION_BASELINE_NAMES =" in run_source
    assert "scoring_plans" in run_source
    assert "formal_input_contract_snapshot" in run_source
    assert "if BASELINE_FORMAL_SCORING_EXECUTION_MAX_WORK_ITEMS is not None:" in run_source

def test_baseline_notebook_passes_gpu_profile_to_formal_execution() -> None:
    """验证 notebook 的 formal execution cell 会把 GPU profiling 参数传给仓库脚本。"""
    notebook_path = ROOT / "paper_workflow" / "run_baseline_comparison_gate.ipynb"
    notebook_payload = json.loads(notebook_path.read_text(encoding="utf-8"))
    notebook_source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook_payload.get("cells", [])
        if cell.get("cell_type") == "code"
    )

    execution_cell_index = notebook_source.index("RUN_BASELINE_FORMAL_SCORING_SMALL_VALIDATION")
    profile_arg_index = notebook_source.index('"--gpu-profile-interval-seconds", str(BASELINE_GPU_PROFILE_INTERVAL_SECONDS)')

    assert execution_cell_index < profile_arg_index


def test_baseline_notebook_decouples_smoke_from_execution_dependency_install() -> None:
    """验证跳过 smoke 时仍会为 formal execution 安装所需 baseline 依赖。"""
    notebook_path = ROOT / "paper_workflow" / "run_baseline_comparison_gate.ipynb"
    notebook_payload = json.loads(notebook_path.read_text(encoding="utf-8"))
    notebook_source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook_payload.get("cells", [])
        if cell.get("cell_type") == "code"
    )

    assert "RUN_VIDEOSEAL_REAL_SMOKE = False" in notebook_source
    assert "RUN_RIVAGAN_REAL_SMOKE = False" in notebook_source
    assert "RUN_HIDDEN_FRAMEWISE_REAL_SMOKE = False" in notebook_source
    assert "RUN_BASELINE_REAL_SMOKE_SUMMARY = False" in notebook_source
    assert (
        'if RUN_VIDEOSEAL_REAL_SMOKE or "external_videoseal" in BASELINE_FORMAL_SCORING_EXECUTION_BASELINE_NAMES:'
        in notebook_source
    )
    assert (
        'if RUN_RIVAGAN_REAL_SMOKE or "external_rivagan" in BASELINE_FORMAL_SCORING_EXECUTION_BASELINE_NAMES:'
        in notebook_source
    )
    assert (
        'if RUN_HIDDEN_FRAMEWISE_REAL_SMOKE or "external_hidden_framewise" in BASELINE_FORMAL_SCORING_EXECUTION_BASELINE_NAMES:'
        in notebook_source
    )

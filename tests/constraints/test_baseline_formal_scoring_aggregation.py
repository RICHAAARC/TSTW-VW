"""验证 baseline score records 聚合层。"""

from __future__ import annotations

import json
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


def test_baseline_notebook_defines_score_aggregation_config_before_use() -> None:
    """验证 notebook 在聚合 cell 之前定义聚合开关和输入路径配置。"""
    notebook_path = ROOT / "paper_workflow" / "run_baseline_comparison_gate.ipynb"
    notebook_payload = json.loads(notebook_path.read_text(encoding="utf-8"))
    notebook_source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook_payload.get("cells", [])
        if cell.get("cell_type") == "code"
    )

    definition_index = notebook_source.index("RUN_BASELINE_SCORE_RECORDS_AGGREGATION = False")
    use_index = notebook_source.index("if RUN_BASELINE_SCORE_RECORDS_AGGREGATION:")

    assert definition_index < use_index
    assert "BASELINE_SCORE_AGGREGATION_RECORD_PATHS = []" in notebook_source
    assert "BASELINE_SCORE_AGGREGATION_RUN_ROOT =" in notebook_source
    assert "BASELINE_FORMAL_SCORING_EXECUTION_MAX_WORK_ITEMS = 8" in notebook_source
    assert "BASELINE_FORMAL_SCORING_WORKER_COUNT = 2" in notebook_source

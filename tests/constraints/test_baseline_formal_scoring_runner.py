"""验证 baseline comparison 正式 scoring runner。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.formal_scoring_runner import (
    build_scoring_work_items,
    build_stage_two_event_universe,
    materialize_formal_scoring_plan_run,
    run_formal_scoring_execution,
    run_formal_scoring_plan,
)
from main.core.digest import compute_object_digest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def write_stage_two_records(root: Path) -> Path:
    """写出包含3个内部方法变体的最小阶段二 records。"""
    package_root = root / "real_video_vae_latent_probe_formal"
    records_dir = package_root / "records"
    records_dir.mkdir(parents=True)
    rows = []
    for method in ("frame_prc", "tubelet_only", "tubelet_sync"):
        for split, role, attack in (
            ("calibration", "attacked_negative", "h264_compression"),
            ("test", "attacked_positive", "h264_compression"),
            ("test", "watermarked_positive", "no_attack"),
        ):
            rows.append(
                {
                    "event_id": f"{method}:{split}:{role}:{attack}",
                    "split": split,
                    "sample_role": role,
                    "sample_id": f"sample_{split}_{role}",
                    "method_variant": method,
                    "attack_name": attack,
                    "attack_params": {"crf": 28} if attack == "h264_compression" else {},
                    "target_fpr": 0.001,
                    "mechanism_trace": {
                        "payload_digest": "payload_digest",
                        "video_source_relpath": f"artifacts/videos/source/{split}/{role}.mp4",
                        "video_source_digest": compute_object_digest([split, role]),
                        "video_frame_count": 32,
                        "video_fps": 8,
                        "video_resolution": [256, 256],
                    },
                }
            )
    (records_dir / "event_scores.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return package_root


def write_contract(path: Path, *, ready: bool = True) -> Path:
    """写出最小 formal input contract。"""
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"ready_for_formal_baseline_runner": ready}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_scoring_work_items_deduplicate_internal_method_variants(tmp_path: Path) -> None:
    """确认 work-item 宇宙不会因内部3个 method_variant 被重复放大。"""
    package_root = write_stage_two_records(tmp_path)

    events = build_stage_two_event_universe(package_root)
    items = build_scoring_work_items(
        stage_two_package_root=package_root,
        baseline_names=["external_videoseal"],
    )

    assert len(events) == 3
    assert len(items) == 3
    assert {item["baseline_name"] for item in items} == {"external_videoseal"}
    assert all(item["execution_status"] == "pending_external_baseline_scoring" for item in items)


def test_scoring_work_items_support_sharding_and_multiple_baselines(tmp_path: Path) -> None:
    """确认 baseline 过滤和 shard 切分语义稳定。"""
    package_root = write_stage_two_records(tmp_path)

    shard_items = build_scoring_work_items(
        stage_two_package_root=package_root,
        baseline_names=["external_videoseal", "external_rivagan"],
        shard_count=2,
        shard_index=1,
    )

    assert len(shard_items) == 3
    assert {item["baseline_name"] for item in shard_items}.issubset(
        {"external_videoseal", "external_rivagan"}
    )


def test_run_formal_scoring_plan_writes_manifest_and_materializes(tmp_path: Path) -> None:
    """确认 scoring plan 可先写入 session-local 后再复制到 Drive 风格目录。"""
    package_root = write_stage_two_records(tmp_path)
    contract_path = write_contract(tmp_path / "contract" / "baseline_comparison_formal_input_contract.json")
    run_root = tmp_path / "runs" / "baseline_comparison_formal_scoring_plan"

    summary = run_formal_scoring_plan(
        run_root=run_root,
        stage_two_package_root=package_root,
        formal_input_contract_path=contract_path,
        baseline_names=["external_videoseal"],
    )
    destination = materialize_formal_scoring_plan_run(
        run_root=run_root,
        result_root=tmp_path / "results",
        run_id="baseline_comparison_formal_scoring_plan_20260611T080000Z_abcdef0",
    )

    assert summary["work_item_count"] == 3
    assert Path(summary["work_items_path"]).exists()
    assert Path(summary["manifest_path"]).exists()
    assert (destination / "work_items" / "baseline_scoring_work_items.jsonl").exists()


class FakeDetectionResult:
    """测试用检测结果, 避免约束测试加载真实外部模型。"""

    baseline_score = 0.75
    baseline_raw_detector_output = {"bit_accuracy": 0.75}
    runtime_metrics = {"detect_seconds": 0.01}
    baseline_trace = {
        "adapter_version": "fake_formal_adapter",
        "model_digest": "fake_model_digest",
        "score_mapping_rule": "fake_bit_accuracy",
    }
    failure_reason = None


class FakeEmbedResult:
    """测试用嵌入结果, 只创建占位视频路径。"""

    def __init__(self, output_video_path: Path) -> None:
        self.baseline_name = "external_videoseal"
        self.output_video_path = output_video_path
        self.embed_success = True
        self.runtime_metrics = {"embed_seconds": 0.01}
        self.baseline_trace = {"adapter_version": "fake_formal_adapter", "model_digest": "fake_model_digest"}
        self.failure_reason = None


class FakeAdapter:
    """测试用 adapter, 验证 execution runner 的数据流而不是外部模型。"""

    baseline_name = "external_videoseal"

    def prepare(self, context):
        return {"adapter_version": "fake_formal_adapter", "baseline_name": context.baseline_name}

    def embed(self, input_video_path, payload_bits, output_video_path, metadata):
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        output_video_path.write_bytes(Path(input_video_path).read_bytes())
        return FakeEmbedResult(output_video_path)

    def detect(self, input_video_path, metadata):
        assert Path(input_video_path).exists()
        return FakeDetectionResult()


def write_stage_two_records_with_source_video(root: Path) -> Path:
    """写出带源视频文件的最小阶段二包, 用于 execution runner 约束测试。"""
    package_root = write_stage_two_records(root)
    for relpath in {
        "artifacts/videos/source/calibration/attacked_negative.mp4",
        "artifacts/videos/source/test/attacked_positive.mp4",
        "artifacts/videos/source/test/watermarked_positive.mp4",
    }:
        video_path = package_root / relpath
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"fake video bytes")
    return package_root


def test_run_formal_scoring_execution_writes_score_records_with_fake_adapter(tmp_path: Path) -> None:
    """确认小规模 execution runner 会写出 score records, 且不会声称 fixed-FPR 已完成。"""
    package_root = write_stage_two_records_with_source_video(tmp_path)
    contract_path = write_contract(tmp_path / "contract" / "baseline_comparison_formal_input_contract.json")
    run_root = tmp_path / "runs" / "baseline_comparison_formal_scoring_execution"

    summary = run_formal_scoring_execution(
        run_root=run_root,
        stage_two_package_root=package_root,
        formal_input_contract_path=contract_path,
        config_dir=Path("configs") / "baselines",
        external_root=tmp_path / "external_baselines",
        run_id="baseline_comparison_formal_scoring_execution_20260611T090000Z_abcdef0",
        baseline_names=["external_videoseal"],
        shard_count=3,
        shard_index=2,
        max_work_items=1,
        worker_count=2,
        batch_size=1,
        adapter_factory=lambda name: FakeAdapter(),
    )

    records_path = Path(summary["records_path"])
    rows = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line]
    assert summary["completed_record_count"] == 1
    assert summary["formal_fixed_fpr_complete"] is False
    assert summary["baseline_isolation_enabled"] is True
    assert summary["worker_count"] == 2
    assert summary["batch_size"] == 1
    assert rows[0]["baseline_name"] == "external_videoseal"
    assert rows[0]["decision"] == "pending_threshold_calibration"
    assert rows[0]["baseline_score"] == 0.75

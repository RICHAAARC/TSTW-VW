"""验证 baseline comparison 正式 scoring plan runner。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.formal_scoring_runner import (
    build_scoring_work_items,
    build_stage_two_event_universe,
    materialize_formal_scoring_plan_run,
    run_formal_scoring_plan,
)
from main.core.digest import compute_object_digest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def write_stage_two_records(root: Path) -> Path:
    """写出含 3 个内部方法变体的最小阶段二 records。"""
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
    """确认 work-item 宇宙不会因内部 3 个 method_variant 被重复放大。"""
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
    """确认 scoring plan 可写入 session-local 后再复制到 Drive 风格目录。"""
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

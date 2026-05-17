"""
文件用途：验证 cross-event VAE batching 与 sequential runner 的关键输出等价。
模块类型：集成测试。
"""

from __future__ import annotations

import importlib.util
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.smoke]

from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner


ROOT = Path(__file__).resolve().parents[2]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv_table_shape(path: Path) -> tuple[tuple[str, ...], int]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return (), 0
    return tuple(rows[0]), max(0, len(rows) - 1)


def _write_debug_protocol_with_watermarked_positive(tmp_path: Path) -> Path:
    protocol_config = _load_json(ROOT / "configs" / "protocol" / "real_video_vae_latent_probe.json")
    protocol_config["sample_roles_by_profile"]["debug_real_video"] = [
        "clean_negative",
        "attacked_negative",
        "watermarked_positive",
    ]
    protocol_config_path = tmp_path / "real_video_vae_latent_probe_debug_protocol.json"
    protocol_config_path.write_text(
        json.dumps(protocol_config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return protocol_config_path


def _run_debug_profile(
    tmp_path: Path,
    *,
    run_name: str,
    batching_enabled: bool,
    protocol_config_path: Path,
) -> Path:
    run_root = tmp_path / "outputs" / "runs" / run_name
    RealVideoVaeLatentRunner(ROOT).run(
        output_root=run_root,
        run_mode="smoke",
        runtime_profile_override="debug_real_video",
        protocol_config_path=protocol_config_path,
        worker_count=1,
        cross_event_vae_batching_enabled=batching_enabled,
        cross_event_vae_decode_batch_size=2,
        cross_event_vae_encode_batch_size=2,
    )
    return run_root


def test_cross_event_vae_batching_matches_sequential_debug_records(tmp_path: Path) -> None:
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("imageio_ffmpeg is unavailable")

    protocol_config_path = _write_debug_protocol_with_watermarked_positive(tmp_path)
    sequential_root = _run_debug_profile(
        tmp_path,
        run_name="real_video_vae_latent_probe_debug_sequential",
        batching_enabled=False,
        protocol_config_path=protocol_config_path,
    )
    batched_root = _run_debug_profile(
        tmp_path,
        run_name="real_video_vae_latent_probe_debug_batched",
        batching_enabled=True,
        protocol_config_path=protocol_config_path,
    )

    sequential_records = _load_jsonl(sequential_root / "records" / "event_scores.jsonl")
    batched_records = _load_jsonl(batched_root / "records" / "event_scores.jsonl")
    assert len(sequential_records) == len(batched_records)

    sequential_by_event = {record["event_id"]: record for record in sequential_records}
    batched_by_event = {record["event_id"]: record for record in batched_records}
    assert set(sequential_by_event) == set(batched_by_event)

    exact_fields = [
        "event_id",
        "sample_id",
        "split",
        "sample_role",
        "method_variant",
        "attack_name",
        "decision",
        "failure_reason",
        "disabled_evidence",
    ]
    for event_id, sequential_record in sequential_by_event.items():
        batched_record = batched_by_event[event_id]
        for field_name in exact_fields:
            assert batched_record[field_name] == sequential_record[field_name]
        for score_name, sequential_score in sequential_record["evidence_scores"].items():
            batched_score = batched_record["evidence_scores"][score_name]
            if sequential_score is None:
                assert batched_score is None
            else:
                assert batched_score == pytest.approx(sequential_score, abs=1e-5, rel=1e-4)
        assert batched_record["mechanism_trace"]["cross_event_vae_batching_enabled"] is True

    sequential_thresholds = _load_json(sequential_root / "thresholds" / "thresholds.json")
    batched_thresholds = _load_json(batched_root / "thresholds" / "thresholds.json")
    assert len(sequential_thresholds) == len(batched_thresholds)
    assert [item["method_variant"] for item in batched_thresholds] == [
        item["method_variant"] for item in sequential_thresholds
    ]

    sequential_manifest = _load_json(sequential_root / "artifacts" / "artifact_manifest.json")
    batched_manifest = _load_json(batched_root / "artifacts" / "artifact_manifest.json")
    assert Counter(item["artifact_kind"] for item in batched_manifest) == Counter(
        item["artifact_kind"] for item in sequential_manifest
    )
    assert "watermarked_latent" in {
        item["artifact_kind"] for item in batched_manifest
    }

    sequential_tables = {
        path.relative_to(sequential_root / "tables").as_posix(): _load_csv_table_shape(path)
        for path in (sequential_root / "tables").glob("*.csv")
    }
    batched_tables = {
        path.relative_to(batched_root / "tables").as_posix(): _load_csv_table_shape(path)
        for path in (batched_root / "tables").glob("*.csv")
    }
    assert sequential_tables
    assert batched_tables == sequential_tables

    batching_summary = _load_json(
        batched_root / "runtime_profile" / "cross_event_vae_batching_summary.json"
    )
    assert batching_summary["enabled"] is True
    assert batching_summary["decode_request_count"] > 0
    assert batching_summary["encode_request_count"] > 0

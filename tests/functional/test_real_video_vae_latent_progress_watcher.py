"""
文件用途：验证 real-video VAE latent progress watcher 的统计与 stall 检测合同。
File purpose: Validate counting and stall-detection contracts for the real-video VAE latent progress watcher.
Module type: Functional test module
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from scripts.profile_runtime.watch_real_video_vae_latent_progress import (
    watch_real_video_vae_latent_progress,
)


pytestmark = pytest.mark.quick


def _touch(path: Path, *, content: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_progress_watcher_counts_artifacts_and_detects_stall(tmp_path: Path) -> None:
    """Validate progress counting and stall detection on a synthetic run root.

    Args:
        tmp_path: Temporary test root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    output_json = run_root / "runtime_profile" / "run_progress_snapshot.json"
    records_path = run_root / "records" / "event_scores.jsonl"
    gpu_trace_path = run_root / "runtime_profile" / "gpu_runtime_trace.csv"

    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text('{"event_id": 1}\n{"event_id": 2}\n', encoding="utf-8")
    (run_root / "thresholds").mkdir(parents=True, exist_ok=True)
    (run_root / "thresholds" / "thresholds.json").write_text("{}\n", encoding="utf-8")
    (run_root / "tables").mkdir(parents=True, exist_ok=True)
    (run_root / "tables" / "summary.csv").write_text("metric,value\nfoo,1\n", encoding="utf-8")
    (run_root / "reports").mkdir(parents=True, exist_ok=True)
    (run_root / "reports" / "vae_latent_probe_report.md").write_text("# report\n", encoding="utf-8")
    _touch(run_root / "artifacts" / "videos" / "source" / "sample.mp4")
    _touch(run_root / "artifacts" / "videos" / "decoded" / "sample.mp4")
    _touch(run_root / "artifacts" / "videos" / "attacked" / "sample.mp4")
    _touch(run_root / "artifacts" / "latents" / "encoded" / "sample.npy")
    _touch(run_root / "artifacts" / "latents" / "watermarked" / "sample.npy")
    _touch(run_root / "artifacts" / "latents" / "reencoded" / "sample.npy")
    gpu_trace_path.parent.mkdir(parents=True, exist_ok=True)
    gpu_trace_path.write_text("timestamp_utc,elapsed_seconds,event_tag,gpu_index,gpu_name\n", encoding="utf-8")

    stale_timestamp = time.time() - 2000.0
    os.utime(records_path, (stale_timestamp, stale_timestamp))
    os.utime(gpu_trace_path, (stale_timestamp, stale_timestamp))

    payload = watch_real_video_vae_latent_progress(
        run_root=run_root,
        output_json=output_json,
        stall_threshold_seconds=900.0,
    )

    assert payload["status"] is True
    assert payload["records_written"] == 2
    assert payload["thresholds_ready"] is True
    assert payload["tables_ready"] is True
    assert payload["report_ready"] is True
    assert payload["source_video_count"] == 1
    assert payload["decoded_video_count"] == 1
    assert payload["attacked_video_count"] == 1
    assert payload["encoded_latent_count"] == 1
    assert payload["watermarked_latent_count"] == 1
    assert payload["reencoded_latent_count"] == 1
    assert payload["possible_stall"] is True
    assert payload["stall_reason"] == "record_and_gpu_trace_stalled"
    assert output_json.exists()


def test_progress_watcher_reports_missing_run_root(tmp_path: Path) -> None:
    """Validate missing run-root handling remains non-crashing.

    Args:
        tmp_path: Temporary test root.

    Returns:
        None.
    """
    run_root = tmp_path / "missing_run_root"
    output_json = tmp_path / "runtime_profile" / "run_progress_snapshot.json"

    payload = watch_real_video_vae_latent_progress(
        run_root=run_root,
        output_json=output_json,
    )

    assert payload["status"] is False
    assert payload["error_message"] == "run_root does not exist"
    assert output_json.exists()

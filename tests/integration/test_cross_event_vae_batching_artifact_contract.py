"""
文件用途：验证 cross-event VAE batching 不破坏阶段 2 artifact 输出合同。
模块类型：集成测试。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.smoke]

from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner


ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def test_cross_event_vae_batching_writes_governed_artifacts(tmp_path: Path) -> None:
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("imageio_ffmpeg is unavailable")

    protocol_config_path = _write_debug_protocol_with_watermarked_positive(tmp_path)
    run_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_probe_batched_artifacts"
    RealVideoVaeLatentRunner(ROOT).run(
        output_root=run_root,
        run_mode="smoke",
        runtime_profile_override="debug_real_video",
        protocol_config_path=protocol_config_path,
        worker_count=1,
        cross_event_vae_batching_enabled=True,
        cross_event_vae_decode_batch_size=2,
        cross_event_vae_encode_batch_size=2,
    )

    required_paths = [
        run_root / "records" / "event_scores.jsonl",
        run_root / "thresholds" / "thresholds.json",
        run_root / "reports" / "vae_latent_probe_report.md",
        run_root / "artifacts" / "artifact_manifest.json",
        run_root / "runtime_profile" / "cross_event_vae_batching_summary.json",
        run_root / "runtime_profile" / "cross_event_vae_batching_trace.jsonl",
    ]
    for required_path in required_paths:
        assert required_path.exists(), required_path
    assert list((run_root / "tables").glob("*.csv"))

    artifact_manifest = _load_json(run_root / "artifacts" / "artifact_manifest.json")
    artifact_kinds = {entry["artifact_kind"] for entry in artifact_manifest}
    assert {
        "source_video",
        "encoded_latent",
        "watermarked_latent",
        "decoded_video",
        "attacked_video",
        "reencoded_latent",
    }.issubset(artifact_kinds)

    summary = _load_json(run_root / "runtime_profile" / "cross_event_vae_batching_summary.json")
    assert summary["enabled"] is True
    assert summary["decode_batch_count"] > 0
    assert summary["encode_batch_count"] > 0

    trace_entries = [
        json.loads(line)
        for line in (
            run_root / "runtime_profile" / "cross_event_vae_batching_trace.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert trace_entries
    assert all("split" in entry for entry in trace_entries)
    assert {entry["split"] for entry in trace_entries}.issubset({"dev", "calibration", "test"})

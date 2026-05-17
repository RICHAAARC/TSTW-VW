"""
文件用途：验证 cross-event VAE batching 在 CUDA OOM 时可回退到单 event 调度。
模块类型：集成测试。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.smoke]

import experiments.real_video_vae_latent_probe.runner as runner_module
from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner


ROOT = Path(__file__).resolve().parents[2]


class _OomOnCrossEventBackend:
    """功能：当一次 VAE 调用包含多条 debug event 帧数时模拟 CUDA OOM。"""

    def decode_video(self, latent_batch: np.ndarray, *, config: dict[str, Any] | None = None) -> np.ndarray:
        del config
        if int(latent_batch.shape[0]) > 4:
            raise RuntimeError("CUDA out of memory")
        return latent_batch.astype(np.float32)

    def encode_video(self, video_batch: np.ndarray, *, config: dict[str, Any] | None = None) -> np.ndarray:
        del config
        if int(video_batch.shape[0]) > 4:
            raise RuntimeError("CUDA out of memory")
        return video_batch.astype(np.float32)

    def backend_metadata(self) -> dict[str, Any]:
        return {
            "vae_backend_name": "video_vae_tensor_runtime",
            "vae_backend_version": "framewise_tensor_runtime",
            "vae_encode_mode": "framewise",
            "vae_decode_mode": "framewise",
            "device": "cuda",
            "dtype": "float32",
            "runtime_impl": "oom_test_backend",
            "deterministic_encode": True,
        }


def test_cross_event_vae_batching_falls_back_to_single_event_batches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if importlib.util.find_spec("imageio_ffmpeg") is None:
        pytest.skip("imageio_ffmpeg is unavailable")

    monkeypatch.setattr(
        runner_module,
        "resolve_vae_backend",
        lambda config: _OomOnCrossEventBackend(),
    )
    run_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_probe_batched_fallback"

    RealVideoVaeLatentRunner(ROOT).run(
        output_root=run_root,
        run_mode="smoke",
        runtime_profile_override="debug_real_video",
        samples_per_role=2,
        worker_count=1,
        cross_event_vae_batching_enabled=True,
        cross_event_vae_decode_batch_size=2,
        cross_event_vae_encode_batch_size=2,
    )

    summary = json.loads(
        (run_root / "runtime_profile" / "cross_event_vae_batching_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["decode_fallback_count"] > 0
    assert summary["encode_fallback_count"] > 0

    event_scores_path = run_root / "records" / "event_scores.jsonl"
    records = [
        json.loads(line)
        for line in event_scores_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records
    assert any(
        "cuda_oom" in str(record["mechanism_trace"].get("cross_event_vae_batching_fallback_reason"))
        for record in records
    )

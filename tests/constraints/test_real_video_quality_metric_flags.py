"""
文件用途：验证真实视频质量指标的 governed flags 与 failure reason 行为。
File purpose: Validate governed flags and failure reasons for real-video quality metrics.
Module type: General module
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

import main.analysis.real_video_quality_metrics as real_quality_metrics
import main.analysis.clip_similarity_metrics as clip_similarity_metrics


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_real_video_quality_metrics_disabled_flags_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate disabled LPIPS and CLIP metrics report explicit reasons.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    frames = np.ones((4, 8, 8, 3), dtype=np.float32) * 0.5
    monkeypatch.setattr(
        real_quality_metrics,
        "read_video_frames",
        lambda path: SimpleNamespace(frames=frames),
    )

    payload = real_quality_metrics.build_real_video_quality_metrics_payload(
        "reference.mp4",
        "comparison.mp4",
        runtime_config={
            "quality_metrics": {
                "enable_lpips": False,
                "enable_clip_similarity": False,
            }
        },
    )

    assert payload["watermarked_video_lpips"] is None
    assert payload["lpips_failure_reason"] == "lpips_disabled_by_config"
    assert payload["clip_failure_reason"] == "clip_similarity_disabled_by_config"
    assert "watermarked_video_lpips" in payload["disabled_quality_metrics"]
    assert "clip_similarity" in payload["disabled_quality_metrics"]


def test_real_video_quality_metrics_clip_flag_reports_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate enabled CLIP scoring surfaces a governed similarity payload.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    frames = np.ones((4, 8, 8, 3), dtype=np.float32) * 0.5
    monkeypatch.setattr(
        real_quality_metrics,
        "read_video_frames",
        lambda path: SimpleNamespace(frames=frames),
    )
    monkeypatch.setattr(
        real_quality_metrics,
        "compute_clip_similarity_payload_from_frames",
        lambda reference_frames, comparison_frames, runtime_config=None: {
            "clip_similarity_score": 0.987654,
            "clip_model_id": "openai/clip-vit-base-patch32",
            "clip_frame_sample_count": 4,
            "clip_failure_reason": None,
        },
    )

    payload = real_quality_metrics.build_real_video_quality_metrics_payload(
        "reference.mp4",
        "comparison.mp4",
        runtime_config={
            "quality_metrics": {
                "enable_lpips": False,
                "enable_clip_similarity": True,
            }
        },
    )

    assert payload["clip_similarity_score"] == pytest.approx(0.987654)
    assert payload["clip_model_id"] == "openai/clip-vit-base-patch32"
    assert payload["clip_frame_sample_count"] == 4
    assert payload["clip_failure_reason"] is None


def test_real_video_quality_metrics_clip_backend_failure_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate CLIP backend failures remain auditable in the payload.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    frames = np.ones((4, 8, 8, 3), dtype=np.float32) * 0.5
    monkeypatch.setattr(
        real_quality_metrics,
        "read_video_frames",
        lambda path: SimpleNamespace(frames=frames),
    )
    monkeypatch.setattr(
        real_quality_metrics,
        "compute_clip_similarity_payload_from_frames",
        lambda reference_frames, comparison_frames, runtime_config=None: {
            "clip_similarity_score": None,
            "clip_model_id": "openai/clip-vit-base-patch32",
            "clip_frame_sample_count": 4,
            "clip_failure_reason": "clip_backend_unavailable: transformers missing",
        },
    )

    payload = real_quality_metrics.build_real_video_quality_metrics_payload(
        "reference.mp4",
        "comparison.mp4",
        runtime_config={
            "quality_metrics": {
                "enable_lpips": False,
                "enable_clip_similarity": True,
            }
        },
    )

    assert payload["clip_similarity_score"] is None
    assert payload["clip_failure_reason"] == "clip_backend_unavailable: transformers missing"


def test_clip_similarity_extracts_tensor_from_transformers_output() -> None:
    """Validate CLIP output objects are converted to tensor-like embeddings.

    Args:
        None.

    Returns:
        None.
    """
    fake_embedding = SimpleNamespace(norm=lambda **kwargs: None)
    fake_output = SimpleNamespace(pooler_output=fake_embedding)

    resolved_embedding = clip_similarity_metrics._extract_clip_embedding_tensor(fake_output)

    assert resolved_embedding is fake_embedding


def test_lpips_score_creates_cache_dir_and_routes_torch_hub(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Validate LPIPS cache roots are auto-created and passed to torch hub.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary path fixture.

    Returns:
        None.
    """

    class _FakeTensor:
        def __init__(self, array: np.ndarray) -> None:
            self.array = np.asarray(array, dtype=np.float32)

        def permute(self, *axes: int) -> "_FakeTensor":
            return _FakeTensor(np.transpose(self.array, axes))

        def unsqueeze(self, axis: int) -> "_FakeTensor":
            return _FakeTensor(np.expand_dims(self.array, axis))

        def float(self) -> "_FakeTensor":
            return self

        def to(self, device: object) -> "_FakeTensor":
            del device
            return self

        def __mul__(self, value: float) -> "_FakeTensor":
            return _FakeTensor(self.array * value)

        def __sub__(self, value: float) -> "_FakeTensor":
            return _FakeTensor(self.array - value)

    class _FakeNoGrad:
        def __enter__(self) -> None:
            return None

        def __exit__(self, exc_type, exc, traceback) -> bool:
            del exc_type, exc, traceback
            return False

    class _FakeHub:
        def __init__(self) -> None:
            self.received_dir: str | None = None

        def set_dir(self, path: str) -> None:
            self.received_dir = path

    class _FakeTorchModule:
        def __init__(self) -> None:
            self.hub = _FakeHub()
            self.cuda = SimpleNamespace(is_available=lambda: False)

        def device(self, name: str) -> str:
            return name

        def from_numpy(self, array: np.ndarray) -> _FakeTensor:
            return _FakeTensor(array)

        def no_grad(self) -> _FakeNoGrad:
            return _FakeNoGrad()

    class _FakeLpipsModule:
        @staticmethod
        def LPIPS(net: str, verbose: bool = False) -> SimpleNamespace:
            del net, verbose

            class _FakeLoss:
                def to(self, device: object) -> "_FakeLoss":
                    del device
                    return self

                def eval(self) -> None:
                    return None

                def __call__(self, ref_tensor: _FakeTensor, cmp_tensor: _FakeTensor) -> SimpleNamespace:
                    del ref_tensor, cmp_tensor
                    return SimpleNamespace(item=lambda: 0.123)

            return _FakeLoss()

    fake_torch = _FakeTorchModule()
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "lpips", _FakeLpipsModule())
    monkeypatch.delenv("TORCH_HOME", raising=False)

    cache_root = tmp_path / "session_models" / "lpips"
    frames = np.ones((2, 8, 8, 3), dtype=np.float32) * 0.5
    score = real_quality_metrics._compute_lpips_score(frames, frames, cache_root)

    assert score == pytest.approx(0.123)
    assert cache_root.exists()
    assert fake_torch.hub.received_dir == str(cache_root)
    assert os.environ["TORCH_HOME"] == str(cache_root)


def test_lpips_batch_size_accepts_notebook_top_level_runtime_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """验证 notebook 顶层 `lpips_batch_size` 会传递给 LPIPS 计算函数。

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Temporary path fixture.

    Returns:
        None.
    """
    captured: dict[str, object] = {}

    def _fake_compute_lpips_score(
        reference_frames: np.ndarray,
        comparison_frames: np.ndarray,
        lpips_model_root: str,
        *,
        lpips_backbone: str,
        lpips_device: str,
        lpips_batch_size: int,
    ) -> float:
        del reference_frames, comparison_frames, lpips_model_root, lpips_backbone, lpips_device
        captured["lpips_batch_size"] = lpips_batch_size
        return 0.234

    monkeypatch.setattr(
        real_quality_metrics,
        "_compute_lpips_score",
        _fake_compute_lpips_score,
    )
    frames = np.ones((4, 8, 8, 3), dtype=np.float32) * 0.5

    payload = real_quality_metrics.build_real_video_quality_metrics_payload_from_frames(
        frames,
        frames,
        runtime_config={
            "local_lpips_model_root": str(tmp_path / "lpips"),
            "lpips_batch_size": 32,
            "quality_metrics": {
                "enable_lpips": True,
                "enable_clip_similarity": False,
            },
        },
    )

    assert captured["lpips_batch_size"] == 32
    assert payload["watermarked_video_lpips"] == pytest.approx(0.234)

"""
文件用途：验证阶段 2 formal backend 不依赖 synthetic backend。
File purpose: Validate that stage-two formal backend has no synthetic backend dependency.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path


def test_real_video_vae_latent_backend_source_has_no_synthetic_backend_import() -> None:
    """Validate backend source does not import synthetic backend symbols.

    Args:
        None.

    Returns:
        None.
    """
    backend_source_path = (
        Path(__file__).resolve().parents[1]
        / "main"
        / "backends"
        / "real_video_vae_latent.py"
    )
    backend_source = backend_source_path.read_text(encoding="utf-8")

    assert "from main.backends.synthetic_video_latent" not in backend_source
    assert "SyntheticVideoLatentBackend" not in backend_source


def test_real_video_vae_latent_backend_formal_status_marker_exists() -> None:
    """Validate backend source declares formal runtime status marker.

    Args:
        None.

    Returns:
        None.
    """
    backend_source_path = (
        Path(__file__).resolve().parents[1]
        / "main"
        / "backends"
        / "real_video_vae_latent.py"
    )
    backend_source = backend_source_path.read_text(encoding="utf-8")

    assert "real_video_vae_formal_runtime" in backend_source

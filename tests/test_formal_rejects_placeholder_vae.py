"""
文件用途：验证 formal 模式拒绝 placeholder VAE backend。
File purpose: Validate that formal mode rejects placeholder VAE backends.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.unit
def test_formal_runtime_profile_rejects_placeholder_vae(tmp_path: Path) -> None:
    """Validate runner rejects placeholder VAE backend under formal runtime.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    output_root = tmp_path / "outputs" / "runs" / "real_video_vae_latent_formal_reject_placeholder"
    backend_config_path = tmp_path / "formal_backend_config.json"
    backend_config_path.write_text(
        json.dumps(
            {
                "project_stage": "synthetic_tubelet_sync_probe",
                "target_construction_phase": "real_video_vae_latent_probe",
                "latent_backend_name": "real_video_vae_latent",
                "latent_backend_status": "video_vae_tensor_scaffold_runtime",
                "runtime_profile": "formal",
                "latent_shape": {"frames": 16, "channels": 4, "height": 16, "width": 16},
                "formal_latent_shape": {"frames": 32, "channels": 4, "height": 32, "width": 32},
                "latent_generation_seed": 20260510,
                "video_fps": 8,
                "vae_backend_name": "video_vae_tensor_runtime",
                "formal_vae_backend_name": "video_vae_backend_placeholder",
                "vae_backend_version": "framewise_tensor_runtime",
                "formal_vae_backend_version": "framewise_tensor_runtime",
                "vae_encode_mode": "framewise",
                "vae_decode_mode": "framewise",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    runner = RealVideoVaeLatentRunner(ROOT)
    with pytest.raises(ValueError):
        runner.run(
            output_root=output_root,
            run_mode="formal",
            samples_per_role=1,
            runtime_profile_override="formal",
            backend_config_path=backend_config_path,
        )

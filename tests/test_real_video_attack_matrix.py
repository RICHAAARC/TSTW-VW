"""
文件用途：验证阶段 2 attack matrix 可实例化并运行。
File purpose: Validate that the stage-two attack matrix can be instantiated and executed.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.attacks.real_video_attack_registry import build_real_video_attack_registry
from main.backends.real_video_vae_latent import RealVideoVAELatentBackend
from main.core.registry import load_json_config


def test_real_video_attack_matrix_materializes_all_attacks(tmp_path: Path) -> None:
    """Validate that all configured stage-two attacks can materialize outputs.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    repository_root = Path(__file__).resolve().parents[1]
    attack_config = load_json_config(
        repository_root / "configs" / "attacks" / "real_video_attack_matrix.json"
    )
    attack_registry = build_real_video_attack_registry(attack_config)
    backend = RealVideoVAELatentBackend(latent_shape=(8, 2, 8, 8), runtime_profile="tiny")
    output_root = tmp_path / "outputs" / "runs" / "stage2_attack_matrix"
    backend.set_output_root(output_root)
    sample = backend.build_sample("rvp_attack_case", "test", "clean_negative")

    observed_attack_names = {attack_object.attack_name for attack_object in attack_registry}
    assert observed_attack_names == {
        "no_attack",
        "h264_compression",
        "h265_compression",
        "spatial_resize",
        "crop_resize",
        "gaussian_noise",
        "blur",
        "temporal_crop",
        "frame_dropping",
        "speed_change",
        "local_clip",
    }
    for attack_object in attack_registry:
        attacked_sample = attack_object.apply(sample)
        assert attacked_sample.latent_artifact_path is not None
        assert Path(attacked_sample.latent_artifact_path).exists()

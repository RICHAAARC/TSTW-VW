"""
文件用途：验证 trajectory source 不允许读取 positive-only artifact。
File purpose: Validate that trajectory source access rejects positive-only artifacts.
Module type: General module
"""

from __future__ import annotations

import pytest

from main.core.schema import LatentSample
from main.core.tensor_artifact import write_float_tensor_npy
from main.trajectory.trajectory_reconstruction import reconstruct_trajectory_observation


pytestmark = [pytest.mark.quick, pytest.mark.unit]


def test_positive_only_artifact_access_guard_blocks_trajectory_reconstruction() -> None:
    """验证 positive-only artifact access guard 会在重建前阻断。"""
    sample = LatentSample(
        sample_id="sample_guard",
        split="test",
        sample_role="attacked_positive",
        latent_shape=(4, 1, 2, 2),
        latent_tensor_digest_random="digest_random",
        latent_generation_seed_random=7,
        latent_backend_name="synthetic_video_latent",
        latent_backend_status="synthetic_runtime",
        mechanism_trace={"positive_only_artifact_access": True},
    )

    with pytest.raises(ValueError, match="positive_only_artifact_access_forbidden"):
        reconstruct_trajectory_observation(
            sample,
            {
                "trajectory_source_kind": "latent_interpolation_surrogate",
                "trajectory_time_grid": [0.0, 1.0],
                "fail_on_positive_only_artifact_access": True,
            },
        )


def test_stage2_frozen_endpoint_replay_requires_manifest_digest(tmp_path) -> None:
    """验证 formal source candidate 必须绑定阶段 2 frozen baseline manifest digest。"""
    artifact_path = tmp_path / "latent.npy"
    write_float_tensor_npy(artifact_path, (1, 1, 1, 1), [1.0])
    sample = LatentSample(
        sample_id="sample_formal_source",
        split="test",
        sample_role="attacked_positive",
        latent_shape=(1, 1, 1, 1),
        latent_tensor_digest_random="digest_random",
        latent_generation_seed_random=7,
        latent_backend_name="synthetic_video_latent",
        latent_backend_status="synthetic_runtime",
        latent_artifact_path=str(artifact_path),
    )

    with pytest.raises(ValueError, match="stage2_frozen_baseline_manifest_digest"):
        reconstruct_trajectory_observation(
            sample,
            {
                "trajectory_source_kind": "stage2_frozen_endpoint_replay",
                "trajectory_time_grid": [0.0, 1.0],
            },
        )

    observation = reconstruct_trajectory_observation(
        sample,
        {
            "trajectory_source_kind": "stage2_frozen_endpoint_replay",
            "trajectory_time_grid": [0.0, 1.0],
            "stage2_frozen_baseline_manifest_digest": "stage2_digest",
        },
    )

    assert observation.source_kind == "stage2_frozen_endpoint_replay"
    assert observation.time_grid == (0.0, 1.0)

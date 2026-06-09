"""
文件用途：验证 trajectory source 不允许读取 positive-only artifact。
File purpose: Validate that trajectory source access rejects positive-only artifacts.
Module type: General module
"""

from __future__ import annotations

import pytest

from main.core.schema import LatentSample
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

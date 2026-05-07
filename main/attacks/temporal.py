"""
文件用途：声明阶段 1 temporal attack matrix 的受治理攻击名称与默认参数。
File purpose: Declare governed attack names and support defaults for the stage-1 temporal attack matrix.
Module type: Semi-general module
"""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Any

from main.core.digest import compute_object_digest
from main.core.schema import LatentSample


PROJECT_STAGE = "protocol_skeleton"
TARGET_CONSTRUCTION_PHASE = "synthetic_tubelet_sync_probe"
ATTACK_MATRIX_NAME = "temporal_attack_matrix"
SUPPORTED_TEMPORAL_ATTACK_NAMES = (
    "no_attack",
    "temporal_crop",
    "frame_dropping",
    "speed_change",
    "local_clip",
    "latent_gaussian_noise",
)


def build_temporal_attack_matrix_support_defaults() -> dict[str, object]:
    """功能：返回阶段 1 temporal attack matrix 的冻结默认值。

    Build the governed default payload for the stage-1 temporal attack matrix.

    Args:
        None.

    Returns:
        A dictionary containing the frozen temporal attack entries.
    """
    return {
        "project_stage": PROJECT_STAGE,
        "target_construction_phase": TARGET_CONSTRUCTION_PHASE,
        "attack_matrix_name": ATTACK_MATRIX_NAME,
        "attacks": [
            {"attack_name": "no_attack", "attack_params": {}},
            {
                "attack_name": "temporal_crop",
                "attack_params": {
                    "crop_start_candidates": [4, 8, 12],
                    "crop_length": 20,
                },
            },
            {
                "attack_name": "frame_dropping",
                "attack_params": {
                    "drop_rate": 0.25,
                    "drop_policy": "deterministic_keyed",
                },
            },
            {
                "attack_name": "speed_change",
                "attack_params": {
                    "speed_ratio": 1.25,
                    "resample_policy": "nearest",
                },
            },
            {
                "attack_name": "local_clip",
                "attack_params": {"clip_lengths": [4, 8, 12, 16]},
            },
            {
                "attack_name": "latent_gaussian_noise",
                "attack_params": {"sigma": 0.05},
            },
        ],
    }


class TemporalAttackPlaceholder:
    """功能：提供阶段 1 temporal attack 的可运行占位接口。

    Runnable placeholder attack interface for the stage-1 temporal attack matrix.

    Args:
        attack_name: Governed attack name.
        attack_params: Attack parameter payload.

    Returns:
        None.
    """

    def __init__(self, attack_name: str, attack_params: dict[str, Any]) -> None:
        if attack_name not in SUPPORTED_TEMPORAL_ATTACK_NAMES:
            raise ValueError(f"unsupported attack_name: {attack_name}")
        if not isinstance(attack_params, dict):
            raise TypeError("attack_params must be a dictionary")
        self.attack_name = attack_name
        self.attack_params = self._normalize_attack_params(attack_name, attack_params)

    def apply(self, sample: LatentSample) -> LatentSample:
        """功能：对 latent sample 应用占位 temporal attack 语义。

        Apply placeholder temporal-attack semantics to a latent sample.

        Args:
            sample: Input latent sample.

        Returns:
            An attacked `LatentSample` instance.
        """
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")

        if self.attack_name == "no_attack":
            return sample

        attacked_shape = self._derive_attacked_shape(sample)
        attacked_seed = self._derive_attacked_seed(sample, attacked_shape)
        attacked_digest = compute_object_digest(
            {
                "source_digest": sample.latent_tensor_digest_random,
                "attack_name": self.attack_name,
                "attack_params": self.attack_params,
                "attacked_shape": list(attacked_shape),
                "attacked_seed": attacked_seed,
            }
        )
        return replace(
            sample,
            latent_shape=attacked_shape,
            latent_tensor_digest_random=attacked_digest,
            latent_generation_seed_random=attacked_seed,
        )

    def _normalize_attack_params(
        self,
        attack_name: str,
        attack_params: dict[str, Any],
    ) -> dict[str, Any]:
        if attack_name == "temporal_crop":
            crop_start_candidates = attack_params.get("crop_start_candidates", [])
            crop_length = attack_params.get("crop_length")
            if not isinstance(crop_start_candidates, list) or not crop_start_candidates:
                raise ValueError("temporal_crop requires crop_start_candidates")
            if not isinstance(crop_length, int) or crop_length < 1:
                raise ValueError("temporal_crop requires a positive crop_length")
            return {
                "crop_start": int(crop_start_candidates[0]),
                "crop_start_candidates": [int(candidate) for candidate in crop_start_candidates],
                "crop_length": crop_length,
            }

        if attack_name == "frame_dropping":
            drop_rate = attack_params.get("drop_rate")
            drop_policy = attack_params.get("drop_policy")
            if not isinstance(drop_rate, (int, float)) or not 0 <= float(drop_rate) < 1:
                raise ValueError("frame_dropping requires drop_rate in [0, 1)")
            if not isinstance(drop_policy, str) or not drop_policy:
                raise ValueError("frame_dropping requires a non-empty drop_policy")
            return {
                "drop_rate": float(drop_rate),
                "drop_policy": drop_policy,
            }

        if attack_name == "speed_change":
            speed_ratio = attack_params.get("speed_ratio")
            resample_policy = attack_params.get("resample_policy")
            if not isinstance(speed_ratio, (int, float)) or float(speed_ratio) <= 0:
                raise ValueError("speed_change requires a positive speed_ratio")
            if not isinstance(resample_policy, str) or not resample_policy:
                raise ValueError("speed_change requires a non-empty resample_policy")
            return {
                "speed_ratio": float(speed_ratio),
                "resample_policy": resample_policy,
            }

        if attack_name == "local_clip":
            clip_lengths = attack_params.get("clip_lengths", [])
            if not isinstance(clip_lengths, list) or not clip_lengths:
                raise ValueError("local_clip requires clip_lengths")
            return {
                "clip_length": int(clip_lengths[0]),
                "clip_lengths": [int(clip_length) for clip_length in clip_lengths],
            }

        if attack_name == "latent_gaussian_noise":
            sigma = attack_params.get("sigma")
            if not isinstance(sigma, (int, float)) or float(sigma) <= 0:
                raise ValueError("latent_gaussian_noise requires a positive sigma")
            return {"sigma": float(sigma)}

        if attack_name == "no_attack":
            return {}

        raise ValueError(f"unsupported attack_name: {attack_name}")

    def _derive_attacked_shape(
        self,
        sample: LatentSample,
    ) -> tuple[int, int, int, int]:
        frame_count, channels, height, width = sample.latent_shape
        if self.attack_name == "temporal_crop":
            attacked_frames = min(frame_count, int(self.attack_params["crop_length"]))
        elif self.attack_name == "frame_dropping":
            attacked_frames = max(
                1,
                frame_count - int(math.floor(frame_count * self.attack_params["drop_rate"])),
            )
        elif self.attack_name == "speed_change":
            attacked_frames = max(
                1,
                int(round(frame_count / self.attack_params["speed_ratio"])),
            )
        elif self.attack_name == "local_clip":
            attacked_frames = min(frame_count, int(self.attack_params["clip_length"]))
        elif self.attack_name == "latent_gaussian_noise":
            attacked_frames = frame_count
        else:
            attacked_frames = frame_count

        return (attacked_frames, channels, height, width)

    def _derive_attacked_seed(
        self,
        sample: LatentSample,
        attacked_shape: tuple[int, int, int, int],
    ) -> int:
        attack_digest = compute_object_digest(
            {
                "source_seed": sample.latent_generation_seed_random,
                "source_digest": sample.latent_tensor_digest_random,
                "attack_name": self.attack_name,
                "attack_params": self.attack_params,
                "attacked_shape": list(attacked_shape),
            }
        )
        return int(attack_digest[:12], 16)
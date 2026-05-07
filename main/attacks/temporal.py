"""
文件用途：声明阶段 1 temporal attack matrix 的受治理攻击名称与默认参数。
File purpose: Declare governed attack names and support defaults for the stage-1 temporal attack matrix.
Module type: Semi-general module
"""

from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import random
from typing import Any

from main.core.digest import compute_file_digest, compute_object_digest
from main.core.schema import LatentSample
from main.core.tensor_artifact import read_float_tensor_npy, write_float_tensor_npy


PROJECT_STAGE = "synthetic_tubelet_sync_probe"
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
        self._artifact_cache: dict[tuple[str, str], LatentSample] = {}

    def apply(self, sample: LatentSample) -> LatentSample:
        """功能：对 latent sample 应用真实 tensor-based temporal attack。

        Apply the tensor-based temporal attack to a latent sample.

        Args:
            sample: Input latent sample.

        Returns:
            An attacked `LatentSample` instance.
        """
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")
        if sample.latent_artifact_path is None or sample.run_root_path is None:
            raise ValueError("sample must carry latent_artifact_path and run_root_path")

        if self.attack_name == "no_attack":
            return sample

        materialized_attack_params = self._materialize_attack_params(sample)
        attacked_shape = self._derive_attacked_shape(sample, materialized_attack_params)
        attacked_seed = self._derive_attacked_seed(sample, attacked_shape)
        attack_params_digest = compute_object_digest(materialized_attack_params)[:12]
        source_artifact_digest = compute_object_digest(
            {
                "sample_id": sample.sample_id,
                "source_digest": sample.latent_tensor_digest_random,
                "attack_name": self.attack_name,
            }
        )[:16]
        artifact_relpath = (
            Path("artifacts")
            / "latents"
            / "attacked"
            / self.attack_name
            / f"{source_artifact_digest}_{attack_params_digest}.npy"
        )
        artifact_path = Path(sample.run_root_path) / artifact_relpath
        cache_key = (sample.latent_tensor_digest_random, attack_params_digest)
        cached_sample = self._artifact_cache.get(cache_key)
        if (
            cached_sample is not None
            and cached_sample.latent_artifact_path is not None
            and Path(cached_sample.latent_artifact_path).exists()
        ):
            return cached_sample

        if artifact_path.exists():
            attacked_digest = compute_file_digest(artifact_path)
            attacked_sample = self._build_attacked_sample(
                sample,
                artifact_relpath,
                artifact_path,
                attacked_shape,
                attacked_seed,
                materialized_attack_params,
                attacked_digest,
            )
            self._artifact_cache[cache_key] = attacked_sample
            return attacked_sample

        tensor_artifact = read_float_tensor_npy(sample.latent_artifact_path)
        attacked_values = self._apply_attack_to_tensor(
            tensor_artifact.values,
            sample.latent_shape,
            materialized_attack_params,
            attacked_seed,
        )
        write_float_tensor_npy(artifact_path, attacked_shape, attacked_values)
        attacked_digest = compute_file_digest(artifact_path)
        attacked_sample = self._build_attacked_sample(
            sample,
            artifact_relpath,
            artifact_path,
            attacked_shape,
            attacked_seed,
            materialized_attack_params,
            attacked_digest,
        )
        self._artifact_cache[cache_key] = attacked_sample
        return attacked_sample

    def _build_attacked_sample(
        self,
        sample: LatentSample,
        artifact_relpath: Path,
        artifact_path: Path,
        attacked_shape: tuple[int, int, int, int],
        attacked_seed: int,
        materialized_attack_params: dict[str, Any],
        attacked_digest: str,
    ) -> LatentSample:
        mechanism_trace = dict(sample.mechanism_trace or {})
        mechanism_trace.setdefault("reference_latent_shape", list(sample.latent_shape))
        mechanism_trace.update(
            {
                "latent_shape": list(attacked_shape),
                "latent_artifact_relpath": artifact_relpath.as_posix(),
                "latent_artifact_digest": attacked_digest,
                "sync_ground_truth_offset": materialized_attack_params.get(
                    "ground_truth_offset"
                ),
                "clip_length": materialized_attack_params.get("clip_length"),
            }
        )
        return replace(
            sample,
            latent_shape=attacked_shape,
            latent_tensor_digest_random=attacked_digest,
            latent_generation_seed_random=attacked_seed,
            latent_artifact_relpath=artifact_relpath.as_posix(),
            latent_artifact_path=str(artifact_path),
            latent_artifact_digest=attacked_digest,
            mechanism_trace=mechanism_trace,
            applied_attack_params=materialized_attack_params,
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
            clip_length = attack_params.get("clip_length")
            if isinstance(clip_length, int) and clip_length > 0:
                return {
                    "clip_length": int(clip_length),
                }
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
        attack_params: dict[str, Any],
    ) -> tuple[int, int, int, int]:
        frame_count, channels, height, width = sample.latent_shape
        if self.attack_name == "temporal_crop":
            attacked_frames = min(frame_count, int(attack_params["crop_length"]))
        elif self.attack_name == "frame_dropping":
            attacked_frames = int(attack_params["observed_frame_count"])
        elif self.attack_name == "speed_change":
            attacked_frames = int(attack_params["observed_frame_count"])
        elif self.attack_name == "local_clip":
            attacked_frames = int(attack_params["clip_length"])
        elif self.attack_name == "latent_gaussian_noise":
            attacked_frames = frame_count
        else:
            attacked_frames = frame_count

        return (attacked_frames, channels, height, width)

    def _materialize_attack_params(self, sample: LatentSample) -> dict[str, Any]:
        frame_count = sample.latent_shape[0]
        if self.attack_name == "temporal_crop":
            crop_start_candidates = list(self.attack_params["crop_start_candidates"])
            crop_start = crop_start_candidates[
                sample.latent_generation_seed_random % len(crop_start_candidates)
            ]
            crop_length = min(frame_count - int(crop_start), int(self.attack_params["crop_length"]))
            return {
                "crop_start": int(crop_start),
                "crop_length": int(crop_length),
                "original_frame_count": frame_count,
                "observed_frame_count": int(crop_length),
                "ground_truth_offset": -int(crop_start),
            }

        if self.attack_name == "frame_dropping":
            drop_rate = float(self.attack_params["drop_rate"])
            drop_stride = max(2, int(round(1.0 / max(1e-6, drop_rate))))
            offset = sample.latent_generation_seed_random % drop_stride
            kept_indices = [
                frame_index
                for frame_index in range(frame_count)
                if (frame_index - offset) % drop_stride != 0
            ]
            if not kept_indices:
                kept_indices = [0]
            return {
                "drop_rate": drop_rate,
                "drop_policy": self.attack_params["drop_policy"],
                "kept_frame_indices": kept_indices,
                "original_frame_count": frame_count,
                "observed_frame_count": len(kept_indices),
                "ground_truth_offset": None,
            }

        if self.attack_name == "speed_change":
            speed_ratio = float(self.attack_params["speed_ratio"])
            observed_frame_count = max(1, int(round(frame_count / speed_ratio)))
            return {
                "speed_ratio": speed_ratio,
                "resample_policy": self.attack_params["resample_policy"],
                "original_frame_count": frame_count,
                "observed_frame_count": observed_frame_count,
                "ground_truth_offset": None,
            }

        if self.attack_name == "local_clip":
            if "clip_lengths" in self.attack_params:
                clip_lengths = list(self.attack_params["clip_lengths"])
                clip_length = clip_lengths[
                    sample.latent_generation_seed_random % len(clip_lengths)
                ]
            else:
                clip_length = int(self.attack_params["clip_length"])
            max_start = max(0, frame_count - int(clip_length))
            clip_start_candidates = list(range(0, max_start + 1, 4)) or [0]
            clip_start = clip_start_candidates[
                (sample.latent_generation_seed_random // 7) % len(clip_start_candidates)
            ]
            return {
                "clip_start": int(clip_start),
                "clip_length": int(clip_length),
                "original_frame_count": frame_count,
                "observed_frame_count": int(clip_length),
                "ground_truth_offset": -int(clip_start),
            }

        if self.attack_name == "latent_gaussian_noise":
            return {
                "sigma": float(self.attack_params["sigma"]),
                "original_frame_count": frame_count,
                "observed_frame_count": frame_count,
                "ground_truth_offset": None,
            }

        return {}

    def _apply_attack_to_tensor(
        self,
        tensor_values: Any,
        latent_shape: tuple[int, int, int, int],
        attack_params: dict[str, Any],
        attacked_seed: int,
    ) -> list[float]:
        frame_count, channels, height, width = latent_shape
        frame_size = channels * height * width
        frame_slices = [
            [
                float(value)
                for value in tensor_values[
                    frame_index * frame_size : (frame_index + 1) * frame_size
                ]
            ]
            for frame_index in range(frame_count)
        ]

        if self.attack_name == "temporal_crop":
            start = int(attack_params["crop_start"])
            stop = start + int(attack_params["crop_length"])
            selected_frames = frame_slices[start:stop]
        elif self.attack_name == "frame_dropping":
            selected_frames = [frame_slices[index] for index in attack_params["kept_frame_indices"]]
        elif self.attack_name == "speed_change":
            observed_frame_count = int(attack_params["observed_frame_count"])
            selected_frames = []
            for observed_index in range(observed_frame_count):
                source_index = min(
                    frame_count - 1,
                    int(round(observed_index * float(attack_params["speed_ratio"]))),
                )
                selected_frames.append(frame_slices[source_index])
        elif self.attack_name == "local_clip":
            start = int(attack_params["clip_start"])
            stop = start + int(attack_params["clip_length"])
            selected_frames = frame_slices[start:stop]
        elif self.attack_name == "latent_gaussian_noise":
            generator = random.Random(attacked_seed)
            sigma = float(attack_params["sigma"])
            selected_frames = [
                [
                    round(float(value) + generator.gauss(0.0, sigma), 6)
                    for value in frame_slice
                ]
                for frame_slice in frame_slices
            ]
        else:
            selected_frames = frame_slices

        return [value for frame_slice in selected_frames for value in frame_slice]

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
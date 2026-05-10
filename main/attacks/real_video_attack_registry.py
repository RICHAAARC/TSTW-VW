"""
文件用途：构建阶段 2 占位 real-video attack registry。
File purpose: Build the placeholder real-video attack registry for the stage-two scaffold.
Module type: Semi-general module
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import random
from typing import Any

from main.attacks.temporal import TemporalAttackPlaceholder
from main.core.digest import compute_file_digest, compute_object_digest
from main.core.schema import LatentSample
from main.core.tensor_artifact import read_float_tensor_npy, write_float_tensor_npy


SUPPORTED_PLACEHOLDER_ATTACK_NAMES = {
    "h264_compression",
    "h265_compression",
    "spatial_resize",
    "crop_resize",
    "gaussian_noise",
    "blur",
}
SUPPORTED_TEMPORAL_ATTACK_NAMES = {
    "no_attack",
    "temporal_crop",
    "frame_dropping",
    "speed_change",
    "local_clip",
}


class VideoTensorAttackPlaceholder:
    """功能：对 latent tensor 应用占位 real-video attack。

    Apply placeholder real-video attacks directly on latent tensors.

    Args:
        attack_name: Stable attack name.
        attack_params: Attack parameter payload.

    Returns:
        None.
    """

    def __init__(self, attack_name: str, attack_params: dict[str, Any]) -> None:
        if attack_name not in SUPPORTED_PLACEHOLDER_ATTACK_NAMES:
            raise ValueError(f"unsupported attack_name: {attack_name}")
        if not isinstance(attack_params, dict):
            raise TypeError("attack_params must be a dictionary")
        self.attack_name = attack_name
        self.attack_params = dict(attack_params)
        self._artifact_cache: dict[tuple[str, str], LatentSample] = {}

    def apply(self, sample: LatentSample) -> LatentSample:
        """功能：对输入 sample 施加占位 attack。

        Apply the placeholder attack to an input sample.

        Args:
            sample: Input latent sample.

        Returns:
            An attacked sample.
        """
        if not isinstance(sample, LatentSample):
            raise TypeError("sample must be a LatentSample instance")
        if sample.latent_artifact_path is None or sample.run_root_path is None:
            raise ValueError("sample must carry latent_artifact_path and run_root_path")

        attack_params_digest = compute_object_digest(self.attack_params)[:12]
        cache_key = (sample.latent_tensor_digest_random, attack_params_digest)
        cached_sample = self._artifact_cache.get(cache_key)
        if (
            cached_sample is not None
            and cached_sample.latent_artifact_path is not None
            and Path(cached_sample.latent_artifact_path).exists()
        ):
            return cached_sample

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
        if artifact_path.exists():
            attacked_digest = compute_file_digest(artifact_path)
            attacked_sample = self._build_attacked_sample(
                sample,
                artifact_relpath,
                artifact_path,
                attacked_digest,
            )
            self._artifact_cache[cache_key] = attacked_sample
            return attacked_sample

        tensor_artifact = read_float_tensor_npy(sample.latent_artifact_path)
        attacked_values = self._apply_attack_to_tensor(tensor_artifact.values)
        write_float_tensor_npy(artifact_path, tensor_artifact.shape, attacked_values)
        attacked_digest = compute_file_digest(artifact_path)
        attacked_sample = self._build_attacked_sample(
            sample,
            artifact_relpath,
            artifact_path,
            attacked_digest,
        )
        self._artifact_cache[cache_key] = attacked_sample
        return attacked_sample

    def _build_attacked_sample(
        self,
        sample: LatentSample,
        artifact_relpath: Path,
        artifact_path: Path,
        attacked_digest: str,
    ) -> LatentSample:
        mechanism_trace = dict(sample.mechanism_trace or {})
        mechanism_trace.update(
            {
                "latent_shape": list(sample.latent_shape),
                "latent_artifact_relpath": artifact_relpath.as_posix(),
                "latent_artifact_digest": attacked_digest,
            }
        )
        return replace(
            sample,
            latent_artifact_relpath=artifact_relpath.as_posix(),
            latent_artifact_path=str(artifact_path),
            latent_artifact_digest=attacked_digest,
            latent_tensor_digest_random=attacked_digest,
            mechanism_trace=mechanism_trace,
            applied_attack_params=dict(self.attack_params),
        )

    def _apply_attack_to_tensor(self, tensor_values: Any) -> list[float]:
        values = [float(value) for value in tensor_values]
        if self.attack_name in {"h264_compression", "h265_compression"}:
            crf = float(self.attack_params.get("crf", 28))
            quant_step = max(0.01, min(0.5, crf / 200.0))
            return [round(value / quant_step) * quant_step for value in values]
        if self.attack_name == "spatial_resize":
            scale = float(self.attack_params.get("scale", 0.75))
            return [value * scale + (1.0 - scale) * 0.05 for value in values]
        if self.attack_name == "crop_resize":
            crop_ratio = float(self.attack_params.get("crop_ratio", 0.85))
            keep_scale = max(0.1, min(1.0, crop_ratio))
            return [value * keep_scale for value in values]
        if self.attack_name == "blur":
            if len(values) < 3:
                return values
            blurred_values = list(values)
            for value_index in range(1, len(values) - 1):
                blurred_values[value_index] = (
                    values[value_index - 1]
                    + values[value_index]
                    + values[value_index + 1]
                ) / 3.0
            return blurred_values
        if self.attack_name == "gaussian_noise":
            sigma = float(self.attack_params.get("sigma", 0.02))
            generator = random.Random(
                int(
                    compute_object_digest(
                        {
                            "attack_name": self.attack_name,
                            "attack_params": self.attack_params,
                        }
                    )[:12],
                    16,
                )
            )
            return [value + generator.gauss(0.0, sigma) for value in values]
        raise ValueError(f"unsupported attack_name: {self.attack_name}")


def build_real_video_attack_registry(attack_config: dict[str, Any]) -> list[Any]:
    """功能：根据配置构建阶段 2 attack registry。

    Build the stage-two attack registry from a parsed config.

    Args:
        attack_config: Parsed attack config.

    Returns:
        A list of materialized attack objects.
    """
    if not isinstance(attack_config, dict):
        raise TypeError("attack_config must be a dictionary")
    attack_entries = attack_config.get("attacks")
    if not isinstance(attack_entries, list) or not attack_entries:
        raise ValueError("attacks must be a non-empty list")

    attack_registry: list[Any] = []
    for attack_entry in attack_entries:
        attack_name = attack_entry["attack_name"]
        attack_params = attack_entry["attack_params"]
        if attack_name in SUPPORTED_TEMPORAL_ATTACK_NAMES:
            attack_registry.append(
                TemporalAttackPlaceholder(attack_name=attack_name, attack_params=attack_params)
            )
            continue
        attack_registry.append(
            VideoTensorAttackPlaceholder(attack_name=attack_name, attack_params=attack_params)
        )
    return attack_registry
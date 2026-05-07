"""
文件用途：提供 stage-one tubelet payload 与 sync codebook 的确定性构造。
File purpose: Provide deterministic codebook construction for stage-one tubelet payloads and sync codes.
Module type: Semi-general module
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from main.core.digest import compute_object_digest
from main.methods.temporal_tubelet_watermark.tubelet_partition import TubeletDescriptor


@dataclass(frozen=True)
class CodebookConfig:
    """功能：定义 stage-one codebook 配置。

    Stage-one codebook configuration.

    Args:
        direction_key: Stable key for direction generation.
        payload_key: Stable key for payload-sign generation.
        sync_key: Stable key for synchronization-code generation.
        payload_bits: Declared payload bit count.
        sync_code_family: Stable sync-code family name.
        direction_normalization: Direction normalization rule.

    Returns:
        None.
    """

    direction_key: str = "direction_key_synthetic_probe"
    payload_key: str = "payload_key_synthetic_probe"
    sync_key: str = "sync_key_synthetic_probe"
    payload_bits: int = 64
    sync_code_family: str = "keyed_binary_low_correlation"
    direction_normalization: str = "l2"


@dataclass(frozen=True)
class TubeletCodebook:
    """功能：定义 stage-one tubelet codebook 的物化结果。

    Materialized tubelet codebook for the stage-one detector.

    Args:
        directions: Direction vectors indexed by tubelet index.
        payload_codes: Payload signs indexed by tubelet index.
        sync_codes: Sync signs indexed by temporal index.
        combined_codes: Final per-tubelet signs after optional sync coupling.
        codebook_digest: Digest for the full direction construction.
        sync_code_digest: Digest for the synchronization code family.
        payload_digest: Digest for the payload sign map.

    Returns:
        None.
    """

    directions: dict[int, list[float]]
    payload_codes: dict[int, int]
    sync_codes: dict[int, int]
    combined_codes: dict[int, int]
    codebook_digest: str
    sync_code_digest: str
    payload_digest: str


def build_codebook_config() -> CodebookConfig:
    """功能：返回 stage-one codebook 默认配置。

    Build the default stage-one codebook configuration.

    Args:
        None.

    Returns:
        A `CodebookConfig` instance.
    """
    return CodebookConfig()


def build_tubelet_codebook(
    sample_id: str,
    tubelet_descriptors: list[TubeletDescriptor],
    vector_length: int | None,
    codebook_config: CodebookConfig,
    enable_sync: bool,
    reference_temporal_indices: list[int] | None = None,
) -> TubeletCodebook:
    """功能：为一个样本构建稳定 tubelet codebook。

    Build the stable tubelet codebook for one governed sample.

    Args:
        sample_id: Stable source sample identifier.
        tubelet_descriptors: Tubelet descriptor list.
        vector_length: Optional flattened tubelet vector length hint.
        codebook_config: Codebook configuration.
        enable_sync: Whether sync coupling is active.

    Returns:
        A `TubeletCodebook` instance.
    """
    if not isinstance(sample_id, str) or not sample_id:
        raise ValueError("sample_id must be a non-empty string")
    if not isinstance(tubelet_descriptors, list) or not tubelet_descriptors:
        raise ValueError("tubelet_descriptors must be a non-empty list")
    if vector_length is not None and (
        not isinstance(vector_length, int) or vector_length < 1
    ):
        raise ValueError("vector_length must be a positive integer")
    if not isinstance(codebook_config, CodebookConfig):
        raise TypeError("codebook_config must be a CodebookConfig instance")

    temporal_indices = (
        sorted(reference_temporal_indices)
        if reference_temporal_indices is not None
        else sorted({descriptor.temporal_index for descriptor in tubelet_descriptors})
    )
    sync_codes = {
        temporal_index: _build_binary_code(
            codebook_config.sync_key,
            sample_id,
            temporal_index,
        )
        for temporal_index in temporal_indices
    }
    payload_codes: dict[int, int] = {}
    combined_codes: dict[int, int] = {}
    directions: dict[int, list[float]] = {}
    direction_seed_payload: list[dict[str, int]] = []

    for descriptor in tubelet_descriptors:
        descriptor_vector_length = len(descriptor.flat_indices)
        payload_code = _build_binary_code(
            codebook_config.payload_key,
            sample_id,
            descriptor.tubelet_index,
        )
        direction_seed = _build_integer_seed(
            codebook_config.direction_key,
            sample_id,
            descriptor.tubelet_index,
        )
        payload_codes[descriptor.tubelet_index] = payload_code
        combined_codes[descriptor.tubelet_index] = payload_code * (
            sync_codes[descriptor.temporal_index] if enable_sync else 1
        )
        directions[descriptor.tubelet_index] = _build_normalized_direction(
            direction_seed,
            descriptor_vector_length,
            codebook_config.direction_normalization,
        )
        direction_seed_payload.append(
            {
                "tubelet_index": descriptor.tubelet_index,
                "temporal_index": descriptor.temporal_index,
                "direction_seed": direction_seed,
                "vector_length": descriptor_vector_length,
            }
        )

    return TubeletCodebook(
        directions=directions,
        payload_codes=payload_codes,
        sync_codes=sync_codes,
        combined_codes=combined_codes,
        codebook_digest=compute_object_digest(direction_seed_payload),
        sync_code_digest=compute_object_digest(sync_codes),
        payload_digest=compute_object_digest(payload_codes),
    )


def _build_integer_seed(key: str, sample_id: str, index_value: int) -> int:
    digest = compute_object_digest(
        {
            "key": key,
            "sample_id": sample_id,
            "index_value": index_value,
        }
    )
    return int(digest[:16], 16)


def _build_binary_code(key: str, sample_id: str, index_value: int) -> int:
    seed_value = _build_integer_seed(key, sample_id, index_value)
    return 1 if seed_value % 2 == 0 else -1


def _build_normalized_direction(
    seed_value: int,
    vector_length: int,
    normalization_rule: str,
) -> list[float]:
    if normalization_rule != "l2":
        raise ValueError(f"unsupported direction_normalization: {normalization_rule}")
    generator = random.Random(seed_value)
    values = [generator.uniform(-1.0, 1.0) for _ in range(vector_length)]
    l2_norm = math.sqrt(sum(value * value for value in values))
    if l2_norm == 0.0:
        raise ValueError("direction generation produced a zero vector")
    return [round(value / l2_norm, 8) for value in values]
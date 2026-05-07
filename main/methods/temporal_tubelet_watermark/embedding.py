"""
文件用途：提供 stage-one projection-margin embedding 的最小实现。
File purpose: Provide the minimal stage-one implementation of projection-margin embedding.
Module type: Semi-general module
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from main.core.digest import compute_file_digest
from main.core.schema import LatentSample
from main.core.tensor_artifact import read_float_tensor_npy, write_float_tensor_npy
from main.methods.temporal_tubelet_watermark.codebook import (
    CodebookConfig,
    build_codebook_config,
    build_tubelet_codebook,
)
from main.methods.temporal_tubelet_watermark.tubelet_partition import (
    TubeletPartitionConfig,
    add_tubelet_delta_in_place,
    build_tubelet_descriptors,
    build_tubelet_partition_config,
    compute_tubelet_partition_digest,
    dot_tubelet_direction,
)


EMBEDDING_RULE = "projection_margin"
DEFAULT_EMBEDDING_MARGIN = 0.25


def build_partition_config_from_method_config(
    method_config: dict[str, Any],
) -> TubeletPartitionConfig:
    """功能：从 method config 解析 tubelet partition 配置。

    Resolve the tubelet partition configuration from a method config.

    Args:
        method_config: Parsed method configuration.

    Returns:
        A `TubeletPartitionConfig` instance.
    """
    if not isinstance(method_config, dict):
        raise TypeError("method_config must be a dictionary")

    tubelet_length = int(method_config.get("tubelet_length", 1))
    tubelet_partition = method_config.get("tubelet_partition", {})
    if tubelet_partition and not isinstance(tubelet_partition, dict):
        raise TypeError("tubelet_partition must be a dictionary")
    spatial_patch_size = tuple(tubelet_partition.get("spatial_patch_size", (4, 4)))
    if len(spatial_patch_size) != 2:
        raise ValueError("spatial_patch_size must contain two integers")
    spatial_stride_payload = tubelet_partition.get("spatial_stride", spatial_patch_size)
    if isinstance(spatial_stride_payload, dict):
        spatial_stride = (
            int(spatial_stride_payload.get("height", spatial_patch_size[0])),
            int(spatial_stride_payload.get("width", spatial_patch_size[1])),
        )
    else:
        spatial_stride = tuple(spatial_stride_payload)
    temporal_stride = int(tubelet_partition.get("temporal_stride", tubelet_length))
    return build_tubelet_partition_config(
        tubelet_length=tubelet_length,
        spatial_patch_size=(int(spatial_patch_size[0]), int(spatial_patch_size[1])),
        temporal_stride=temporal_stride,
        spatial_stride=(int(spatial_stride[0]), int(spatial_stride[1])),
        allow_partial_tubelet=bool(
            tubelet_partition.get("allow_partial_tubelet", True)
        ),
    )


def apply_projection_margin_embedding(
    sample: LatentSample,
    method_variant: str,
    partition_config: TubeletPartitionConfig,
    codebook_config: CodebookConfig | None = None,
    enable_sync: bool | None = None,
    embedding_margin: float = DEFAULT_EMBEDDING_MARGIN,
) -> LatentSample:
    """功能：对输入 sample 应用 projection-margin embedding。

    Apply projection-margin embedding to the input sample.

    Args:
        sample: Input latent sample.
        method_variant: Governed method variant.
        partition_config: Tubelet partition configuration.
        codebook_config: Optional codebook configuration.
        enable_sync: Optional override for sync-code coupling.
        embedding_margin: Minimum coded projection margin.

    Returns:
        The embedded `LatentSample` instance.
    """
    if not isinstance(sample, LatentSample):
        raise TypeError("sample must be a LatentSample instance")
    if not isinstance(method_variant, str) or not method_variant:
        raise ValueError("method_variant must be a non-empty string")
    if not isinstance(partition_config, TubeletPartitionConfig):
        raise TypeError("partition_config must be a TubeletPartitionConfig instance")
    if not isinstance(embedding_margin, (int, float)) or float(embedding_margin) <= 0:
        raise ValueError("embedding_margin must be a positive number")
    if sample.latent_artifact_path is None or sample.run_root_path is None:
        raise ValueError("sample must carry latent_artifact_path and run_root_path")

    tensor_artifact = read_float_tensor_npy(sample.latent_artifact_path)
    tubelet_descriptors = build_tubelet_descriptors(sample.latent_shape, partition_config)
    vector_length = len(tubelet_descriptors[0].flat_indices)
    resolved_codebook_config = (
        build_codebook_config() if codebook_config is None else codebook_config
    )
    codebook = build_tubelet_codebook(
        sample.sample_id,
        tubelet_descriptors,
        vector_length,
        resolved_codebook_config,
        enable_sync=(method_variant.startswith("tubelet_sync") if enable_sync is None else enable_sync),
    )

    projection_before_values: list[float] = []
    projection_after_values: list[float] = []
    delta_norm_values: list[float] = []
    for descriptor in tubelet_descriptors:
        direction = codebook.directions[descriptor.tubelet_index]
        code_sign = codebook.combined_codes[descriptor.tubelet_index]
        coded_projection_before = code_sign * dot_tubelet_direction(
            tensor_artifact,
            descriptor,
            direction,
        )
        projection_before_values.append(coded_projection_before)
        if coded_projection_before < float(embedding_margin):
            delta_scale = float(embedding_margin) - coded_projection_before
            add_tubelet_delta_in_place(
                tensor_artifact,
                descriptor,
                direction,
                delta_scale * code_sign,
            )
            delta_norm_values.append(delta_scale)
            projection_after_values.append(
                coded_projection_before
                + (
                    delta_scale
                    * codebook.direction_norm_squares[descriptor.tubelet_index]
                )
            )
        else:
            delta_norm_values.append(0.0)
            projection_after_values.append(coded_projection_before)

    artifact_relpath = (
        Path("artifacts")
        / "latents"
        / "embedded"
        / method_variant
        / f"{sample.sample_id}.npy"
    )
    artifact_path = Path(sample.run_root_path) / artifact_relpath
    write_float_tensor_npy(artifact_path, tensor_artifact.shape, tensor_artifact.values)
    artifact_digest = compute_file_digest(artifact_path)

    mechanism_trace = dict(sample.mechanism_trace or {})
    mechanism_trace.update(
        {
            "latent_shape": list(sample.latent_shape),
            "latent_artifact_relpath": artifact_relpath.as_posix(),
            "latent_artifact_digest": artifact_digest,
            "tubelet_length": partition_config.tubelet_length,
            "spatial_patch_size": list(partition_config.spatial_patch_size),
            "partition_digest": compute_tubelet_partition_digest(
                sample.latent_shape,
                partition_config,
            ),
            "embedding_rule": EMBEDDING_RULE,
            "embedding_margin": round(float(embedding_margin), 6),
            "mean_projection_before": round(
                sum(projection_before_values) / len(projection_before_values),
                6,
            ),
            "mean_projection_after": round(
                sum(projection_after_values) / len(projection_after_values),
                6,
            ),
            "mean_embedding_delta_norm": round(
                sum(delta_norm_values) / len(delta_norm_values),
                6,
            ),
            "codebook_digest": codebook.codebook_digest,
            "sync_code_digest": codebook.sync_code_digest,
            "payload_digest": codebook.payload_digest,
        }
    )
    return replace(
        sample,
        latent_artifact_relpath=artifact_relpath.as_posix(),
        latent_artifact_path=str(artifact_path),
        latent_artifact_digest=artifact_digest,
        latent_tensor_digest_random=artifact_digest,
        mechanism_trace=mechanism_trace,
    )
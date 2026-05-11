"""
文件用途：验证 stage-one projection-margin embedding 的最小语义。
File purpose: Validate the minimal semantics of stage-one projection-margin embedding.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from experiments.synthetic_tubelet_sync_probe.synthetic_video_latent import (
    SyntheticVideoLatentPlaceholder,
)
from main.core.tensor_artifact import read_float_tensor_npy
from main.methods.temporal_tubelet_watermark.codebook import build_codebook_config, build_tubelet_codebook
from main.methods.temporal_tubelet_watermark.embedding import (
    DEFAULT_EMBEDDING_MARGIN,
    apply_projection_margin_embedding,
    build_partition_config_from_method_config,
)
from main.methods.temporal_tubelet_watermark.tubelet_partition import (
    build_tubelet_descriptors,
    extract_tubelet_values,
)


METHOD_CONFIG = {
    "method_family": "temporal_tubelet_watermark",
    "method_variant": "tubelet_sync",
    "method_status": "formal_synthetic_probe",
    "tubelet_length": 4,
    "enable_frame_prc": False,
    "enable_tubelet": True,
    "enable_sync": True,
    "enable_trajectory": False,
    "fusion_rule": "calibrated_tubelet_sync",
}


def test_projection_margin_embedding_satisfies_tubelet_margin(tmp_path: Path) -> None:
    """Validate that the embedded sample satisfies the configured projection margin.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)
    clean_sample = backend.build_sample(
        "sample_test_watermarked_positive_000001",
        "test",
        "watermarked_positive",
    )
    partition_config = build_partition_config_from_method_config(METHOD_CONFIG)
    embedded_sample = apply_projection_margin_embedding(
        clean_sample,
        METHOD_CONFIG["method_variant"],
        partition_config,
        embedding_margin=DEFAULT_EMBEDDING_MARGIN,
    )

    tensor_artifact = read_float_tensor_npy(embedded_sample.latent_artifact_path)
    descriptors = build_tubelet_descriptors(embedded_sample.latent_shape, partition_config)
    codebook = build_tubelet_codebook(
        embedded_sample.sample_id,
        descriptors,
        len(extract_tubelet_values(tensor_artifact, descriptors[0])),
        build_codebook_config(),
        enable_sync=True,
    )
    coded_projections = []
    for descriptor in descriptors:
        values = extract_tubelet_values(tensor_artifact, descriptor)
        direction = codebook.directions[descriptor.tubelet_index]
        code_sign = codebook.combined_codes[descriptor.tubelet_index]
        coded_projections.append(
            code_sign * sum(value * direction_value for value, direction_value in zip(values, direction))
        )

    assert min(coded_projections) >= DEFAULT_EMBEDDING_MARGIN - 1e-5
    assert embedded_sample.mechanism_trace["embedding_margin"] == DEFAULT_EMBEDDING_MARGIN
    assert embedded_sample.mechanism_trace["mean_embedding_delta_norm"] > 0.0


def test_clean_negative_sample_is_not_embedded_when_left_unchanged(tmp_path: Path) -> None:
    """Validate that a clean-negative sample remains unchanged without embedding.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    backend = SyntheticVideoLatentPlaceholder()
    backend.set_output_root(tmp_path)
    clean_sample = backend.build_sample(
        "sample_test_clean_negative_000001",
        "test",
        "clean_negative",
    )

    assert clean_sample.mechanism_trace["embedding_margin"] is None
    assert clean_sample.latent_artifact_digest == clean_sample.latent_tensor_digest_random
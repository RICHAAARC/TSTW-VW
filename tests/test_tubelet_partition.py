"""
文件用途：验证 stage-one tubelet partition 的边界与 digest 语义。
File purpose: Validate stage-one tubelet partition boundaries and digest semantics.
Module type: General module
"""

from __future__ import annotations

from array import array

from main.core.tensor_artifact import FloatTensorArtifact
from main.methods.temporal_tubelet_watermark.tubelet_partition import (
    build_tubelet_partition_config,
    build_tubelet_descriptors,
    compute_tubelet_partition_digest,
    extract_tubelet_values,
)


LATENT_SHAPE = (32, 4, 32, 32)


def test_tubelet_partition_does_not_cross_boundaries() -> None:
    """Validate that every tubelet descriptor stays within tensor bounds.

    Args:
        None.

    Returns:
        None.
    """
    partition_config = build_tubelet_partition_config(tubelet_length=4)
    descriptors = build_tubelet_descriptors(LATENT_SHAPE, partition_config)

    assert descriptors
    assert all(0 <= descriptor.frame_start < descriptor.frame_stop <= LATENT_SHAPE[0] for descriptor in descriptors)
    assert all(0 <= descriptor.height_start < descriptor.height_stop <= LATENT_SHAPE[2] for descriptor in descriptors)
    assert all(0 <= descriptor.width_start < descriptor.width_stop <= LATENT_SHAPE[3] for descriptor in descriptors)


def test_tubelet_partition_degenerates_to_frame_level_when_length_is_one() -> None:
    """Validate that `L_t=1` produces frame-level temporal spans.

    Args:
        None.

    Returns:
        None.
    """
    partition_config = build_tubelet_partition_config(tubelet_length=1)
    descriptors = build_tubelet_descriptors(LATENT_SHAPE, partition_config)

    assert descriptors[0].frame_stop - descriptors[0].frame_start == 1
    assert {descriptor.frame_stop - descriptor.frame_start for descriptor in descriptors} == {1}


def test_tubelet_partition_forms_cross_frame_groups_when_length_exceeds_one() -> None:
    """Validate that `L_t>1` forms multi-frame tubelets.

    Args:
        None.

    Returns:
        None.
    """
    partition_config = build_tubelet_partition_config(tubelet_length=4)
    descriptors = build_tubelet_descriptors(LATENT_SHAPE, partition_config)

    assert {descriptor.frame_stop - descriptor.frame_start for descriptor in descriptors} == {4}


def test_tubelet_partition_digest_is_stable_and_changes_with_length() -> None:
    """Validate digest stability and length sensitivity for the partition spec.

    Args:
        None.

    Returns:
        None.
    """
    length_one = build_tubelet_partition_config(tubelet_length=1)
    length_four = build_tubelet_partition_config(tubelet_length=4)

    stable_digest = compute_tubelet_partition_digest(LATENT_SHAPE, length_four)
    assert stable_digest == compute_tubelet_partition_digest(LATENT_SHAPE, length_four)
    assert stable_digest != compute_tubelet_partition_digest(LATENT_SHAPE, length_one)


def test_tubelet_partition_extracts_expected_payload_size() -> None:
    """Validate that extracted tubelet payloads match the descriptor volume.

    Args:
        None.

    Returns:
        None.
    """
    partition_config = build_tubelet_partition_config(tubelet_length=4)
    descriptor = build_tubelet_descriptors(LATENT_SHAPE, partition_config)[0]
    tensor_artifact = FloatTensorArtifact(
        shape=LATENT_SHAPE,
        values=array("f", [0.0] * (32 * 4 * 32 * 32)),
    )

    values = extract_tubelet_values(tensor_artifact, descriptor)
    assert len(values) == 4 * 4 * 4 * 4
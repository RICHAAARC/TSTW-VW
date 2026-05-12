"""
文件用途：验证 placeholder 与 random 字段治理规则。
File purpose: Validate placeholder and random field governance helpers and audits.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

from pathlib import Path

from tools.harness.lib.field_rules import (
    find_placeholder_field_violations,
    find_random_field_violations,
)


def test_reject_seed_payload_and_random_payload() -> None:
    assert find_random_field_violations("seed: 1\n", "memory")
    assert find_random_field_violations("payload: '01'\n", "memory")
    assert find_random_field_violations("random_payload: '01'\n", "memory")


def test_reject_placeholder_weak_fields() -> None:
    assert find_placeholder_field_violations("placeholder_backend: x\n", "memory")
    assert find_placeholder_field_violations("method_placeholder_flag: true\n", "memory")
    assert find_placeholder_field_violations("dummy_metric: 1\n", "memory")


def test_accept_random_suffix_with_trace() -> None:
    text = "\n".join(
        [
            "latent_generation_seed_random: 1",
            "payload_bits_random: 1010",
            "payload_bits_digest_random: digest",
            "random_score_digest_random: digest",
        ]
    )
    assert find_random_field_violations(text, "memory") == []


def test_accept_placeholder_suffix_fields() -> None:
    text = "\n".join(
        [
            "latent_backend_placeholder: x",
            "quality_metric_placeholder: y",
        ]
    )
    assert find_placeholder_field_violations(text, "memory") == []


def test_accept_registered_semantic_fields() -> None:
    text = "\n".join(
        [
            "method_variant: tubelet_sync",
            "attack_name: local_clip",
            "target_fpr: 0.001",
        ]
    )
    assert find_placeholder_field_violations(text, "memory") == []
    assert find_random_field_violations(text, "memory") == []


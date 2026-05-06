"""
文件用途：验证 placeholder 与 random 字段治理规则。
File purpose: Validate placeholder and random field governance helpers and audits.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from tools.harness.audits.audit_placeholder_random_fields import run_audit
from tools.harness.lib.field_rules import (
    find_placeholder_field_violations,
    find_random_field_violations,
)


def test_placeholder_suffix_valid_example_passes() -> None:
    """Validate that governed placeholder fields pass the helper rule.

    Args:
        None.

    Returns:
        None.
    """
    text = 'latent_backend_placeholder: "synthetic_gaussian_latent_placeholder"\n'
    assert find_placeholder_field_violations(text, "memory") == []


def test_placeholder_semantics_without_suffix_fail() -> None:
    """Validate that placeholder semantics without the suffix are rejected.

    Args:
        None.

    Returns:
        None.
    """
    text = 'latent_backend: "synthetic_placeholder"\n'
    violations = find_placeholder_field_violations(text, "memory")
    assert violations
    assert violations[0]["reason"] == "placeholder_value_on_ungoverned_field"


def test_random_field_with_digest_trace_passes() -> None:
    """Validate that governed random fields pass when digest trace exists.

    Args:
        None.

    Returns:
        None.
    """
    text = (
        'payload_bits_random: "1010"\n'
        'payload_bits_digest_random: "digest-123"\n'
        'latent_seed_random: 123\n'
    )
    assert find_random_field_violations(text, "memory") == []


def test_seed_as_formal_random_field_fails() -> None:
    """Validate that plain `seed` is rejected as a governed random field.

    Args:
        None.

    Returns:
        None.
    """
    text = "seed: 123\n"
    violations = find_random_field_violations(text, "memory")
    assert violations
    assert violations[0]["reason"] == "random_field_missing_governed_suffix"


def test_placeholder_field_allowed_in_claims_fails(tmp_path: Path) -> None:
    """Validate that placeholder fields cannot be marked claim-safe.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    docs_root = tmp_path / "docs"
    docs_root.mkdir(parents=True)
    (docs_root / "field_registry.md").write_text(
        "\n".join(
            [
                "| field_name | category | required_suffix | allowed_in_records | allowed_in_claims | replacement_required | description |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| latent_backend_placeholder | placeholder | _placeholder | true | true | true | bad row |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "configs").mkdir(parents=True)

    report = run_audit(tmp_path)
    assert report["decision"] == "fail"
    assert any(
        violation["reason"] == "placeholder_field_allowed_in_claims"
        for violation in report["violations"]
    )

"""
文件用途：提供 placeholder 与 random 字段治理规则。
File purpose: Provide reusable field governance rules for placeholder and random-trace validation.
Module type: General module
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


KEY_VALUE_PATTERN = re.compile(
    r"^\s*['\"]?([A-Za-z][A-Za-z0-9_]*)['\"]?\s*:\s*(.+?)\s*,?\s*$"
)

PLACEHOLDER_META_FIELDS = {"placeholder_suffix"}
ALLOWED_PLACEHOLDER_VALUE_FIELDS = {
    "method_status",
    "method_variant",
    "fusion_rule",
    "attack_name",
}
RANDOM_META_FIELDS = {
    "random_fields_required",
    "random_suffix",
    "random_digest_suffix",
}
DISALLOWED_RANDOM_FIELDS = {"seed", "payload", "random_payload"}


def _iter_key_value_pairs(text: str) -> list[tuple[int, str, str]]:
    """Extract key-value like lines from governed text.

    Args:
        text: Raw text content.

    Returns:
        A list of `(line_number, key, value)` tuples.
    """
    pairs: list[tuple[int, str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = KEY_VALUE_PATTERN.match(line)
        if match:
            pairs.append((line_number, match.group(1), match.group(2).strip()))
    return pairs


def find_placeholder_field_violations(text: str, path: str | Path) -> list[dict[str, Any]]:
    """Find placeholder field governance violations in governed text.

    Args:
        text: Raw text content from a governed file.
        path: Source file path.

    Returns:
        A list of placeholder governance violation records.
    """
    violations: list[dict[str, Any]] = []
    source_path = str(path)
    for line_number, field_name, value in _iter_key_value_pairs(text):
        lowered_name = field_name.lower()
        lowered_value = value.lower()
        if lowered_name in PLACEHOLDER_META_FIELDS:
            continue
        if "placeholder" in lowered_name and not lowered_name.endswith("_placeholder"):
            violations.append(
                {
                    "path": source_path,
                    "line": line_number,
                    "field_name": field_name,
                    "reason": "placeholder_field_missing_suffix",
                }
            )
            continue
        if (
            "placeholder" in lowered_value
            and not lowered_name.endswith("_placeholder")
            and lowered_name not in ALLOWED_PLACEHOLDER_VALUE_FIELDS
        ):
            violations.append(
                {
                    "path": source_path,
                    "line": line_number,
                    "field_name": field_name,
                    "reason": "placeholder_value_on_ungoverned_field",
                }
            )
    return violations


def check_random_field_has_seed_or_digest(
    field_name: str,
    surrounding_text: str,
) -> bool:
    """Check whether a governed random field is reproducible.

    Args:
        field_name: Random field name ending with `_random` or `_digest_random`.
        surrounding_text: Nearby or file-level text containing sibling fields.

    Returns:
        True when the field has explicit seed or digest traceability.
    """
    lowered_name = field_name.lower()
    lowered_text = surrounding_text.lower()
    if lowered_name.endswith("_digest_random"):
        return True
    if "seed" in lowered_name or "digest" in lowered_name:
        return True
    if not lowered_name.endswith("_random"):
        return False
    base_name = lowered_name[: -len("_random")]
    if f"{base_name}_seed" in lowered_text:
        return True
    if f"{base_name}_digest" in lowered_text:
        return True
    if f"{base_name}_digest_random" in lowered_text:
        return True
    return False


def find_random_field_violations(text: str, path: str | Path) -> list[dict[str, Any]]:
    """Find random-field governance violations in governed text.

    Args:
        text: Raw text content from a governed file.
        path: Source file path.

    Returns:
        A list of random governance violation records.
    """
    violations: list[dict[str, Any]] = []
    source_path = str(path)
    for line_number, field_name, _value in _iter_key_value_pairs(text):
        lowered_name = field_name.lower()
        if lowered_name in RANDOM_META_FIELDS:
            continue
        if lowered_name.endswith("_digest_random"):
            continue
        if lowered_name.endswith("_random"):
            if not check_random_field_has_seed_or_digest(lowered_name, text):
                violations.append(
                    {
                        "path": source_path,
                        "line": line_number,
                        "field_name": field_name,
                        "reason": "random_field_missing_seed_or_digest",
                    }
                )
            continue
        if lowered_name in DISALLOWED_RANDOM_FIELDS:
            violations.append(
                {
                    "path": source_path,
                    "line": line_number,
                    "field_name": field_name,
                    "reason": "random_field_missing_governed_suffix",
                }
            )
            continue
        if "random" in lowered_name:
            violations.append(
                {
                    "path": source_path,
                    "line": line_number,
                    "field_name": field_name,
                    "reason": "random_field_missing_governed_suffix",
                }
            )
    return violations

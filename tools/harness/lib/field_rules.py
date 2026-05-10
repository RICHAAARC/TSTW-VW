"""
文件用途：提供 placeholder 与 random 字段治理规则。
File purpose: Provide reusable field governance rules for placeholder and random-trace validation.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any


KEY_VALUE_PATTERN = re.compile(
    r"^\s*['\"]?([A-Za-z][A-Za-z0-9_]*)['\"]?\s*:\s*(.+?)\s*,?\s*$"
)
DICT_KEY_PATTERN = re.compile(r"['\"]([A-Za-z][A-Za-z0-9_]*)['\"]\s*:")
DATACLASS_FIELD_PATTERN = re.compile(r"^\s*([a-z][a-z0-9_]*)\s*:\s*[^=].*$")
MARKDOWN_FENCE_PATTERN = re.compile(
    r"```(json|yaml|yml|python)\s*\n(.*?)```",
    flags=re.IGNORECASE | re.DOTALL,
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
DISALLOWED_PLACEHOLDER_FIELDS = {
    "placeholder_backend",
    "method_placeholder_flag",
    "backend_placeholder_flag",
    "placeholder_metric",
    "dummy_backend",
    "dummy_metric",
    "fake_method",
    "toy_baseline",
    "baseline_placeholder_flag",
}
RANDOM_SEMANTIC_TOKENS = ("seed", "payload", "noise", "generated", "sampled", "stochastic", "random")
RANDOM_SAFE_FIELDS = {
    "sample_role",
    "sample_id",
    "num_calibration_negatives",
    "latent_generation_seed",
}
GOVERNANCE_METADATA_FIELDS = {
    "field",
    "field_name",
    "reason",
    "data",
    "value",
    "path",
    "line",
    "source_kind",
    "violation_level",
}


@dataclass(frozen=True)
class FieldCandidate:
    field_name: str
    line: int
    path: str
    source_kind: str
    value: str


@dataclass(frozen=True)
class FieldRegistry:
    rows: dict[str, dict[str, str]]
    path: str


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


def load_field_registry(root: Path) -> FieldRegistry:
    """Load governed field registry from markdown table.

    Args:
        root: Repository root.

    Returns:
        Parsed `FieldRegistry`.
    """
    registry_path = root / "docs" / "field_registry.md"
    rows: dict[str, dict[str, str]] = {}
    if not registry_path.exists():
        return FieldRegistry(rows=rows, path=str(registry_path))
    headers = [
        "field_name",
        "category",
        "required_suffix",
        "allowed_in_records",
        "allowed_in_claims",
        "replacement_required",
        "description",
    ]
    for raw_line in registry_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        if cells[0] in {"field_name", "---"} or set(cells[0]) == {"-"}:
            continue
        row = dict(zip(headers, cells))
        rows[row["field_name"]] = row
    return FieldRegistry(rows=rows, path=str(registry_path))


def _extract_governed_candidates(text: str, path: Path, source_kind: str) -> list[FieldCandidate]:
    candidates: list[FieldCandidate] = []
    for line_number, key, value in _iter_key_value_pairs(text):
        candidates.append(
            FieldCandidate(
                field_name=key,
                line=line_number,
                path=str(path),
                source_kind=source_kind,
                value=value,
            )
        )
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in DICT_KEY_PATTERN.finditer(line):
            field_name = match.group(1)
            candidates.append(
                FieldCandidate(
                    field_name=field_name,
                    line=line_number,
                    path=str(path),
                    source_kind=source_kind,
                    value=line.strip(),
                )
            )
        dataclass_match = DATACLASS_FIELD_PATTERN.match(line)
        if dataclass_match:
            field_name = dataclass_match.group(1)
            candidates.append(
                FieldCandidate(
                    field_name=field_name,
                    line=line_number,
                    path=str(path),
                    source_kind=source_kind,
                    value=line.strip(),
                )
            )
    return candidates


def find_governed_field_candidates(text: str, path: Path) -> list[FieldCandidate]:
    """Find governed field candidates across config/code/docs surfaces.

    Args:
        text: File text.
        path: File path.

    Returns:
        Field candidate list.
    """
    suffix = path.suffix.lower()
    candidates: list[FieldCandidate] = []
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        candidates.extend(_extract_governed_candidates(text, path, "source"))
    if suffix == ".md":
        for match in MARKDOWN_FENCE_PATTERN.finditer(text):
            code_block = match.group(2)
            candidates.extend(_extract_governed_candidates(code_block, path, "markdown_code_block"))
    return candidates


def validate_field_registry_row(row: dict[str, str]) -> list[dict[str, Any]]:
    """Validate one field-registry row against governance constraints."""
    violations: list[dict[str, Any]] = []
    field_name = row.get("field_name", "")
    category = row.get("category", "")
    required_suffix = row.get("required_suffix", "")
    description = row.get("description", "")
    if not category:
        violations.append({"field_name": field_name, "reason": "registry_missing_category"})
    if not required_suffix:
        violations.append({"field_name": field_name, "reason": "registry_missing_required_suffix"})
    if not description:
        violations.append({"field_name": field_name, "reason": "registry_missing_description"})
    if category == "placeholder":
        if not field_name.endswith("_placeholder"):
            violations.append({"field_name": field_name, "reason": "registry_placeholder_suffix_mismatch"})
        if row.get("allowed_in_claims", "").lower() == "true":
            violations.append({"field_name": field_name, "reason": "placeholder_field_allowed_in_claims"})
        if row.get("replacement_required", "").lower() != "true":
            violations.append({"field_name": field_name, "reason": "placeholder_field_missing_replacement_requirement"})
    if category == "random":
        if not (field_name.endswith("_random") or field_name.endswith("_digest_random")):
            violations.append({"field_name": field_name, "reason": "registry_random_suffix_mismatch"})
        if row.get("allowed_in_claims", "").lower() == "true":
            violations.append({"field_name": field_name, "reason": "random_field_allowed_in_claims"})
    return violations


def find_unregistered_governed_fields(
    candidates: list[FieldCandidate],
    registry: FieldRegistry,
) -> list[dict[str, Any]]:
    """Find governed fields that are missing from registry."""
    violations: list[dict[str, Any]] = []
    for candidate in candidates:
        lowered_name = candidate.field_name.lower()
        if lowered_name in PLACEHOLDER_META_FIELDS or lowered_name in RANDOM_META_FIELDS:
            continue
        has_governed_semantics = (
            lowered_name in registry.rows
            or lowered_name in DISALLOWED_RANDOM_FIELDS
            or lowered_name in DISALLOWED_PLACEHOLDER_FIELDS
            or lowered_name.endswith("_placeholder")
            or lowered_name.endswith("_random")
            or lowered_name.endswith("_digest_random")
            or "placeholder" in lowered_name
            or any(token in lowered_name for token in RANDOM_SEMANTIC_TOKENS)
        )
        enforce_registration = False
        if candidate.path.endswith((".json", ".yaml", ".yml", ".toml")) or candidate.source_kind == "markdown_code_block":
            enforce_registration = has_governed_semantics
        elif candidate.path.endswith(".py"):
            enforce_registration = has_governed_semantics and lowered_name.startswith(
                ("record_", "threshold_", "manifest_", "table_", "report_")
            )
        if not enforce_registration:
            continue
        if candidate.field_name not in registry.rows:
            violations.append(
                {
                    "path": candidate.path,
                    "line": candidate.line,
                    "field_name": candidate.field_name,
                    "reason": "unregistered_governed_field",
                    "source_kind": candidate.source_kind,
                }
            )
    return violations


def find_placeholder_suffix_violations(candidates: list[FieldCandidate]) -> list[dict[str, Any]]:
    """Find placeholder-suffix violations from governed candidates."""
    violations: list[dict[str, Any]] = []
    for candidate in candidates:
        lowered_name = candidate.field_name.lower()
        lowered_value = candidate.value.lower()
        has_placeholder_semantics = (
            "placeholder" in lowered_name
            or any(token in lowered_name for token in ("dummy", "fake", "toy", "stub"))
            or (
                candidate.path.endswith((".json", ".yaml", ".yml", ".toml"))
                or candidate.source_kind == "markdown_code_block"
            )
            and any(token in lowered_value for token in ("placeholder", "dummy", "fake", "toy", "stub"))
        )
        if lowered_name in PLACEHOLDER_META_FIELDS:
            continue
        if lowered_name in ALLOWED_PLACEHOLDER_VALUE_FIELDS:
            continue
        if candidate.path.endswith(".py") and lowered_name in GOVERNANCE_METADATA_FIELDS:
            continue
        if lowered_name in DISALLOWED_PLACEHOLDER_FIELDS:
            violations.append(
                {
                    "path": candidate.path,
                    "line": candidate.line,
                    "field_name": candidate.field_name,
                    "reason": "placeholder_field_missing_suffix",
                }
            )
            continue
        if has_placeholder_semantics and not lowered_name.endswith("_placeholder"):
            if candidate.source_kind == "markdown_code_block" or candidate.path.endswith(".py") or candidate.path.endswith(".json") or candidate.path.endswith(".yaml") or candidate.path.endswith(".yml"):
                violations.append(
                    {
                        "path": candidate.path,
                        "line": candidate.line,
                        "field_name": candidate.field_name,
                        "reason": "placeholder_field_missing_suffix",
                    }
                )
    return violations


def find_random_suffix_violations(candidates: list[FieldCandidate]) -> list[dict[str, Any]]:
    """Find random-field suffix violations from governed candidates."""
    violations: list[dict[str, Any]] = []
    for candidate in candidates:
        lowered_name = candidate.field_name.lower()
        if lowered_name in RANDOM_META_FIELDS:
            continue
        if lowered_name in RANDOM_SAFE_FIELDS:
            continue
        if candidate.path.endswith(".py") and lowered_name in GOVERNANCE_METADATA_FIELDS:
            continue
        has_random_semantics = any(token in lowered_name for token in RANDOM_SEMANTIC_TOKENS)
        if lowered_name.endswith("_random") or lowered_name.endswith("_digest_random"):
            continue
        if lowered_name in DISALLOWED_RANDOM_FIELDS or has_random_semantics:
            violations.append(
                {
                    "path": candidate.path,
                    "line": candidate.line,
                    "field_name": candidate.field_name,
                    "reason": "random_field_missing_governed_suffix",
                }
            )
    return violations


def find_placeholder_field_violations(text: str, path: str | Path) -> list[dict[str, Any]]:
    """Find placeholder field governance violations in governed text.

    Args:
        text: Raw text content from a governed file.
        path: Source file path.

    Returns:
        A list of placeholder governance violation records.
    """
    candidates = _extract_governed_candidates(text, Path(path), "source")
    violations = find_placeholder_suffix_violations(candidates)
    for violation in violations:
        if violation["field_name"].lower() in ALLOWED_PLACEHOLDER_VALUE_FIELDS:
            violation["reason"] = "placeholder_value_on_ungoverned_field"
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
    candidates = _extract_governed_candidates(text, Path(path), "source")
    violations = find_random_suffix_violations(candidates)
    for candidate in candidates:
        lowered_name = candidate.field_name.lower()
        if lowered_name.endswith("_random") and not check_random_field_has_seed_or_digest(
            lowered_name,
            text,
        ):
            violations.append(
                {
                    "path": candidate.path,
                    "line": candidate.line,
                    "field_name": candidate.field_name,
                    "reason": "random_field_missing_seed_or_digest",
                }
            )
    return violations

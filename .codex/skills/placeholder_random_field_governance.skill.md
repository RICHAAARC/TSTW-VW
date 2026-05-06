# Skill Name

placeholder_random_field_governance

## Purpose

Freeze suffix-based governance for placeholder fields and random trace fields across configs, JSON, and Markdown examples.

## Scope

Applies to governed fields in configuration files, JSON fragments, Markdown code blocks, field registries, and auditable examples.

## Required Inputs

- Proposed field names and example records.
- `docs/field_registry.md`.
- Repository field governance rules.

## Required Outputs

- Field naming validation result.
- Registration requirement for any newly added governed field.
- Violations for unsupported placeholder or random semantics.

## Blocking Rules

- Placeholder semantics require an `_placeholder` suffix.
- Random trace semantics require an `_random` or `_digest_random` suffix.
- Every newly introduced governed field must be registered in `docs/field_registry.md`.
- Placeholder fields are blocked from supported claims.

## Allowed Changes

- Update field registry entries.
- Update governance docs.
- Add harness rules that scan config files, JSON, and Markdown code blocks.

## Forbidden Changes

- Using plain `seed`, `payload`, or `random_payload` as governed formal fields.
- Using placeholder semantics without the `_placeholder` suffix.
- Introducing unregistered governed fields.

## Required Tests

- Accept `latent_backend_placeholder`.
- Reject placeholder semantics without the governed suffix.
- Accept tracked random fields when seed or digest semantics exist.
- Reject placeholder fields that are marked as allowed in claims.

## Required Audit Hooks

- `audit_placeholder_random_fields.py`
- `run_all_audits.py`

# Skill Name

placeholder_random_field_governance

## Purpose

Freeze suffix-based governance for placeholder fields and random trace fields across configs, JSON, and Markdown examples.

## Scope

Applies to Python source code, test fixtures, Markdown examples, and JSON configs.

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
- Reject `seed`.
- Reject `payload`.
- Reject `random_payload`.
- Reject `placeholder_backend`.
- Reject `method_placeholder_flag`.
- Accept `latent_generation_seed_random`.
- Accept `payload_bits_digest_random`.
- Accept `latent_backend_placeholder`.
- Reject unregistered governed fields.

## Required Audit Hooks

- `audit_placeholder_random_fields.py`
- `run_all_audits.py`

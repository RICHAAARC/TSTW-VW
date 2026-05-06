# Skill Name

claim_audit

## Purpose

Prevent unsupported claims by requiring every supported claim to map to formal evidence and by excluding placeholder fields from claim support.

## Scope

Applies to supported claims, evidence references, tables, curves, reports, and governed placeholder fields.

## Required Inputs

- Claim definitions or claim documentation.
- Field registry.
- Evidence categories and artifact governance rules.

## Required Outputs

- Claim support requirements.
- Violations for placeholder-backed claims.
- Required evidence binding expectations.

## Blocking Rules

- Supported claims must bind to a governed table, curve, or report artifact.
- Placeholder fields cannot support supported claims.
- Current stage may define only claim audit rules, not final claim reports.

## Allowed Changes

- Add claim governance docs.
- Add field registry constraints.
- Add tests that reject placeholder-backed claims.

## Forbidden Changes

- Marking placeholder fields as claim-safe.
- Introducing unsupported supported claims.
- Generating final paper claim reports in `protocol_skeleton`.

## Required Tests

- Reject `allowed_in_claims: true` for placeholder fields.
- Validate field registry keeps placeholder fields claim-blocked.

## Required Audit Hooks

- `audit_placeholder_random_fields.py`
- `run_all_audits.py`

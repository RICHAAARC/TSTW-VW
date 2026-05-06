# Skill Name

protocol_records

## Purpose

Define the required event-level record schema and keep protocol outputs grounded in governed records instead of ad hoc artifacts.

## Scope

Applies to event-level records, threshold records, manifests, schema documentation, and future record writers.

## Required Inputs

- Stage contract.
- Required sample roles and splits.
- Required evidence names and score names.

## Required Outputs

- Schema documentation for event-level records.
- Config skeletons that reserve required protocol fields.
- Audit-ready field definitions.

## Blocking Rules

- Current stage may only define schema and config skeletons.
- Real `RecordWriter` implementation is not allowed in `protocol_skeleton`.
- Required role, split, and evidence fields cannot be omitted from the governed schema.

## Allowed Changes

- Add or refine schema docs.
- Add contract validation utilities.
- Add tests that validate schema completeness.

## Forbidden Changes

- Implementing full record pipelines.
- Writing formal experiment records under `outputs/`.
- Dropping intermediate evidence fields from schema definitions.

## Required Tests

- Validate the presence of required sample roles.
- Validate the presence of required evidence names.
- Validate the stage contract remains in `protocol_skeleton`.

## Required Audit Hooks

- `audit_protocol_skeleton_contract.py`
- `run_all_audits.py`

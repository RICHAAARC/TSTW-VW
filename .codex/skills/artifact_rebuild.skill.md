# Skill Name

artifact_rebuild

## Purpose

Freeze the rule that future tables, figures, and reports must remain rebuildable from governed records and manifests.

## Scope

Applies to future artifact generation, records-to-artifact reconstruction, manifest linkage, and report governance.

## Required Inputs

- Record schema definitions.
- Manifest expectations.
- Target artifact categories.

## Required Outputs

- Artifact rebuild constraints.
- Required provenance fields for future artifact generators.
- Blocking notes for manual artifact paths.

## Blocking Rules

- Tables, figures, and reports must be rebuildable from governed records.
- Manual table assembly is blocked.
- Current stage may define only constraints, not a real table builder.

## Allowed Changes

- Add rebuild governance docs.
- Add manifest-facing field definitions.
- Add tests that assert rebuild constraints are declared.

## Forbidden Changes

- Creating hand-authored formal result tables.
- Creating report files that cannot be traced to governed inputs.
- Implementing a real artifact pipeline in the bootstrap stage.

## Required Tests

- Validate rebuild constraints are documented.
- Validate governed outputs reference records and manifests.

## Required Audit Hooks

- `audit_protocol_skeleton_contract.py`
- `audit_notebook_formal_output_bypass.py`

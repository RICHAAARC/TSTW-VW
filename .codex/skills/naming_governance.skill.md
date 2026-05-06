# Skill Name

naming_governance

## Purpose

Freeze formal naming rules for files, directories, modules, configuration fields, JSON fields, and method variants.

## Scope

Applies to every new formal file, directory, field, method variant, config entry, and report identifier.

## Required Inputs

- Proposed names.
- Governed forbidden suffix list.
- Governed forbidden method variant list.

## Required Outputs

- Naming validation result.
- Concrete violations with blocking reasons.
- Approved semantic alternatives when needed.

## Blocking Rules

- Formal names must use `snake_case`.
- `method_variant` must use mechanism semantics.
- `full`, `default`, `new`, `old`, `best`, and `final_method` are blocked as formal `method_variant` values.
- `*_v1`, `*_v2`, `*_p0`, and `*_p1` are blocked as formal names.

## Allowed Changes

- Add naming governance documentation.
- Add harness rules for naming inspection.
- Update tests that validate snake_case and blocked variants.

## Forbidden Changes

- Using semantic-free names for formal methods.
- Adding version-like suffixes to formal artifacts.
- Encoding stage identity inside version suffixes.

## Required Tests

- Accept `tubelet_sync` as a valid mechanism name.
- Reject `full` as a `method_variant`.
- Reject `protocol_skeleton_v1` and similar names.

## Required Audit Hooks

- `audit_naming_conventions.py`
- `run_all_audits.py`

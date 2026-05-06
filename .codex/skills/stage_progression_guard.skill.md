# Skill Name

stage_progression_guard

## Purpose

Prevent invalid stage jumps and freeze semantic stage names for the project lifecycle.

## Scope

Applies to stage naming, stage configuration, stage-related docs, and progression decisions.

## Required Inputs

- Current `project_stage`.
- Proposed target stage.
- Stage ordering from `.codex/project_contract.md`.

## Required Outputs

- Stage validation decision.
- Blocking rationale when progression is not allowed.
- Updated governed stage references when a valid transition is approved.

## Blocking Rules

- `protocol_skeleton` cannot be skipped.
- Progression directly to `synthetic_tubelet_sync_probe` or higher before satisfying bootstrap gates is blocked.
- `stage_0`, `stage_1`, `*_v1`, and `*_p0` style stage identifiers are blocked as formal stage names.

## Allowed Changes

- Update semantic stage documentation.
- Update compatibility fields such as `legacy_stage_id`.
- Add tests and audits that validate stage naming rules.

## Forbidden Changes

- Using stage-number names as primary directories, config names, method names, or report names.
- Introducing version-like stage aliases as formal identifiers.
- Advancing the stage without passing harness gates.

## Required Tests

- Reject `stage_0` as a formal `project_stage`.
- Reject version-like stage names.
- Accept `protocol_skeleton` as the active stage.

## Required Audit Hooks

- `audit_naming_conventions.py`
- `audit_protocol_skeleton_contract.py`

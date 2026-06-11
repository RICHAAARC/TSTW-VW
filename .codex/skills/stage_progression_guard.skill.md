# Skill Name

stage_progression_guard

## Purpose

Prevent invalid stage jumps and freeze semantic stage names for the project lifecycle.

## Scope

Applies to stage naming, stage configuration, stage-related docs, and progression decisions.

## Required Inputs

- Current `project_stage`.
- Proposed target stage.
- Allowed semantic stage names from `.codex/project_contract.md`.
- Stage ordering from `.codex/project_contract.md`.

## Required Outputs

- Stage validation decision.
- Blocking rationale when progression is not allowed.
- Updated governed stage references when a valid transition is approved.

## Blocking Rules

- `protocol_skeleton` cannot be skipped when progression starts from bootstrap.
- Progression directly to `synthetic_tubelet_sync_probe` or higher before satisfying bootstrap gates is blocked.
- Stage-number or version-like identifiers such as `stage1`, `stage_1`, `stage-1`, `*_v1`, and `*_p0` are blocked as formal stage identifiers.
- Formal stage references must use the allowed semantic stage names from `.codex/project_contract.md`, including `protocol_skeleton`, `synthetic_tubelet_sync_probe`, `real_video_vae_latent_probe`, `baseline_comparison_gate`, `paper_artifact_gate`, `submission_readiness_gate`, and `minimal_release_extraction`.

## Allowed Changes

- Update semantic stage documentation.
- Update compatibility fields such as `legacy_stage_id`.
- Add tests and audits that validate stage naming rules.

## Forbidden Changes

- Using stage-number names as primary directories, config names, method names, or report names.
- Introducing version-like stage aliases as formal identifiers.
- Advancing the stage without passing harness gates.

## Required Tests

- Reject stage-number and version-like stage names.
- Accept governed semantic stage names declared in `.codex/project_contract.md`, including submission-workflow gates.
- Block stage advancement when harness gates are incomplete.

## Required Audit Hooks

- `audit_naming_conventions.py`
- `audit_protocol_skeleton_contract.py`
- `audit_skill_file_presence.py`

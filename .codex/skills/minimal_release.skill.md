# Skill Name

minimal_release

## Purpose

Freeze the boundary for the future `minimal_release_extraction` stage without creating release artifacts in the bootstrap stage.

## Scope

Applies to future release boundary definitions, `minimal_release/` and `release/` extraction constraints, and current-stage release prohibitions.

## Required Inputs

- Ordered semantic stages.
- Release boundary requirements.
- Current stage contract.

## Required Outputs

- Minimal release boundary description.
- Current-stage prohibition against `minimal_release/` and `release/` directory creation.
- Required future extraction prerequisites.

## Blocking Rules

- `minimal_release_extraction` is a later semantic stage.
- Current stage must not create a `minimal_release/` directory.
- Current stage must not create a `release/` directory.
- Release extraction must wait until governed records, manifests, and audits are mature.

## Allowed Changes

- Add release boundary documentation.
- Add tests that confirm release directories are absent in `protocol_skeleton`.
- Add audit references that enforce stage order.

## Forbidden Changes

- Creating a `minimal_release` directory now.
- Shipping release manifests before protocol maturity.
- Treating bootstrap docs as release artifacts.

## Required Tests

- Confirm the bootstrap repository does not create `minimal_release/`.
- Confirm the bootstrap repository does not create `release/`.
- Confirm stage order still places release extraction last.

## Required Audit Hooks

- `audit_skill_file_presence.py`
- `audit_file_organization_contract.py`
- `audit_protocol_skeleton_contract.py`

# Skill Name

repository_intake

## Purpose

Force repository state inspection before any modification and classify the repository as `empty_repository_bootstrap` when only bootstrap material exists.

## Scope

Applies to repository intake, structure inspection, stage identification, and status reporting before work begins.

## Required Inputs

- Repository root path.
- Current visible directory structure.
- Existing stage contract from `.codex/project_contract.md`.

## Required Outputs

- Intake summary with repository mode.
- Directory status for `configs`, `docs`, `tools`, `tests`, `main`, `paper_workflow`, and `outputs`.
- Explicit confirmation of current governed stage.

## Blocking Rules

- Modifications must not start before repository intake is completed.
- If the repository is still an `empty_repository_bootstrap`, only skills, harness, configs, docs, and tests may be created.
- Stage assumptions without repository inspection are blocking violations.

## Allowed Changes

- Add or update intake-oriented documentation.
- Add inspection utilities under `tools/harness/`.
- Update tests that validate repository intake reporting.

## Forbidden Changes

- Creating algorithm directories during intake.
- Skipping status reporting for governed directories.
- Reclassifying the stage without updating governed contracts.

## Required Tests

- Validate that empty bootstrap repositories are classified as `empty_repository_bootstrap`.
- Validate that governed directories are reported with presence or absence status.

## Required Audit Hooks

- `audit_skill_file_presence.py`
- `run_all_audits.py`

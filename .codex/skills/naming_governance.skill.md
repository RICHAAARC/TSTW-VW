# Skill Name

naming_governance

## Purpose

Freeze formal naming rules for files, directories, modules, configuration fields, JSON fields, and method variants.

## Scope

Applies to file names, test file names, module names, config keys, JSON keys, Python dict keys, comment example fields, and Markdown code blocks.

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
- `stage1`, `stage2`, `stage-1`, `stage_1`, `stage-2`, `stage_2`, `*_v1`, `*_v2`, `*_v3`, `*_p0`, `*_p1`, and `*_p2` are blocked as weak semantic names.

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
- Reject `main/protocol/stage2_runner.py`.
- Reject `tests/test_stage2_records_schema.py`.
- Reject `tools/harness/run_stage1_profile.py`.
- Accept `main/protocol/real_video_vae_latent_runner.py`.
- Accept `tests/test_real_video_vae_latent_records_schema.py`.
- Accept `tools/harness/run_synthetic_tubelet_sync_profile.py`.

## Required Audit Hooks

- `audit_naming_conventions.py`
- `run_all_audits.py`

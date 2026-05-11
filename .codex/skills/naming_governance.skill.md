# Skill Name

naming_governance

## Purpose

Freeze formal naming rules for files, directories, modules, configuration fields, JSON fields, method variants, and the governed `paper_workflow/` notebook surfaces.

## Scope

Applies to file names, test file names, module names, config keys, JSON keys, Python dict keys, comment example fields, Markdown code blocks, governed notebook file names, and `paper_workflow/notebook_utils/` helper names.

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
- `paper_workflow/` root notebooks are the only file-name exception and must use `Stage<index>_<Purpose>.ipynb`.
- `paper_workflow/notebook_utils/` stage-specific helper modules are the only Python-module exception and must use `stage<index>_<purpose>.py`.
- `paper_workflow/colab_utils/` shared helpers must stay generic `snake_case` and must not use stage-prefixed names.
- `method_variant` must use mechanism semantics.
- `full`, `default`, `new`, `old`, `best`, and `final_method` are blocked as formal `method_variant` values.
- Weak semantic names matching patterns `stage[0-9]+`, `stage_[0-9]+`, `stage-[0-9]+` (any digit), `*_v[0-9]+`, `*_p[0-9]+` (any digit), `test_stage[0-9]+_*`, and `run_stage[0-9]+_*` are blocked as weak semantic names.

## Allowed Changes

- Add naming governance documentation.
- Add harness rules for naming inspection.
- Update tests that validate snake_case, the governed notebook exception, and blocked variants.

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
- Accept `paper_workflow/Stage2_Real_Video_VAE_Latent_Probe.ipynb`.
- Accept `paper_workflow/notebook_utils/stage2_real_video_vae_latent_probe_result_checker.py`.
- Reject `paper_workflow/Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb`.

## Required Audit Hooks

- `audit_naming_conventions.py`
- `run_all_audits.py`

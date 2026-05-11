# Skill Name

notebook_entrypoint

## Purpose

Ensure future notebooks remain entrypoints only and do not become the sole implementation path for formal protocol logic.

## Scope

Applies to future `.ipynb` files, notebook execution entrypoints, `paper_workflow/colab_utils/` wrappers, `scripts/` notebook-adjacent helpers, and notebook audit rules.

## Required Inputs

- Repository notebook inventory.
- Formal protocol runner expectations.
- Artifact path governance.

## Required Outputs

- Notebook governance requirements.
- Audit decision for notebook bypass risk.
- Blocking rationale when notebooks attempt to write formal artifacts directly.

## Blocking Rules

- Notebooks must not be the only place where governed protocol logic exists.
- Notebooks must not write formal `records/`, `thresholds/`, `tables/`, `figures/`, or `reports/` artifacts directly.
- While `project_stage` remains `synthetic_tubelet_sync_probe`, only `paper_workflow/Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb` may exist, and only as a transition-preparation entrypoint.

## Allowed Changes

- Add notebook governance documentation.
- Add notebook audit scripts.
- Add or update the governed stage-two Colab notebook entrypoint.
- Move notebook-only wrappers into `paper_workflow/colab_utils/` and reusable check or package logic into `scripts/`.
- Add tests that confirm the governed notebook contract and output-bypass audit.

## Forbidden Changes

- Creating additional `paper_workflow` notebooks before an explicit stage-transition decision.
- Writing formal output paths directly from notebook cells.
- Encoding protocol-only logic inside notebook code cells.
- Placing notebook-only wrappers under `main/`.

## Required Tests

- Pass the stage-two Colab notebook contract test.
- Flag notebook output bypass patterns when notebooks attempt direct formal-output writes.

## Required Audit Hooks

- `audit_notebook_formal_output_bypass.py`
- `run_all_audits.py`

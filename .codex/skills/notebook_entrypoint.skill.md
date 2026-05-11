# Skill Name

notebook_entrypoint

## Purpose

Ensure future notebooks remain entrypoints only and do not become the sole implementation path for formal protocol logic.

## Scope

Applies to future `.ipynb` files, notebook execution entrypoints, `paper_workflow/colab_utils/` shared wrappers, `paper_workflow/notebook_utils/` stage-specific helpers, `scripts/` notebook-adjacent helpers, and notebook audit rules.

## Required Inputs

- Repository notebook inventory.
- Formal protocol runner expectations.
- Artifact path governance.

## Required Outputs

- Notebook governance requirements.
- Notebook naming and helper-placement decision.
- Audit decision for notebook bypass risk.
- Blocking rationale when notebooks attempt to write formal artifacts directly.

## Blocking Rules

- Notebooks must not be the only place where governed protocol logic exists.
- Notebooks must not write formal `records/`, `thresholds/`, `tables/`, `figures/`, or `reports/` artifacts directly.
- Governed notebook entrypoints must use `snake_case` semantic names and must not append `_Colab`, `_Notebook`, `Run_`, or weak stage-number prefixes.
- Notebook-specific or notebook-adjacent helpers may live under `paper_workflow/notebook_utils/`, but they must also use stage-free `snake_case`; reusable helpers may stay under `paper_workflow/colab_utils/`.
- While `project_stage` remains `synthetic_tubelet_sync_probe`, only `paper_workflow/build_processed_real_video_dataset.ipynb` and `paper_workflow/run_real_video_vae_latent_probe.ipynb` may exist as the governed transition-preparation workflow.

## Allowed Changes

- Add notebook governance documentation.
- Add notebook audit scripts.
- Add or update the governed two-notebook stage-two workflow entrypoints.
- Move notebook-only or stage-specific wrappers into `paper_workflow/notebook_utils/`, keep reusable Colab helpers in `paper_workflow/colab_utils/`, and keep reusable check or package logic in `scripts/`.
- Add tests that confirm the governed notebook contract and output-bypass audit.

## Forbidden Changes

- Creating additional `paper_workflow` notebooks beyond the governed two-notebook workflow before an explicit stage-transition decision.
- Writing formal output paths directly from notebook cells.
- Encoding protocol-only logic inside notebook code cells.
- Placing notebook-only wrappers under `main/`.
- Placing stage-specific notebook wrappers under `paper_workflow/colab_utils/`.

## Required Tests

- Pass the real-video workflow notebook contract test.
- Pass the notebook naming and placement audit.
- Flag notebook output bypass patterns when notebooks attempt direct formal-output writes.

## Required Audit Hooks

- `audit_notebook_naming_contract.py`
- `audit_notebook_formal_output_bypass.py`
- `run_all_audits.py`

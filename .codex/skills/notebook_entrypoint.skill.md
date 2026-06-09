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
- Parallel-semantics decision for `shard_count`, `shard_index`, and `worker_count`.
- Audit decision for notebook bypass risk.
- Blocking rationale when notebooks attempt to write formal artifacts directly.

## Blocking Rules

- Notebooks must not be the only place where governed protocol logic exists.
- Notebooks must not write formal `records/`, `thresholds/`, `tables/`, `figures/`, or `reports/` artifacts directly.
- Governed notebook entrypoints must use `snake_case` semantic names and must not append `_Colab`, `_Notebook`, `Run_`, or weak stage-number prefixes.
- Notebook-specific or notebook-adjacent helpers may live under `paper_workflow/notebook_utils/`, but they must also use stage-free `snake_case`; reusable helpers may stay under `paper_workflow/colab_utils/`.
- Governed notebook config and helper guidance must distinguish outer shard parallelism from in-shard worker parallelism: `shard_count` is the outer event-shard count, `shard_index` selects the current outer shard, and `worker_count` is the in-shard local worker count after shard selection.
- While `project_stage` remains `synthetic_tubelet_sync_probe`, only `paper_workflow/build_processed_real_video_dataset.ipynb`, `paper_workflow/run_real_video_vae_latent_probe.ipynb`, and `paper_workflow/run_trajectory_statistic_probe.ipynb` may exist as governed notebook entrypoints; the trajectory notebook is limited to Colab GPU validation through repository helper / CLI code.

## Allowed Changes

- Add notebook governance documentation.
- Add notebook audit scripts.
- Add or update the governed notebook entrypoints, including the two stage-two transition-preparation notebooks and the trajectory formal GPU validation notebook.
- Add or update notebook contract text that freezes the order: first select the shard with `shard_count` and `shard_index`, then parallelize within the selected shard using `worker_count`.
- Move notebook-only or stage-specific wrappers into `paper_workflow/notebook_utils/`, keep reusable Colab helpers in `paper_workflow/colab_utils/`, and keep reusable check or package logic in `scripts/`.
- Add tests that confirm the governed notebook contract and output-bypass audit.

## Forbidden Changes

- Creating additional `paper_workflow` notebooks beyond the governed notebook entrypoints without an explicit stage-transition or validation decision.
- Writing formal output paths directly from notebook cells.
- Encoding protocol-only logic inside notebook code cells.
- Placing notebook-only wrappers under `main/`.
- Placing stage-specific notebook wrappers under `paper_workflow/colab_utils/`.

## Required Tests

- Pass the real-video workflow notebook contract test and the trajectory statistic probe notebook contract test.
- Pass the notebook naming and placement audit.
- Flag notebook output bypass patterns when notebooks attempt direct formal-output writes.

## Required Audit Hooks

- `audit_notebook_naming_contract.py`
- `audit_notebook_formal_output_bypass.py`
- `run_all_audits.py`

# Skill Name

notebook_entrypoint

## Purpose

Ensure future notebooks remain entrypoints only and do not become the sole implementation path for formal protocol logic.

## Scope

Applies to future `.ipynb` files, notebook execution entrypoints, and notebook audit rules.

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
- Notebooks must not write formal `tables/` or `thresholds/` artifacts directly.
- Current stage must not create notebooks.

## Allowed Changes

- Add notebook governance documentation.
- Add notebook audit scripts.
- Add tests that confirm a notebook-free bootstrap passes.

## Forbidden Changes

- Creating `paper_workflow` notebooks in `protocol_skeleton`.
- Writing formal output paths directly from notebook cells.
- Encoding protocol-only logic inside notebook code cells.

## Required Tests

- Pass audit when no notebooks exist.
- Flag notebook output bypass patterns when notebooks are later introduced.

## Required Audit Hooks

- `audit_notebook_formal_output_bypass.py`
- `run_all_audits.py`

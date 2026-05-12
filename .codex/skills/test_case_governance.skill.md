# Skill Name

test_case_governance

## Purpose

Freeze test-case construction, migration, marker, fixture, and runtime-cost rules for the governed repository.

## Scope

Applies to `tests/`, `tests/constraints/`, `tests/functional/`, `tests/integration/`, `tests/helpers/`, `tests/fixtures/`, `pyproject.toml`, `docs/test_list.md`, `docs/test_case_constraints.md`, and test-related harness rules.

## Required Inputs

- Proposed or modified test file paths.
- Expected runtime cost and external resource needs.
- Required pytest markers.
- Fixture or helper placement.
- `docs/test_case_constraints.md`.

## Required Outputs

- Test type classification: `constraints`, `functional`, or `integration`.
- Marker decision using `unit`, `constraint`, `quick`, `integration`, `smoke`, `slow`, and `formal`.
- Fixture and output-path decision.
- Required documentation or harness updates.

## Blocking Rules

- Root-level `tests/test_*.py` files are forbidden.
- Constraint tests must not run runners, real mp4 I/O, `ffmpeg`, VAE/model loading, or artifact rebuild workflows.
- Functional tests must be `unit` or `quick` by default and must not carry `integration`, `smoke`, `slow`, or `formal` markers.
- Integration tests must carry `integration`; key end-to-end tests must also carry `smoke`, formal gate tests must carry `formal`, and broad or long tests must carry `slow`.
- Test outputs must use `tmp_path` or `tmp_path_factory`, never checked-in `outputs/` or repository-root scratch paths.
- Helper files under `tests/helpers/` must not be named `test_*.py`.
- Test file names, fixture names, and temporary artifact fields must follow naming and placeholder/random governance.

## Allowed Changes

- Move, split, merge, or rename tests to satisfy `docs/test_case_constraints.md`.
- Add or update module-level pytest markers.
- Add lightweight fixtures under `tests/fixtures/`.
- Add helpers under `tests/helpers/`.
- Update `docs/test_list.md`, `pyproject.toml`, and test-case harness audits.

## Forbidden Changes

- Deleting test coverage to reduce default runtime.
- Moving runtime-heavy or formal tests into `constraints/` or default quick paths.
- Allowing unmarked tests to enter the default pytest selection.
- Writing test artifacts into checked-in formal output directories.
- Bypassing `audit_test_case_constraints.py` or `run_all_audits.py`.

## Required Tests

- Collect all tests with `python -m pytest --collect-only -q -m "not __never__"`.
- Run default `python -m pytest -q`.
- Validate constraints with `python -m pytest -q tests/constraints`.
- Validate quick functional tests with `python -m pytest -q tests/functional -m "unit or quick"`.
- Collect smoke and formal gates with marker-specific pytest commands when runtime is not intended for the default path.

## Required Audit Hooks

- `audit_test_case_constraints.py`
- `audit_naming_conventions.py`
- `audit_utf8_encoding_contract.py`
- `run_all_audits.py`

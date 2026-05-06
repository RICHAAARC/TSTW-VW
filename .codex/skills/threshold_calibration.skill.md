# Skill Name

threshold_calibration

## Purpose

Freeze the fixed low-FPR threshold protocol and prevent threshold leakage into the test split.

## Scope

Applies to threshold configs, threshold records, calibration role definitions, and threshold governance documentation.

## Required Inputs

- Threshold protocol config.
- Required calibration split.
- Required calibration negative roles.

## Required Outputs

- Threshold protocol skeleton.
- Validation result for calibration and test gating rules.
- Audit-ready threshold field definitions.

## Blocking Rules

- `calibration_split` must be `calibration`.
- `calibration_negative_roles` must include `clean_negative` and `attacked_negative`.
- `test` split must not update thresholds.
- `test` split data must not be used to calibrate thresholds.

## Allowed Changes

- Update threshold protocol docs.
- Add or refine threshold validation utilities.
- Add tests for calibration-only threshold rules.

## Forbidden Changes

- Allowing `test` split threshold updates.
- Calibrating on positive samples.
- Creating attack-specific thresholds in the bootstrap stage.

## Required Tests

- Accept `calibration` as the calibration split.
- Reject `test_threshold_update_allowed: true`.
- Require both negative calibration roles.

## Required Audit Hooks

- `audit_threshold_protocol_fields.py`
- `run_all_audits.py`

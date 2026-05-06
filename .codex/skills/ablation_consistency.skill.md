# Skill Name

ablation_consistency

## Purpose

Freeze shared protocol constraints for future ablations so that all variants remain comparable under one governed evaluation protocol.

## Scope

Applies to future ablation configs, split sharing, attack matrix sharing, target FPR sharing, and table builder sharing.

## Required Inputs

- Ablation config skeleton.
- Shared protocol requirements.
- Target evaluation stage.

## Required Outputs

- Declared shared protocol requirements for ablations.
- Blocking notes for unsupported divergence.
- Audit-ready consistency expectations.

## Blocking Rules

- Ablations must share split definitions.
- Ablations must share attack matrix definitions.
- Ablations must share `target_fpr` and `table_builder` governance.
- Current stage may define only constraints, not a full ablation runner.

## Allowed Changes

- Add ablation governance docs.
- Add placeholder ablation configs.
- Add tests that validate shared protocol requirements.

## Forbidden Changes

- Implementing a real ablation runner in `protocol_skeleton`.
- Declaring ablation variants that silently change split or target FPR.
- Creating manual comparison tables.

## Required Tests

- Validate `shared_protocol_required: true` in the placeholder ablation config.
- Validate governed ablation placeholder names use the placeholder suffix.

## Required Audit Hooks

- `audit_protocol_skeleton_contract.py`
- `audit_placeholder_random_fields.py`

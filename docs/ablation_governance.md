# Ablation Governance

本文档冻结 `protocol_skeleton` 阶段的 ablation shared-protocol 约束。当前阶段只声明约束，不实现真实 `AblationRunner`。

## Frozen Requirements

- 所有 ablation variant 必须共享同一 split 定义。
- 所有 ablation variant 必须共享同一 attack matrix。
- 所有 ablation variant 必须共享同一 target FPR。
- 所有 ablation variant 必须共享同一 table builder 治理口径。

## Governed Placeholder Variants

- `frame_prc_placeholder`
- `tubelet_only_placeholder`
- `tubelet_sync_placeholder`

这些 variant 只用于冻结后续消融入口，不代表当前阶段已经实现对应方法。

## Governed Config Entries

- `configs/ablation/ablation_placeholder.json`
- `configs/attacks/identity_attack_placeholder.json`
- `configs/schema/protocol_artifact_schema.json`

## Stage Boundary

- 当前阶段不得创建真实 ablation runner。
- 当前阶段不得手工拼接 comparison tables。
- 当前阶段只允许通过 config 和 audit 冻结 shared protocol requirements。
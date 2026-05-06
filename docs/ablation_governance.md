# Ablation Governance

本文档冻结 `protocol_skeleton` 阶段的 ablation shared-protocol 约束。当前阶段实现的是 placeholder / random 驱动的 `AblationRunner` scaffold，而不是真实算法比较器。

## Frozen Requirements

- 所有 ablation variant 必须共享同一 split 定义。
- 所有 ablation variant 必须共享同一 attack matrix。
- 所有 ablation variant 必须共享同一 target FPR。
- 所有 ablation variant 必须共享同一 table builder 治理口径。

## Governed Stage-0 Method Variants

- `empty_watermark_method_placeholder`
- `random_score_detector_random`

这些 variant 用于完成阶段 0 的 schema、threshold、record 与 table rebuild 骨架验证，不代表当前阶段已经实现具有方法性能意义的真实算法。

## Governed Config Entries

- `configs/ablation/ablation_placeholder.json`
- `configs/ablation/protocol_skeleton_methods.json`
- `configs/attacks/identity_attack_placeholder.json`
- `configs/schema/protocol_artifact_schema.json`

## Stage Boundary

- 当前阶段不得创建真实算法驱动的 ablation runner。
- 当前阶段不得手工拼接 comparison tables。
- 当前阶段只允许通过 config 和 audit 冻结 shared protocol requirements。
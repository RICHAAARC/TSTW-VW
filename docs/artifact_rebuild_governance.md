# Artifact Rebuild Governance

本文档冻结 `protocol_skeleton` 阶段的 artifact rebuild 约束。当前阶段实现的是 placeholder / random 驱动的最小 `TableBuilder` scaffold，而不是真实论文 artifact pipeline。

## Rebuild Rules

- tables 必须能够从 governed records 和 manifest 重建。
- figures 必须能够从 governed records、manifest 与正式 builder 重建。
- reports 必须能够追溯到 governed records、manifest 与正式 artifact builders。
- manual table、curve 或 report assembly 属于阻断违规。

## Governed Provenance Fields

- `records_digest`
- `thresholds_digest`
- `tables_digest`
- `method_config_digest`
- `protocol_config_digest`
- `attack_matrix_digest`
- `ablation_config_digest`

## Stage Boundary

- 当前阶段不在仓库中 check in 正式 `tables/`、`figures/` 或 `reports/`。
- 当前阶段通过临时输出路径执行 table rebuild 验证，并冻结 schema、digest 字段和输出布局。
- 后续阶段实现真实 artifact pipeline 时，不得绕过 `configs/schema/protocol_artifact_schema.json` 中的冻结路径与字段口径。
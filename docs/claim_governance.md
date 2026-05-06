# Claim Governance

本文档冻结 `protocol_skeleton` 阶段的 supported claim 边界。当前阶段只定义 claim audit 规则，不生成正式 `paper_claim_audit` 报告。

## Supported Claim Rules

- 每个 supported claim 必须绑定到受治理的 table、curve 或 report artifact。
- placeholder 字段不得支持 supported claim。
- random trace 字段不得被解释为方法有效性证据。
- 当前阶段不得把 bootstrap docs、临时 notebook 输出或终端日志当作正式 claim evidence。

## Governed References

- `docs/field_registry.md`
- `docs/protocol_artifact_schema.md`
- `docs/artifact_rebuild_governance.md`

## Stage Boundary

- 当前阶段只允许声明 claim-support requirements。
- 当前阶段不得生成正式论文 claim report。
- 进入后续阶段时，所有 supported claim 仍必须保持对 table、curve 或 report artifact 的可追溯绑定。
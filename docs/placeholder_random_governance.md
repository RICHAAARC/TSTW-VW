# Placeholder And Random Governance

## Scope

- 本规则适用于 `configs`、`docs`、`main`、`tests`、`tools`、`.codex`、`AGENTS.md`、`README.md`。
- Python 源码中的 record dict key、manifest dict key、测试 fixture key 必须遵守 suffix 规则。
- Markdown 中 JSON / YAML / Python 示例代码块必须遵守 suffix 规则。

## Placeholder Rules

- 占位字段必须以 `_placeholder` 结尾。
- 所有 placeholder 字段必须登记到 `docs/field_registry.md`。
- 所有 placeholder 字段必须 `allowed_in_claims=false`。
- 所有 placeholder 字段应设置 `replacement_required=true`。

## Random Trace Rules

- 随机追踪字段必须以 `_random` 或 `_digest_random` 结尾。
- 所有 random 字段必须登记到 `docs/field_registry.md`。
- `*_random` 必须具备 seed 或 digest 追踪语义。
- 所有 random 字段必须 `allowed_in_claims=false`。

## Registration Rule

- 未登记字段不得进入正式 `records`、`thresholds`、`manifest`、`tables`、`reports`。
- 未登记临时字段不得作为 governed field 使用。

# Placeholder And Random Governance

## Placeholder Rules

- 占位实现、占位后端、占位指标、占位方法、占位路径、占位 baseline 的字段名必须以 `_placeholder` 结尾。
- 当前阶段允许 placeholder 配置存在，但必须显式登记到 `docs/field_registry.md`。
- `*_placeholder` 字段不得进入 supported claim。

## Random Trace Rules

- 随机生成且需要后续复现、替换、追踪或清理的字段名必须以 `_random` 或 `_digest_random` 结尾。
- 所有 `*_random` 字段必须具有 seed 或 digest 追踪条件。
- `*_digest_random` 可作为自包含 digest 追踪字段。

## Blocked Examples

- `seed`
- `payload`
- `random_payload`
- `placeholder_method`
- `method_placeholder_flag`
- `backend_random_flag`

## Audit Surface

- 配置文件。
- JSON 片段。
- Markdown 示例代码块。
- 字段登记表。

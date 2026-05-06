# Naming Governance

## Formal Naming Rules

- 正式文件名、目录名、Python 模块名、配置字段名、JSON 字段名必须使用 `snake_case`。
- `project_stage` 必须使用语义阶段名，而不是编号阶段名。
- `method_variant` 必须表达机制语义，例如 `tubelet_sync`。

## Blocked Names

- 禁止 `stage_0`、`stage_1` 作为正式阶段名。
- 禁止 `*_v1`、`*_v2`、`*_p0`、`*_p1` 作为正式命名后缀。
- 禁止 `full`、`default`、`new`、`old`、`best`、`final_method` 作为正式 `method_variant`。

## Compatibility Exceptions

- `schema_version`
- `compatibility_version`
- `legacy_stage_id`

这些字段表达 schema 或兼容性，不表达正式方法阶段。

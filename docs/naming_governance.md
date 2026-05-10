# Naming Governance

## Governance Surface

- 正式 文件名、目录名、Python 模块名、测试 文件名、配置 文件名必须使用 `snake_case`。
- 配置键、JSON key、Python dict key、测试 fixture key、Markdown 代码块中的 key 都属于治理面。
- 文档标题、注释、docstring、示例字段名中的弱阶段命名也属于治理面。

## Global Blocking Rules

- 全仓库阻断弱阶段编号：`stage0`、`stage1`、`stage2`、`stage_0`、`stage_1`、`stage_2`、`stage-0`、`stage-1`、`stage-2`。
- 全仓库阻断弱测试和脚本命名：`test_stage1_*`、`test_stage2_*`、`run_stage1_*`、`run_stage2_*`。
- 全仓库阻断弱版本后缀：`*_v1`、`*_v2`、`*_v3`、`*_p0`、`*_p1`、`*_p2`。
- `method_variant` 必须使用机制语义，禁止 `full`、`default`、`new`、`old`、`best`、`final_method`。

## Allowed Exceptions

- `schema_version`
- `compatibility_version`
- `legacy_stage_id`
- 外部技术版本表达，例如 Python / CUDA / 依赖版本号。

## Historical Docs Exemption

- 仅 `docs/builds/**` 允许保留历史阶段说明与历史弱命名示例。
- 除 `docs/builds/**` 外，不允许以历史原因绕过治理。

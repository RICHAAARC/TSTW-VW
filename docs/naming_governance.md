# Naming Governance

## Governance Surface

- 正式 文件名、目录名、Python 模块名、测试 文件名、配置 文件名必须使用 `snake_case`。
- `paper_workflow/` 根下受治理的 notebook 同样必须使用 `snake_case` 机制语义命名。
- `paper_workflow/notebook_utils/` 下的 helper 也必须使用 stage-free `snake_case`。
- `paper_workflow/colab_utils/` 下的共享 helper 仍必须使用通用 `snake_case`，且不得把单一阶段语义写进文件名。
- 配置键、JSON key、Python dict key、测试 fixture key、Markdown 代码块中的 key 都属于治理面。
- 文档标题、注释、docstring、示例字段名中的弱阶段命名也属于治理面。

## Global Blocking Rules

- 全仓库阻断弱阶段编号（正则形式 `stage[0-9]+` 等覆盖任意版本）：`stage0`、`stage1`、`stage2`、`stage_0`、`stage_1`、`stage_2`、`stage-0`、`stage-1`、`stage-2`。
- 全仓库阻断弱测试和脚本命名（正则形式 `test_stage[0-9]+_*` 等覆盖任意版本）：`test_stage0_*`、`test_stage1_*`、`test_stage2_*`、`run_stage0_*`、`run_stage1_*`、`run_stage2_*`。
- 全仓库阻断弱版本后缀（正则形式 `*_v[0-9]+` 和 `*_p[0-9]+` 等覆盖任意版本）：`*_v0`、`*_v1`、`*_v2`、`*_v3`、`*_p0`、`*_p1`、`*_p2` 等任意后续数字版本。
- `method_variant` 必须使用机制语义，禁止 `full`、`default`、`new`、`old`、`best`、`final_method`。

## Allowed Exceptions

- `schema_version`
- `compatibility_version`
- `legacy_stage_id`
- `paper_workflow/build_processed_real_video_dataset.ipynb`
- `paper_workflow/run_real_video_vae_latent_probe.ipynb`
- 外部技术版本表达，例如 Python / CUDA / 依赖版本号。

## Historical Docs Exemption

- 仅 `docs/builds/**` 允许保留历史阶段说明与历史弱命名示例。
- 除 `docs/builds/**` 外，不允许以历史原因绕过治理。

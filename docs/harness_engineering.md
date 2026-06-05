# Harness Engineering

本目录定义当前 `synthetic_tubelet_sync_probe` 阶段与后续 `real_video_vae_latent_probe` 过渡期的可执行工程门禁，并与 `docs/file_organization.md` 保持一致。

## Scope

- `tools/harness/lib/` 提供标准库实现的扫描、命名规则、字段规则与 JSON 报告能力。
- `tools/harness/audits/` 提供命名、字段、项目契约、support config、阈值协议、notebook bypass、notebook 命名、file organization、UTF-8 编码、main 边界与 skill 存在性审计。
- `tools/harness/audits/audit_runtime_profile_boundaries.py` 与相关 notebook contract / governance docs 共同冻结运行并行语义：`shard_count` 表示外层 event shard 总数，`shard_index` 表示当前选中的外层 shard 编号，`worker_count` 表示已选 shard 内部的本地 worker 数；这些字段都属于 execution-only knob，不得被解释为方法语义。
- `tools/harness/audits/audit_test_case_constraints.py` 执行 `docs/test_case_constraints.md` 对应的测试目录、marker、helper 命名与 pytest 默认口径审计。
- `tools/harness/inspect_repository.py` 提供 governed repository intake，并报告 `configs/`、`docs/`、`tools/`、`tests/`、`main/`、`paper_workflow/`、`scripts/`、`experiments/`、`audit_reports/`、`.codex/`、`examples/`、`release/` 的状态，同时将 `outputs/` 归类为 ephemeral runtime root。
- `docs/file_organization.md` 冻结目录边界：`main/` 为核心方法包，`experiments/` 为阶段性 runner，`scripts/` 为命令行辅助工具，`paper_workflow/` 为 Colab / Notebook workflow。
- `tools/harness/audits/audit_file_organization_contract.py` 阻断旧 `main/colab/`、阶段性 runner 反留在 `main/`、顶层 placeholder scaffold 配置，以及过早创建 `minimal_release/` / `release/` 根目录。
- `tools/harness/audits/audit_notebook_naming_contract.py` 冻结 `paper_workflow/` 根 notebook 的 `Stage<数字>_<用途>` 命名、`paper_workflow/notebook_utils/` 的 `stage<数字>_<用途>` 命名，以及 shared `colab_utils/` 与 notebook-specific helper 的目录分层。
- `tools/harness/audits/audit_utf8_encoding_contract.py` 阻断 governed roots 中的非 `UTF-8` 文本文件，避免再次出现乱码或本地代码页写入污染。
- `tools/harness/run_all_audits.py` 统一汇总审计，并将摘要写入 `audit_reports/harness_audit_summary.json`。
- `tests/` 提供 pytest 分层闭环：`constraints/` 保存默认治理测试，`functional/` 保存默认 quick 功能测试，`integration/` 保存默认排除的 runner、smoke、slow 与 formal gate 测试。

## Layer Boundary

- `tools/harness/` 是外层 governance 层，不属于 `method_core`、`protocol_core` 或未来 `minimal_demo` 的运行时依赖。
- `main/` 可以被 harness 和 tests 检查，但 `main/` 不得反向 import `tools/harness`、`tests`、`paper_workflow` 或 `experiments`。
- protocol runtime validation 可以保留在 `main/core/`、`main/protocol/` 与 `main/analysis/`。
- stage-specific runner、artifact builder 与 synthetic probe contract 必须留在 `experiments/`，不能长期留在 `main/`。
- Colab runtime preflight、共享 Drive 打包与 shared session wrapper 必须留在 `paper_workflow/colab_utils/` 或 `scripts/`，notebook-specific / stage-specific helper 必须留在 `paper_workflow/notebook_utils/`，这些能力都不能长期留在 `main/`。

## Runtime Guarantees

- Harness 脚本仅依赖 Python 标准库。
- `audit_reports/` 仅作为运行时审计输出目录，不属于正式论文 `outputs/`。
- 受治理文本文件默认使用 `UTF-8`；仓库文本读写应显式声明 `encoding="utf-8"`，避免依赖本地默认代码页。
- 项目构建、notebook 运行、脚本执行与开发工具保存文件时必须保持 `UTF-8`；不得依赖 Windows 本地 ANSI 代码页、PowerShell 默认输入编码或 cmd 默认活动代码页。
- Windows 终端入口应在启动时设置 `chcp 65001`、PowerShell `Console` 输入输出编码、`PYTHONUTF8=1` 与 `PYTHONIOENCODING=utf-8`，确保中文注释、notebook JSON 与审计报告不会被本地代码页替换成问号。
- harness、governance docs 与 notebook contract 必须保持统一的并行语义：先按 `shard_count` / `shard_index` 选择 outer shard，再按 `worker_count` 对该 shard 内部做本地并行；不得把 `worker_count` 当作额外 shard 数，也不得把 `shard_count` / `shard_index` 当作线程数解释。
- 当前阶段允许 synthetic / placeholder 驱动的最小 mechanism runtime，但这些实现不应继续占据 `main/` 的最终发布边界。
- 当前阶段不创建 `minimal_release/`，也不允许将 `paper_workflow/` 变成唯一 formal 入口。

## Required Entry Commands

```bash
pytest -q
python tools/harness/run_all_audits.py
```

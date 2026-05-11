# Harness Engineering

本目录定义当前 `synthetic_tubelet_sync_probe` 阶段与后续 `real_video_vae_latent_probe` 过渡期的可执行工程门禁，并与 `docs/file_organization.md` 保持一致。

## Scope

- `tools/harness/lib/` 提供标准库实现的扫描、命名规则、字段规则与 JSON 报告能力。
- `tools/harness/audits/` 提供命名、字段、项目契约、support config、阈值协议、notebook bypass、file organization、main 边界与 skill 存在性审计。
- `tools/harness/inspect_repository.py` 提供 governed repository intake，并报告 `configs/`、`docs/`、`tools/`、`tests/`、`main/`、`paper_workflow/`、`scripts/`、`experiments/` 与 `outputs/` 状态。
- `docs/file_organization.md` 冻结目录边界：`main/` 为核心方法包，`experiments/` 为阶段性 runner，`scripts/` 为命令行辅助工具，`paper_workflow/` 为 Colab / Notebook workflow。
- `tools/harness/run_all_audits.py` 统一汇总审计，并将摘要写入 `audit_reports/harness_audit_summary.json`。
- `tests/` 提供 pytest 最小闭环，验证命名、字段治理、协议契约、目录边界与汇总审计。

## Layer Boundary

- `tools/harness/` 是外层 governance 层，不属于 `method_core`、`protocol_core` 或未来 `minimal_demo` 的运行时依赖。
- `main/` 可以被 harness 和 tests 检查，但 `main/` 不得反向 import `tools/harness`、`tests`、`paper_workflow` 或 `experiments`。
- protocol runtime validation 可以保留在 `main/core/`、`main/protocol/` 与 `main/analysis/`。
- stage-specific runner、artifact builder 与 synthetic probe contract 必须留在 `experiments/`，不能长期留在 `main/`。
- Colab runtime preflight、Drive 打包、Notebook checker 与 session wrapper 必须留在 `paper_workflow/colab_utils/` 或 `scripts/`，不能长期留在 `main/`。

## Runtime Guarantees

- Harness 脚本仅依赖 Python 标准库。
- `audit_reports/` 仅作为运行时审计输出目录，不属于正式论文 `outputs/`。
- 当前阶段允许 synthetic / placeholder 驱动的最小 mechanism runtime，但这些实现不应继续占据 `main/` 的最终发布边界。
- 当前阶段不创建 `minimal_release/`，也不允许将 `paper_workflow/` 变成唯一 formal 入口。

## Required Entry Commands

```bash
pytest -q
python tools/harness/run_all_audits.py
```

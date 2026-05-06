# Harness Engineering

本目录定义 `protocol_skeleton` 阶段的可执行工程门禁。

## Scope

- `tools/harness/lib/` 提供标准库实现的扫描、命名规则、字段规则与 JSON 报告能力。
- `tools/harness/audits/` 提供命名、字段、阶段契约、阶段 0 support config、阈值协议、notebook bypass 与 skill 存在性审计。
- `configs/schema/protocol_artifact_schema.json` 冻结阶段 0 的 records、thresholds、manifest 与 table layout schema skeleton。
- `configs/attacks/identity_attack_placeholder.json` 与 `configs/ablation/ablation_placeholder.json` 冻结阶段 0 的 attack 与 ablation support config skeleton。
- `tools/harness/run_all_audits.py` 统一汇总审计，并将摘要写入 `audit_reports/harness_audit_summary.json`。
- `tests/` 提供 pytest 最小闭环，验证命名、字段治理、协议契约与汇总审计。

## Runtime Guarantees

- Harness 脚本仅依赖 Python 标准库。
- `audit_reports/` 仅作为运行时审计输出目录，不属于正式论文 `outputs/`。
- 当前阶段不实现真实 records writer、threshold calibrator、table builder 或 notebook runner。
- 当前阶段仅冻结 protocol artifact schema，不落地真实实验产物写入。
- 当前阶段仅冻结 support config、claim 边界与 release boundary，不创建真实 `minimal_release/` 或 runtime 目录。

## Required Entry Commands

```bash
pytest -q
python tools/harness/run_all_audits.py
```

# Harness Engineering

本目录定义 `protocol_skeleton` 阶段的可执行工程门禁。

## Scope

- `tools/harness/lib/` 提供标准库实现的扫描、命名规则、字段规则与 JSON 报告能力。
- `tools/harness/audits/` 提供命名、字段、阶段契约、阈值协议、notebook bypass 与 skill 存在性审计。
- `tools/harness/run_all_audits.py` 统一汇总审计，并将摘要写入 `audit_reports/harness_audit_summary.json`。
- `tests/` 提供 pytest 最小闭环，验证命名、字段治理、协议契约与汇总审计。

## Runtime Guarantees

- Harness 脚本仅依赖 Python 标准库。
- `audit_reports/` 仅作为运行时审计输出目录，不属于正式论文 `outputs/`。
- 当前阶段不实现真实 records writer、threshold calibrator、table builder 或 notebook runner。

## Required Entry Commands

```bash
pytest
python tools/harness/run_all_audits.py
```

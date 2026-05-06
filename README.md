# TSTW-VW

本仓库当前处于 `protocol_skeleton` 阶段。

当前仓库包含阶段 0 所需的 governance 层与 placeholder / random 驱动的 runtime skeleton；不包含真实视频水印算法、不包含真实 DiT / Flow Matching 接入、不包含真实视频生成流程。

## Current Scope

- 固定后续阶段推进入口与阻断规则。
- 固定 naming governance 与 placeholder/random field governance。
- 固定 protocol records、threshold calibration、claim audit 与 artifact rebuild 的骨架约束。
- 提供可执行的 harness 审计脚本与 pytest 最小闭环。
- 提供阶段 0 的 placeholder / random runtime skeleton，包括 synthetic latent backend、protocol runner、threshold calibrator、record writer、ablation runner 与 table rebuild scaffold。
- 冻结阶段 0 的 event score record、threshold record、run manifest 与 table output layout schema skeleton。

## Formal Config Entries

- `configs/project/project_contract.json`
- `configs/protocol/protocol_skeleton.json`
- `configs/method/method_placeholder.json`
- `configs/method/empty_watermark_method_placeholder.json`
- `configs/method/random_score_detector_random.json`
- `configs/ablation/ablation_placeholder.json`
- `configs/ablation/protocol_skeleton_methods.json`
- `configs/attacks/identity_attack_placeholder.json`
- `configs/schema/protocol_artifact_schema.json`

## Reference Materials

- `docs/builds/` 保存方法机制与项目构建参考材料。
- `docs/builds/` 不参与 formal governance audit。
- `docs/builds/` 中的历史命名、示例命名或旧阶段草案不代表当前正式命名规范。

## Test Gate

测试入口和审计入口是两个独立门禁；`run_all_audits.py` 通过不能替代 `pytest` 通过。
这些门禁属于外层检查入口，不得成为 `main/` 的运行时依赖；`main/core/`、`main/protocol/` 与 `main/analysis/` 内部只允许保留协议运行时契约。

PowerShell 示例：

```powershell
New-Item -ItemType Directory -Force audit_reports | Out-Null
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest -q -s | Tee-Object audit_reports/pytest_output.txt
```

## Audit Gate

PowerShell 示例：

```powershell
New-Item -ItemType Directory -Force audit_reports | Out-Null
python tools/harness/run_all_audits.py
	| Tee-Object audit_reports/run_all_audits_output.json
```

`tools/harness/`、`.codex/` 与 `tests/` 提供 governance / regression gate；它们可以检查 `main/`，但不得被 `main/` 反向导入。

## Naming Rules

- 文件名、目录名、Python 模块名、配置字段名、JSON 字段名统一使用 `snake_case`。
- `project_stage` 必须使用语义阶段名，例如 `protocol_skeleton`。
- `method_variant` 必须使用机制语义命名。
- 禁止使用 `*_v1`、`*_v2`、`*_p0`、`*_p1` 作为正式文件名、方法名、配置名或产物名。
- 禁止使用 `full`、`default`、`new`、`old`、`best`、`final_method` 作为正式 `method_variant`。

## Placeholder And Random Rules

- 所有占位字段必须以 `_placeholder` 结尾。
- 所有需要后续复现、替换、追踪或清理的随机字段必须以 `_random` 或 `_digest_random` 结尾。
- 所有 `*_random` 字段必须满足 seed 或 digest 追踪条件。
- 所有 `*_placeholder` 字段不得进入 supported claim。

## Stage-0 Artifact Freeze

- 当前阶段只冻结 records、thresholds、manifest 与 tables 的 schema 和相对输出布局。
- 当前阶段实现的是 placeholder / random 驱动的 `RecordWriter`、`ThresholdCalibrator`、`ProtocolRunner` 与 `TableBuilder` scaffold，而不是真实算法或真实模型流程。
- 当前阶段不在仓库中 check in 正式实验产物。

## Stage-0 Support Freeze

- 当前阶段冻结 attack placeholder config、ablation shared-protocol config、claim 边界与 artifact rebuild 约束。
- 当前阶段允许创建 `main/` 下的 stage-0 代码骨架，但仍不得创建 `paper_workflow/` 或 `minimal_release/` 目录。
- 当前阶段只允许为后续阶段声明边界，不允许提前创建 release artifacts。

## Next-Stage Gate

进入 `synthetic_tubelet_sync_probe` 之前，必须同时满足：

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -s` 全部通过，并保留可保存的测试输出。
- `python tools/harness/run_all_audits.py` 全部通过，并保留可保存的审计输出。
- 审计通过不能替代 `pytest` 通过。
- `docs/field_registry.md` 完整登记当前字段。
- `configs/project/project_contract.json` 与 `configs/protocol/protocol_skeleton.json` 通过审计。
- `configs/schema/protocol_artifact_schema.json` 通过审计。
- `configs/attacks/identity_attack_placeholder.json` 与 `configs/ablation/ablation_placeholder.json` 通过审计。

在满足以上门禁之前，不允许进入下一阶段。

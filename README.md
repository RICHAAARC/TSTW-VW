# TSTW-VW

本仓库当前 active formal stage 为 `synthetic_tubelet_sync_probe`。

当前仓库包含 synthetic tubelet sync probe 所需的 governance 层与 synthetic / placeholder 驱动的 runtime scaffold；同时保留受治理的阶段 2 transition-preparation 入口，包括 real-video VAE latent scaffold 模块与 Colab notebook entrypoint。仓库仍不包含真实视频水印算法、不包含真实 DiT / Flow Matching 接入、不包含真实视频生成流程。

## Current Scope

- 固定后续阶段推进入口与阻断规则。
- 固定 naming governance 与 placeholder/random field governance。
- 固定 `docs/test_case_constraints.md` 测试用例构建约束与 pytest 分层默认口径。
- 固定 protocol records、threshold calibration、claim audit 与 artifact rebuild 的骨架约束。
- 提供可执行的 harness 审计脚本与 pytest 最小闭环。
- 提供阶段 0 的 placeholder / random runtime skeleton，包括 synthetic latent backend、protocol runner、threshold calibrator、record writer、ablation runner 与 table rebuild scaffold。
- 冻结阶段 0 的 event score record、threshold record、run manifest 与 table output layout schema skeleton。
- 提供阶段 2 的 real-video VAE latent scaffold、结果检查器、打包器与单一 Colab notebook 入口，用于受治理的 transition-preparation 验证。

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

当前默认 `pytest -q` 只执行 `constraint`、`unit` 或 `quick` 测试，并默认排除 `integration`、`smoke`、`slow` 与 `formal`。测试目录按 `tests/constraints/`、`tests/functional/`、`tests/integration/` 分层，根目录不得新增平铺 `test_*.py`。

PowerShell 示例：

```powershell
New-Item -ItemType Directory -Force audit_reports | Out-Null
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest -q -s | Tee-Object audit_reports/pytest_output.txt
```

## UTF-8 Build Requirement

- 仓库内受治理文本文件、notebook JSON、配置 JSON、Markdown、Python 脚本与审计报告必须使用 `UTF-8`。
- 编辑器保存文件时必须使用 `UTF-8`；仓库提供 `.editorconfig` 与 `.vscode/settings.json` 作为开发工具默认配置。
- Windows PowerShell 与 cmd 启动时应使用 UTF-8 控制台输入输出，并设置 `PYTHONUTF8=1` 与 `PYTHONIOENCODING=utf-8`。
- 所有新增仓库文本读写代码应显式声明 `encoding="utf-8"`，不得依赖本地默认代码页。

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
- `paper_workflow/` 根下受治理的 notebook 同样使用 `snake_case` 机制语义命名，当前固定为 `build_processed_real_video_dataset.ipynb` 与 `run_real_video_vae_latent_probe.ipynb`。
- `paper_workflow/notebook_utils/` 下的单 notebook helper 使用 stage-free `snake_case`；`paper_workflow/colab_utils/` 继续保留共享 helper 的通用 `snake_case`。
- `project_stage` 必须使用语义阶段名，例如 `protocol_skeleton`。
- `method_variant` 必须使用机制语义命名。
- 禁止使用 `*_v1`、`*_v2`、`*_p0`、`*_p1` 作为正式文件名、方法名、配置名或产物名。
- 禁止使用 `full`、`default`、`new`、`old`、`best`、`final_method` 作为正式 `method_variant`。

## Placeholder And Random Rules

- 所有占位字段必须以 `_placeholder` 结尾。
- 所有需要后续复现、替换、追踪或清理的随机字段必须以 `_random` 或 `_digest_random` 结尾。
- 所有 `*_random` 字段必须满足 seed 或 digest 追踪条件。
- 所有 `*_placeholder` 字段不得进入 supported claim。

## Protocol Skeleton Artifact Freeze

- 当前阶段只冻结 records、thresholds、manifest 与 tables 的 schema 和相对输出布局。
- 当前阶段实现的是 placeholder / random 驱动的 `RecordWriter`、`ThresholdCalibrator`、`ProtocolRunner` 与 `TableBuilder` scaffold，而不是真实算法或真实模型流程。
- 当前阶段不在仓库中 check in 正式实验产物。

## Protocol Skeleton Support Freeze

- 当前阶段冻结 attack placeholder config、ablation shared-protocol config、claim 边界与 artifact rebuild 约束。
- 当前阶段允许保留 `paper_workflow/build_processed_real_video_dataset.ipynb` 与 `paper_workflow/run_real_video_vae_latent_probe.ipynb` 作为受治理的 transition-preparation workflow，但仍不得创建额外 notebook 或 `minimal_release/` 目录。
- 当前阶段只允许为后续阶段声明边界，不允许提前创建 release artifacts。

## Next-Stage Gate

进入 `synthetic_tubelet_sync_probe` 之前，必须同时满足：

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q -s` 默认分层测试全部通过，并保留可保存的测试输出。
- `python tools/harness/run_all_audits.py` 全部通过，并保留可保存的审计输出。
- 审计通过不能替代 `pytest` 通过。
- `docs/field_registry.md` 完整登记当前字段。
- `configs/project/project_contract.json` 与 `configs/protocol/protocol_skeleton.json` 通过审计。
- `configs/schema/protocol_artifact_schema.json` 通过审计。
- `configs/attacks/identity_attack_placeholder.json` 与 `configs/ablation/ablation_placeholder.json` 通过审计。

在满足以上门禁之前，不允许进入下一阶段。

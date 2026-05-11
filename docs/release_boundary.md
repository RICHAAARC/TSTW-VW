# Release Boundary

本文档冻结 `protocol_skeleton` 阶段对 future `minimal_release_extraction` 的边界约束，并与 `docs/file_organization.md` 中关于 `release/`、`docs/builds/` 与 governance harness 的边界保持一致。

## Ordered Stages

1. `protocol_skeleton`
2. `synthetic_tubelet_sync_probe`
3. `real_video_vae_latent_probe`
4. `trajectory_statistic_probe`
5. `trajectory_aware_sampling_probe`
6. `full_paper_protocol`
7. `minimal_release_extraction`

## Current-Stage Prohibitions

- 当前阶段不得创建 `minimal_release/` 目录。
- 当前阶段不得创建 `release/` 目录或 release extraction 产物目录。
- 当前阶段不得创建 release manifest 或 release demo artifacts。
- 当前阶段不得把 bootstrap docs 误当作 release assets。

## Future Entry Conditions

- 只有在 governed records、manifests、tables 和 audits 成熟后，才允许进入 `minimal_release_extraction`。
- release extraction 必须保持对 governed configs、records 与 manifests 的可追溯性。

## Core Extraction Boundary

- future `method_core` 只抽取方法接口、evidence、fusion 与方法实现本身。
- future `protocol_core` 只抽取 fixed low-FPR、split、records、thresholds、manifest 与 table rebuild 协议。
- future `minimal_demo` 只能依赖 `method_core` 与 `protocol_core`。
- `tools/harness/`、`.codex/`、`docs/builds/`、`audit_reports/` 与完整实验产物不得进入 `minimal_demo`。
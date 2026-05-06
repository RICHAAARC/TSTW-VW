# Release Boundary

本文档冻结 `protocol_skeleton` 阶段对 future `minimal_release_extraction` 的边界约束。

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
- 当前阶段不得创建 release manifest 或 release demo artifacts。
- 当前阶段不得把 bootstrap docs 误当作 release assets。

## Future Entry Conditions

- 只有在 governed records、manifests、tables 和 audits 成熟后，才允许进入 `minimal_release_extraction`。
- release extraction 必须保持对 governed configs、records 与 manifests 的可追溯性。
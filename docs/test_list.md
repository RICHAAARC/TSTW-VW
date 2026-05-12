# 测试列表

本文档由 `python tools/harness/update_test_list.py` 根据当前 pytest 收集结果重建。

## 1. 当前测试执行口径

- 测试根目录：`tests/`
- 测试构建约束：`docs/test_case_constraints.md`
- 当前 pytest 默认参数来自 `pyproject.toml`：`(constraint or unit or quick) and not integration and not smoke and not slow and not formal`
- 当前全量测试节点：237 个
- 当前默认会执行的测试节点：176 个
- 当前默认排除的测试节点：61 个

## 2. 分层统计

| Layer | Files | Nodes | Default role |
| --- | --- | --- | --- |
| constraints | 26 | 119 | default governance checks |
| functional | 21 | 83 | default quick behavior checks |
| integration | 18 | 35 | excluded runner/smoke/formal checks |

## 3. 推荐执行命令

```bash
python -m pytest -q
python -m pytest -q tests/constraints
python -m pytest -q tests/functional -m "unit or quick"
python -m pytest -q tests/integration -m "smoke" --collect-only
python -m pytest -q -m "formal" --collect-only
python tools/harness/run_all_audits.py
```

## 4. 测试文件清单

| Test file | Nodes | Layer | Markers | Default nodes | I/O | External | Model/data | Summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `tests/constraints/test_core_boundary_layering.py` | 3 | constraints | `constraint`, `unit` | 3 | no | no | no | 验证 main 运行时代码与外层 governance 层之间的边界。 |
| `tests/constraints/test_governance_docs.py` | 15 | constraints | `constraint`, `unit` | 15 | no | no | yes | Validate governed documentation constraints. |
| `tests/constraints/test_naming_conventions.py` | 7 | constraints | `constraint`, `unit` | 7 | yes | no | no | 验证命名治理规则与命名审计行为。File purpose: Validate naming governance helper functions and the naming audit behavior. |
| `tests/constraints/test_notebook_naming_contract.py` | 5 | constraints | `constraint`, `unit` | 5 | yes | no | yes | 验证 notebook 命名与 helper 归属审计行为。 |
| `tests/constraints/test_packager_notebook_contract.py` | 1 | constraints | `constraint`, `unit` | 1 | yes | no | yes | 验证 real video tar.zst packager notebook handoff contract。 |
| `tests/constraints/test_placeholder_random_field_governance.py` | 5 | constraints | `constraint`, `unit` | 5 | no | no | no | 验证 placeholder 与 random 字段治理规则。 |
| `tests/constraints/test_protocol_artifact_schema.py` | 7 | constraints | `constraint`, `unit` | 7 | no | no | no | 验证 stage-one protocol artifact schema 配置。 |
| `tests/constraints/test_protocol_skeleton_contract.py` | 6 | constraints | `constraint`, `unit` | 6 | no | no | no | 验证 protocol_skeleton 项目契约配置。 |
| `tests/constraints/test_protocol_support_configs.py` | 10 | constraints | `constraint`, `unit` | 10 | no | no | no | 验证阶段 0 support config 骨架配置。 |
| `tests/constraints/test_real_video_formal_notebook_gate_strict.py` | 2 | constraints | `constraint`, `unit` | 2 | no | no | yes | 验证阶段 2 Colab notebook formal gate 的严格约束。 |
| `tests/constraints/test_real_video_formal_pass_criteria.py` | 7 | constraints | `constraint`, `formal` | 0 | no | no | yes | 验证 real video VAE latent probe formal mode 下的 PASS 条件。 |
| `tests/constraints/test_real_video_governance_summary.py` | 12 | constraints | `constraint`, `formal` | 0 | no | no | yes | 验证 governance summary 中的 18 个 PASS 条件。 |
| `tests/constraints/test_real_video_lpips_metric_formal_required.py` | 7 | constraints | `constraint`, `formal` | 0 | no | no | yes | 验证 LPIPS 在 formal 模式下的必需性与行为。 |
| `tests/constraints/test_real_video_vae_latent_ablation_consistency.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | yes | 验证阶段 2 scaffold 消融配置共享同一协议语义。File purpose: Validate that the stage-two scaffold ablation config shares one protocol contract. |
| `tests/constraints/test_real_video_vae_latent_backend_no_synthetic_dependency_formal.py` | 2 | constraints | `constraint`, `unit` | 2 | no | no | yes | 验证阶段 2 formal backend 不依赖 synthetic backend。 |
| `tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py` | 3 | constraints | `constraint`, `unit` | 3 | yes | no | yes | 验证真实视频 workflow notebook 入口遵循受治理合同。 |
| `tests/constraints/test_real_video_vae_latent_no_flow_matching_dependency.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | yes | 验证阶段 2 scaffold 不依赖 Flow Matching、DiT hook 或 trajectory 实现。File purpose: Validate that the stage-two scaffold does not depend on Flow Matching, DiT hooks, or trajectory implementations. |
| `tests/constraints/test_records_schema.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | no | 验证 active formal stage 的 records schema 约束。 |
| `tests/constraints/test_repository_intake.py` | 2 | constraints | `constraint`, `unit` | 2 | yes | no | yes | 验证仓库 intake 检查与当前 formal stage 的目录边界。 |
| `tests/constraints/test_run_all_audits.py` | 4 | constraints | `constraint`, `unit` | 4 | yes | no | no | 验证全部 harness 审计可执行并输出治理摘要。 |
| `tests/constraints/test_runtime_check.py` | 2 | constraints | `constraint`, `unit` | 2 | yes | yes | yes | 验证 Colab runtime 预检的版本、导入与 formal 阻断行为。 |
| `tests/constraints/test_semantic_naming_governance.py` | 4 | constraints | `constraint`, `unit` | 4 | no | no | yes | Validate semantic naming governance rules. |
| `tests/constraints/test_stage_boundaries.py` | 3 | constraints | `constraint`, `unit` | 3 | no | no | no | 验证阶段顺序与 release boundary 未越界。 |
| `tests/constraints/test_synthetic_tubelet_sync_contract.py` | 4 | constraints | `constraint`, `unit` | 4 | no | no | no | 验证阶段 1 synthetic tubelet sync 入口 method config 契约。 |
| `tests/constraints/test_synthetic_tubelet_sync_no_dit_dependency.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | yes | 验证 stage-one runtime 不依赖真实视频生成模型栈。File purpose: Validate that the stage-one runtime has no real video model dependency. |
| `tests/constraints/test_threshold_protocol_fields.py` | 4 | constraints | `constraint`, `unit` | 4 | no | no | no | 验证 fixed low-FPR 阈值协议字段。File purpose: Validate threshold protocol governance for the protocol_skeleton stage. |
| `tests/functional/test_diffusers_autoencoder_kl_framewise_backend.py` | 2 | functional | `quick`, `unit` | 2 | yes | no | yes | 验证 framewise AutoencoderKL backend 的基础编解码行为。 |
| `tests/functional/test_packager.py` | 4 | functional | `quick` | 4 | yes | yes | yes | 验证 tar.zst 打包器的轻量功能契约。 |
| `tests/functional/test_projection_margin_embedding.py` | 2 | functional | `quick` | 2 | yes | no | no | 验证 stage-one projection-margin embedding 的最小语义。 |
| `tests/functional/test_protocol_runner_dependency_injection.py` | 5 | functional | `quick` | 5 | no | no | no | 验证 ProtocolRunner 的依赖注入与方法家族解耦行为。File purpose: Validate ProtocolRunner dependency injection and method-family decoupling. |
| `tests/functional/test_real_vae_backend_registry.py` | 5 | functional | `quick`, `unit` | 5 | yes | no | yes | 验证阶段 2 VAE registry 的 backend 解析行为。 |
| `tests/functional/test_real_video_dataset_localization.py` | 2 | functional | `quick`, `unit` | 2 | yes | no | yes | 验证阶段 2 本地数据集定位与 manifest 解析。 |
| `tests/functional/test_real_video_mp4_io.py` | 3 | functional | `quick`, `unit` | 3 | yes | yes | yes | 验证真实 mp4 读写与帧标准化工具。 |
| `tests/functional/test_real_video_vae_latent_backend_uses_mp4_manifest.py` | 1 | functional | `quick`, `unit` | 1 | yes | yes | yes | 验证阶段 2 backend 会使用 manifest 中的 mp4 样本构建 source artifact。 |
| `tests/functional/test_real_video_vae_latent_quality_metrics.py` | 1 | functional | `quick` | 1 | yes | no | yes | 验证阶段 2 scaffold 质量指标负载。File purpose: Validate quality-metrics payloads for the stage-two scaffold. |
| `tests/functional/test_real_video_vae_latent_temporal_metrics.py` | 1 | functional | `quick` | 1 | yes | no | yes | 验证阶段 2 scaffold 时序指标负载。File purpose: Validate temporal-metrics payloads for the stage-two scaffold. |
| `tests/functional/test_sync_alignment.py` | 4 | functional | `quick` | 4 | yes | no | no | 验证 stage-one offset search synchronization 的最小语义。 |
| `tests/functional/test_sync_rescue_fusion.py` | 5 | functional | `quick`, `unit` | 5 | yes | no | no | Validate sync-rescue fusion semantics for the synthetic tubelet probe. |
| `tests/functional/test_synthetic_video_latent_reproducibility.py` | 2 | functional | `quick` | 2 | yes | no | no | 验证 synthetic video latent tensor artifact backend 的可复现性。 |
| `tests/functional/test_synthetic_video_latent_runtime.py` | 3 | functional | `quick` | 3 | no | no | no | 验证 synthetic video latent tensor artifact runtime 的最小运行语义。 |
| `tests/functional/test_temporal_attack_runtime.py` | 3 | functional | `quick` | 3 | yes | no | no | 验证 temporal attack placeholder runtime 的最小运行语义。 |
| `tests/functional/test_tubelet_partition.py` | 5 | functional | `quick` | 5 | no | no | no | 验证 stage-one tubelet partition 的边界与 digest 语义。 |
| `tests/functional/test_video_artifact_digest.py` | 1 | functional | `quick` | 1 | yes | no | yes | 验证阶段 2 视频 artifact digest 行为。 |
| `tests/functional/test_video_attack_registry.py` | 10 | functional | `quick` | 10 | no | no | no | 验证真实视频攻击 registry 支持两种运行时模式。 |
| `tests/functional/test_video_compression_attack.py` | 6 | functional | `quick` | 6 | yes | yes | yes | 验证真实视频压缩攻击功能。 |
| `tests/functional/test_video_spatial_attacks.py` | 10 | functional | `quick` | 10 | no | no | no | 验证真实视频空间攻击功能。 |
| `tests/functional/test_video_temporal_attacks.py` | 8 | functional | `quick` | 8 | no | no | no | 验证真实视频噪声攻击功能。 |
| `tests/integration/test_ablation_consistency.py` | 1 | integration | `integration`, `smoke` | 0 | yes | no | no | 验证 active formal stage 的方法变体共享同一 protocol 口径。 |
| `tests/integration/test_processed_dataset_builder_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 验证 processed real-video dataset builder 的最小行为。 |
| `tests/integration/test_protocol_no_threshold_leakage.py` | 2 | integration | `integration`, `smoke` | 0 | yes | no | no | 验证阶段 0 threshold calibration 不发生 test leakage。 |
| `tests/integration/test_real_video_attack_matrix.py` | 1 | integration | `integration` | 0 | yes | no | yes | 验证阶段 2 attack matrix 可实例化并运行。 |
| `tests/integration/test_real_video_drive_packager_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | no | yes | 验证阶段 2 scaffold 打包器生成 zip 与摘要文件。 |
| `tests/integration/test_real_video_formal_blocks_placeholder_runtime.py` | 1 | integration | `formal`, `integration` | 0 | yes | no | yes | 验证 formal 模式会阻断 placeholder runtime。 |
| `tests/integration/test_real_video_formal_rejects_placeholder_vae.py` | 1 | integration | `formal`, `integration` | 0 | yes | no | yes | 验证 formal 模式拒绝 placeholder VAE backend。 |
| `tests/integration/test_real_video_packager_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 验证 real video tar.zst 打包器的 smoke 归档路径。 |
| `tests/integration/test_real_video_quality_metrics_smoke.py` | 6 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 测试阶段 2 真实视频帧级质量指标。 |
| `tests/integration/test_real_video_records_schema_smoke.py` | 2 | integration | `integration`, `smoke` | 0 | yes | no | yes | 验证阶段 2 scaffold event records 的扩展字段与产物布局。 |
| `tests/integration/test_real_video_table_rebuild_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | no | yes | 验证阶段 2 scaffold 表格与报告可从 records 重建。 |
| `tests/integration/test_real_video_temporal_metrics_smoke.py` | 6 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 测试阶段 2 真实视频帧级时序指标。 |
| `tests/integration/test_real_video_vae_encode_decode_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 验证阶段 2 VAE encode/decode 元数据与 digest 稳定性。File purpose: Validate metadata and digest stability for the stage-two VAE path. |
| `tests/integration/test_real_video_vae_latent_backend_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 验证阶段 2 backend 的 source video 与 encoded latent artifact 行为。 |
| `tests/integration/test_records_schema_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | no | no | 验证 active formal stage 的 runtime records smoke schema。 |
| `tests/integration/test_synthetic_tubelet_records_schema_smoke.py` | 2 | integration | `integration`, `smoke` | 0 | yes | no | no | 验证 stage-one event record 中的 mechanism_trace 与正式机制字段语义。 |
| `tests/integration/test_synthetic_tubelet_table_rebuild_smoke.py` | 5 | integration | `integration`, `slow`, `smoke` | 0 | yes | no | no | 验证 stage-one 表格、曲线与报告可由 records 重建。 |
| `tests/integration/test_table_rebuild_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | no | no | 验证阶段 0 tables 可由 records 重建。 |

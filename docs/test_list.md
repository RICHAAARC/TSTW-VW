# 测试列表

本文档由 `python tools/harness/update_test_list.py` 根据当前 pytest 收集结果重建。

## 1. 当前测试执行口径

- 测试根目录：`tests/`
- 测试构建约束：`docs/test_case_constraints.md`
- 当前 pytest 默认参数来自 `pyproject.toml`：`(constraint or unit or quick) and not integration and not smoke and not slow and not formal`
- 当前全量测试节点：448 个
- 当前默认会执行的测试节点：378 个
- 当前默认排除的测试节点：70 个

## 2. 分层统计

| Layer | Files | Nodes | Default role |
| --- | --- | --- | --- |
| constraints | 36 | 159 | default governance checks |
| functional | 47 | 247 | default quick behavior checks |
| integration | 23 | 42 | excluded runner/smoke/formal checks |

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
| `tests/constraints/test_family_id_materialization_contract.py` | 2 | constraints | `constraint`, `unit` | 2 | no | no | yes | 验证 family_id 模板占位符会被物化为真实 UTC 时间与 short commit。 |
| `tests/constraints/test_family_package_metadata_contract.py` | 1 | constraints | `constraint`, `unit` | 1 | yes | no | yes | 验证 family package metadata 与实际 canonical archive 一致。 |
| `tests/constraints/test_governance_docs.py` | 18 | constraints | `constraint`, `unit` | 18 | no | no | yes | Validate governed documentation constraints. |
| `tests/constraints/test_mechanism_decision_contract.py` | 6 | constraints | `constraint`, `unit` | 6 | no | no | yes | 验证 Stage2MechanismDecision 的门禁语义与字段完整性。 |
| `tests/constraints/test_naming_conventions.py` | 7 | constraints | `constraint`, `unit` | 7 | yes | no | no | 验证命名治理规则与命名审计行为。File purpose: Validate naming governance helper functions and the naming audit behavior. |
| `tests/constraints/test_notebook_naming_contract.py` | 5 | constraints | `constraint`, `unit` | 5 | yes | no | yes | 验证 notebook 命名与 helper 归属审计行为。 |
| `tests/constraints/test_packager_notebook_contract.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | yes | 验证 real video tar.zst packager notebook handoff contract。 |
| `tests/constraints/test_placeholder_random_field_governance.py` | 5 | constraints | `constraint`, `unit` | 5 | no | no | no | 验证 placeholder 与 random 字段治理规则。 |
| `tests/constraints/test_protocol_artifact_schema.py` | 7 | constraints | `constraint`, `unit` | 7 | no | no | no | 验证 stage-one protocol artifact schema 配置。 |
| `tests/constraints/test_protocol_skeleton_contract.py` | 6 | constraints | `constraint`, `unit` | 6 | no | no | no | 验证 protocol_skeleton 项目契约配置。 |
| `tests/constraints/test_protocol_support_configs.py` | 10 | constraints | `constraint`, `unit` | 10 | no | no | no | 验证阶段 0 support config 骨架配置。 |
| `tests/constraints/test_real_video_formal_notebook_gate_strict.py` | 2 | constraints | `constraint`, `unit` | 2 | no | no | yes | 验证阶段 2 Colab notebook formal gate 的严格约束。 |
| `tests/constraints/test_real_video_formal_pass_criteria.py` | 7 | constraints | `constraint`, `formal` | 0 | no | no | yes | 验证 real video VAE latent probe formal mode 下的 PASS 条件。 |
| `tests/constraints/test_real_video_governance_summary.py` | 14 | constraints | `constraint`, `formal` | 0 | no | no | yes | 验证 governance summary 中的 18 个 PASS 条件。 |
| `tests/constraints/test_real_video_lpips_metric_formal_required.py` | 7 | constraints | `constraint`, `formal` | 0 | no | no | yes | 验证 LPIPS 在 formal 模式下的必需性与行为。 |
| `tests/constraints/test_real_video_probe_no_trajectory_regression.py` | 2 | constraints | `constraint`, `unit` | 2 | no | no | yes | 验证 real_video_vae_latent_probe 默认路径未被 trajectory scaffold 污染。 |
| `tests/constraints/test_real_video_quality_metric_flags.py` | 5 | constraints | `constraint`, `unit` | 5 | yes | no | yes | 验证真实视频质量指标的 governed flags 与 failure reason 行为。 |
| `tests/constraints/test_real_video_vae_latent_ablation_consistency.py` | 2 | constraints | `constraint`, `unit` | 2 | no | no | yes | 验证阶段 2 scaffold 消融配置共享同一协议语义。File purpose: Validate that the stage-two scaffold ablation config shares one protocol contract. |
| `tests/constraints/test_real_video_vae_latent_backend_no_synthetic_dependency_formal.py` | 2 | constraints | `constraint`, `unit` | 2 | no | no | yes | 验证阶段 2 formal backend 不依赖 synthetic backend。 |
| `tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py` | 4 | constraints | `constraint`, `unit` | 4 | yes | no | yes | 验证真实视频 workflow notebook 入口遵循受治理合同。 |
| `tests/constraints/test_real_video_vae_latent_no_flow_matching_dependency.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | yes | 验证阶段 2 scaffold 不依赖 Flow Matching、DiT hook 或 trajectory 实现。File purpose: Validate that the stage-two scaffold does not depend on Flow Matching, DiT hooks, or trajectory implementations. |
| `tests/constraints/test_records_schema.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | no | 验证 active formal stage 的 records schema 约束。 |
| `tests/constraints/test_repository_intake.py` | 2 | constraints | `constraint`, `unit` | 2 | yes | no | no | 验证仓库 intake 检查与当前 formal stage 的目录边界。 |
| `tests/constraints/test_run_all_audits.py` | 5 | constraints | `constraint`, `unit` | 5 | yes | no | no | 验证全部 harness 审计可执行并输出治理摘要。 |
| `tests/constraints/test_runtime_check.py` | 2 | constraints | `constraint`, `unit` | 2 | yes | yes | yes | 验证 Colab runtime 预检的版本、导入与 formal 阻断行为。 |
| `tests/constraints/test_runtime_profile_boundaries.py` | 5 | constraints | `constraint`, `unit` | 5 | no | no | yes | 验证 runtime_profile 治理边界、配置目录与 release 可移除性约束。 |
| `tests/constraints/test_runtime_profile_file_organization.py` | 5 | constraints | `constraint`, `unit` | 5 | no | no | yes | 验证 runtime profiling 脚本与 notebook helper 的文件组织合同。 |
| `tests/constraints/test_semantic_naming_governance.py` | 4 | constraints | `constraint`, `unit` | 4 | no | no | yes | Validate semantic naming governance rules. |
| `tests/constraints/test_stage_boundaries.py` | 3 | constraints | `constraint`, `unit` | 3 | no | no | no | 验证阶段顺序与 release boundary 未越界。 |
| `tests/constraints/test_synthetic_tubelet_sync_contract.py` | 4 | constraints | `constraint`, `unit` | 4 | no | no | no | 验证阶段 1 synthetic tubelet sync 入口 method config 契约。 |
| `tests/constraints/test_synthetic_tubelet_sync_no_dit_dependency.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | yes | 验证 stage-one runtime 不依赖真实视频生成模型栈。File purpose: Validate that the stage-one runtime has no real video model dependency. |
| `tests/constraints/test_threshold_protocol_fields.py` | 4 | constraints | `constraint`, `unit` | 4 | no | no | no | 验证 fixed low-FPR 阈值协议字段。File purpose: Validate threshold protocol governance for the protocol_skeleton stage. |
| `tests/constraints/test_trajectory_aware_sampling_contract.py` | 4 | constraints | `constraint`, `unit` | 4 | no | no | no | 验证 trajectory-aware sampling probe 的配置与边界契约。 |
| `tests/constraints/test_trajectory_aware_sampling_probe_notebook_contract.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | no | 文件用途: 验证 trajectory-aware sampling probe notebook 入口遵守受治理合同。 |
| `tests/constraints/test_trajectory_statistic_probe_notebook_contract.py` | 1 | constraints | `constraint`, `unit` | 1 | no | no | yes | 验证阶段 3 trajectory statistic probe notebook 入口遵循受治理合同。 |
| `tests/functional/test_cross_event_vae_batching_config.py` | 5 | functional | `quick`, `unit` | 5 | no | no | yes | 验证 cross-event VAE batching 配置解析与批处理工具。 |
| `tests/functional/test_diffusers_autoencoder_kl_framewise_backend.py` | 4 | functional | `quick`, `unit` | 4 | yes | no | yes | 验证 framewise AutoencoderKL backend 的基础编解码行为。 |
| `tests/functional/test_gpu_runtime_profiler.py` | 10 | functional | `quick` | 10 | yes | yes | yes | 验证 GPU runtime profiler 在无 GPU 与 stop-file 场景下的行为。 |
| `tests/functional/test_mechanism_audit.py` | 2 | functional | `quick` | 2 | yes | no | yes | 验证阶段 2 mechanism audit 能重建表格与决策文件。 |
| `tests/functional/test_mechanism_calibration_runner.py` | 7 | functional | `quick`, `unit` | 7 | yes | no | yes | 验证 real_video_vae_latent_probe mechanism calibration runner 的 orchestration 行为。 |
| `tests/functional/test_mechanism_candidate_selection.py` | 16 | functional | `quick` | 16 | yes | no | yes | 验证 real_video_vae_latent_probe mechanism calibration candidate selector 的 quick 行为。 |
| `tests/functional/test_packager.py` | 10 | functional | `quick` | 10 | yes | yes | yes | 验证 real-video zip / tar.zst 打包器的轻量功能契约。 |
| `tests/functional/test_projection_margin_embedding.py` | 3 | functional | `quick` | 3 | yes | no | no | 验证 stage-one projection-margin embedding 的最小语义。 |
| `tests/functional/test_protocol_runner_dependency_injection.py` | 6 | functional | `quick` | 6 | no | no | no | 验证 ProtocolRunner 的依赖注入与方法家族解耦行为。File purpose: Validate ProtocolRunner dependency injection and method-family decoupling. |
| `tests/functional/test_real_vae_backend_registry.py` | 5 | functional | `quick`, `unit` | 5 | yes | no | yes | 验证阶段 2 VAE registry 的 backend 解析行为。 |
| `tests/functional/test_real_video_dataset_localization.py` | 3 | functional | `quick`, `unit` | 3 | yes | no | yes | 验证阶段 2 本地数据集定位与 manifest 解析。 |
| `tests/functional/test_real_video_formal_backend_fallback_guard.py` | 1 | functional | `quick`, `unit` | 1 | yes | no | yes | 验证 formal 阶段 2 backend 禁止回退为 synthetic fallback video。 |
| `tests/functional/test_real_video_mp4_io.py` | 3 | functional | `quick`, `unit` | 3 | yes | yes | yes | 验证真实 mp4 读写与帧标准化工具。 |
| `tests/functional/test_real_video_probe_runner_profiles.py` | 32 | functional | `quick`, `unit` | 32 | yes | no | yes | 验证 real-video debug profile 的受治理配置解析。 |
| `tests/functional/test_real_video_probe_workflow.py` | 22 | functional | `quick`, `unit` | 22 | yes | yes | yes | 验证阶段 2 notebook workflow helper 的 manifest handoff 与 session model 语义。 |
| `tests/functional/test_real_video_vae_latent_backend_uses_mp4_manifest.py` | 4 | functional | `quick`, `unit` | 4 | yes | yes | yes | 验证阶段 2 backend 会使用 manifest 中的 mp4 样本构建 source artifact。 |
| `tests/functional/test_real_video_vae_latent_progress_watcher.py` | 2 | functional | `quick` | 2 | yes | no | yes | 验证 real-video VAE latent progress watcher 的统计与 stall 检测合同。 |
| `tests/functional/test_real_video_vae_latent_quality_metrics.py` | 1 | functional | `quick` | 1 | yes | no | yes | 验证阶段 2 scaffold 质量指标负载。File purpose: Validate quality-metrics payloads for the stage-two scaffold. |
| `tests/functional/test_real_video_vae_latent_run_scale_estimator.py` | 3 | functional | `quick` | 3 | yes | yes | yes | 验证 real-video VAE latent run scale estimator 的输出合同。 |
| `tests/functional/test_real_video_vae_latent_temporal_metrics.py` | 2 | functional | `quick` | 2 | yes | no | yes | 验证阶段 2 scaffold 时序指标负载。File purpose: Validate temporal-metrics payloads for the stage-two scaffold. |
| `tests/functional/test_run_failure_summary.py` | 1 | functional | `quick` | 1 | yes | no | yes | 验证运行失败摘要脚本对 records、checker 与 timing 失败的汇总行为。 |
| `tests/functional/test_run_timing_profiler.py` | 1 | functional | `quick` | 1 | yes | no | yes | 验证运行时间记录器与 timing 汇总脚本的功能合同。 |
| `tests/functional/test_runtime_environment_snapshot.py` | 1 | functional | `quick` | 1 | yes | yes | no | 验证 runtime environment snapshot 脚本在无 GPU 环境下的输出合同。 |
| `tests/functional/test_runtime_parameter_recommendation.py` | 3 | functional | `quick` | 3 | yes | no | yes | 验证 profiling 汇总到运行参数建议的映射合同。 |
| `tests/functional/test_runtime_profile_packaging.py` | 1 | functional | `quick`, `unit` | 1 | yes | no | yes | 验证结果打包器会纳入 runtime_profile 目录。 |
| `tests/functional/test_runtime_profile_recommendation.py` | 5 | functional | `quick`, `unit` | 5 | yes | no | yes | 验证受治理 runtime profile recommendation 的具体 profile 与 batch 建议。 |
| `tests/functional/test_sync_alignment.py` | 7 | functional | `quick`, `unit` | 7 | yes | no | no | 验证 stage-one offset search synchronization 的最小语义。 |
| `tests/functional/test_sync_rescue_fusion.py` | 12 | functional | `quick`, `unit` | 12 | yes | no | no | Validate sync-rescue fusion semantics for the synthetic tubelet probe. |
| `tests/functional/test_synthetic_video_latent_reproducibility.py` | 2 | functional | `quick` | 2 | yes | no | no | 验证 synthetic video latent tensor artifact backend 的可复现性。 |
| `tests/functional/test_synthetic_video_latent_runtime.py` | 3 | functional | `quick` | 3 | no | no | no | 验证 synthetic video latent tensor artifact runtime 的最小运行语义。 |
| `tests/functional/test_temporal_attack_runtime.py` | 3 | functional | `quick` | 3 | yes | no | no | 验证 temporal attack placeholder runtime 的最小运行语义。 |
| `tests/functional/test_trajectory_artifact_report.py` | 1 | functional | `quick` | 1 | no | no | no | 验证 trajectory statistic probe 报告读取正式机制决策产物。 |
| `tests/functional/test_trajectory_aware_sampling_artifact_builder.py` | 1 | functional | `quick` | 1 | yes | no | no | 文件用途: 验证 trajectory-aware sampling scaffold 产物写出路径。 |
| `tests/functional/test_trajectory_aware_sampling_backend_transition_guard.py` | 3 | functional | `quick` | 3 | no | no | no | 文件用途: 验证 trajectory-aware sampling 后端切换前治理守卫。 |
| `tests/functional/test_trajectory_aware_sampling_gpu_validation_contract.py` | 3 | functional | `quick` | 3 | no | no | no | 文件用途: 验证 trajectory-aware sampling 后续真实 GPU runtime 合同。 |
| `tests/functional/test_trajectory_aware_sampling_readiness.py` | 4 | functional | `quick` | 4 | no | no | no | 验证 trajectory-aware sampling probe 的 readiness gate 语义。 |
| `tests/functional/test_trajectory_aware_sampling_runner.py` | 2 | functional | `quick` | 2 | yes | no | no | 文件用途: 验证 trajectory-aware sampling runner 和 CLI 的 CPU scaffold 闭环。 |
| `tests/functional/test_trajectory_aware_sampling_selection_plan.py` | 4 | functional | `quick` | 4 | no | no | no | 文件用途: 验证 trajectory-aware sampling 的记录摘要选择计划。 |
| `tests/functional/test_trajectory_mechanism_audit.py` | 5 | functional | `quick` | 5 | no | no | no | 验证阶段 3 trajectory mechanism audit 的基本决策语义。 |
| `tests/functional/test_trajectory_source_access_guard.py` | 2 | functional | `quick`, `unit` | 2 | yes | no | no | 验证 trajectory source 不允许读取 positive-only artifact。 |
| `tests/functional/test_trajectory_statistic.py` | 2 | functional | `quick` | 2 | no | no | no | 验证阶段 3 trajectory 统计核心的快速功能语义。 |
| `tests/functional/test_tubelet_partition.py` | 5 | functional | `quick` | 5 | no | no | no | 验证 stage-one tubelet partition 的边界与 digest 语义。 |
| `tests/functional/test_video_artifact_digest.py` | 1 | functional | `quick` | 1 | yes | no | yes | 验证阶段 2 视频 artifact digest 行为。 |
| `tests/functional/test_video_attack_registry.py` | 10 | functional | `quick` | 10 | no | no | no | 验证真实视频攻击 registry 支持两种运行时模式。 |
| `tests/functional/test_video_compression_attack.py` | 6 | functional | `quick` | 6 | yes | yes | yes | 验证真实视频压缩攻击功能。 |
| `tests/functional/test_video_spatial_attacks.py` | 10 | functional | `quick` | 10 | no | no | no | 验证真实视频空间攻击功能。 |
| `tests/functional/test_video_temporal_attacks.py` | 8 | functional | `quick` | 8 | no | no | no | 验证真实视频噪声攻击功能。 |
| `tests/integration/test_ablation_consistency.py` | 1 | integration | `integration`, `smoke` | 0 | yes | no | no | 验证 active formal stage 的方法变体共享同一 protocol 口径。 |
| `tests/integration/test_cross_event_vae_batching_artifact_contract.py` | 1 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 验证 cross-event VAE batching 不破坏阶段 2 artifact 输出合同。 |
| `tests/integration/test_cross_event_vae_batching_equivalence.py` | 1 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 验证 cross-event VAE batching 与 sequential runner 的关键输出等价。 |
| `tests/integration/test_cross_event_vae_batching_fallback.py` | 1 | integration | `integration`, `smoke` | 0 | yes | yes | yes | 验证 cross-event VAE batching 在 CUDA OOM 时可回退到单 event 调度。 |
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
| `tests/integration/test_trajectory_formal_replay_smoke.py` | 3 | integration | `integration`, `smoke` | 0 | yes | no | yes | 验证 trajectory statistic probe 的冻结 baseline 与 replay 闭环。 |
| `tests/integration/test_trajectory_records_schema_smoke.py` | 1 | integration | `integration`, `smoke` | 0 | yes | no | no | 验证阶段 3 trajectory statistic probe 的 smoke records schema。 |

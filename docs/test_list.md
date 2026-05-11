# 测试列表

## 1. 当前测试执行口径

- 测试根目录：`tests/`
- 当前 pytest 默认参数来自 [pyproject.toml](../pyproject.toml)
  - `-m not slow and not formal and not smoke`
- 当前全量测试节点（`python -m pytest --collect-only -q`）：226 个
- 当前默认会执行的测试节点：136 个
- 当前默认排除的测试节点：90 个

本文档按“测试文件”维度列出当前全量测试清单，并对每个文件说明：

- 主要测试内容
- 属于功能测试还是约束测试
- 是否在默认 `pytest -q` 口径中执行

分类规则如下：

- 功能测试：验证方法、runtime、I/O、attack、metrics、packager、rebuild、backend 行为是否正确。
- 约束测试：验证 contract、schema、boundary、naming、governance、dependency gate、formal gate、audit 或 intake 口径是否正确。

默认执行状态说明：

- 默认执行：未被 `slow` / `formal` / `smoke` marker 排除。
- 混合：同一文件中既有默认执行节点，也有默认排除节点。
- 默认排除：当前文件内测试节点全部由 `slow` / `formal` / `smoke` marker 排除。

## 2. 默认执行测试文件

| 测试文件 | 节点数 | 类型 | 主要测试内容 |
| --- | ---: | --- | --- |
| `tests/test_core_boundary_layering.py` | 3 | 约束测试 | 验证 `main/` 不反向依赖外层 governance 层，也不硬编码外层目录根。 |
| `tests/test_diffusers_autoencoder_kl_framewise_backend.py` | 2 | 功能测试 | 验证 framewise `AutoencoderKL` backend 的元数据、shape 和 formal 模式模型路径要求。 |
| `tests/test_formal_rejects_placeholder_vae.py` | 1 | 约束测试 | 验证 formal runtime 会拒绝 placeholder VAE backend。 |
| `tests/test_governance_docs.py` | 11 | 约束测试 | 验证治理文档、file organization、UTF-8 约束、release boundary 与 skill 文案是否齐全一致。 |
| `tests/test_naming_conventions.py` | 7 | 约束测试 | 验证命名治理规则、弱命名阻断、YAML 配置拒绝与 stale reference 检测。 |
| `tests/test_placeholder_random_field_governance.py` | 5 | 约束测试 | 验证 placeholder / random 字段后缀、痕迹字段与注册治理规则。 |
| `tests/test_projection_margin_embedding.py` | 2 | 功能测试 | 验证 stage-one projection-margin embedding 的基本语义。 |
| `tests/test_protocol_artifact_schema.py` | 7 | 约束测试 | 验证 protocol artifact schema、trace 字段和输出布局契约。 |
| `tests/test_protocol_runner_dependency_injection.py` | 4 | 功能测试 | 验证 `ProtocolRunner` 的依赖注入、fake backend / fake method family 支持与解耦行为。 |
| `tests/test_protocol_skeleton_contract.py` | 6 | 约束测试 | 验证 `protocol_skeleton` 的项目契约配置与必需字段。 |
| `tests/test_protocol_support_configs.py` | 10 | 约束测试 | 验证 stage-zero / stage-one support config 的结构与字段约束。 |
| `tests/test_real_vae_backend_registry.py` | 4 | 功能测试 | 验证 stage-two VAE registry 的 backend 解析与 runtime config 映射。 |
| `tests/test_real_video_attack_matrix.py` | 1 | 功能测试 | 验证 stage-two attack matrix 可以完整实例化并运行。 |
| `tests/test_real_video_dataset_localization.py` | 2 | 功能测试 | 验证本地数据集根目录、manifest 路径解析与 formal 模式缺文件失败行为。 |
| `tests/test_real_video_formal_blocks_placeholder_runtime.py` | 1 | 约束测试 | 验证 stage-two formal 检查会阻断 placeholder runtime。 |
| `tests/test_real_video_formal_notebook_gate_strict.py` | 2 | 约束测试 | 验证 stage-two notebook formal gate 严格禁止直接写 formal outputs。 |
| `tests/test_real_video_mp4_io.py` | 3 | 功能测试 | 验证真实 mp4 写入、读取、metadata probe 与帧标准化行为。 |
| `tests/test_real_video_vae_latent_ablation_consistency.py` | 1 | 约束测试 | 验证 stage-two scaffold ablation config 复用共享协议语义。 |
| `tests/test_real_video_vae_latent_backend_no_synthetic_dependency_formal.py` | 2 | 约束测试 | 验证 stage-two formal backend 源码不依赖 synthetic backend。 |
| `tests/test_real_video_vae_latent_backend_uses_mp4_manifest.py` | 1 | 功能测试 | 验证 stage-two backend 通过 manifest 中的 mp4 样本构建 source artifact。 |
| `tests/test_real_video_vae_latent_colab_notebook_contract.py` | 2 | 约束测试 | 验证 stage-two Colab notebook 入口遵循受治理入口与 metadata 规范。 |
| `tests/test_real_video_vae_latent_no_flow_matching_dependency.py` | 1 | 约束测试 | 验证 stage-two scaffold 不依赖 Flow Matching、DiT hook 或 trajectory 实现。 |
| `tests/test_real_video_vae_latent_quality_metrics.py` | 1 | 功能测试 | 验证 stage-two scaffold 能 materialize 质量指标负载。 |
| `tests/test_real_video_vae_latent_temporal_metrics.py` | 1 | 功能测试 | 验证 stage-two scaffold 能 materialize 时序指标负载。 |
| `tests/test_repository_intake.py` | 2 | 约束测试 | 验证 repository intake、directory boundary source-of-truth 与当前 stage 状态报告。 |
| `tests/test_run_all_audits.py` | 4 | 约束测试 | 验证 `run_all_audits.py` 的审计清单以及 UTF-8 audit 的最小通过 / 失败行为。 |
| `tests/test_runtime_check.py` | 2 | 约束测试 | 验证 Colab runtime preflight 报告与 formal 模式缺失 LPIPS 阻断。 |
| `tests/test_semantic_naming_governance.py` | 4 | 约束测试 | 验证语义命名规则、弱 stage 名阻断与兼容版本名例外。 |
| `tests/test_stage_boundaries.py` | 3 | 约束测试 | 验证阶段顺序、release boundary 和 active formal phase 没有越界。 |
| `tests/test_sync_alignment.py` | 4 | 功能测试 | 验证 stage-one synchronization offset search 的最小行为语义。 |
| `tests/test_sync_rescue_fusion.py` | 5 | 功能测试 | 验证 sync-rescue fusion 的 payload rescue gain 和对齐语义。 |
| `tests/test_synthetic_tubelet_sync_contract.py` | 4 | 约束测试 | 验证 stage-one method config / method matrix 契约。 |
| `tests/test_synthetic_tubelet_sync_no_dit_dependency.py` | 1 | 约束测试 | 验证 stage-one runtime 不依赖真实视频生成模型栈。 |
| `tests/test_synthetic_video_latent_reproducibility.py` | 2 | 功能测试 | 验证 synthetic video latent backend 产物可复现且按样本身份隔离。 |
| `tests/test_synthetic_video_latent_runtime.py` | 3 | 功能测试 | 验证 synthetic video latent runtime 的最小构建语义与 proof profile 支持。 |
| `tests/test_temporal_attack_runtime.py` | 3 | 功能测试 | 验证 temporal attack placeholder runtime 的最小运行语义与 artifact 复用。 |
| `tests/test_threshold_protocol_fields.py` | 4 | 约束测试 | 验证 fixed low-FPR 阈值协议字段与 calibration / test 边界。 |
| `tests/test_tubelet_partition.py` | 5 | 功能测试 | 验证 tubelet partition 的边界、digest 和 payload size 语义。 |
| `tests/test_vae_encode_decode_reproducibility.py` | 1 | 功能测试 | 验证 stage-two VAE encode/decode 元数据与 digest 稳定性。 |
| `tests/test_video_artifact_digest.py` | 1 | 功能测试 | 验证 stage-two 视频 artifact digest 稳定且保持相对路径语义。 |

## 3. 混合执行测试文件

| 测试文件 | 节点数 | 类型 | 默认执行情况 | 主要测试内容 |
| --- | ---: | --- | --- | --- |
| `tests/test_real_video_ffmpeg_compression_attack.py` | 7 | 功能测试 | 1 个节点默认执行，6 个 `smoke` 节点默认排除 | 验证真实视频 ffmpeg compression attack 的功能；文件内既有轻量 contract / guard 测试，也有真实压缩路径 smoke 测试。 |
| `tests/test_real_video_tar_zst_packager.py` | 6 | 功能测试 | 5 个节点默认执行，1 个 `smoke` 节点默认排除 | 验证 tar.zst 打包器的 summary / checks / 扩展名 / notebook contract；其中 `test_real_video_tar_zst_packager_outputs_archive_and_checks` 会跑完整 tiny stage-two run 并检查实际归档内容。 |
| `tests/test_records_schema.py` | 2 | 约束测试 | 1 个节点默认执行，1 个 `smoke` 节点默认排除 | 验证 active formal stage 的 split 计划覆盖和 event records / thresholds / manifest schema；其中 schema 闭环节点依赖 smoke runtime。 |

## 4. 默认排除的重型测试文件

这些文件当前不会被默认 `pytest -q` 执行，主要原因是它们带有 `smoke`、`slow` 或 `formal` marker，用于运行更重的 runtime 闭环、artifact rebuild、真实视频指标或 formal gate。

| 测试文件 | 节点数 | marker | 类型 | 主要测试内容 |
| --- | ---: | --- | --- | --- |
| `tests/test_ablation_consistency.py` | 1 | `smoke` | 约束测试 | 验证 active formal stage 的 method variant 共享同一 protocol 口径。 |
| `tests/test_protocol_no_threshold_leakage.py` | 2 | `smoke` | 约束测试 | 验证阶段 0 / 阶段 1 的 threshold calibration 不发生 test leakage。 |
| `tests/test_real_video_attack_registry_dual_mode.py` | 10 | `smoke` | 功能测试 | 验证真实视频 attack registry 在两种运行模式下的攻击实例化与行为。 |
| `tests/test_real_video_lpips_metric_formal_required.py` | 7 | `smoke` | 约束测试 | 验证 LPIPS 在 formal mode 下的必需性与阻断规则。 |
| `tests/test_real_video_quality_metrics_frame_based.py` | 6 | `smoke` | 功能测试 | 验证 stage-two 真实视频帧级质量指标。 |
| `tests/test_real_video_spatial_attacks.py` | 10 | `smoke` | 功能测试 | 验证真实视频空间攻击功能。 |
| `tests/test_real_video_temporal_attacks.py` | 8 | `smoke` | 功能测试 | 验证真实视频噪声 / 时域攻击功能。 |
| `tests/test_real_video_temporal_metrics_frame_based.py` | 6 | `smoke` | 功能测试 | 验证 stage-two 真实视频帧级时序指标。 |
| `tests/test_real_video_vae_latent_backend.py` | 1 | `smoke` | 功能测试 | 验证 stage-two backend 的 source video 与 encoded latent artifact 行为。 |
| `tests/test_real_video_vae_latent_drive_packager.py` | 1 | `smoke` | 功能测试 | 验证 stage-two scaffold drive packager 的归档与摘要行为。 |
| `tests/test_real_video_vae_latent_formal_pass_criteria.py` | 7 | `smoke` | 约束测试 | 验证 stage-two formal PASS 条件集合。 |
| `tests/test_real_video_vae_latent_governance_summary.py` | 12 | `smoke` | 约束测试 | 验证 governance summary 的 18 条 PASS / FAIL / INCONCLUSIVE 条件。 |
| `tests/test_real_video_vae_latent_records_schema.py` | 2 | `smoke` | 约束测试 | 验证 stage-two records schema 与 artifacts 布局。 |
| `tests/test_real_video_vae_latent_table_rebuild.py` | 1 | `smoke` | 功能测试 | 验证 stage-two scaffold tables / report 可以从 records 重建。 |
| `tests/test_synthetic_tubelet_sync_records_schema.py` | 2 | `smoke` | 约束测试 | 验证 stage-one event records 中的 `mechanism_trace` 与正式字段语义。 |
| `tests/test_synthetic_tubelet_sync_table_rebuild.py` | 5 | `smoke`, `slow` | 功能测试 | 验证 stage-one tables / curves / report 可重建；其中 proof profile 测试会跑更重的 sweep。 |
| `tests/test_table_rebuild.py` | 1 | `smoke` | 功能测试 | 验证阶段 0 tables 可以从 records 重建。 |

## 5. 默认执行中仍然偏重的测试

虽然下列测试没有被 `smoke` / `slow` / `formal` marker 排除，但它们仍然是默认 `pytest -q` 较耗时的主要来源：

| 测试文件 | 偏重原因 |
| --- | --- |
| `tests/test_real_video_tar_zst_packager.py` | 其中多个默认执行节点会通过 `run_real_video_vae_latent_tiny()` 反复生成 tiny stage-two run root，实际代价高于纯 contract test。 |
| `tests/test_vae_encode_decode_reproducibility.py` | 会写 mp4、构建 `RealVideoVAELatentBackend` 并执行 `build_sample()`。 |
| `tests/test_real_video_mp4_io.py` | 会做 mp4 写入、读取、metadata probe 与帧标准化。 |
| `tests/test_real_video_attack_matrix.py` | 会实例化真实视频 backend 与完整 attack matrix。 |
| `tests/test_real_vae_backend_registry.py` | 除 registry 断言外，还覆盖 runner 对 runtime config 的映射路径。 |

## 6. 当前测试结构结论

- 默认执行集并不只是纯 unit test，而是混合了不少未标记的集成测试。
- 当前 suite 的治理覆盖较完整，命名、字段、boundary、intake、file organization、UTF-8 编码、audit 汇总都有单独约束测试。
- 当前默认排除的 90 个节点主要属于 runtime 闭环、rebuild、formal gate、真实视频指标与 stage-specific smoke 测试。
- 如果后续要继续缩短默认 `pytest -q` 时间，优先应处理：
  - 将 runner-backed 的 packager contract 测试进一步拆成纯 contract 与 smoke 两层；
  - 将重复生成 tiny run root 的 helper 改为可复用 fixture；
  - 将 mp4 / ffmpeg / backend build 类测试进一步细分 `unit` 与 `smoke`。
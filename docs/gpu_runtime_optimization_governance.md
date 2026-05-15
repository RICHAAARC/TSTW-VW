# GPU Runtime Optimization Governance

本文档冻结论文实验执行层的 GPU 资源治理与运行优化边界。当前阶段允许通过 notebook、runtime profiling、batch scheduling、cache reuse 与 runtime profile 提高论文实验执行效率，但这些能力不属于水印方法核心，不得污染 main/ 的方法语义、统计判决口径或 formal PASS 语义。

## 一、边界定位

- main/ 只保存水印方法、VAE backend、视频 IO、攻击、指标、统计协议、records、thresholds、tables 与 CLI 等核心能力。
- experiments/ 保存阶段性 runner、artifact builder 与 protocol-specific table builder；它可以调用 main/，但不得把 profiling / Colab / Drive 会话逻辑深嵌进方法机制。
- paper_workflow/ 与 scripts/profile_runtime/、scripts/check_results/、scripts/package_results/ 构成论文实验执行与资源治理层。该层负责 Colab notebook、GPU trace、timing summary、Drive IO profile、runtime recommendation、结果检查与打包。
- GPU 优化层不属于方法核心。论文完成后的最终 release 可以移除 paper_workflow/ 与 Colab 专用路径，而不改变 main/ 的核心方法表达。

## 二、当前阶段入口

- 在论文完成前，paper_workflow/ 是正式实验执行入口，而不是临时 demo。
- notebook 必须调用受治理的 runner、checker 与 packager；不得手动拼接 formal tables、reports 或 evidence 结论。
- notebook 可以负责 environment setup、Drive handoff、runtime profiling 与 packaging，但不得绕过 records/、thresholds/、tables/、reports/ 的正式产物路径。

## 三、runtime_profile 规则

- runtime_profile 是执行配置，不是方法配置。
- 受治理的 profile 位于 configs/runtime_profiles/，并使用 stage-free、可审计的 snake_case 命名。
- runtime_profile 只能影响执行效率参数，例如：
  - vae_batch_size_frames
  - lpips_batch_size
  - clip_batch_size
  - attack_worker_count
  - video_io_worker_count
  - shard_count
  - local_cache_policy
  - reuse_encoded_latents
  - reuse_decoded_videos
  - reuse_attacked_videos
  - profile_gpu_runtime
  - profile_run_timing
  - profile_drive_io
- runtime_profile 不得包含或覆盖任何方法语义字段，例如：
  - target_fpr
  - threshold_override
  - threshold_policy
  - score_weight_override
  - method_variant_selection_from_test
  - sample split / attack severity / decision rule 覆盖

### `shard_count` / `shard_index` / `worker_count` 并行语义

- `shard_count` 表示外层 event shard 总数。它表示把某个 `sample_role` 的全部 source events 总共切成多少个 outer shard。
- `shard_index` 不属于 checked-in `runtime_profile` JSON 字段，而是受治理的单次运行选择参数。它表示当前运行只处理第几个 outer shard，并且必须满足 `0 <= shard_index < shard_count`。
- `worker_count` 表示已选 shard 内部的本地 worker 数。它不是额外的 outer shard 数，也不代表再次切分新的 shard 平面。
- 受治理的执行顺序必须固定为两步：先用 `shard_count` 决定总任务切成几片，再用 `shard_index` 选中当前运行的 outer shard；只有在选中这一片之后，才允许用 `worker_count` 把该 shard 内部的 events 分给本地 worker 并行处理。
- `shard_count` / `shard_index` 属于 shard 级并行语义，`worker_count` 属于 shard 内并行语义；governed notebook、workflow helper、harness audit 与约束测试不得将两者混用或互相重解释。

## 四、允许与禁止

允许的运行优化：

- 提高或降低 batch size、worker count、cache reuse 与 shard_count；
- 按 L4 / A100-80G 规划不同 runtime_profile；
- 记录 GPU utilization、peak memory、timing summary 与 Drive IO profile；
- 依据 profiling summary 推荐下一轮 batch size 或 runtime profile；
- 在 formal checker 失败时保留 runtime_profile/ 产物用于诊断。

禁止的运行优化：

- 修改 watermark embedding 语义；
- 修改 evidence score 定义或 S_tubelet / S_sync / S_traj / S_final 的计算；
- 修改 threshold calibration 口径、target_fpr 或 formal checker 语义；
- 根据 test split 结果调参或选择 method variant；
- 将 runtime profiling 结果写入正式 evidence records 或将 GPU utilization 作为论文性能指标。

## 五、运行记录与可追溯性

每次受治理 run 必须在 <run_root>/runtime_profile/ 中保留执行侧诊断产物。最小集合包括：

- runtime_profile_plan.json
- colab_environment_snapshot.json
- gpu_runtime_trace.csv
- gpu_runtime_summary.json
- run_timing_events.jsonl
- run_timing_summary.json
- run_scale_estimate.json
- run_failure_summary.json
- runtime_parameter_recommendation.json

这些产物只服务执行诊断、资源规划与结果可复现性，不得进入 records/、thresholds/ 或 tables/ 作为方法证据。

## 六、L4 与 A100-80G 规划

- L4 profile 主要服务 debug、smoke 与 formal 的受治理运行，重点是稳定性、Drive handoff 与 session-local cache reuse。
- A100-80G profile 只允许提高吞吐相关参数，例如更高的 vae_batch_size_frames、lpips_batch_size、clip_batch_size、worker_count 与 cache reuse。
- A100-80G 不得改变 split、threshold policy、target_fpr、method variants、attack severity 或 decision rule。
- 更强 GPU 的职责是更快产出论文数据，而不是改变实验口径。

## 七、release 边界

- paper_workflow/ 在当前论文期是正式执行入口，但不属于最终发布版默认内容。
- paper_workflow/ 不属于最终发布版默认内容。
- 最终 release 抽取时，应能够移除 paper_workflow/、Colab 会话路径与 notebook-specific wrapper，而不影响 main/ 的核心方法、experiments/ 的协议 runner、scripts/ 的通用检查与打包能力。
- release 边界的合格判据仍以 docs/file_organization.md 为准：paper_workflow/ 可以完全删除而不影响最终发布版命令行复现。

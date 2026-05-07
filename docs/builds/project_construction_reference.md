# 项目构建

## 一、文件定位与冻结性质

本文件是“面向 DiT / Flow Matching 视频生成模型的时空同步轨迹水印项目”的项目构建冻结约束。Codex 在构建、重构、补齐、修复或扩展本项目时，必须以本文件作为高层构建路线与工程边界依据。

本文件不是一次性开发任务清单，而是整个项目从最小可跑通、机制验证、真实视频验证、轨迹统计验证、完整论文实验，到最小发布版本抽取的长期构建约束。

本项目最终目标是形成一个能够支撑论文投稿、消融实验、统一统计判决、稳定数据产出和最小代码发布的视频生成水印研究框架。项目构建过程中不得偏离以下三项总目标：

1. 方法机制可递进验证：每一阶段只回答一个核心机制问题，避免过早接入完整 DiT / Flow Matching 视频生成模型导致问题混杂。
2. 论文数据可稳定产出：所有实验结果必须通过统一 `records`、`thresholds`、`metrics`、`tables`、`figures` 生成，避免人工拼表和实验口径混淆。
3. 核心方法可最小发布：最终能够从完整工程中抽取 `method_core`、`protocol_core` 与 `minimal_demo`，形成供论文审查和代码开源的最小版本。

Codex 必须按照本文件定义的阶段顺序推进项目构建。除非用户明确要求，否则不得跳阶段、合并阶段、重写整体架构或提前接入高风险模块。

---

## 二、方法机制边界

### （一）项目核心方法对象

本项目的方法机制围绕以下三个算法对象展开：

1. `temporal-synchronized tubelet code`：将水印承载单元从逐帧 latent 扩展为跨帧 latent tubelet，并通过 temporal synchronization 恢复未知时间对齐。
2. `Flow Matching trajectory statistic`：将水印证据从静态 latent 投影扩展到采样轨迹或近似轨迹的速度场统计量。
3. `fixed low-FPR calibrated detector`：在 clean negative 与 attacked negative 上统一标定阈值，并在 test split 上固定阈值评估 positive 与 attacked positive。

项目构建不得将方法实现为互不相关的工程分数堆叠。所有 evidence 必须围绕统一的 tubelet code、同步码、轨迹统计与固定低假阳性率统计协议组织。

### （二）证据链定义

本项目至少包含以下 evidence：

1. `tubelet_evidence`：由 latent tubelet 投影统计量产生。
2. `sync_evidence`：由 temporal PRC synchronization 或等价时间对齐恢复机制产生。
3. `trajectory_evidence`：由 Flow Matching trajectory statistic 或近似 inversion trajectory statistic 产生。
4. `final_evidence`：由 fixed low-FPR calibrated fusion 产生。

每个 evidence 必须有独立字段、独立启用开关、独立消融入口和独立记录输出。不得只写最终分数而丢失中间 evidence。

### （三）统计判决边界

所有检测必须被实现为二元假设检验：

```text
H0: clean 或 attacked clean negative
H1: watermarked positive 或 attacked watermarked positive
```

阈值必须只由 calibration negative 估计。test split 不得参与阈值选择、权重选择、attack-specific 调参或最终规则选择。

阈值协议必须支持以下基本字段：

```text
target_fpr
calibration_split
calibration_negative_roles
threshold_value
threshold_quantile
threshold_source_record_digest
score_name
method_variant
fusion_rule
created_at
```

---

## 三、总体工程原则

### （一）递进式构建原则

本项目采用递进式构建，而不是每个阶段重新搭建项目。阶段推进时允许新增模块、扩展配置、补充 records schema，但不得破坏已冻结阶段的可运行性与历史结果可解释性。

阶段顺序固定如下：

1. 阶段 0：协议骨架与记录层冻结。
2. 阶段 1：Synthetic Video Latent Probe。
3. 阶段 2：Real Video VAE Latent Probe。
4. 阶段 3：Flow Matching Trajectory Statistic Probe。
5. 阶段 4：Trajectory-Aware Embedding for DiT / Flow Matching。
6. 阶段 5：论文协议冻结。
7. 阶段 6：Minimal Release Extraction。

在阶段 1 未通过之前，不得实现或强依赖完整 DiT / Flow Matching sampling-time embedding。阶段 3 未证明 trajectory evidence 具有独立增益之前，不得将 trajectory-aware embedding 写成主线必需模块。

### （二）配置驱动原则

所有实验变体、消融设置、攻击矩阵、split、target FPR、method variant、fusion rule、输出路径均必须由配置文件控制。

禁止通过以下方式实现正式实验差异：

1. 手动注释代码。
2. 临时修改函数内部常量。
3. 复制一份几乎相同的脚本作为新方法。
4. 在 notebook cell 中临时覆盖关键协议参数但不写入配置与 records。
5. 根据 test positive 结果反向修改阈值、权重或 fusion rule。

### （三）统一记录原则

所有正式实验必须写入统一 records。任何进入论文表格、曲线、报告、失败样例分析的数据，都必须能追溯到 event-level records。

正式结果不得只存在于 notebook 输出、终端日志、临时变量、图片文件或手工整理表格中。

### （四）阶段可回放原则

每个阶段必须能够独立回放。删除 `tables/`、`figures/`、`reports/` 后，应能仅根据 `records/`、`thresholds/`、`manifest/` 与配置重新生成该阶段所有统计表格和图形。

### （五）最小发布可抽取原则

项目从阶段 0 开始就必须避免核心方法与大型实验工程强耦合。最终应能抽取：

```text
method_core/
protocol_core/
minimal_demo/
```

最小发布版本不得依赖完整 notebook、历史实验目录、大型模型权重、完整数据集或本地绝对路径。

### （六）门禁分层与核心代码解耦原则

门禁必须分为两类：

1. 协议运行时契约：允许存在于 `main/core/`、`main/protocol/` 与 `main/analysis/`，例如 records schema、threshold calibration、manifest validation、table rebuild。
2. 外层治理门禁：只能存在于 `tools/harness/`、`.codex/`、`tests/` 或 docs 中，例如 naming governance、placeholder/random audit、stage progression guard、notebook bypass audit、skill file presence audit。

当前与后续阶段必须明确禁止以下耦合：

1. `main/` import `tools/harness`。
2. `main/` import `tests`。
3. `main/` 中出现 stage progression guard。
4. `main/` 中出现 skill file audit。
5. `main/` 中出现 naming governance 的全仓扫描逻辑。
6. `method_core` 依赖 project construction governance。
7. `protocol_core` 硬编码具体 method family、具体 method factory 或具体 latent backend。

未来最小发布抽取必须满足：

1. `method_core` 只抽取方法本身。
2. `protocol_core` 只抽取 fixed low-FPR、split、records、thresholds、manifest、metrics / tables 等复现协议。
3. `minimal_demo` 只依赖 `method_core` 与 `protocol_core`。
4. `tools/harness/`、`.codex/`、`docs/builds/`、`audit_reports/` 与大型实验产物不得进入 `minimal_demo`。

阶段推进要求：

1. 阶段 0 完成后，进入阶段 1 前必须先保证核心解耦边界成立。
2. 阶段 1 只允许新增 synthetic tubelet / sync 机制，不允许重写阶段 0 协议层。

---

## 四、推荐目录结构

Codex 构建项目时应优先采用以下目录结构。允许根据真实仓库已有结构做最小适配，但不得破坏职责分离。

```text
project_root/
├── configs/
│   ├── method/
│   │   ├── tubelet_sync.yaml
│   │   ├── trajectory_statistic_probe.yaml
│   │   └── tubelet_sync_trajectory_fusion.yaml
│   ├── protocol/
│   │   ├── split_dev_calib_test.yaml
│   │   ├── fixed_low_fpr.yaml
│   │   └── temporal_attack_matrix.yaml
│   ├── ablation/
│   │   ├── frame_prc.yaml
│   │   ├── tubelet_only.yaml
│   │   ├── tubelet_sync.yaml
│   │   ├── tubelet_traj.yaml
│   │   ├── traj_only.yaml
│   │   └── tubelet_sync_trajectory_fusion.yaml
│   └── release/
│       └── release_manifest.yaml
│
├── main/
│   ├── core/
│   │   ├── records.py
│   │   ├── manifest.py
│   │   ├── schema.py
│   │   ├── registry.py
│   │   └── digest.py
│   ├── backends/
│   │   ├── synthetic_video_latent.py
│   │   ├── real_video_vae_latent.py
│   │   └── flow_matching_backend.py
│   ├── methods/
│   │   └── temporal_tubelet_watermark/
│   │       ├── codebook.py
│   │       ├── tubelet_partition.py
│   │       ├── embedding.py
│   │       ├── synchronization.py
│   │       ├── trajectory_statistic.py
│   │       ├── fusion.py
│   │       └── method.py
│   ├── attacks/
│   │   ├── temporal.py
│   │   ├── spatial.py
│   │   ├── compression.py
│   │   └── attack_registry.py
│   ├── protocol/
│   │   ├── split_builder.py
│   │   ├── event_builder.py
│   │   ├── calibrator.py
│   │   ├── detector_runner.py
│   │   ├── evaluator.py
│   │   └── ablation_runner.py
│   ├── analysis/
│   │   ├── table_builder.py
│   │   ├── curve_builder.py
│   │   ├── confidence_interval.py
│   │   └── failure_case_exporter.py
│   └── release/
│       ├── extract_method_core.py
│       ├── check_minimal_release.py
│       └── build_minimal_demo.py
│
├── paper_workflow/
│   ├── PW00_prepare.ipynb
│   ├── PW01_generate_or_load_latents.ipynb
│   ├── PW02_calibrate_thresholds.ipynb
│   ├── PW03_attack_and_detect.ipynb
│   ├── PW04_evaluate_tables.ipynb
│   └── PW05_export_release.ipynb
│
├── tests/
│   ├── test_protocol_no_threshold_leakage.py
│   ├── test_records_schema.py
│   ├── test_ablation_consistency.py
│   ├── test_sync_alignment.py
│   ├── test_table_rebuild.py
│   └── test_minimal_release.py
│
└── outputs/
    └── runs/
        └── <run_id>/
            ├── records/
            ├── thresholds/
            ├── artifacts/
            ├── tables/
            ├── figures/
            ├── reports/
            └── release/
```

上述目录树中的 `release/`、`check_minimal_release.py`、`test_minimal_release.py` 等 release 相关条目表示后期抽取目标，不表示当前阶段即可创建 `minimal_release/` 或正式 release 产物。

若真实仓库已经存在不同目录结构，Codex 必须优先复用现有结构，并在不破坏现有入口的基础上实现上述职责划分。

---

## 五、阶段 0：协议骨架与记录层冻结

### （一）阶段目标

建立可递进扩展的项目骨架，固定 sample role、split、record schema、threshold protocol、method variant、evidence interface 与输出结构。

阶段 0 不追求水印性能，只追求协议可执行、记录可审计、结果可复现。

### （二）必须实现的核心对象

1. `LatentBackend`：统一 latent 来源接口。
2. `WatermarkMethod`：统一 `embed()`、`detect()`、`detect_batch()` 接口。
3. `EvidenceExtractor`：统一输出 tubelet、sync、trajectory evidence。
4. `ProtocolRunner`：统一执行 dev / calibration / test。
5. `ThresholdCalibrator`：只使用 calibration negative 估计阈值。
6. `RecordWriter`：写入 event record、score record、threshold record。
7. `AblationRunner`：按配置运行不同方法变体。
8. `TableBuilder`：从 records 生成 tables。
9. `ManifestBuilder`：记录 run 配置、代码版本、记录摘要、表格摘要。

### （三）必须固定的 sample role

至少支持：

```text
clean_negative
attacked_negative
watermarked_positive
attacked_positive
```

可扩展角色必须显式加入 schema，不得用字符串散落在代码中。

### （四）必须固定的 split

至少支持：

```text
dev
calibration
test
```

要求：

1. `dev` 可用于开发阶段选择参数。
2. `calibration` 只能用于阈值、标准化统计量与预先声明的 fusion rule 标定。
3. `test` 只能用于最终评估。
4. 同一 sample id 不得跨 split 泄漏。
5. test positive 不得参与任何阈值或权重选择。

### （五）阶段 0 验证方法

Codex 必须补充或更新测试，至少验证：

1. `threshold` 只由 calibration negative 产生。
2. test 阶段不能写入新的 threshold。
3. 每条 score record 都包含 split、sample role、method variant、attack name、evidence scores、final score、decision。
4. 所有 ablation variant 使用同一 split 与 attack matrix。
5. 删除 tables 后可以从 records 重建。
6. notebook 入口不得绕过正式 protocol runner 写出正式结果。

### （六）阶段 0 通过标准

阶段 0 通过标准：

1. 空方法或随机占位方法可以跑通 calibration / test。
2. 能生成 `thresholds.json`、`event_scores.jsonl`、`main_metrics.csv`、`ablation_table.csv`、`run_manifest.json`。
3. 所有正式产物均位于 `outputs/runs/<run_id>/` 下。
4. 所有论文候选表格均可从 records 重建。
5. 阈值泄漏测试必须通过。

---

## 六、阶段 1：Synthetic Video Latent Probe

### （一）阶段目标

在受控 synthetic video latent 上验证 temporal-synchronized tubelet code 是否成立。

本阶段只回答一个核心问题：

```text
在 fixed low-FPR protocol 下，Tubelet+Sync 是否相对于 Frame-PRC 与 Tubelet-only 稳定提升 temporal crop、frame dropping、speed change 与 local clip detection 的鲁棒性，同时不造成 attacked negative FPR 失控。
```

### （二）必须实现的模块

1. `synthetic_video_latent.py`：生成 \(z\sim\mathcal{N}(0,I)\) 的视频 latent。
2. `tubelet_partition.py`：实现 frame-to-tubelet 划分。
3. `codebook.py`：实现 PRG direction、payload code、sync code。
4. `embedding.py`：实现 projection-margin embedding。
5. `synchronization.py`：实现 offset search 与可选 scale search。
6. `temporal.py`：实现 temporal crop、frame dropping、speed change、local clip、latent Gaussian noise。
7. `ablation_runner.py`：运行 Frame-PRC、Tubelet-only、Tubelet+Sync。

### （三）必须支持的 ablation variant

1. `frame_prc`：逐帧 PRC baseline。
2. `tubelet_only`：启用 tubelet code，禁用 sync search。
3. `tubelet_sync`：启用 tubelet code 与 temporal synchronization。

### （四）必须记录的核心指标

1. `clean_negative_FPR`。
2. `attacked_negative_FPR`。
3. `clean_positive_TPR`。
4. `attacked_positive_TPR`。
5. `temporal_crop_TPR`。
6. `frame_dropping_TPR`。
7. `speed_change_TPR`。
8. `local_clip_TPR`。
9. `sync_peak_rank`。
10. `sync_alignment_error`。
11. `tubelet_length_ablation`。
12. `clip_length_curve`。

### （五）阶段 1 必须产出

```text
main_tpr_fpr_table.csv
ablation_table.csv
local_clip_curve.csv
temporal_attack_curve.csv
tubelet_length_ablation.csv
sync_peak_examples.png
method_validation_report.md
```

### （六）阶段 1 通过标准

阶段 1 通过标准：

1. `tubelet_only` 在至少一种时间攻击下稳定优于 `frame_prc`。
2. `tubelet_sync` 在 temporal crop 或 local clip detection 下稳定优于 `tubelet_only`。
3. attacked negative FPR 不因 sync search 明显失控。
4. \(L_t>1\) 相比 \(L_t=1\) 存在可解释趋势。
5. local clip 长度下降时，TPR 呈现可解释下降趋势。
6. 所有结果均通过 records 自动生成，不依赖人工拼表。

若阶段 1 不通过，不得进入阶段 2。必须优先检查 tubelet 划分、sync code、search range、embedding margin、calibration negative 与 record 口径。

---

## 七、阶段 2：Real Video VAE Latent Probe

### （一）阶段目标

验证阶段 1 的 tubelet synchronization 机制在真实视频 VAE latent 中是否仍成立，并评估质量和时序一致性。

本阶段只回答一个核心问题：

```text
在真实视频经 VAE 编码与解码后，Tubelet+Sync 是否仍能在 fixed low-FPR protocol 下保持对时间攻击、空间攻击、压缩攻击和 local clip detection 的鲁棒性，同时保证质量损失可控。
```

### （二）必须实现的模块

1. `real_video_vae_latent.py`：负责视频读取、VAE 编码、VAE 解码与重编码。
2. `compression.py`：实现 H.264 / H.265 compression。
3. `spatial.py`：实现 resize、crop-resize、blur、Gaussian noise。
4. `quality_metrics.py`：实现视频质量指标。
5. `temporal_metrics.py`：实现时序一致性指标。
6. `failure_case_exporter.py`：导出检测失败、同步失败、质量下降样例。

### （三）必须支持的攻击矩阵

1. no attack。
2. H.264 compression。
3. H.265 compression。
4. spatial resize。
5. crop-resize。
6. Gaussian noise。
7. blur。
8. temporal crop。
9. frame dropping。
10. speed change。
11. local clip detection。

### （四）必须记录的核心指标

1. 鲁棒性指标：FPR、TPR、attack-wise TPR、local clip TPR。
2. 质量指标：PSNR、SSIM、LPIPS、CLIP similarity 或项目中可用的替代指标。
3. 时序指标：temporal consistency、flicker score、motion consistency 或项目中可用的替代指标。
4. 失败样例索引：sample id、attack name、method variant、failure reason。

### （五）阶段 2 必须产出

```text
real_video_attack_breakdown.csv
quality_table.csv
temporal_consistency_table.csv
failure_case_gallery/
vae_latent_probe_report.md
```

### （六）阶段 2 通过标准

阶段 2 通过标准：

1. `tubelet_sync` 在真实 VAE latent 中仍优于 `frame_prc` 与 `tubelet_only`。
2. temporal synchronization 对 temporal crop、frame dropping 或 local clip detection 有可解释增益。
3. attacked negative FPR 仍可由 calibration negative 控制。
4. 视频质量下降可量化、可报告、可调参。
5. 没有大规模不可接受的 flicker 或 motion artifact。
6. 所有表格均可由 records 重建。

若阶段 2 不通过，不得直接进入阶段 4。必须优先分析 VAE 编码噪声、latent normalization、carrier tubelet 选择、压缩破坏模式与同步失败模式。

---

## 八、阶段 3：Flow Matching Trajectory Statistic Probe

### （一）阶段目标

验证 trajectory evidence 是否提供独立于 tubelet evidence 与 sync evidence 的补充判别力。

本阶段只回答一个核心问题：

```text
Flow Matching trajectory statistic 是否在 fixed low-FPR protocol 下为最终检测提供非冗余的边际增益。
```

### （二）必须实现的模块

1. `flow_matching_backend.py`：统一管理 trajectory latent、inversion latent 或近似 reconstruction latent。
2. `trajectory_statistic.py`：实现 velocity projection、displacement projection 与可选 curvature residual。
3. `score_correlation.py`：分析 trajectory score 与 tubelet score 的相关性。
4. `runtime_breakdown.py`：记录 trajectory reconstruction 与 detection overhead。
5. `trajectory_ablation_runner.py`：统一运行 trajectory 相关消融。

### （三）必须支持的 ablation variant

1. `tubelet_only`。
2. `tubelet_sync`。
3. `tubelet_traj`。
4. `traj_only`。
5. `tubelet_sync_trajectory_fusion`。

### （四）必须记录的核心指标

1. `S_tubelet`。
2. `S_sync`。
3. `S_traj`。
4. `S_final`。
5. `score_correlation_matrix`。
6. `trajectory_positive_negative_separation`。
7. `trajectory_runtime_overhead`。
8. `delta_traj = TPR(tubelet_sync_trajectory_fusion) - TPR(tubelet_sync)`。

### （五）阶段 3 必须产出

```text
trajectory_score_distribution.png
score_correlation_matrix.csv
trajectory_ablation_table.csv
runtime_breakdown.csv
trajectory_probe_report.md
```

### （六）阶段 3 通过标准

阶段 3 通过标准：

1. `S_traj` 在 positive 与 negative 之间存在统计分离。
2. `tubelet_traj` 或 `tubelet_sync_trajectory_fusion` 相比无 trajectory variant 存在边际增益。
3. `S_traj` 与 `S_tubelet` 不是高度冗余。
4. trajectory evidence 的增益能映射到明确攻击类型或失败模式。
5. trajectory overhead 可量化并可在论文中报告。
6. 所有结论均由统一 records 与 ablation table 支撑。

若阶段 3 不通过，Codex 不得把 trajectory evidence 强制写入主论文核心路径。此时应保留代码接口，但将 trajectory 模块标记为 optional 或 exploratory。

---

## 九、阶段 4：Trajectory-Aware Embedding for DiT / Flow Matching

### （一）阶段目标

将水印机制从 latent post-hoc embedding 推进到 sampling-time weak constraint，使方法真正绑定 DiT / Flow Matching 生成过程。

本阶段只回答一个核心问题：

```text
在 DiT / Flow Matching 采样过程中加入弱轨迹约束，是否能提升 trajectory evidence 与最终鲁棒性，同时不破坏视频质量、语义一致性和运动一致性。
```

### （二）进入条件

只有同时满足以下条件，才允许进入阶段 4：

1. 阶段 1 已证明 `tubelet_sync` 的机制成立。
2. 阶段 2 已证明真实 VAE latent 中机制没有崩溃。
3. 阶段 3 已证明 trajectory evidence 至少具有非零边际增益或明确探索价值。
4. 阶段 0 的 records、threshold、ablation、table builder 已稳定。

### （三）必须实现的模块

1. `sampling_hook.py`：在采样过程中插入 weak constraint。
2. `lambda_schedule.py`：定义 \(\lambda(t)\) 的时间调度。
3. `velocity_projection.py`：实现局部 velocity perturbation。
4. `motion_artifact_audit.py`：检查运动异常。
5. `semantic_consistency.py`：检查 prompt / video consistency。
6. `sampling_constraint_ablation.py`：运行不同 \(\lambda\) 与时间窗口消融。

### （四）必须记录的核心指标

1. `trajectory_score_gain`。
2. `final_tpr_gain`。
3. `quality_drop`。
4. `motion_consistency_drop`。
5. `semantic_consistency_drop`。
6. `runtime_overhead`。
7. `artifact_failure_count`。
8. `lambda_schedule_id`。

### （五）阶段 4 必须产出

```text
lambda_schedule_ablation.csv
trajectory_aware_embedding_table.csv
quality_robustness_tradeoff.png
motion_artifact_failure_cases/
flow_matching_probe_report.md
```

### （六）阶段 4 通过标准

阶段 4 通过标准：

1. sampling-time weak constraint 增强 `S_traj` 或 `S_final`。
2. trajectory-aware 主方法配置在至少部分攻击下优于不使用 sampling constraint 的版本。
3. 视频质量下降、语义一致性下降和运动一致性下降均可量化并处于可报告范围。
4. \(\lambda(t)\) 的选择不依赖 test positive 调参。
5. 失败样例和 trade-off 曲线完整记录。

若阶段 4 破坏质量或无稳定增益，该模块必须降级为 exploratory，不得阻断阶段 5 的论文协议构建。

---

## 十、阶段 5：论文协议冻结

### （一）阶段目标

冻结完整论文实验协议，自动产出主表、消融表、攻击曲线、局部片段检测曲线、质量表、runtime 表、失败样例分析与统计协议附录。

本阶段只回答一个核心问题：

```text
在统一 fixed low-FPR protocol 下，本项目是否能够稳定、准确、无口径混淆地产出论文所需全部实验数据。
```

### （二）必须固定的实验协议

1. dev / calibration / test 三段式划分。
2. clean negative、attacked negative、watermarked positive、attacked positive 四类样本。
3. fixed low-FPR threshold。
4. 统一 attack matrix。
5. 统一 ablation variants。
6. 统一 baseline comparison。
7. 统一 quality metric。
8. 统一 runtime metric。
9. 统一 confidence interval 计算方式。
10. 统一 failure case taxonomy。

### （三）必须支持的主表字段

1. `method_variant`。
2. `clean_negative_FPR`。
3. `attacked_negative_FPR`。
4. `clean_positive_TPR`。
5. `attacked_positive_TPR`。
6. `local_clip_TPR`。
7. `temporal_attack_TPR`。
8. `quality_score`。
9. `temporal_consistency_score`。
10. `runtime_overhead`。
11. `confidence_interval`。
12. `threshold_id`。

### （四）必须支持的消融指标

至少报告：

```text
delta_tubelet = TPR(tubelet_only) - TPR(frame_prc)
delta_sync = TPR(tubelet_sync) - TPR(tubelet_only)
delta_traj = TPR(tubelet_sync_trajectory_fusion) - TPR(tubelet_sync)
```

若某个 evidence 不成立，必须在 `paper_claim_audit.md` 中标记为 `not_supported`，不得在论文主张中强行表述为核心贡献。

### （五）必须产出的论文数据文件

```text
outputs/runs/<run_id>/tables/
├── main_tpr_fpr_table.csv
├── attack_breakdown_table.csv
├── ablation_table.csv
├── local_clip_curve.csv
├── temporal_attack_curve.csv
├── quality_table.csv
├── runtime_table.csv
└── threshold_stability_table.csv

outputs/runs/<run_id>/figures/
├── attack_curve.pdf
├── local_clip_curve.pdf
├── score_distribution.pdf
├── score_correlation_matrix.pdf
├── quality_robustness_tradeoff.pdf
└── sync_peak_examples.pdf

outputs/runs/<run_id>/reports/
├── protocol_report.md
├── ablation_report.md
├── failure_case_report.md
└── paper_claim_audit.md
```

### （六）阶段 5 验证方法

Codex 必须实现或更新以下审计：

1. 主表是否只使用 test split。
2. 阈值是否只来自 calibration negative。
3. attacked negative 是否进入 calibration。
4. 每个 ablation 是否使用同一 attack matrix。
5. 每张图是否可从 records 复现。
6. 每个论文 claim 是否能映射到具体表格或曲线。
7. 是否存在 test positive 调参痕迹。
8. 是否存在人工拼表路径。
9. 是否存在 notebook 临时变量绕过正式 table builder 的路径。

### （七）阶段 5 通过标准

阶段 5 通过标准：

1. 删除 `tables/`、`figures/`、`reports/` 后，可仅根据 records、thresholds、manifest 与 configs 重建全部论文产物。
2. `paper_claim_audit.md` 中每个 supported claim 都有明确表格或曲线证据。
3. 所有 ablation 使用统一统计协议。
4. 所有 baseline 与本方法使用统一 split、attack matrix 与 target FPR。
5. 不存在 test leakage、threshold leakage、attack-specific threshold 或人工拼表。

---

## 十一、阶段 6：Minimal Release Extraction

### （一）阶段目标

从完整工程中抽取供论文审查和代码开源的最小发布版本。

本阶段只回答一个核心问题：

```text
是否能够从完整项目中抽取 method_core、protocol_core 与 minimal_demo，使外部用户无需完整工程即可复现核心机制验证。
```

### （二）最小发布版本必须包含

```text
minimal_release/
├── README.md
├── configs/
│   ├── method_minimal.yaml
│   ├── protocol_minimal.yaml
│   └── ablation_minimal.yaml
├── method_core/
│   ├── codebook.py
│   ├── tubelet_partition.py
│   ├── embedding.py
│   ├── synchronization.py
│   ├── trajectory_statistic.py
│   └── fusion.py
├── protocol_core/
│   ├── calibrator.py
│   ├── evaluator.py
│   └── metrics.py
├── minimal_demo/
│   ├── run_synthetic_probe.py
│   └── reproduce_main_table.py
├── tests/
│   ├── test_threshold_no_leakage.py
│   ├── test_sync_alignment.py
│   ├── test_ablation_consistency.py
│   └── test_records_rebuild_tables.py
└── release_manifest.json
```

### （三）最小发布版本不得包含

1. 大型模型权重。
2. 完整视频数据集。
3. 历史实验全部 records。
4. notebook 临时变量。
5. 本地绝对路径。
6. 未进入论文主张的探索性模块。
7. 与核心方法无关的工程脚手架。
8. 需要私有环境才能运行的硬编码依赖。

### （四）最小发布版本验证方法

Codex 必须实现：

1. `extract_method_core.py`：从完整工程抽取核心方法。
2. `check_minimal_release.py`：检查最小发布版本依赖闭包。
3. `build_minimal_demo.py`：生成最小 synthetic latent demo。
4. `test_minimal_release.py`：验证最小发布版本可运行。

### （五）阶段 6 通过标准

阶段 6 通过标准：

1. `minimal_demo/run_synthetic_probe.py` 可运行。
2. `minimal_demo/reproduce_main_table.py` 可生成最小主表。
3. Frame-PRC、Tubelet-only、Tubelet+Sync 消融可复现。
4. fixed low-FPR calibration 可复现。
5. `release_manifest.json` 完整列出发布文件、配置、版本与摘要。
6. 最小发布版本不依赖完整实验工程路径。

---

## 十二、Notebook 构建约束

若项目使用 `paper_workflow/` notebook 作为 Colab 或本地运行入口，Codex 必须遵守以下约束：

1. notebook 可以作为运行入口，但不得成为唯一协议实现位置。
2. notebook 中的配置区域必须显式写入 run config，并进入 manifest。
3. notebook 不得直接绕过 `ProtocolRunner`、`ThresholdCalibrator`、`RecordWriter` 和 `TableBuilder` 写正式结果。
4. notebook 修改实验规模、attack matrix、method variant、target FPR 时，必须同步写入 records 与 manifest。
5. notebook 输出的表格只允许来自正式 `TableBuilder`。
6. notebook 中允许可视化临时结果，但不得将临时结果作为论文正式表格来源。
7. 每个 notebook 阶段必须有明确输入目录、输出目录和可检查产物。

推荐 notebook 阶段职责如下：

1. `PW00_prepare.ipynb`：加载配置、构建 split、初始化 run manifest。
2. `PW01_generate_or_load_latents.ipynb`：生成或加载 latent / video。
3. `PW02_calibrate_thresholds.ipynb`：仅使用 calibration negative 标定 threshold。
4. `PW03_attack_and_detect.ipynb`：执行 attack matrix 与 detect。
5. `PW04_evaluate_tables.ipynb`：从 records 生成 metrics、tables、figures。
6. `PW05_export_release.ipynb`：抽取 minimal release 并运行 release checks。

---

## 十三、消融实验冻结约束

### （一）消融必须配置化

所有消融 variant 必须由配置文件定义。例如：

```yaml
method_variant: tubelet_sync
enable_frame_prc: false
enable_tubelet: true
enable_sync: true
enable_trajectory: false
enable_sampling_constraint: false
fusion_rule: calibrated_linear
```

禁止通过代码复制、函数重命名、局部注释或 notebook 临时覆盖实现消融。

### （二）消融必须共享协议

所有消融必须共享：

1. 同一 split。
2. 同一 sample role 定义。
3. 同一 attack matrix。
4. 同一 target FPR。
5. 同一 calibration negative 规则。
6. 同一 metrics builder。
7. 同一 table builder。
8. 同一 confidence interval 计算方式。

### （三）消融必须记录 disabled evidence

若某个 evidence 在某个 variant 中被禁用，record 中仍必须显式记录：

```json
{
  "S_tubelet": 0.123,
  "S_sync": null,
  "S_traj": null,
  "disabled_evidence": ["sync", "trajectory"]
}
```

不得通过缺失字段表示禁用状态。

### （四）消融结论必须由 delta 指标支撑

至少支持：

```text
delta_tubelet
delta_sync
delta_traj
delta_sampling_constraint
```

每个 delta 必须明确来源 variant，不得人工计算后写入报告。

---

## 十四、Records 与产物 schema 约束

### （一）event-level score record 必须包含

```json
{
  "run_id": "string",
  "event_id": "string",
  "sample_id": "string",
  "split": "dev|calibration|test",
  "sample_role": "clean_negative|attacked_negative|watermarked_positive|attacked_positive",
  "method_variant": "string",
  "attack_name": "string",
  "attack_params": {},
  "target_fpr": 0.001,
  "threshold_id": "string|null",
  "evidence_scores": {
    "S_tubelet": "float|null",
    "S_sync": "float|null",
    "S_traj": "float|null",
    "S_final": "float"
  },
  "decision": "bool",
  "failure_reason": "string|null"
}
```

### （二）threshold record 必须包含

```json
{
  "threshold_id": "string",
  "run_id": "string",
  "method_variant": "string",
  "score_name": "S_final",
  "target_fpr": 0.001,
  "calibration_split": "calibration",
  "calibration_negative_roles": ["clean_negative", "attacked_negative"],
  "threshold_value": "float",
  "threshold_quantile": "float",
  "num_calibration_negatives": "int",
  "fusion_rule": "string",
  "created_at": "string"
}
```

### （三）run manifest 必须包含

```json
{
  "run_id": "string",
  "created_at": "string",
  "project_stage": "protocol_skeleton|synthetic_tubelet_sync_probe|real_video_vae_latent_probe|trajectory_statistic_probe|trajectory_aware_sampling_probe|full_paper_protocol|minimal_release_extraction",
  "method_config_digest": "string",
  "protocol_config_digest": "string",
  "attack_matrix_digest": "string",
  "ablation_config_digest": "string",
  "records_digest": "string",
  "thresholds_digest": "string",
  "tables_digest": "string|null",
  "figures_digest": "string|null"
}
```

### （四）正式产物生成约束

1. `tables/` 只能由 `analysis/table_builder.py` 生成。
2. `figures/` 只能由 `analysis/curve_builder.py` 或明确注册的 figure builder 生成。
3. `reports/` 只能由正式 report builder 生成。
4. 所有产物必须记录来源 records 与配置摘要。
5. 禁止从 notebook 手动复制数值生成正式论文表格。

---

## 十五、测试与审计约束

Codex 每完成一个阶段，必须同步补充或更新测试。测试不得只检查函数能运行，还必须检查研究协议是否被遵守。

### （一）最低测试集合

1. `test_protocol_no_threshold_leakage.py`：检查 test split 不参与阈值。
2. `test_records_schema.py`：检查 event record 与 threshold record 字段完整。
3. `test_ablation_consistency.py`：检查 ablation 共享 split、attack matrix 与 target FPR。
4. `test_sync_alignment.py`：检查 synthetic temporal crop 下 sync 能恢复合理 offset。
5. `test_table_rebuild.py`：检查删除 tables 后可从 records 重建。
6. `test_paper_claim_audit.py`：检查 supported claim 必须绑定证据表格。
7. `test_minimal_release.py`：检查最小发布版本可运行。

### （二）必须阻断的失败

以下失败必须阻断阶段通过：

1. threshold 使用 test positive。
2. calibration negative 不包含 attacked negative，但配置声称启用 attacked negative calibration。
3. ablation variant 使用不同 split 或 attack matrix。
4. evidence score 字段缺失。
5. 表格无法从 records 重建。
6. notebook 绕过正式 table builder 生成正式结果。
7. 最小发布版本依赖完整工程路径。
8. test positive 结果反向影响 fusion rule 或 threshold。

---

## 十六、Codex 执行规则

### （一）每次变更前必须执行的检查

Codex 在修改前必须先读取真实仓库结构，并确认：

1. 当前已有目录与文件。
2. 当前已有配置入口。
3. 当前已有 notebook 入口。
4. 当前已有 records / metrics / tables 生成方式。
5. 当前已有测试与审计脚本。
6. 当前阶段属于阶段 0 至阶段 6 中的哪一阶段。

不得在未读取真实代码的情况下凭空创建一套与现有项目冲突的新结构。

### （二）每次变更必须说明

每次变更完成时必须给出：

1. 本次对应阶段。
2. 本次解决的核心机制问题。
3. 修改或新增文件列表。
4. 未修改且不得修改的文件列表。
5. 新增配置项。
6. 新增 records 字段。
7. 新增测试。
8. 如何运行验证。
9. 已知未完成项。
10. 是否允许进入下一阶段。

### （三）禁止行为

Codex 禁止执行以下行为：

1. 未经用户要求重写整个项目。
2. 跳过 synthetic latent 直接接入完整 DiT / Flow Matching sampling-time embedding。
3. 为了让结果好看而修改 test threshold。
4. 针对不同 attack type 使用不同阈值，除非协议明确声明并完整记录。
5. 手工拼接论文表格。
6. 将 notebook 临时变量作为正式论文结果来源。
7. 隐式改变 sample role 或 split 语义。
8. 将 trajectory evidence 在无验证时写成主论文必需机制。
9. 把失败实验静默过滤出表格。
10. 删除历史阶段可复现能力。

---

## 十七、阶段推进门禁

项目推进必须满足以下门禁。

### （一）阶段 0 → 阶段 1

允许条件：

1. records、thresholds、tables、manifest 基础设施可运行。
2. threshold leakage 测试通过。
3. ablation 配置机制可运行。
4. synthetic latent backend 可接入。

### （二）阶段 1 → 阶段 2

允许条件：

1. `tubelet_sync` 相比 `frame_prc` 与 `tubelet_only` 存在可解释增益。
2. attacked negative FPR 未失控。
3. local clip 与 temporal crop 曲线可由 records 重建。
4. `method_validation_report.md` 已生成。

### （三）阶段 2 → 阶段 3

允许条件：

1. real video VAE latent 中 `tubelet_sync` 未崩溃。
2. 视频质量与时序一致性指标已记录。
3. failure case 已导出。
4. 真实攻击矩阵已形成稳定 records。

### （四）阶段 3 → 阶段 4

允许条件：

1. trajectory evidence 有非零边际增益，或用户明确要求作为探索模块继续。
2. score correlation 与 runtime overhead 已报告。
3. trajectory 相关消融不破坏原有 tubelet_sync 结果。
4. trajectory 模块可被配置禁用。

### （五）阶段 4 → 阶段 5

允许条件：

1. sampling-time weak constraint 有稳定收益，或已被降级为 exploratory。
2. 主论文路径已明确是否包含 trajectory-aware embedding。
3. 质量、运动、语义一致性 trade-off 已报告。
4. 论文协议冻结所需方法变体和指标已齐备。

### （六）阶段 5 → 阶段 6

允许条件：

1. 主表、消融表、攻击曲线、质量表、runtime 表可自动生成。
2. paper claim audit 已完成。
3. 删除派生产物后可从 records 重建。
4. 核心方法模块与协议模块已与大型实验工程解耦。

---

## 十八、最终完成标准

当且仅当满足以下条件时，项目构建可视为完成：

1. 项目能够按阶段 0 至阶段 5 完整运行。
2. 每个阶段只回答一个清晰机制问题。
3. 所有正式实验结果均来自统一 records、thresholds、metrics、tables、figures。
4. 所有消融实验均通过配置切换，不通过复制代码或手工改函数完成。
5. 所有论文表格与曲线均可从 records 重建。
6. fixed low-FPR protocol 无 threshold leakage。
7. clean negative、attacked negative、watermarked positive、attacked positive 四类样本角色完整记录。
8. tubelet evidence、sync evidence、trajectory evidence 均有独立字段、独立消融和独立统计。
9. 不成立的 evidence 不被写成核心论文贡献。
10. 能够抽取 `method_core`、`protocol_core` 与 `minimal_demo`。
11. 最小发布版本能够独立运行 synthetic probe 并复现核心机制表格。
12. `release_manifest.json` 完整记录最小发布版本文件、配置、版本和摘要。

---

## 十九、当前优先起点

若从零或从现有未成型仓库开始构建，本项目的第一优先任务是：

```text
构建 `protocol_skeleton` 阶段骨架，并保证 `synthetic_tubelet_sync_probe` 能够作为阶段 1 的直接入口。
```

第一轮 Codex 变更不得实现复杂 DiT / Flow Matching 模型接入。第一轮应优先完成：

1. 配置结构。
2. records schema。
3. threshold calibration。
4. ablation runner。
5. synthetic latent backend。
6. Frame-PRC / Tubelet-only / Tubelet+Sync 的最小接口。
7. table builder。
8. threshold leakage test。
9. table rebuild test。
10. notebook 或 CLI 最小运行入口。

该起点完成后，项目才具备稳定进入真实视频 latent、trajectory statistic 与完整论文协议的基础。

# baseline_comparison_gate 构建流程步骤

## 1. 文档目标

本文档用于指导完成 `baseline_comparison_gate` 的全部工程与实验构建工作。该阶段的直接目标不是撰写论文正文, 而是产出后续 `paper_artifact_gate` 可直接使用的投稿级实验原始数据、阈值、表格、图表数据、审计材料与复现包。

本阶段完成后, 项目应具备以下能力:

1. 在相同真实视频数据集、相同 split、相同 payload 设定、相同攻击矩阵、相同质量指标、相同 fixed-FPR 校准协议下, 比较内部方法与外部视频水印 baseline。
2. 为主实验、压缩鲁棒性实验、空间攻击实验、时间攻击实验、质量保持实验、运行成本实验和消融实验提供可重建 records。
3. 将每次 Colab 冷启动运行产生的完整结果打包落盘到 Google Drive, 后续运行只从包中恢复, 不依赖前序 Colab session 状态。
4. 为后续论文阶段提供可追溯的 `tables/`, `figures/`, `reports/`, `claim_audit/`, `manifest.json` 和压缩归档。

## 2. 当前阶段边界

### 2.1 当前允许内容

`baseline_comparison_gate` 允许构建以下内容:

1. 外部 baseline 的来源审计、license 审计、权重审计与依赖审计。
2. 外部 baseline 的隔离式拉取、可运行复现修复与统一 adapter。
3. 基于真实视频 VAE 阶段结果包的 baseline 评估。
4. H.264 / H.265 压缩攻击、空间攻击、时间攻击和真实视频重编码链路。
5. LPIPS、CLIP similarity、PSNR、SSIM、码率、文件大小、运行时间、显存或 GPU runtime trace 等质量与成本指标。
6. fixed-FPR 阈值校准、主实验表格、攻击 breakdown 表格、运行成本表格、质量表格和 claim audit。

### 2.2 当前禁止内容

本阶段仍禁止以下行为:

1. 不得将外部 baseline 替代内部正式方法 `frame_prc`, `tubelet_only`, `tubelet_sync`。
2. 不得用未完成 source digest、model digest、license 审计、adapter 审计和 fixed-FPR 校准的 baseline 支撑优势 claim。
3. 不得把核心 protocol 逻辑只写在 notebook 中。Notebook 只能调度仓库模块。
4. 不得把正式实验输出提交到 `outputs/`。
5. 不得绕过 `pytest`、harness audit、package check 或 claim audit。
6. 不得为了提高 baseline 或内部方法结果而在 test split 上调整阈值、攻击参数或后处理规则。

## 3. 冷启动 Colab 结果交接原则

Colab 每次运行都应视为全新环境。因此, 任一 notebook 或 Colab runner 必须遵守以下原则:

1. 运行开始时只允许从 Git 仓库、Google Drive 输入包和公开依赖恢复状态。
2. 运行过程中先写入 session-local 目录, 例如 `/content/TSTW_runtime/runs/<workflow_key>/...`。
3. 只有当 runner、checker、package builder 和 manifest audit 全部通过后, 才将完整结果 materialize 到 Google Drive。
4. Google Drive 上不得提前创建空的正式结果目录。
5. 后续阶段只能通过解压前一阶段的完整包继续, 不能依赖 Colab 内存、临时目录或 notebook 输出单元格。

正式落盘路径应统一为:

```text
/content/drive/MyDrive/TSTW/results/<WORKFLOW_KEY>/<RUN_ID>_<UTC_TIME>_<SHORT_COMMIT>/
```

其中:

1. `<WORKFLOW_KEY>` 表示当前工作流语义名称, 例如 `baseline_comparison_gate`。
2. `<RUN_ID>` 表示本次运行的语义身份, 例如 `baseline_comparison_formal` 或 `baseline_comparison_smoke`。
3. `<UTC_TIME>` 使用 UTC 时间戳, 例如 `20260611T034500Z`。
4. `<SHORT_COMMIT>` 使用当前 Git commit 的短哈希。

## 4. 推荐目录组织

### 4.1 外部 baseline 隔离目录

建议使用如下目录组织, 用于区分上游代码、本项目补丁、adapter 和审计材料:

```text
external_baselines/
  external_videoseal/
    upstream/
    patches/
    adapter/
    README_TSTW.md
    source_manifest.json

  external_rivagan/
    upstream/
    patches/
    adapter/
    README_TSTW.md
    source_manifest.json

  external_hidden_framewise/
    upstream/
    patches/
    adapter/
    README_TSTW.md
    source_manifest.json
```

说明:

1. `upstream/` 保存外部 baseline 的原始代码快照或受控子模块引用。
2. `patches/` 保存本项目为 Colab 可运行、依赖兼容、路径兼容、日志兼容所做的补丁。
3. `adapter/` 保存统一接口封装, 不应修改 baseline 核心算法语义。
4. `source_manifest.json` 保存来源、commit、license、权重、digest、依赖和限制说明。
5. `README_TSTW.md` 说明本项目如何运行该 baseline, 以及哪些修改属于复现修复。

### 4.2 阶段三运行输出目录

一次正式运行的结果包建议包含:

```text
<run_root>/
  manifest.json
  configs/
  source_digest/
  input_packages/
  baseline_traces/
  records/
  thresholds/
  tables/
  figures/
  reports/
  claim_audit/
  environment/
  logs/
  archives/
```

各目录职责如下:

1. `configs/`: 保存本次运行使用的 dataset、attack、baseline、threshold 和 quality metric 配置。
2. `source_digest/`: 保存代码源、baseline 源、权重文件、输入包的 digest。
3. `input_packages/`: 保存本次运行实际加载的阶段二结果包索引和解压校验记录。
4. `baseline_traces/`: 保存每个 baseline 的 adapter 版本、score 映射规则、失败原因和 unsupported attack 说明。
5. `records/`: 保存逐样本、逐方法、逐攻击的原始记录。
6. `thresholds/`: 保存 calibration split 产生的阈值。
7. `tables/`: 保存从 records 和 thresholds 重建的投稿表格候选数据。
8. `figures/`: 保存图表所需的 CSV / JSON 数据和候选图片。
9. `reports/`: 保存自动生成的 markdown 报告。
10. `claim_audit/`: 保存每条实验 claim 到 records、tables、figures 的映射。
11. `environment/`: 保存 Colab 环境、Python 包、CUDA、GPU、ffmpeg、git 状态。
12. `logs/`: 保存 runner 日志、stderr、异常堆栈和耗时。
13. `archives/`: 保存完整 `.zip` 或 `.tar.zst` 包。

## 5. baseline 范围

本阶段正式 baseline 固定为:

1. `external_videoseal`
2. `external_rivagan`
3. `external_hidden_framewise`

其中:

1. `external_videoseal` 代表现代公开视频水印 baseline。
2. `external_rivagan` 代表经典视频水印 baseline。
3. `external_hidden_framewise` 代表图像水印逐帧迁移 baseline。

`external_hidden_framewise` 的定位必须明确: 它不是原生视频水印方法, 而是 frame-wise 图像水印迁移 baseline。论文中若使用该 baseline, 需要在表格和文字中标注其方法族限制。

## 6. 统一 baseline adapter 契约

每个 baseline 必须通过统一 adapter 接入, 仓库其他模块不得直接调用 baseline 内部函数。推荐 adapter 接口如下:

```python
class BaselineAdapter:
    def prepare(self, context):
        """准备依赖、模型权重、运行目录和环境检查。"""

    def embed(self, input_video_path, payload_bits, output_video_path, metadata):
        """将 payload 嵌入视频, 返回嵌入状态和运行 trace。"""

    def detect(self, input_video_path, metadata):
        """检测视频中的 payload 或水印分数, 返回原始输出和统一分数。"""

    def evaluate(self, detection_output, payload_bits, threshold):
        """根据统一阈值协议生成 decision、BER、bit accuracy 等字段。"""
```

该接口的设计属于通用工程写法。它的主要作用是将外部方法差异隔离在 adapter 内部, 让主实验 runner 只处理统一输入输出。

## 7. 统一 records 字段

每条 baseline 记录至少应包含以下字段:

```json
{
  "workflow_key": "baseline_comparison_gate",
  "run_id": "baseline_comparison_formal_20260611T034500Z_abcdef0",
  "sample_id": "...",
  "split": "test",
  "method_name": "external_videoseal",
  "method_family": "external_video_watermark",
  "payload_length_bits": 128,
  "payload_digest": "...",
  "attack_name": "h264_crf_28",
  "attack_family": "compression",
  "attack_config_digest": "...",
  "baseline_score": 0.0,
  "baseline_raw_detector_output": {},
  "threshold": 0.0,
  "target_fpr": 0.001,
  "decision": "positive",
  "bit_accuracy": 0.0,
  "ber": 1.0,
  "quality_metrics": {},
  "temporal_metrics": {},
  "runtime_metrics": {},
  "baseline_trace": {},
  "failure_reason": null
}
```

关键说明:

1. `baseline_score` 是统一比较分数, 需要在 adapter 文档中说明从原始输出到统一分数的映射规则。
2. `baseline_raw_detector_output` 保存 baseline 原始检测结果, 便于复查。
3. `threshold` 必须来自 calibration split, 不能由 test split 更新。
4. `failure_reason` 为 `null` 表示该样本成功完成。若失败, 必须记录可分类原因, 不能静默丢弃。
5. `baseline_trace` 必须包含 source digest、model digest、adapter version、license 状态和 unsupported attack 原因。

## 8. 数据输入与 split 冻结

阶段三不得重新发明数据集处理逻辑, 应复用阶段二正式结果包。

### 8.1 输入包

默认输入为阶段二 canonical formal package:

```text
TSTW/results/real_video_vae_latent_probe_stage2_final_formal_audit/real_video_vae_latent_probe_formal_20260611T012845Z_2dbc783/
```

阶段三 runner 必须记录:

1. 输入包路径。
2. 输入包 archive digest。
3. 输入包 manifest digest。
4. 输入包 record count。
5. 输入包 split 分布。
6. 输入包质量指标可用性, 包括 LPIPS 和 CLIP similarity。

### 8.2 split 冻结规则

阶段三必须沿用阶段二的 split 语义:

1. `calibration`: 只用于阈值校准。
2. `test`: 只用于最终比较和投稿表格。
3. `dev`: 只用于 adapter 调试、smoke 和异常定位。

禁止在 `test` split 上调节:

1. 阈值。
2. score 映射规则。
3. baseline 超参数。
4. attack 强度。
5. 样本过滤规则。

## 9. 攻击矩阵

### 9.1 主实验攻击集合

正式主实验至少应包含:

1. `clean`: 无攻击。
2. `h264_crf_23`: H.264 轻度压缩。
3. `h264_crf_28`: H.264 中度压缩。
4. `h265_crf_28`: H.265 中度压缩。
5. `spatial_resize_0_75`: 空间缩放。
6. `spatial_center_crop_0_875`: 中心裁剪后恢复尺寸。
7. `spatial_random_crop_0_875`: 随机裁剪后恢复尺寸。
8. `temporal_crop`: 时间裁剪。
9. `local_clip`: 局部片段保留或局部片段替换。
10. `frame_drop`: 丢帧后恢复帧率。

### 9.2 可选扩展攻击

若运行预算允许, 可以加入:

1. `h264_crf_35`: H.264 强压缩。
2. `h265_crf_35`: H.265 强压缩。
3. `gaussian_blur`: 模糊。
4. `color_jitter`: 颜色扰动。
5. `speed_change`: 速度变化。
6. `frame_interpolation`: 插帧。

可选扩展攻击只能作为额外分析, 不应阻塞阶段三主 gate, 除非项目文档明确升级其为正式 gate 条件。

## 10. 质量指标

阶段三必须为每个成功样本记录以下质量指标:

1. `psnr`: 像素级失真指标。
2. `ssim`: 结构相似性指标。
3. `lpips`: 感知质量指标。
4. `clip_similarity`: 语义相似性指标。
5. `bitrate_kbps`: 视频码率。
6. `file_size_bytes`: 文件大小。
7. `frame_count`: 帧数。
8. `fps`: 帧率。
9. `resolution`: 分辨率。

若某 baseline 或攻击导致指标无法计算, 必须写入 `failure_reason` 或 `quality_metric_failure_reason`, 不能将缺失值当作成功值。

## 11. fixed-FPR 阈值校准

### 11.1 目标 FPR

建议至少使用:

```text
target_fpr = 0.001
```

如样本量允许, 可以额外报告:

```text
target_fpr = 0.0001
```

### 11.2 校准输入

每个方法的阈值必须只从 `calibration` split 的 negative 样本获得, negative 样本包括:

1. `clean_negative`
2. `attacked_negative`

### 11.3 校准输出

应输出:

```text
thresholds/baseline_threshold_table.csv
thresholds/baseline_threshold_manifest.json
```

字段至少包括:

1. `method_name`
2. `attack_name`
3. `target_fpr`
4. `threshold`
5. `num_calibration_negatives`
6. `empirical_fpr`
7. `score_direction`
8. `calibration_record_digest`

## 12. 主实验构建步骤

### 12.1 准备阶段

1. 确认当前分支为 `explicit-sync`。
2. 确认 `.codex/project_contract.md` 中 `project_stage` 为 `baseline_comparison_gate`。
3. 确认阶段二 canonical package 可读取并可解压。
4. 确认本地或 Colab 环境可以调用 `ffmpeg`。
5. 确认 LPIPS 和 CLIP similarity 依赖可安装或已缓存。
6. 确认 Google Drive 可写入最终结果目录。

### 12.2 baseline source intake

对每个 baseline 执行:

1. 记录上游仓库 URL。
2. 记录上游 commit hash。
3. 记录 license。
4. 记录权重来源。
5. 计算权重 digest。
6. 记录依赖版本。
7. 记录已知限制。
8. 记录本项目允许的复现修复范围。

输出文件:

```text
source_digest/external_videoseal_source_manifest.json
source_digest/external_rivagan_source_manifest.json
source_digest/external_hidden_framewise_source_manifest.json
reports/baseline_source_intake_report.md
```

### 12.3 baseline 拉取与复现修复

对每个 baseline 执行:

1. 拉取上游代码到隔离目录。
2. 固定 commit。
3. 安装依赖。
4. 下载或登记权重。
5. 修复导入错误、路径错误、Colab 文件系统错误和依赖版本冲突。
6. 将修复内容记录为 patch 或本项目 adapter 代码。
7. 编写最小 smoke 命令。
8. 生成 `README_TSTW.md`。

该步骤的通过标准是: 每个 baseline 可以在一个短视频上完成 embed 和 detect, 并写出统一 records。

### 12.4 adapter smoke

每个 baseline 先运行 smoke:

1. `dev` split 中选取少量样本。
2. 只运行 `clean` 和 `h264_crf_28`。
3. 每个样本使用固定 payload。
4. 检查输出视频是否存在。
5. 检查检测分数是否为数值。
6. 检查统一 records 字段是否完整。
7. 检查失败样本是否保留记录。

输出文件:

```text
records/baseline_smoke_records.jsonl
reports/baseline_smoke_report.md
```

### 12.5 calibration run

对每个方法运行 calibration:

1. 加载 `calibration` split。
2. 生成 negative 和 positive 记录。
3. 只使用 negative score 校准阈值。
4. 固定 `target_fpr`。
5. 写出 threshold table。
6. 锁定 score direction 和 score mapping rule。

输出文件:

```text
records/baseline_calibration_records.jsonl
thresholds/baseline_threshold_table.csv
thresholds/baseline_threshold_manifest.json
reports/baseline_calibration_report.md
```

### 12.6 formal test run

对每个方法、每个 test 样本、每个正式攻击运行:

1. 嵌入 payload。
2. 应用攻击。
3. 运行检测。
4. 按 calibration 阈值生成 decision。
5. 计算 BER、bit accuracy、TPR、FNR。
6. 计算 PSNR、SSIM、LPIPS、CLIP similarity。
7. 记录运行时间、显存或 GPU runtime trace。
8. 写出逐样本 records。

输出文件:

```text
records/baseline_test_records.jsonl
records/baseline_quality_records.jsonl
records/baseline_runtime_records.jsonl
reports/baseline_formal_run_report.md
```

## 13. 消融实验构建步骤

阶段三应同时为内部方法提供消融结果。建议消融集合如下:

1. `frame_prc`: 帧级基线。
2. `tubelet_only`: 只使用 tubelet, 不使用显式同步。
3. `tubelet_sync`: 完整显式同步方法。
4. `tubelet_sync_without_aligned_payload_safety`: 去除 aligned payload safety 协议的 ablation, 仅当现有代码支持且命名不作为正式方法名时使用。
5. `tubelet_sync_without_sync_rescue`: 去除 sync-rescue 判定逻辑的 ablation, 仅当现有代码支持且不会改变正式方法定义时使用。

注意:

1. `aligned_payload_safety` 应作为 `tubelet_sync` 的机制协议字段, 不应作为新的正式方法名。
2. 消融方法不得使用 `full`, `default`, `best`, `new`, `old` 等弱语义名称。
3. 消融必须复用同一 split、攻击矩阵、payload 和 fixed-FPR 阈值协议。

输出文件:

```text
records/ablation_test_records.jsonl
tables/ablation_summary_table.csv
tables/ablation_attack_breakdown.csv
reports/ablation_report.md
```

## 14. 投稿表格候选

阶段三至少应产出以下表格数据:

### 14.1 主比较表

```text
tables/baseline_comparison_table.csv
```

建议列:

1. `method_name`
2. `method_family`
3. `target_fpr`
4. `clean_tpr`
5. `h264_tpr`
6. `h265_tpr`
7. `spatial_attack_tpr`
8. `temporal_attack_tpr`
9. `local_clip_tpr`
10. `average_tpr`
11. `average_ber`
12. `average_lpips`
13. `average_clip_similarity`
14. `runtime_seconds_per_video`

### 14.2 攻击 breakdown 表

```text
tables/baseline_attack_breakdown.csv
```

每行对应一个 `method_name` 和 `attack_name`。

### 14.3 阈值表

```text
tables/baseline_threshold_table.csv
```

该表应能证明所有方法都在相同 `target_fpr` 协议下比较。

### 14.4 质量表

```text
tables/baseline_quality_table.csv
```

用于支撑“鲁棒性提升不是通过不可接受的视频质量退化获得”的 claim。

### 14.5 运行成本表

```text
tables/baseline_runtime_table.csv
```

用于报告各方法的嵌入时间、检测时间、总时间、显存或 GPU trace。

### 14.6 消融表

```text
tables/ablation_summary_table.csv
```

用于支撑显式同步机制的必要性。

## 15. 投稿图表候选

阶段三应至少产出图表数据, 图片可在阶段四重新排版。

建议输出:

```text
figures/baseline_robustness_by_attack.csv
figures/baseline_quality_robustness_tradeoff.csv
figures/fixed_fpr_detection_curves.csv
figures/ablation_sync_gain_by_attack.csv
figures/compression_robustness_curve.csv
figures/spatial_attack_robustness_curve.csv
figures/runtime_cost_breakdown.csv
```

对应图表含义:

1. `baseline_robustness_by_attack`: 展示不同方法在各攻击下的 TPR 或 bit accuracy。
2. `baseline_quality_robustness_tradeoff`: 展示质量指标与鲁棒性的关系。
3. `fixed_fpr_detection_curves`: 展示 fixed-FPR 校准下的检测曲线。
4. `ablation_sync_gain_by_attack`: 展示 `tubelet_sync` 相对 `tubelet_only` 的同步收益。
5. `compression_robustness_curve`: 展示 H.264 / H.265 不同强度下的性能变化。
6. `spatial_attack_robustness_curve`: 展示 resize、crop 等空间攻击结果。
7. `runtime_cost_breakdown`: 展示嵌入、攻击、检测、质量指标计算的运行成本。

## 16. claim audit

每个实验 claim 必须映射到具体 artifacts。建议 claim audit 表如下:

```text
claim_audit/baseline_claim_audit.csv
claim_audit/baseline_claim_audit.md
```

字段至少包括:

1. `claim_id`
2. `claim_text`
3. `claim_type`
4. `supported_by_records`
5. `supported_by_tables`
6. `supported_by_figures`
7. `required_thresholds`
8. `required_quality_metrics`
9. `audit_decision`
10. `blocking_reason`

示例 claim:

1. `tubelet_sync` 在 temporal crop 或 local clip 下优于 `tubelet_only`。
2. `tubelet_sync` 在相同 fixed-FPR 协议下优于三个外部 baseline 的平均鲁棒性。
3. `tubelet_sync` 的鲁棒性提升没有依赖明显质量退化。
4. H.264 / H.265 重编码下, 内部方法保持可检测性。
5. `external_hidden_framewise` 在时间攻击下受限, 该限制与其 frame-wise 方法族一致。

任何未被 records、thresholds、tables 或 figures 支撑的 claim 都必须标记为 `unsupported`。

## 17. gate 通过条件

`baseline_comparison_gate` 通过至少需要满足以下条件:

1. 三个 baseline 都完成 source intake。
2. 三个 baseline 都有 license、source digest、adapter version 和 model digest 记录。若某 baseline 无公开权重或不可运行, 必须进入 limitation report, 不得参与优势 claim。
3. 三个 baseline 都完成 smoke。若失败, 必须有可复现失败记录。
4. 至少一个正式 target FPR 完成 calibration。
5. calibration 和 test split 没有混用。
6. 主实验 records 可以重建所有正式表格。
7. H.264、H.265、空间攻击、时间攻击和 local clip 至少覆盖主实验方法集合。
8. LPIPS 和 CLIP similarity 对成功样本可计算, 缺失样本有明确失败原因。
9. `baseline_comparison_table.csv`、`baseline_attack_breakdown.csv`、`baseline_threshold_table.csv`、`baseline_quality_table.csv`、`baseline_runtime_table.csv`、`ablation_summary_table.csv` 全部存在且由 records 重建。
10. claim audit 中所有准备进入论文的 claim 均为 `supported`。
11. 完整结果包成功落盘到 Google Drive。
12. 本地或 CI 的 `pytest` 和 `tools/harness/run_all_audits.py` 通过。

## 18. 建议执行顺序

### 18.1 最小可行顺序

1. 建立 baseline source intake 配置。
2. 拉取并隔离三个 baseline。
3. 为每个 baseline 写 adapter skeleton。
4. 完成单视频 `clean` smoke。
5. 完成单视频 `h264_crf_28` smoke。
6. 完成统一 records schema 检查。
7. 完成 calibration runner。
8. 完成 formal test runner。
9. 完成 table builder。
10. 完成 claim audit builder。
11. 完成 Google Drive package materialization。

### 18.2 推荐工程提交批次

第一批提交: 文档和契约。

1. 本文档。
2. baseline source manifest schema。
3. records 字段注册。
4. gate 检查项。

第二批提交: baseline intake 和 adapter skeleton。

1. `external_videoseal` adapter skeleton。
2. `external_rivagan` adapter skeleton。
3. `external_hidden_framewise` adapter skeleton。
4. smoke tests。

第三批提交: 攻击和质量链路。

1. H.264 / H.265 wrapper。
2. 空间攻击 wrapper。
3. 时间攻击 wrapper。
4. LPIPS / CLIP similarity 指标复用。

第四批提交: calibration 和 formal runner。

1. calibration records。
2. threshold builder。
3. test runner。
4. package builder。

第五批提交: 表格、图表和 claim audit。

1. 主表。
2. breakdown 表。
3. 消融表。
4. 图表数据。
5. claim audit。

## 19. 风险与降级策略

### 19.1 baseline 无法运行

处理方式:

1. 保留 source intake。
2. 保留失败日志。
3. 保留 environment report。
4. 写入 `baseline_limitation_report.md`。
5. 不将该 baseline 用于优势 claim。

### 19.2 baseline 不支持 payload 解码

处理方式:

1. 明确 score 映射规则。
2. 若只能输出 presence score, 则只比较 detection TPR/FPR, 不比较 BER。
3. 在表格中将 BER 标记为 not applicable, 并在 limitation report 中解释。

### 19.3 baseline 不支持某类攻击

处理方式:

1. 不删除该行。
2. 写入 records, `decision` 标记为 `unsupported` 或 `failed`。
3. 在 attack breakdown 表中显示 unsupported 计数。
4. 不用该攻击下的缺失结果支撑优势 claim。

### 19.4 Colab 运行中断

处理方式:

1. session-local 中间结果可以用于调试, 但不能作为正式结果。
2. 只有完整 package check 通过后才能写入 Google Drive 正式目录。
3. 如果需要断点续跑, 必须从已完成的正式包恢复, 并生成新的 `RUN_ID`。

## 20. 阶段三完成后交付物清单

阶段三结束时, 应至少交付:

```text
manifest.json
configs/baseline_comparison_config.json
source_digest/*_source_manifest.json
records/baseline_calibration_records.jsonl
records/baseline_test_records.jsonl
records/ablation_test_records.jsonl
thresholds/baseline_threshold_table.csv
tables/baseline_comparison_table.csv
tables/baseline_attack_breakdown.csv
tables/baseline_threshold_table.csv
tables/baseline_quality_table.csv
tables/baseline_runtime_table.csv
tables/ablation_summary_table.csv
figures/baseline_robustness_by_attack.csv
figures/baseline_quality_robustness_tradeoff.csv
figures/fixed_fpr_detection_curves.csv
figures/ablation_sync_gain_by_attack.csv
reports/baseline_source_intake_report.md
reports/baseline_smoke_report.md
reports/baseline_calibration_report.md
reports/baseline_formal_run_report.md
reports/baseline_limitation_report.md
claim_audit/baseline_claim_audit.csv
claim_audit/baseline_claim_audit.md
environment/colab_environment.json
environment/python_packages.txt
environment/ffmpeg_version.txt
environment/git_state.json
archives/baseline_comparison_formal.zip
```

这些交付物构成 `paper_artifact_gate` 的输入。阶段四不应重新运行 baseline 主实验, 而应从这些 records、tables、figures 和 claim audit 中生成论文图表、论文表格、补充材料和复现说明。

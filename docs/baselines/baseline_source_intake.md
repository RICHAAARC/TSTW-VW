# baseline source intake

本文档记录 `baseline_comparison_gate` 当前固定的三个外部 baseline 的来源审计状态。该文档只记录来源、license、权重和 adapter 准备状态, 不记录任何正式实验结论。

## 1. 固定 baseline

| baseline_name | baseline_family | source manifest | 当前状态 |
| --- | --- | --- | --- |
| `external_videoseal` | `external_video_watermark` | `configs/baselines/external_videoseal_source.json` | 已提供真实 smoke adapter 入口, 等待 Colab 权重下载和真实 smoke 验证 |
| `external_rivagan` | `external_video_watermark` | `configs/baselines/external_rivagan_source.json` | 已提供真实 smoke adapter 入口, 等待 Colab 权重下载和真实 smoke 验证 |
| `external_hidden_framewise` | `external_image_watermark_framewise` | `configs/baselines/external_hidden_framewise_source.json` | 已提供逐帧真实 smoke adapter 入口, 等待 Colab 真实 smoke 验证 |

## 2. 审计原则

1. 每个 baseline 必须有 `upstream_repository_url` 和完整 40 位 `upstream_commit`。
2. 每个 baseline 必须记录 license 名称和 license URL。
3. 每个 baseline 必须记录模型权重来源和 `weight_digest_status`。
4. 在 `weight_digest_status` 仍为 `pending_colab_download` 时, 该 baseline 不能支撑正式优势 claim。
5. 在 `adapter_status` 仍为 `adapter_skeleton_only` 时, 该 baseline 只能用于工程准备, 不能用于正式实验表格。
6. `external_hidden_framewise` 必须在报告中声明为图像水印逐帧迁移 baseline, 不能描述为原生视频水印方法。

## 3. 复现修复边界

允许的修复包括:

1. 依赖版本固定。
2. 导入路径修复。
3. Colab 路径适配。
4. 视频读写封装。
5. 统一 adapter 封装。
6. 日志、digest、manifest 和 records 输出。

禁止的修改包括:

1. 改变核心嵌入算法语义。
2. 改变检测分数定义以提高结果。
3. 在 test split 上调节阈值。
4. 删除失败样本。
5. 将 unsupported attack 静默排除在平均值之外。

## 4. 下一步

下一步应先完成本地不依赖 GPU 的 adapter skeleton 和 record schema gate, 然后在 Colab 中执行以下 smoke:

1. 拉取上游代码。
2. 安装依赖。
3. 下载权重并计算 digest。
4. 单视频 `clean` embed / detect。
5. 单视频 `h264_crf_28` embed / attack / detect。
6. 写出统一 `records/baseline_smoke_records.jsonl`。
7. 将完整 smoke 包落盘到 Google Drive。

## 5. 当前本地推进状态

截至当前构建, 本地已完成以下非 GPU 步骤:

1. 三个 baseline 的 source manifest 已登记。
2. 三个 baseline 的上游源码已可通过 `scripts/prepare_baselines/fetch_external_baselines.py` 拉取到 `external_baselines/`。
3. `external_baselines/` 已加入 `.gitignore`, 上游源码不作为本项目正式提交内容。
4. 本地 adapter skeleton smoke 可生成阻断型 records、manifest 和 limitation report。
5. Colab preflight 可检查上游 commit、权重 digest 状态、adapter 状态和阶段二输入包契约。
6. source probe 已确认三个上游源码树包含预期入口线索。

本地命令如下:

```bash
python scripts/prepare_baselines/fetch_external_baselines.py --print-plan
python scripts/prepare_baselines/probe_external_baseline_sources.py
python scripts/prepare_baselines/check_baseline_colab_preflight.py
python scripts/prepare_baselines/run_baseline_comparison_smoke.py --run-root <temporary_run_root> --result-root <drive_result_root>
```

这些命令仍不构成正式 baseline 实验。正式比较前仍需要 Colab 完成:

1. 权重下载。
2. 权重 digest。
3. 单视频真实 embed / detect smoke。
4. H.264 轻量攻击 smoke。
5. Google Drive 结果包落盘。

## 6. Colab 冷启动结果落盘规则

对于 `baseline_comparison_gate` 的 smoke 验证, 推荐使用如下两层路径:

```text
会话本地运行目录: /content/TSTW_runtime/runs/<RUN_ID>/
Drive 结果根目录: /content/drive/MyDrive/TSTW/results/
最终结果目录: /content/drive/MyDrive/TSTW/results/baseline_comparison_gate/<RUN_ID>/
```

`run_baseline_comparison_smoke.py` 的 `--result-root` 参数只会在 smoke 运行成功并且本地目录中已经存在 `manifest.json`、`records/baseline_smoke_records.jsonl` 和 `reports/baseline_limitation_report.md` 后复制结果。该设计属于通用工程写法, 主要目的是避免 Colab 运行失败时先在 Google Drive 中创建空目录。

当前 smoke 仍然是 adapter skeleton 验证, 不代表真实外部 baseline 已完成。真实比较仍需后续把三个 adapter 升级为可运行版本, 并在 Colab 中完成权重 digest、单视频 embed / detect、攻击后 detect 和结果包审计。

## 7. external_videoseal 真实 smoke 入口

当前已经补充 `external_videoseal` 的真实 smoke adapter 与命令行入口:

```bash
python scripts/prepare_baselines/run_videoseal_real_smoke.py \
  --run-root /content/TSTW_runtime/runs/external_videoseal_real_smoke \
  --result-root /content/drive/MyDrive/TSTW/results
```

该入口会在 Colab 中完成以下工作:

1. 从 `external_baselines/external_videoseal/upstream` 动态导入上游 VideoSeal。
2. 调用 `videoseal.load("videoseal")` 下载并加载官方权重。
3. 计算实际权重文件的 SHA-256 digest。
4. 生成或读取一个单视频 smoke 输入。
5. 执行 clean embed / detect。
6. 执行 H.264 CRF 28 攻击后 detect。
7. 写出 `records/external_videoseal_real_smoke_records.jsonl`、`manifest.json` 与 `reports/external_videoseal_real_smoke_report.md`。

该结果仍然只表示 `external_videoseal` 单 baseline 可运行性 smoke, 不支持正式论文 claim。进入投稿级比较前, 仍需统一 split、统一攻击矩阵、calibration-only fixed-FPR 阈值、全量表格重建与 claim audit。

### external_videoseal 路径修复记录

在 Colab 真实 smoke 中, VideoSeal 权重可以下载成功, 但上游代码会尝试读取 `videoseal/configs/attenuation.yaml`。当前固定 commit 的仓库实际配置目录是上游根目录 `configs/`, 因此会触发 `FileNotFoundError`。本项目已在 `ExternalVideoSealAdapter.prepare()` 中加入 `ensure_videoseal_package_config_paths()`:

1. 检查 `external_baselines/external_videoseal/upstream/configs/` 是否存在。
2. 将 `attenuation.yaml`、`embedder.yaml`、`extractor.yaml` 复制到 `external_baselines/external_videoseal/upstream/videoseal/configs/`。
3. 仅修复上游包内配置查找路径, 不修改权重、模型结构、嵌入算法或检测分数定义。

该修复属于允许的复现路径修复, 不是方法语义修改。

## 8. external_rivagan 真实 smoke 入口

当前已经补充 `external_rivagan` 的真实 smoke adapter 与命令行入口:

```bash
python scripts/prepare_baselines/run_rivagan_real_smoke.py \
  --run-root /content/TSTW_runtime/runs/external_rivagan_real_smoke \
  --result-root /content/drive/MyDrive/TSTW/results
```

该入口会在 Colab 中完成以下工作:

1. 从 `external_baselines/external_rivagan/upstream` 动态导入 DAI-Lab RivaGAN 上游实现。
2. 下载公开的 32-bit RivaGAN checkpoint, 并计算权重 SHA-256 digest。
3. 为该 checkpoint 注册 PyTorch 反序列化兼容类名。
4. 生成或读取一个单视频 smoke 输入。
5. 执行 clean encode / decode。
6. 执行 H.264 CRF 28 攻击后 decode。
7. 写出 `records/external_rivagan_real_smoke_records.jsonl`、`manifest.json` 与 `reports/external_rivagan_real_smoke_report.md`。

该结果仍然只表示 `external_rivagan` 单 baseline 可运行性 smoke, 不支持正式论文 claim。由于 DAI-Lab 官方仓库未随源码提供正式 checkpoint, 当前权重来源必须在 limitation report 和 claim audit 中显式标注。

## 9. external_hidden_framewise 真实 smoke 入口

当前已经补充 `external_hidden_framewise` 的逐帧真实 smoke adapter 与命令行入口:

```bash
python scripts/prepare_baselines/run_hidden_framewise_real_smoke.py \
  --run-root /content/TSTW_runtime/runs/external_hidden_framewise_real_smoke \
  --result-root /content/drive/MyDrive/TSTW/results
```

该入口会完成以下工作:

1. 从 `external_baselines/external_hidden_framewise/upstream` 动态导入 HiDDeN 上游实现。
2. 使用上游 `experiments/combined-noise/options-and-config.pickle` 和 `checkpoints/combined-noise--epoch-400.pyt`。
3. 计算 checkpoint 的 SHA-256 digest。
4. 生成或读取一个单视频 smoke 输入。
5. 对每一帧独立执行同一 payload 的 encode / decode。
6. 执行 H.264 CRF 28 攻击后逐帧 decode。
7. 写出 `records/external_hidden_framewise_real_smoke_records.jsonl`、`manifest.json` 与 `reports/external_hidden_framewise_real_smoke_report.md`。

该结果仍然只表示 `external_hidden_framewise` 单 baseline 可运行性 smoke, 不支持正式论文 claim。该 baseline 必须在报告中明确标注为图像水印逐帧迁移 baseline, 不能描述为原生视频水印方法。

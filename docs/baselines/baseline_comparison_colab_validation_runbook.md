# baseline comparison Colab validation runbook

本文档给出 `baseline_comparison_gate` 在 Colab 冷启动环境中的验证步骤。该流程的目标不是产出正式论文主表, 而是验证阶段三的外部 baseline 来源拉取、源码探测、preflight、真实单视频 smoke、结果包汇总和 Google Drive 落盘链路是否可执行。

## 1. 当前边界

当前阶段已经具备以下能力:

1. 三个外部 baseline 的 source manifest 已固定: `external_videoseal`、`external_rivagan`、`external_hidden_framewise`。
2. 上游源码可按固定 commit 拉取到 `external_baselines/`。该目录是冷启动缓存, 被 `.gitignore` 排除是合理的。
3. `external_videoseal` 真实 smoke adapter 可下载权重、计算 model digest、执行 clean 与 H.264 CRF 28 检测。
4. `external_rivagan` 真实 smoke adapter 可下载社区公开 32-bit checkpoint、计算 model digest、执行 clean 与 H.264 CRF 28 解码。
5. `external_hidden_framewise` 真实 smoke adapter 可加载 HiDDeN combined-noise checkpoint, 对视频帧逐帧执行 clean 与 H.264 CRF 28 解码。
6. `summarize_baseline_real_smoke.py` 可读取三个真实 smoke 结果包, 生成 JSON、CSV 和 Markdown 摘要。

这些结果仍然只是工程可运行性 smoke。它们不能替代正式 fixed-FPR baseline comparison, 也不能直接支持论文 superiority claim。

## 2. Colab notebook 入口

推荐直接运行:

```text
paper_workflow/run_baseline_comparison_gate.ipynb
```

该 Notebook 只负责会话编排。正式逻辑由 `scripts/prepare_baselines/` 与 `experiments/baseline_comparison_gate/` 中的仓库模块执行。

## 3. 冷启动命令等价流程

在 Colab 中挂载 Google Drive 后, Notebook 等价执行以下命令:

```bash
cd /content
git clone <REPO_URL> TSTW-VW
cd /content/TSTW-VW
git checkout explicit-sync
python scripts/prepare_baselines/fetch_external_baselines.py --print-plan
python scripts/prepare_baselines/probe_external_baseline_sources.py
python scripts/prepare_baselines/check_baseline_colab_preflight.py
python scripts/prepare_baselines/run_baseline_comparison_smoke.py   --run-root /content/TSTW_runtime/runs/baseline_comparison_smoke   --result-root /content/drive/MyDrive/TSTW/results
python scripts/prepare_baselines/run_videoseal_real_smoke.py   --run-root /content/TSTW_runtime/runs/external_videoseal_real_smoke   --result-root /content/drive/MyDrive/TSTW/results
python scripts/prepare_baselines/run_rivagan_real_smoke.py   --run-root /content/TSTW_runtime/runs/external_rivagan_real_smoke   --result-root /content/drive/MyDrive/TSTW/results
python scripts/prepare_baselines/run_hidden_framewise_real_smoke.py   --run-root /content/TSTW_runtime/runs/external_hidden_framewise_real_smoke   --result-root /content/drive/MyDrive/TSTW/results
python scripts/prepare_baselines/summarize_baseline_real_smoke.py   --result-root /content/drive/MyDrive/TSTW/results   --output-dir /content/drive/MyDrive/TSTW/results/baseline_comparison_gate/baseline_real_smoke_summary_latest
```

## 4. 预期输出

真实 smoke 成功后, Drive 中应出现以下目录:

```text
/content/drive/MyDrive/TSTW/results/baseline_comparison_gate/external_videoseal_real_smoke_<UTC_TIME>_<SHORT_COMMIT>/
/content/drive/MyDrive/TSTW/results/baseline_comparison_gate/external_rivagan_real_smoke_<UTC_TIME>_<SHORT_COMMIT>/
/content/drive/MyDrive/TSTW/results/baseline_comparison_gate/external_hidden_framewise_real_smoke_<UTC_TIME>_<SHORT_COMMIT>/
```

每个真实 smoke 结果包至少包含:

```text
manifest.json
records/<baseline_name>_real_smoke_records.jsonl
reports/<baseline_name>_real_smoke_report.md
```

汇总步骤会生成:

```text
baseline_real_smoke_summary.json
baseline_real_smoke_summary.csv
baseline_real_smoke_summary.md
```

## 5. 判定标准

真实 smoke 汇总的最低通过条件是:

1. 三个 baseline 均存在最新真实 smoke 结果包。
2. 每个结果包的 `schema_pass` 为 `true`。
3. 每个结果包的 `records_digest_match` 为 `true`。
4. 每个结果包的 `record_count_match` 为 `true`。
5. 汇总字段 `package_ready_for_formal_planning` 为 `true`。

`all_real_smoke_scores_positive` 不要求必须为 `true`。例如 `external_hidden_framewise` 是图像水印逐帧迁移 baseline, 若其 clean/H.264 smoke 低于阈值, 应记录为 `real_smoke_executed_negative`, 并进入 limitation。

## 6. 不能支持的结论

真实 smoke 包不能用于论文正式 claim。原因是:

1. 它只覆盖单视频或极小样本 smoke。
2. 它没有使用 calibration split 固定 FPR 阈值。
3. 它没有覆盖完整攻击矩阵。
4. 它没有生成正式 `baseline_comparison_table.csv`、`baseline_attack_breakdown.csv`、`baseline_threshold_table.csv`、`baseline_runtime_table.csv` 和 claim audit。

## 7. 下一步正式 baseline comparison 工作

完成三个真实 smoke 后, 下一步应构建正式 comparison runner:

1. 读取阶段二正式 real-video VAE 结果包与 processed dataset 身份。
2. 为内部 `tubelet_sync` 与三个外部 baseline 使用同一 split、同一 payload 规则和同一 attack matrix。
3. 在 calibration split 上为每个方法计算 fixed-FPR 阈值。
4. 在 test split 上冻结 records, 不允许更新阈值或选择规则。
5. 生成 baseline comparison 主表、攻击分解表、阈值表、运行时表和 limitation report。
6. 更新 claim audit, 只允许 fixed-FPR 正式结果支撑投稿级 claim。

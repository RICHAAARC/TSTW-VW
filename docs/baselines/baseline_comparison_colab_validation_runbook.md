# baseline comparison Colab validation runbook

本文档给出 `baseline_comparison_gate` 在 Colab 冷启动环境中的最小验证步骤。该流程的目标不是产出正式论文主表, 而是验证阶段三的外部 baseline 来源拉取、源码探测、preflight、adapter skeleton smoke 和 Google Drive 落盘链路是否可执行。

## 1. 当前边界

当前本地已经完成以下不依赖 GPU 的构建:

1. 三个外部 baseline 的 source manifest 固定。
2. 上游源码可拉取到 `external_baselines/`。
3. 上游源码入口线索可通过 source probe 检查。
4. adapter skeleton 可以产出阻断型 records、manifest 和 limitation report。
5. Colab preflight 可以明确指出真实权重、真实 adapter 和 GPU smoke 尚未完成。

因此, 当前已经到达需要 Colab 验证的位置。继续向正式 baseline comparison 推进时, 需要在 Colab 中完成依赖安装、权重下载、权重 digest 和真实单视频 smoke。

## 2. Colab 冷启动命令

在 Colab 中挂载 Google Drive 后执行以下命令。`<REPO_URL>` 需要替换为当前项目仓库地址。

```bash
cd /content
git clone <REPO_URL> TSTW-VW
cd /content/TSTW-VW
python scripts/prepare_baselines/fetch_external_baselines.py --print-plan
python scripts/prepare_baselines/probe_external_baseline_sources.py
python scripts/prepare_baselines/check_baseline_colab_preflight.py
python scripts/prepare_baselines/run_baseline_comparison_smoke.py   --run-root /content/TSTW_runtime/runs/baseline_comparison_smoke   --result-root /content/drive/MyDrive/TSTW/results
```

## 3. 预期输出

上述 smoke 命令成功后, 应出现如下目录:

```text
/content/drive/MyDrive/TSTW/results/baseline_comparison_gate/<RUN_ID>/
```

其中 `<RUN_ID>` 形如:

```text
baseline_comparison_smoke_<UTC_TIME>_<SHORT_COMMIT>
```

该目录至少应包含:

```text
manifest.json
records/baseline_smoke_records.jsonl
reports/baseline_limitation_report.md
configs/baseline_source_intake_summary.json
```

## 4. 判定标准

本次 Colab 验证通过的最低标准如下:

1. 三个上游源码 checkout 到配置中固定的 commit。
2. `probe_external_baseline_sources.py` 返回 `probe_status = pass`。
3. `check_baseline_colab_preflight.py` 能明确列出真实权重和真实 adapter 的阻断项。
4. `run_baseline_comparison_smoke.py` 成功写出三条 baseline skeleton record。
5. Drive 中只在 smoke 成功后出现完整结果目录, 不应出现提前创建的空目录。

## 5. 不能支持的结论

该 smoke 包不能用于论文 claim。原因是当前 adapter 仍为 skeleton, `baseline_score` 为空, `decision` 为失败状态, 且 `claim_support_allowed = false`。它只能证明阶段三的工程入口、记录 schema 和冷启动落盘链路可用。

## 6. 下一步真实 baseline 工作

Colab smoke 验证后, 应按以下顺序继续:

1. 先实现 `external_videoseal` 的真实 adapter 和权重 digest 流程。
2. 再实现 `external_rivagan` 的真实 adapter 和权重 digest 流程。
3. 最后实现 `external_hidden_framewise` 的逐帧 adapter, 并在报告中明确其不是原生视频水印方法。
4. 每个 baseline 都需要完成 clean、H.264/H.265、空间攻击和时间攻击下的对齐 records。
5. 三个 baseline 均通过固定 FPR 校准后, 才能进入正式 `baseline_comparison_table.csv`、攻击分解表和 claim audit 构建。

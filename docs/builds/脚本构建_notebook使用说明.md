# 脚本构建与 Notebook 使用说明

## 一、文档定位

本文档用于指导 Codex 在当前项目中新增 Colab 运行统计辅助能力，并将其接入 `paper_workflow/run_real_video_vae_latent_probe.ipynb`。本文档不修改水印算法、不修改阶段 2 判决口径、不替代 `docs/file_organization.md`、`docs/notebook_construction_governance.md`、`docs/naming_governance.md` 或阶段 2 formal 构建文档。

本次变更目标是：在不污染 `main/` 核心方法包的前提下，为 Colab 真实运行提供运行时间统计、GPU 利用率统计、环境快照、运行进度监控、失败摘要与下一轮参数建议，便于判断阶段 2 formal run 是否真正使用 GPU、运行时间如何分布、瓶颈位于 VAE、视频攻击、质量指标、Drive IO 还是结果打包。

本次变更必须遵守如下边界：

```text
1. 不修改水印方法核心算法；
2. 不修改 threshold、target_fpr、evidence_scores、decision 或 formal checker 的判定语义；
3. 不把 Colab 运行统计脚本放入 main/；
4. 不把 notebook 专用 wrapper 放入 scripts/；
5. 不把 Google Drive 固定路径写入 main/；
6. 不新增包含 stage2、stage_2、v1、p2、final、latest 等弱语义的文件名、函数名或配置键；
7. 所有新增文件名、Python 模块名、测试文件名必须使用 snake_case；
8. 所有新增输出必须写入 run_root/runtime_profile/ 或 run_root/reports/，不得写入 records/、thresholds/、tables/ 的正式结果语义目录；
9. 新增 profiler 失败不得影响核心 runner 的正式结果生成，但 formal notebook 可以在 profiler 初始化失败时记录 warning；
10. profiler 输出必须被 packager 纳入结果包，作为运行辅助证据。
```

---

## 二、当前仓库边界与新增文件位置

当前项目已经形成如下职责边界：

```text
main/：核心方法、视频 IO、VAE、攻击、协议、指标与 CLI；
experiments/：阶段性机制验证 runner 与 artifact builder；
paper_workflow/：Colab notebook 与 notebook-specific helper；
scripts/：数据准备、模型准备、结果检查、结果打包等命令行辅助工具；
docs/：治理契约与构建说明；
tests/：约束、功能与集成测试。
```

本次新增文件必须进入以下位置：

```text
scripts/profile_runtime/
├── __init__.py
├── capture_colab_environment.py
├── profile_gpu_runtime.py
├── summarize_gpu_profile.py
├── profile_run_timing.py
├── summarize_run_timing.py
├── estimate_real_video_vae_latent_run_scale.py
├── watch_real_video_vae_latent_progress.py
├── profile_drive_io.py
└── recommend_runtime_parameters.py

scripts/check_results/
└── summarize_run_failures.py

paper_workflow/notebook_utils/
├── runtime_profile_workflow.py
└── run_timing_workflow.py

tests/functional/
├── test_runtime_environment_snapshot.py
├── test_run_timing_profiler.py
├── test_gpu_runtime_profiler.py
├── test_real_video_vae_latent_run_scale_estimator.py
├── test_real_video_vae_latent_progress_watcher.py
├── test_runtime_parameter_recommendation.py
└── test_run_failure_summary.py

tests/constraints/
└── test_runtime_profile_file_organization.py
```

不得新增：

```text
main/colab/*
main/runtime_profile/*
main/profiling/*
main/gpu_monitor.py
paper_workflow/gpu_profile.py
scripts/stage2_*.py
scripts/*_v1.py
scripts/*_p2.py
```

---

## 三、输出目录契约

所有运行统计产物统一写入：

```text
<run_root>/runtime_profile/
```

推荐完整结构为：

```text
outputs/runs/<run_id>/runtime_profile/
├── colab_environment_snapshot.json
├── drive_io_profile.json
├── gpu_runtime_trace.csv
├── gpu_runtime_summary.json
├── gpu_runtime_report.md
├── run_timing_events.jsonl
├── run_timing_summary.json
├── run_timing_report.md
├── run_scale_estimate.json
├── run_progress_snapshot.json
├── run_failure_summary.json
├── run_failure_summary.md
└── runtime_parameter_recommendation.json
```

其中：

```text
colab_environment_snapshot.json：记录环境与依赖；
drive_io_profile.json：记录 Drive 与 session local IO 性能；
gpu_runtime_trace.csv：记录逐时间点 GPU / CPU / RAM 曲线；
gpu_runtime_summary.json：聚合 GPU 利用率与显存峰值；
gpu_runtime_report.md：面向人工阅读的 GPU 使用报告；
run_timing_events.jsonl：记录阶段级运行时间事件；
run_timing_summary.json：聚合阶段耗时；
run_timing_report.md：面向人工阅读的运行时间报告；
run_scale_estimate.json：运行前规模估算；
run_progress_snapshot.json：运行中或运行后进度快照；
run_failure_summary.json：机器可读失败摘要；
run_failure_summary.md：人工可读失败报告；
runtime_parameter_recommendation.json：下一轮 batch、GPU 与 profile 建议。
```

这些文件不得被 TableBuilder 当作论文指标输入，也不得参与 threshold、decision 或 evidence score 计算。

---

## 四、必须实现的脚本

### （一）`scripts/profile_runtime/capture_colab_environment.py`

#### 1. 职责

记录当前 Colab 或本地运行环境，输出 `colab_environment_snapshot.json`。该脚本应可在 Colab、本地 Linux、Windows 环境中执行。若某项工具不可用，应写入 `available: false`，不得直接崩溃，除非 CLI 显式设置 `--fail-on-missing-required`。

#### 2. CLI 形式

```bash
python -m scripts.profile_runtime.capture_colab_environment \
  --run-root <run_root> \
  --run-id <run_id> \
  --run-mode formal \
  --runtime-profile formal \
  --output-json <run_root>/runtime_profile/colab_environment_snapshot.json
```

#### 3. 输出字段

至少包含：

```json
{
  "run_id": "string",
  "run_mode": "formal",
  "runtime_profile": "formal",
  "timestamp_utc": "ISO-8601",
  "python_version": "string",
  "platform": "string",
  "working_directory": "string",
  "torch_imported": true,
  "torch_version": "string",
  "cuda_available": true,
  "cuda_device_count": 1,
  "gpu_name": "NVIDIA L4",
  "gpu_memory_mb": 23034,
  "nvidia_smi_available": true,
  "ffmpeg_available": true,
  "ffmpeg_version": "string",
  "tar_zstd_available": true,
  "dependency_imports": {
    "diffusers": true,
    "lpips": true,
    "cv2": true,
    "skimage": true,
    "imageio": true,
    "numpy": true,
    "pandas": true
  },
  "dependency_versions": {
    "diffusers": "string",
    "lpips": "string",
    "cv2": "string",
    "skimage": "string",
    "imageio": "string",
    "numpy": "string",
    "pandas": "string"
  },
  "disk_free_gb": 0.0,
  "ram_total_gb": 0.0,
  "ram_available_gb": 0.0,
  "git_commit": "string|null",
  "git_status_short": "string"
}
```

#### 4. 实现要求

```text
1. 使用标准库与 subprocess；
2. 可选导入 torch、psutil、importlib.metadata；
3. 如果 psutil 不存在，RAM / CPU 字段写 null 或 unavailable；
4. 不得依赖 google.colab API；
5. 不得硬编码 Google Drive 路径；
6. 不得向 main/ 写入任何文件。
```

---

### （二）`scripts/profile_runtime/profile_gpu_runtime.py`

#### 1. 职责

启动一个可在 notebook 中作为后台进程运行的 GPU 采样器，周期性调用 `nvidia-smi`，输出 `gpu_runtime_trace.csv`。

#### 2. CLI 形式

```bash
python -m scripts.profile_runtime.profile_gpu_runtime \
  --run-root <run_root> \
  --interval-seconds 2 \
  --output-csv <run_root>/runtime_profile/gpu_runtime_trace.csv \
  --stop-file <run_root>/runtime_profile/gpu_profile_stop.flag
```

#### 3. 输出字段

`gpu_runtime_trace.csv` 至少包含：

```text
timestamp_utc,elapsed_seconds,event_tag,gpu_index,gpu_name,gpu_util_percent,memory_used_mb,memory_total_mb,memory_util_percent,power_draw_w,temperature_c,cpu_percent,ram_used_gb,ram_total_gb
```

其中 `event_tag` 初始可写为 `unlabeled`。后续如果实现事件标记，可由 notebook wrapper 写入当前状态文件：

```text
<run_root>/runtime_profile/current_runtime_event_tag.txt
```

profiler 每次采样时读取该文件，并写入 `event_tag`。

#### 4. 停止机制

后台采样器必须支持 stop file：

```text
如果 stop-file 存在，则写完最后一行后退出。
```

Notebook wrapper 通过创建 stop file 停止采样器。

#### 5. 实现要求

```text
1. 如果 nvidia-smi 不存在，不得崩溃，应写入只有 header 和 unavailable 标记的 CSV；
2. 如果 nvidia-smi 单次采样失败，应写入 failure row 并继续尝试；
3. 采样循环必须 flush 文件，避免 Colab 中断导致 trace 丢失；
4. 不得直接 import torch 作为唯一 GPU 信息来源；
5. 必须支持 Ctrl-C 或 KeyboardInterrupt 安全退出；
6. 默认 interval_seconds 为 2。
```

---

### （三）`scripts/profile_runtime/summarize_gpu_profile.py`

#### 1. 职责

读取 `gpu_runtime_trace.csv`，生成：

```text
gpu_runtime_summary.json
gpu_runtime_report.md
```

#### 2. CLI 形式

```bash
python -m scripts.profile_runtime.summarize_gpu_profile \
  --run-root <run_root> \
  --trace-csv <run_root>/runtime_profile/gpu_runtime_trace.csv \
  --output-json <run_root>/runtime_profile/gpu_runtime_summary.json \
  --output-md <run_root>/runtime_profile/gpu_runtime_report.md
```

#### 3. 汇总字段

至少包含：

```json
{
  "trace_available": true,
  "sample_count": 100,
  "gpu_name": "NVIDIA L4",
  "total_memory_mb": 23034,
  "peak_memory_used_mb": 12000,
  "peak_memory_ratio": 0.52,
  "mean_gpu_util_percent": 65.3,
  "median_gpu_util_percent": 72.0,
  "low_utilization_ratio": 0.21,
  "mean_memory_util_percent": 51.8,
  "peak_power_draw_w": 68.2,
  "peak_temperature_c": 71.0,
  "total_profile_seconds": 5321.4,
  "estimated_gpu_usage_status": "moderate_utilization",
  "recommended_batch_size_direction": "increase_or_keep"
}
```

#### 4. 推荐规则

```text
peak_memory_ratio < 0.45 且 mean_gpu_util_percent < 50：建议增大 batch_size_frames 或检查 CPU / IO 瓶颈；
0.45 <= peak_memory_ratio <= 0.85：建议保持或小幅增大；
peak_memory_ratio > 0.90：建议降低 batch_size_frames；
low_utilization_ratio > 0.50：建议检查 Drive IO、ffmpeg、视频攻击与小 batch 问题。
```

---

### （四）`scripts/profile_runtime/profile_run_timing.py`

#### 1. 职责

提供 CLI 与 Python API，用于记录阶段级运行时间事件。该脚本既可独立运行，也可被 `paper_workflow/notebook_utils/run_timing_workflow.py` 调用。

#### 2. Python API

必须提供：

```python
class RunTimingRecorder:
    def __init__(self, run_root: str | Path, run_id: str | None = None): ...
    def event(self, event_name: str, **metadata): ...
    def write_event(self, event_name: str, start_time: float, end_time: float, status: str, **metadata): ...
```

`event()` 必须支持 context manager：

```python
with timer.event("stage2_runner", run_mode=RUN_MODE, runtime_profile=RUNTIME_PROFILE):
    probe_workflow.run_probe_runner(...)
```

#### 3. 输出格式

写入：

```text
<run_root>/runtime_profile/run_timing_events.jsonl
```

每条记录：

```json
{
  "run_id": "string",
  "event_name": "stage2_runner",
  "event_group": "real_video_vae_latent_probe",
  "start_time_utc": "ISO-8601",
  "end_time_utc": "ISO-8601",
  "elapsed_seconds": 123.4,
  "status": "ok",
  "metadata": {
    "run_mode": "formal",
    "runtime_profile": "formal"
  },
  "error_type": null,
  "error_message": null
}
```

如果 context 内抛出异常，必须记录：

```text
status = failed
error_type
error_message
```

然后重新抛出异常，不得吞掉 notebook 或 runner 的真实失败。

#### 4. CLI 形式

允许简单写入事件：

```bash
python -m scripts.profile_runtime.profile_run_timing \
  --run-root <run_root> \
  --event-name manual_event \
  --elapsed-seconds 12.3 \
  --status ok
```

但主要使用场景是 Python API。

---

### （五）`scripts/profile_runtime/summarize_run_timing.py`

#### 1. 职责

读取 `run_timing_events.jsonl`，生成：

```text
run_timing_summary.json
run_timing_report.md
```

#### 2. CLI 形式

```bash
python -m scripts.profile_runtime.summarize_run_timing \
  --run-root <run_root> \
  --events-jsonl <run_root>/runtime_profile/run_timing_events.jsonl \
  --output-json <run_root>/runtime_profile/run_timing_summary.json \
  --output-md <run_root>/runtime_profile/run_timing_report.md
```

#### 3. 汇总字段

至少包含：

```json
{
  "event_count": 8,
  "failed_event_count": 0,
  "total_recorded_seconds": 5321.4,
  "events_by_name": {
    "runtime_preflight": 12.4,
    "model_preparation": 96.2,
    "stage2_runner": 4820.1,
    "table_rebuild": 14.3,
    "formal_checker": 8.2,
    "packaging": 370.2
  },
  "slowest_event_name": "stage2_runner",
  "slowest_event_seconds": 4820.1,
  "estimated_work_planning_label": "multi_hour_run"
}
```

`estimated_work_planning_label` 推荐取值：

```text
short_run：小于 30 分钟；
medium_run：30 分钟至 2 小时；
multi_hour_run：2 至 8 小时；
long_run：超过 8 小时。
```

---

### （六）`scripts/profile_runtime/estimate_real_video_vae_latent_run_scale.py`

#### 1. 职责

运行前读取 dataset manifest、attack matrix、method variant、runtime profile，估计 event 数量和大致运行规模。

#### 2. CLI 形式

```bash
python -m scripts.profile_runtime.estimate_real_video_vae_latent_run_scale \
  --dataset-manifest <dataset_manifest.json> \
  --attack-matrix configs/attacks/real_video_attack_matrix.json \
  --ablation-config configs/ablation/real_video_vae_latent_ablation.json \
  --runtime-profile formal \
  --output-json <run_root>/runtime_profile/run_scale_estimate.json
```

#### 3. 输出字段

至少包含：

```json
{
  "dataset_manifest": "string",
  "runtime_profile": "formal",
  "video_count_total": 40,
  "video_count_by_split": {
    "calibration": 20,
    "test": 20
  },
  "method_variant_count": 3,
  "attack_count": 10,
  "estimated_event_count": 1320,
  "estimated_decode_video_count": 660,
  "estimated_attack_video_count": 600,
  "estimated_reencode_latent_count": 600,
  "estimated_quality_metric_pairs": 660,
  "scale_label": "formal_small",
  "warnings": []
}
```

#### 4. 实现要求

```text
1. 不要求精确复刻 runner 内部所有 event 生成逻辑，但要保守估算；
2. 如果某个配置文件缺失，应输出 warning 并返回非零退出码；
3. 不应导入 runner 触发真实运行；
4. 可复用 JSON 解析和简单计数逻辑。
```

---

### （七）`scripts/profile_runtime/watch_real_video_vae_latent_progress.py`

#### 1. 职责

读取 run 目录，生成当前进度快照，帮助判断 Colab 是否卡住。

#### 2. CLI 形式

```bash
python -m scripts.profile_runtime.watch_real_video_vae_latent_progress \
  --run-root <run_root> \
  --output-json <run_root>/runtime_profile/run_progress_snapshot.json
```

#### 3. 检查对象

统计：

```text
records/event_scores.jsonl 行数；
thresholds/thresholds.json 是否存在；
tables/*.csv 数量；
reports/vae_latent_probe_report.md 是否存在；
artifacts/videos/source/**/*.mp4 数量；
artifacts/videos/decoded/**/*.mp4 数量；
artifacts/videos/attacked/**/*.mp4 数量；
artifacts/latents/encoded/**/*.npy 数量；
artifacts/latents/watermarked/**/*.npy 数量；
artifacts/latents/reencoded/**/*.npy 数量；
runtime_profile/gpu_runtime_trace.csv 最后更新时间；
records/event_scores.jsonl 最后更新时间。
```

#### 4. 输出字段

```json
{
  "run_root": "string",
  "timestamp_utc": "ISO-8601",
  "records_written": 128,
  "thresholds_ready": false,
  "tables_ready": false,
  "report_ready": false,
  "source_video_count": 4,
  "decoded_video_count": 20,
  "attacked_video_count": 40,
  "encoded_latent_count": 4,
  "watermarked_latent_count": 12,
  "reencoded_latent_count": 40,
  "last_record_update_age_seconds": 18.2,
  "last_gpu_trace_update_age_seconds": 2.1,
  "possible_stall": false,
  "stall_reason": null
}
```

`possible_stall` 规则：

```text
如果 run_root 存在、records 或 artifact 在 15 分钟以上无更新，且 gpu_runtime_trace.csv 也 15 分钟无更新，则 possible_stall=true。
```

阈值应可通过 CLI 参数配置。

---

### （八）`scripts/check_results/summarize_run_failures.py`

#### 1. 职责

从 records、runtime_profile、checker 输出和 manifest 中提取失败原因，生成失败摘要。

#### 2. CLI 形式

```bash
python -m scripts.check_results.summarize_run_failures \
  --run-root <run_root> \
  --output-json <run_root>/runtime_profile/run_failure_summary.json \
  --output-md <run_root>/runtime_profile/run_failure_summary.md
```

#### 3. 统计内容

至少统计：

```text
record failure_reason 频次；
VAE encode / decode failure；
ffmpeg compression failure；
empty mp4；
moov atom not found；
CUDA OOM；
LPIPS failure；
dataset sample missing；
attack output missing；
checker BlockingReasons；
formal preflight failure；
packaging failure。
```

#### 4. 输出字段

```json
{
  "run_root": "string",
  "record_failure_count": 0,
  "failure_reason_counts": {},
  "checker_status": false,
  "checker_blocking_reasons": ["real_vae_backend"],
  "runtime_profile_failures": [],
  "dominant_failure_category": "checker_blocking_reason",
  "recommended_next_action": "inspect checker blocking reasons"
}
```

---

### （九）`scripts/profile_runtime/profile_drive_io.py`

#### 1. 职责

测量 Drive 与 session local 之间的读写速度。该脚本仅作为 notebook 辅助工具，不应影响正式结果。

#### 2. CLI 形式

```bash
python -m scripts.profile_runtime.profile_drive_io \
  --drive-root /content/drive/MyDrive/TSTW \
  --local-root /content/TSTW_runtime \
  --output-json <run_root>/runtime_profile/drive_io_profile.json \
  --sample-size-mb 64
```

#### 3. 输出字段

```json
{
  "drive_root": "string",
  "local_root": "string",
  "sample_size_mb": 64,
  "drive_to_local_mb_s": 42.1,
  "local_to_drive_mb_s": 18.5,
  "local_write_mb_s": 210.0,
  "drive_io_status": "moderate",
  "warnings": []
}
```

#### 4. 实现要求

```text
1. 写入临时测试文件后必须清理；
2. 如果 drive_root 不存在，应输出 warning；
3. 不得删除任何正式数据集或结果文件；
4. 默认 sample_size_mb 不超过 64，避免浪费 Colab IO。
```

---

### （十）`scripts/profile_runtime/recommend_runtime_parameters.py`

#### 1. 职责

读取 GPU summary、timing summary、scale estimate 和 failure summary，给出下一轮运行建议。

#### 2. CLI 形式

```bash
python -m scripts.profile_runtime.recommend_runtime_parameters \
  --run-root <run_root> \
  --output-json <run_root>/runtime_profile/runtime_parameter_recommendation.json
```

#### 3. 输出字段

```json
{
  "recommended_gpu_tier": "L4_or_better",
  "recommended_batch_size_frames": 4,
  "batch_size_direction": "increase_or_keep",
  "recommended_runtime_profile_next": "debug_real_video_or_smoke",
  "recommended_action": "rerun_with_larger_batch_after_smoke_pass",
  "reasoning": [
    "peak_memory_ratio is below 0.45",
    "mean_gpu_utilization is below 50",
    "stage2_runner dominates timing"
  ],
  "warnings": []
}
```

#### 4. 推荐规则

```text
如果 checker 未 PASS 且 failure_summary 中存在 runtime failure，则优先建议修 runtime failure；
如果 GPU 显存峰值低且 GPU 利用率低，则建议增大 batch 或检查 IO；
如果显存峰值超过 90%，建议降低 batch_size_frames；
如果 Drive IO 很慢，建议减少直接 Drive 读写，优先复制到 /content/TSTW_runtime；
如果 stage2_runner 耗时超过 8 小时估计，建议分 shard 或缩小 attack matrix 做 smoke。
```

---

## 五、Notebook helper 构建要求

### （一）`paper_workflow/notebook_utils/runtime_profile_workflow.py`

#### 1. 职责

为 `run_real_video_vae_latent_probe.ipynb` 提供统一 profiler wrapper，避免 notebook 中直接写复杂 subprocess 代码。

#### 2. 必须提供的函数

```python
def capture_colab_environment(*, run_root: str | Path, run_id: str, run_mode: str, runtime_profile: str) -> dict: ...

def profile_drive_io(*, run_root: str | Path, drive_root: str | Path, local_root: str | Path, sample_size_mb: int = 64) -> dict: ...

def estimate_real_video_vae_latent_run_scale(*, run_root: str | Path, dataset_manifest: str | Path, attack_matrix: str | Path, ablation_config: str | Path, runtime_profile: str) -> dict: ...

def start_gpu_runtime_profile(*, run_root: str | Path, interval_seconds: int = 2) -> subprocess.Popen | None: ...

def stop_gpu_runtime_profile(process: subprocess.Popen | None, *, run_root: str | Path) -> None: ...

def summarize_gpu_runtime_profile(*, run_root: str | Path) -> dict: ...

def watch_real_video_vae_latent_progress(*, run_root: str | Path) -> dict: ...

def summarize_run_failures(*, run_root: str | Path) -> dict: ...

def recommend_runtime_parameters(*, run_root: str | Path) -> dict: ...
```

#### 3. 实现要求

```text
1. 这些函数通过 subprocess 调用 scripts/ 下的 CLI；
2. helper 返回 JSON dict；
3. 如果某个 profiler 失败，helper 应返回 status=false 与 error_message，不得导致正式 runner 被静默跳过；
4. start_gpu_runtime_profile() 不得阻塞 notebook；
5. stop_gpu_runtime_profile() 必须创建 stop flag，并等待进程退出；
6. 若进程无法退出，应 terminate，并写 warning。
```

---

### （二）`paper_workflow/notebook_utils/run_timing_workflow.py`

#### 1. 职责

封装运行时间记录器，供 notebook 用 `with` 语法记录阶段耗时。

#### 2. 必须提供的函数

```python
def start_run_timing(*, run_root: str | Path, run_id: str | None = None): ...

def summarize_run_timing(*, run_root: str | Path) -> dict: ...
```

`start_run_timing()` 返回 `RunTimingRecorder`。

#### 3. 依赖约束

该文件可以从：

```python
from scripts.profile_runtime.profile_run_timing import RunTimingRecorder
```

导入计时器。不得从 `main/` 导入任何 Colab 或 profiling 模块。

---

## 六、Notebook 修改要求

必须修改：

```text
paper_workflow/run_real_video_vae_latent_probe.ipynb
```

不得修改：

```text
paper_workflow/build_processed_real_video_dataset.ipynb
```

除非需要在第一个 notebook 中显示 processed dataset 构建耗时，此项作为后续增强，不属于本次必做。

### （一）新增配置 cell 变量

在 `run_real_video_vae_latent_probe.ipynb` 的顶部配置区新增：

```python
PROFILE_RUNTIME = True
PROFILE_GPU_RUNTIME = True
GPU_PROFILE_INTERVAL_SECONDS = 2
PROFILE_DRIVE_IO = True
DRIVE_IO_SAMPLE_SIZE_MB = 64
WRITE_RUNTIME_RECOMMENDATION = True
```

默认值必须满足：

```text
formal 模式下 PROFILE_RUNTIME = True；
formal 模式下 PROFILE_GPU_RUNTIME = True；
如果 nvidia-smi 不可用，profiler 记录 unavailable，不阻断 preflight；
真正的 formal GPU 阻断仍由 runtime preflight 负责。
```

### （二）新增 import cell

在 notebook helper import 处新增：

```python
from paper_workflow.notebook_utils import runtime_profile_workflow
from paper_workflow.notebook_utils import run_timing_workflow
```

不得在 notebook 中直接调用 `nvidia-smi` 循环，不得在 notebook cell 中手写大量 profiling 逻辑。

### （三）新增环境快照与规模估算 cell

放在 runtime config 写入后、preflight 前或 preflight 后均可，建议顺序如下：

```python
runtime_environment_snapshot = runtime_profile_workflow.capture_colab_environment(
    run_root=RUN_ROOT,
    run_id=RUN_ID,
    run_mode=RUN_MODE,
    runtime_profile=RUNTIME_PROFILE,
)

run_scale_estimate = runtime_profile_workflow.estimate_real_video_vae_latent_run_scale(
    run_root=RUN_ROOT,
    dataset_manifest=PROCESSED_DATASET_MANIFEST,
    attack_matrix=ATTACK_MATRIX_PATH,
    ablation_config=ABLATION_CONFIG_PATH,
    runtime_profile=RUNTIME_PROFILE,
)

runtime_environment_snapshot, run_scale_estimate
```

如果当前 notebook 没有 `ATTACK_MATRIX_PATH` 或 `ABLATION_CONFIG_PATH` 变量，应新增并与 runner 调用保持一致：

```python
ATTACK_MATRIX_PATH = Path('configs/attacks/real_video_attack_matrix.json')
ABLATION_CONFIG_PATH = Path('configs/ablation/real_video_vae_latent_ablation.json')
```

### （四）新增 Drive IO profile cell

放在 dataset 与 model 复制到 session local 之后：

```python
if PROFILE_DRIVE_IO:
    drive_io_profile = runtime_profile_workflow.profile_drive_io(
        run_root=RUN_ROOT,
        drive_root=DRIVE_ROOT,
        local_root=LOCAL_RUNTIME_ROOT,
        sample_size_mb=DRIVE_IO_SAMPLE_SIZE_MB,
    )
else:
    drive_io_profile = {"skipped": True}

drive_io_profile
```

如果当前 notebook 没有 `DRIVE_ROOT` 或 `LOCAL_RUNTIME_ROOT`，使用现有变量中等价路径；不得硬编码到 helper 内部。

### （五）在 runner 前启动 timing 与 GPU profiler

在执行 runner 前新增：

```python
run_timer = run_timing_workflow.start_run_timing(
    run_root=RUN_ROOT,
    run_id=RUN_ID,
)

gpu_profile_process = None
if PROFILE_GPU_RUNTIME:
    gpu_profile_process = runtime_profile_workflow.start_gpu_runtime_profile(
        run_root=RUN_ROOT,
        interval_seconds=GPU_PROFILE_INTERVAL_SECONDS,
    )
```

### （六）用 timing context 包裹关键 notebook 步骤

至少包裹以下步骤：

```text
runtime_preflight；
model_preparation；
stage2_runner；
table_and_report_rebuild；
formal_checker；
result_packaging。
```

示例：

```python
with run_timer.event("runtime_preflight", run_mode=RUN_MODE, runtime_profile=RUNTIME_PROFILE):
    runtime_preflight = probe_workflow.run_probe_runtime_preflight(
        run_mode=RUN_MODE,
        local_dataset_root=LOCAL_DATASET_ROOT,
        local_model_dirs=[LOCAL_MODEL_ROOT],
    )
```

runner cell 必须改成：

```python
with run_timer.event("real_video_vae_latent_runner", run_mode=RUN_MODE, runtime_profile=RUNTIME_PROFILE):
    probe_workflow.run_probe_runner(
        run_root=RUN_ROOT,
        run_mode=RUN_MODE,
        runtime_profile=RUNTIME_PROFILE,
        runtime_config_path=RUNTIME_CONFIG_PATH,
        dataset_manifest=PROCESSED_DATASET_MANIFEST,
        python_executable=sys.executable,
    )
```

如果当前 runner 需要传 `attack_matrix` 或 `ablation_config`，必须与前述估算脚本使用相同变量。

### （七）runner 后停止 profiler 并生成汇总

必须放在 `finally` 语义中，保证 runner 失败时也停止 GPU profiler 并生成失败摘要。

Notebook 中可采用：

```python
try:
    with run_timer.event("real_video_vae_latent_runner", run_mode=RUN_MODE, runtime_profile=RUNTIME_PROFILE):
        probe_workflow.run_probe_runner(...)
finally:
    if PROFILE_GPU_RUNTIME:
        runtime_profile_workflow.stop_gpu_runtime_profile(
            gpu_profile_process,
            run_root=RUN_ROOT,
        )
```

随后新增：

```python
gpu_runtime_summary = runtime_profile_workflow.summarize_gpu_runtime_profile(
    run_root=RUN_ROOT,
)
run_timing_summary = run_timing_workflow.summarize_run_timing(
    run_root=RUN_ROOT,
)
run_progress_snapshot = runtime_profile_workflow.watch_real_video_vae_latent_progress(
    run_root=RUN_ROOT,
)
run_failure_summary = runtime_profile_workflow.summarize_run_failures(
    run_root=RUN_ROOT,
)

if WRITE_RUNTIME_RECOMMENDATION:
    runtime_parameter_recommendation = runtime_profile_workflow.recommend_runtime_parameters(
        run_root=RUN_ROOT,
    )
else:
    runtime_parameter_recommendation = {"skipped": True}

gpu_runtime_summary, run_timing_summary, run_progress_snapshot, run_failure_summary, runtime_parameter_recommendation
```

### （八）formal checker 与 packager 不得被 profiler 替代

保持现有 formal checker 逻辑：

```python
formal_validation_summary = probe_workflow.check_probe_outputs(...)
if not formal_validation_summary["status"]:
    raise RuntimeError(formal_validation_summary)
```

Profiler 的失败摘要只能帮助定位问题，不能将 checker failure 改写为 pass。

### （九）packager 必须纳入 runtime_profile 目录

检查现有 packager 是否包含：

```text
runtime_profile/**
```

如果未包含，修改：

```text
scripts/package_results/package_real_video_vae_latent_outputs.py
scripts/package_results/package_real_video_vae_latent_tar_zst.py
```

使其将 `runtime_profile/` 纳入 zip / tar.zst 结果包。不得把 profiler 输出复制进 `records/` 或 `tables/`。

---

## 七、测试要求

### （一）新增约束测试：`tests/constraints/test_runtime_profile_file_organization.py`

必须验证：

```text
1. scripts/profile_runtime/ 存在；
2. paper_workflow/notebook_utils/runtime_profile_workflow.py 存在；
3. paper_workflow/notebook_utils/run_timing_workflow.py 存在；
4. main/ 下不存在 profile_runtime、gpu_profile、colab profiler 文件；
5. 新增文件名不包含 stage2、stage_2、v1、p2、latest、final 等弱命名；
6. notebook 中 import 的 profiler helper 来自 paper_workflow.notebook_utils，而不是 main。
```

### （二）新增功能测试：`tests/functional/test_runtime_environment_snapshot.py`

验证：

```text
capture_colab_environment.py 可以在无 GPU 环境下运行；
输出 JSON 包含 cuda_available、ffmpeg_available、dependency_imports、disk_free_gb；
无 GPU 时不会崩溃。
```

### （三）新增功能测试：`tests/functional/test_gpu_runtime_profiler.py`

验证：

```text
profile_gpu_runtime.py 在 nvidia-smi 不存在时可以生成合法 CSV；
summarize_gpu_profile.py 可以读取该 CSV 并输出 trace_available 字段；
stop file 机制有效；
输出目录为 run_root/runtime_profile/。
```

该测试不得要求真实 GPU。

### （四）新增功能测试：`tests/functional/test_run_timing_profiler.py`

验证：

```text
RunTimingRecorder context manager 可以写入 run_timing_events.jsonl；
正常事件 status=ok；
异常事件 status=failed 且异常会重新抛出；
summarize_run_timing.py 可以生成 summary 和 report。
```

### （五）新增功能测试：`tests/functional/test_real_video_vae_latent_run_scale_estimator.py`

使用 fixture manifest、attack matrix、ablation config，验证：

```text
estimate_real_video_vae_latent_run_scale.py 输出 estimated_event_count；
输出 video_count_by_split；
配置缺失时返回非零退出码或 status=false。
```

### （六）新增功能测试：`tests/functional/test_real_video_vae_latent_progress_watcher.py`

构造临时 run_root，写入少量 artifact，验证：

```text
watch_real_video_vae_latent_progress.py 可以统计 records、mp4、npy、tables；
输出 possible_stall 字段；
无 run_root 时返回 status=false 或合理错误，不崩溃。
```

### （七）新增功能测试：`tests/functional/test_run_failure_summary.py`

构造临时 records 与 checker 输出，验证：

```text
summarize_run_failures.py 可以统计 failure_reason_counts；
可以读取 checker BlockingReasons；
可以输出 run_failure_summary.md。
```

### （八）新增功能测试：`tests/functional/test_runtime_parameter_recommendation.py`

构造 GPU summary、timing summary、failure summary，验证：

```text
recommend_runtime_parameters.py 可以输出 recommended_batch_size_frames；
当 peak_memory_ratio > 0.90 时建议降低 batch；
当 peak_memory_ratio < 0.45 且 mean_gpu_util_percent < 50 时建议增大 batch 或检查 IO。
```

### （九）更新 notebook contract 测试

更新：

```text
tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py
```

新增检查：

```text
run_real_video_vae_latent_probe.ipynb 引入 runtime_profile_workflow；
run_real_video_vae_latent_probe.ipynb 引入 run_timing_workflow；
notebook 含 PROFILE_RUNTIME、PROFILE_GPU_RUNTIME、GPU_PROFILE_INTERVAL_SECONDS；
notebook 在 runner 前启动 profiler；
notebook 在 runner 后停止 profiler；
notebook 调用 summarize_gpu_runtime_profile 与 summarize_run_timing；
notebook 没有直接写 nvidia-smi while 循环。
```

---

## 八、验收命令

Codex 完成变更后，必须运行以下命令。

### （一）格式与默认测试

```bash
PYTHONPATH=. python -m pytest -q
```

### （二）新增 profiler 测试

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/constraints/test_runtime_profile_file_organization.py \
  tests/functional/test_runtime_environment_snapshot.py \
  tests/functional/test_gpu_runtime_profiler.py \
  tests/functional/test_run_timing_profiler.py \
  tests/functional/test_real_video_vae_latent_run_scale_estimator.py \
  tests/functional/test_real_video_vae_latent_progress_watcher.py \
  tests/functional/test_run_failure_summary.py \
  tests/functional/test_runtime_parameter_recommendation.py
```

### （三）Notebook contract 测试

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/constraints/test_notebook_naming_contract.py \
  tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py \
  tests/constraints/test_packager_notebook_contract.py
```

### （四）审计

```bash
PYTHONPATH=. python tools/harness/run_all_audits.py
```

### （五）最小脚本手动验证

```bash
RUN_ROOT=/tmp/tstw_runtime_profile_smoke
rm -rf "$RUN_ROOT"
mkdir -p "$RUN_ROOT"

PYTHONPATH=. python -m scripts.profile_runtime.capture_colab_environment \
  --run-root "$RUN_ROOT" \
  --run-id runtime_profile_smoke \
  --run-mode smoke \
  --runtime-profile debug_real_video \
  --output-json "$RUN_ROOT/runtime_profile/colab_environment_snapshot.json"

PYTHONPATH=. python -m scripts.profile_runtime.profile_run_timing \
  --run-root "$RUN_ROOT" \
  --event-name manual_event \
  --elapsed-seconds 1.23 \
  --status ok

PYTHONPATH=. python -m scripts.profile_runtime.summarize_run_timing \
  --run-root "$RUN_ROOT" \
  --events-jsonl "$RUN_ROOT/runtime_profile/run_timing_events.jsonl" \
  --output-json "$RUN_ROOT/runtime_profile/run_timing_summary.json" \
  --output-md "$RUN_ROOT/runtime_profile/run_timing_report.md"
```

---

## 九、验收标准

本次变更完成后，必须满足：

```text
1. 所有新增 profiler / timing / recommendation 脚本位于 scripts/profile_runtime/ 或 scripts/check_results/；
2. 所有 notebook wrapper 位于 paper_workflow/notebook_utils/；
3. main/ 未新增任何 Colab、Drive、GPU profiling、runtime timing 专用模块；
4. run_real_video_vae_latent_probe.ipynb 可以启动与停止 GPU profiler；
5. run_real_video_vae_latent_probe.ipynb 可以记录阶段耗时；
6. runner 失败时，GPU profiler 仍能停止，并生成 failure summary；
7. packager 将 runtime_profile/ 纳入 zip / tar.zst；
8. 所有新增脚本在无 GPU 环境下也能通过测试；
9. formal checker 判定逻辑未被改变；
10. 默认测试、profiler 测试、notebook contract 测试与总审计全部通过。
```

不得将以下内容作为通过标准：

```text
1. profiler 输出显示 GPU 利用率高；
2. timing summary 显示运行较快；
3. recommendation 给出某个 batch size；
4. failure summary 无失败。
```

这些只是运行辅助结果，不是阶段 2 formal PASS 依据。阶段 2 是否完成仍由 `scripts/check_results/check_real_video_vae_latent_outputs.py` 与 governance summary 判定。

---

## 十、Codex 执行边界

本次 Codex 任务只允许修改或新增以下类别文件：

```text
scripts/profile_runtime/**
scripts/check_results/summarize_run_failures.py
paper_workflow/notebook_utils/runtime_profile_workflow.py
paper_workflow/notebook_utils/run_timing_workflow.py
paper_workflow/run_real_video_vae_latent_probe.ipynb
tests/functional/test_*runtime*.py
tests/functional/test_*progress*.py
tests/functional/test_*failure*.py
tests/constraints/test_runtime_profile_file_organization.py
tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py
scripts/package_results/package_real_video_vae_latent_outputs.py
scripts/package_results/package_real_video_vae_latent_tar_zst.py
```

除非测试必须调整，不得修改：

```text
main/**
experiments/real_video_vae_latent_probe/runner.py
experiments/real_video_vae_latent_probe/artifact_builder.py
configs/protocol/**
configs/backend/**
configs/attacks/**
configs/ablation/**
scripts/check_results/real_video_vae_latent_output_checker.py
```

严格禁止：

```text
1. 为了让 notebook 通过而放松 formal checker；
2. 为了让测试通过而跳过 GPU profiler 或 timing 写盘；
3. 将 profiler 输出混入正式 records；
4. 改写 evidence_scores、S_final、threshold、decision；
5. 新增 stage2、v1、p2、latest、final 等弱语义命名；
6. 在 main/ 中新增 Colab 或 profiling 代码。
```

---

## 十一、建议提交说明

变更完成后，提交说明建议写为：

```text
Add governed runtime profiling utilities for real-video VAE latent notebook workflow
```

中文说明建议写为：

```text
新增受治理的 Colab 运行统计辅助脚本，包括环境快照、GPU 利用率、阶段耗时、运行规模估算、进度快照、失败摘要与参数建议；将其接入 run_real_video_vae_latent_probe notebook；不修改 main 核心方法与 formal checker 判定语义。
```

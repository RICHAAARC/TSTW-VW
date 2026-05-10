# Notebook 构造总体约束说明

## 一、文件定位

本文档用于约束本项目所有 Colab notebook 的构造方式。本文档是项目级 notebook 治理契约，不描述任何具体阶段的构建方法，不规定某一阶段的算法内容，也不替代任何阶段性设计文档、实验方案文档或论文实验 protocol 文档。

本文档只规定以下通用事项：

```text
1. notebook 之间如何隔离；
2. 数据集、模型、配置、运行结果和归档文件如何组织；
3. FAMILY_ID 如何作为结果包身份；
4. 每次测试、每个 workflow 或每个分步流程如何落盘；
5. 跨 notebook handoff 只能依赖已落盘 artifact；
6. raw dataset、processed dataset、session model 与 run result 的边界；
7. Google Drive 与 Colab 本地会话目录的职责划分。
```

本文档适用于本项目后续所有 notebook，包括但不限于数据下载、数据预处理、模型运行、实验执行、结果检查、结果合并、结果归档、报告生成与 release 打包类 notebook。任何 notebook 均不得在标题、目录、路径或代码中将本治理契约固定为某一具体阶段的构建说明。

全局核心约束如下：

```text
Raw Dataset：官方原始数据仓库，长期保存在 /content/drive/MyDrive/Datasets/，不属于某一次 FAMILY_ID 结果包。
Processed Dataset：正式实验输入，长期保存在 /content/drive/MyDrive/TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/，不属于某一次 run 的临时结果。
Session Model：所有模型相关文件均在 Colab 本地会话中下载、缓存与加载，不保存到 Google Drive。
Family Result：除 raw dataset、processed dataset 与长期 registry 外，所有实验记录、日志、模型会话 manifest、配置快照、workflow 结果与最终结果均必须保存到 /content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/。
Notebook Session：每个 notebook 都视为独立 Colab 会话，不能依赖上一个 notebook 的进程内状态、内存对象、临时缓存、/tmp 文件或 /content 中未归档目录。
Artifact Handoff：跨 notebook 传递的事实只能来自已落盘、已校验、已登记的 family artifact。
```

本文档明确替代旧规则中“模型长期保存到 Google Drive Models”的设计。当前规则为：**所有模型相关文件均为 session-only；Google Drive 不作为模型权重仓库；Google Drive 只保存模型下载与加载的 session manifest，而不保存模型权重文件本体。**

---

## 二、术语定义

### （一）`FAMILY_ID`

`FAMILY_ID` 是一次独立实验、一次独立测试、一个多 notebook workflow、一次正式结果构建或一次 release 归档的最高身份锚点。所有结果文件、配置快照、检查报告、日志、合并结果与最终包均必须归属到某一个 `FAMILY_ID`。

推荐命名格式：

```text
<FAMILY_SCOPE>__<PROTOCOL_KEY>__<DATASET_KEY>__<UTC_TIME>__<SHORT_COMMIT>
```

其中，`FAMILY_SCOPE` 表示本次结果包的研究或工程范围；`PROTOCOL_KEY` 表示实验协议或运行模式；`DATASET_KEY` 表示输入数据集身份；`UTC_TIME` 表示启动时间；`SHORT_COMMIT` 表示仓库短提交号。

禁止使用弱语义名称：

```text
run1
final
new_run
test
best
probe
formal_latest
latest
```

### （二）`WORKFLOW_KEY`

`WORKFLOW_KEY` 表示某个 notebook 或多个 notebook 共同完成的 workflow 类型。它是通用 workflow 名称，不应直接写成某个阶段构建名称。

推荐格式：

```text
raw_dataset_download
processed_dataset_build
source_generation
detection_evaluation
quality_evaluation
result_merge
report_build
release_packaging
sanity_check
```

如果某个项目阶段需要使用这些 workflow，应通过配置文件或 `FAMILY_ID` 进行绑定，而不是在 notebook 治理契约中硬编码阶段名称。

### （三）`PROCESSED_DATASET_KEY`

`PROCESSED_DATASET_KEY` 是某个正式 processed dataset 的身份键。它可以包含任务语义、数据来源、规格与版本，但本文档不规定具体阶段名称。

推荐格式：

```text
<dataset_source>__<task_scope>__<resolution>__<frames>__<fps>__<version>
```

示例格式：

```text
<dataset>__<workflow_scope>__256x256__32f__8fps__freeze001
```

### （四）`STEP_KEY`

`STEP_KEY` 表示某个 family 内部的有序步骤。若一个 family 包含多个 notebook、多个 shard 或多个子流程，必须用 `STEP_KEY` 标识各步骤结果。

推荐格式：

```text
step00_bootstrap
step01_prepare_inputs
step02_run_core
step03_evaluate
step04_merge
step05_release
```

需要注意：`STEP_KEY` 是 workflow 编排键，不是项目阶段定义。它不能替代算法阶段、论文实验 protocol 或方法机制定义。

### （五）`SHARD_ID`

`SHARD_ID` 用于并行任务分片。任何 shard notebook 只能读取 shard plan 中分配给自己的输入，并将结果写入对应 shard 包。

推荐格式：

```text
shard_0000
shard_0001
shard_0002
```

---

## 三、总体原则

### （一）FAMILY_ID 作为最高结果身份

每一次独立运行必须创建或读取一个明确的 `FAMILY_ID`。一个 notebook 不得在没有 `FAMILY_ID` 的情况下写入正式结果。若 notebook 仅用于临时调试，也必须创建 `FAMILY_ID`，并将 `run_mode` 标记为 `debug` 或 `smoke`。

`FAMILY_ID` 必须写入：

```text
family_manifest.json
family_summary.json
family_checks.json
每个 step 的 step_manifest.json
每个 shard 的 shard_manifest.json
每个 run package 的 run_manifest.json
release_manifest.json
registry entry
```

### （二）结果包优先于运行时状态

所有 notebook 之间的依赖必须体现为文件依赖，而不是运行时依赖。任何下游 notebook 只能读取上游已经写入 family root 的 manifest、summary、checks、records、tables、shard package、step package 或 release package。

禁止下游 notebook 依赖：

```text
上一个 notebook 内存中的变量；
上一个 notebook 安装过的 Python package 状态；
上一个 notebook 下载在 /tmp 的文件；
上一个 notebook 未打包的 /content/TSTW_runtime/runs/<RUN_ID>/ 目录；
上一个 notebook 的 torch cache；
上一个 notebook 的 huggingface cache；
上一个 notebook 当前能否 import 某个库；
上一个 notebook 中手动定义但未写盘的路径、阈值、split、seed 或模型对象。
```

如果某个事实需要跨 notebook 使用，必须写入：

```text
family_manifest.json
step_manifest.json
shard_manifest.json
runtime_state/*.json
artifacts/*.json
checks/*.json
records/*.jsonl
tables/*.csv
summaries/*.json
```

### （三）Canonical 与 analysis-only 分层

所有输出必须区分：

```text
canonical outputs：主线结果、workflow 完成、release 或论文结果必需工件；
analysis-only outputs：补充分析、调试表格、可视化、失败样例、辅助一致性检查。
```

`family_summary.json`、`step_summary.json` 与 `release_manifest.json` 必须显式记录两类路径，防止后续 notebook 绕过 canonical 工件链路。

### （四）Notebook 不承担隐式工程状态

Notebook 只允许作为可复现 workflow 的执行入口，不得承担以下隐式状态：

```text
不在 notebook 变量中保存跨步骤唯一事实；
不靠 cell 执行顺序之外的隐藏状态决定结果；
不从 notebook 当前工作目录推断 family；
不根据目录中最新文件自动选择正式输入；
不将临时输出当作正式输入；
不将运行时缓存当作可复现 artifact。
```

---

## 四、Google Drive 固定目录结构

Google Drive 目录固定为：

```text
/content/drive/MyDrive/
├── Datasets/
│   ├── <RAW_DATASET_NAME>/
│   │   └── raw/
│   └── raw_dataset_download_manifest.json
└── TSTW/
    ├── datasets/
    │   ├── processed/
    │   │   └── <PROCESSED_DATASET_KEY>/
    │   └── registry/
    │       └── dataset_registry.json
    ├── configs/
    │   └── <CONFIG_SCOPE_KEY>/
    ├── results/
    │   └── families/
    │       └── <FAMILY_ID>/
    └── registry/
        ├── family_registry.jsonl
        ├── result_registry.jsonl
        ├── drive_state.json
        └── last_bootstrap_summary.json
```

需要注意：

```text
1. /content/drive/MyDrive/Datasets/ 只保存 raw dataset。
2. /content/drive/MyDrive/TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/ 保存正式 processed dataset。
3. /content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/ 保存某一次实验、测试或 workflow family 的所有结果包。
4. 不使用 /content/drive/MyDrive/Models/ 作为正式模型来源。
5. 若历史上已经存在 /content/drive/MyDrive/Models/，后续 notebook 不得读取它作为正式模型来源。
6. 除 raw dataset、processed dataset、registry 与 family result 外，不应在 Drive 根目录下新增项目相关散落目录。
```

---

## 五、FAMILY_ID 结果目录结构

### （一）多步骤 family 结果目录

如果一个实验包含多个 notebook、多个 step、多个 shard 或多个合并流程，应采用多步骤 family 目录：

```text
/content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/
├── family_manifest.json
├── family_summary.json
├── family_checks.json
├── configs/
│   ├── runtime_override.json
│   ├── dataset_override.json
│   ├── model_session_override.json
│   └── protocol_override.json
├── steps/
│   ├── <STEP_KEY>/
│   │   ├── step_manifest.json
│   │   ├── step_summary.json
│   │   ├── step_checks.json
│   │   ├── packages/
│   │   │   └── <STEP_RUN_ID>.tar.zst
│   │   ├── shards/
│   │   │   ├── shard_0000.tar.zst
│   │   │   ├── shard_0001.tar.zst
│   │   │   └── shard_plan.json
│   │   └── merges/
│   │       └── merge_summary.json
│   └── <ANOTHER_STEP_KEY>/
├── releases/
│   ├── <FAMILY_ID>_release.tar.zst
│   ├── <FAMILY_ID>_release_manifest.json
│   ├── <FAMILY_ID>_release_summary.json
│   └── <FAMILY_ID>_release_checks.json
└── registry_updates/
    ├── result_registry_entry.json
    └── family_registry_entry.json
```

该结构适用于：

```text
需要多个 notebook 组合完成的结果；
需要 shard 并行的生成、攻击、检测或质量计算；
需要先生成中间结果再合并的 workflow；
需要从 smoke 逐步推进到 formal 的 workflow；
需要最终 release 或 signoff 的 workflow。
```

### （二）单包 family 结果目录

如果某次测试不分 step，例如单一 sanity check、单 notebook smoke 或单次数据构建检查，则可以保存为一个结果文件包：

```text
/content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/
├── family_manifest.json
├── <FAMILY_ID>.tar.zst
├── <FAMILY_ID>_summary.json
├── <FAMILY_ID>_checks.json
└── registry_updates/
    └── result_registry_entry.json
```

该结构适用于：

```text
单次 smoke；
单 notebook 检查；
单包数据构建检查；
临时但需要审计保存的测试包。
```

禁止将多个独立测试混放到同一个无步骤目录中。如果两个测试的 dataset、protocol、model、commit、run mode 或关键配置不同，应使用不同的 `FAMILY_ID`。

---

## 六、Colab 本地工作空间

每个 notebook 启动时必须重新创建本地工作空间：

```python
DRIVE_ROOT = "/content/drive/MyDrive"
RAW_DATASETS_ROOT = f"{DRIVE_ROOT}/Datasets"
TSTW_ROOT = f"{DRIVE_ROOT}/TSTW"
TSTW_FAMILY_RESULTS_ROOT = f"{TSTW_ROOT}/results/families"

LOCAL_TSTW_ROOT = "/content/TSTW_runtime"
LOCAL_REPO_DIR = f"{LOCAL_TSTW_ROOT}/repo"
LOCAL_DATASET_CACHE_DIR = f"{LOCAL_TSTW_ROOT}/dataset_cache"
LOCAL_DATASETS_DIR = f"{LOCAL_TSTW_ROOT}/datasets"
LOCAL_SESSION_MODELS_DIR = f"{LOCAL_TSTW_ROOT}/session_models"
LOCAL_MODEL_CACHE_DIR = f"{LOCAL_TSTW_ROOT}/model_cache"
LOCAL_RUNS_DIR = f"{LOCAL_TSTW_ROOT}/runs"
LOCAL_TMP_DIR = f"{LOCAL_TSTW_ROOT}/tmp"
```

规则：

```text
1. notebook 每次启动都必须重新创建 /content/TSTW_runtime/。
2. notebook 不得假设 /content/TSTW_runtime/ 中已经存在上次运行的文件。
3. notebook 不得读取 /tmp 作为正式输入。
4. notebook 可以使用 /content/TSTW_runtime/tmp/ 作为本次运行临时目录，但运行结束后不得作为 handoff 依据。
5. notebook 结束前，所有需要保留的结果必须打包并写入 family root。
```

---

## 七、数据集治理规则

### （一）Raw Dataset

Raw Dataset 是官方原始数据仓库，保存位置固定为：

```text
/content/drive/MyDrive/Datasets/
```

Raw Dataset notebook 只允许执行：

```text
下载 raw archive；
保存 raw captions 或 raw metadata；
计算或记录 raw file metadata；
写 raw_dataset_download_manifest.json。
```

Raw Dataset notebook 不得执行：

```text
不解压成正式实验输入；
不切片；
不抽帧；
不生成 processed dataset；
不加载模型；
不运行实验；
不生成正式 records、thresholds、tables 或 reports。
```

### （二）Processed Dataset

Processed Dataset 是正式实验输入，保存位置固定为：

```text
/content/drive/MyDrive/TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/
```

每个 `PROCESSED_DATASET_KEY` 必须独立保存：

```text
videos/ 或 inputs/
manifests/
checks/
cache/
processed_dataset_summary.json
processed_dataset_checks.json
processed_dataset_manifest.json
```

Processed Dataset notebook 只允许执行：

```text
读取 Raw Dataset；
在 Colab 本地解压或转换；
按固定策略生成正式输入；
计算 digest；
写 processed manifest；
写 split manifest；
写 processed summary 与 checks；
打包 processed cache；
更新 dataset_registry.json。
```

Processed Dataset notebook 不得执行：

```text
不加载生成模型或检测模型；
不嵌入水印；
不运行正式 detector；
不生成正式 detection records；
不生成论文结果表格；
不把临时切片直接传给下游 notebook。
```

### （三）Formal Runtime Dataset

实验执行 notebook 不应直接从 Google Drive 高频读取 processed videos 或 large arrays。必须执行：

```text
Drive processed dataset
→ copy / extract 到 /content/TSTW_runtime/datasets/<PROCESSED_DATASET_KEY>/
→ 本地读取
→ 本地运行
→ 结果打包回 family root
```

正式 run 必须写入：

```text
runtime_dataset_manifest.json
runtime_dataset_checks.json
processed_dataset_key
processed_dataset_digest 或 manifest_digest
local_runtime_dataset_path
```

---

## 八、模型治理规则

### （一）所有模型均 session-only

所有模型相关文件均不得保存到 Google Drive。包括：

```text
单权重文件；
checkpoint；
VAE；
CLIP；
DINOv2；
LPIPS backbone；
RAFT；
视频生成 pipeline；
图像生成 pipeline；
text encoder；
tokenizer；
scheduler；
任何 .pth、.pt、.ckpt、.safetensors、.bin 权重文件。
```

模型文件只允许保存到：

```text
/content/TSTW_runtime/session_models/
/content/TSTW_runtime/model_cache/
/root/.cache/huggingface/
/root/.cache/torch/
```

其中，`/root/.cache/*` 只能作为本次会话缓存，不得作为跨 notebook handoff。

### （二）显式模型下载 cell

凡是需要模型的 notebook，必须包含显式模型下载 cell。该 cell 应读取 `model_session_override.json`，并执行：

```text
检查本次 notebook 所需模型列表；
下载缺失模型到 /content/TSTW_runtime/session_models/ 或本地 cache；
记录 repo_id、revision、source_url、selected_files、size、下载时间；
记录是否使用 torchvision 或 huggingface 自动 cache；
写 session_model_manifest.json；
写 session_model_download.log。
```

禁止：

```text
不允许从 /content/drive/MyDrive/Models/ 读取模型；
不允许将模型复制到 Google Drive；
不允许将模型文件打包进 family result；
不允许模型下载行为不写 manifest；
不允许 hidden auto-download 未被记录。
```

### （三）LPIPS 与 torchvision backbone

允许 LPIPS backbone 由 torchvision 在 Colab 本地自动下载，但必须记录：

```text
lpips version；
torch version；
torchvision version；
backbone name；
cache path；
auto_download_status；
model_role；
run_id；
FAMILY_ID。
```

该记录必须写入：

```text
run_root/artifacts/session_model_manifest.json
```

---

## 九、Notebook 会话隔离规则

每个 notebook 都必须假设：

```text
1. 当前 Colab 是全新会话；
2. /content 中没有任何可复用文件；
3. /tmp 中没有任何可复用文件；
4. Python 进程中没有上游 notebook 的对象；
5. 模型 cache 可能为空；
6. pip package 状态可能不是预期状态；
7. 只有 Google Drive 中已落盘、已登记的 artifact 可作为输入。
```

因此，每个 notebook 必须自行完成：

```text
挂载 Google Drive；
读取 FAMILY_ID 或创建 FAMILY_ID；
读取 family manifest；
准备本地 runtime 目录；
拉取或检查仓库；
安装依赖；
复制正式输入到 /content；
显式下载本次所需模型；
运行本次 workflow；
检查本次输出；
打包本次结果；
写回 family root；
更新 family summary 与 registry entry。
```

---

## 十、Notebook 通用 cell 顺序

任何正式 notebook 的 cell 顺序应遵循以下通用模板：

```text
00_runtime_mode_family_and_user_config
01_mount_google_drive
02_read_or_create_family_manifest
03_prepare_local_workspace
04_clone_or_update_repository
05_install_dependencies
06_read_runtime_overrides
07_copy_and_validate_input_artifacts
08_download_session_models_to_local
09_check_runtime_environment
10_verify_repository_contract
11_run_unit_or_smoke_checks
12_run_current_workflow
13_validate_current_outputs
14_pack_current_outputs_to_family
15_update_family_registry
16_print_final_summary
```

不同类型 notebook 可以跳过不适用 cell，但不得改变以下相对顺序：

```text
先挂载 Drive；
再准备 family；
再准备本地 workspace；
再复制输入；
再下载模型；
再运行 workflow；
再检查输出；
最后打包写回 Drive。
```

---

## 十一、结果打包规则

每个 notebook 结束前必须生成一个结果包或 step 包。

### （一）必须进入结果包的内容

```text
records/
thresholds/
tables/
figures/
reports/
logs/
checks/
artifacts/*.json
configs/*.json
runtime_state/*.json
session_model_manifest.json
runtime_dataset_manifest.json
run_manifest.json
run_summary.json
run_checks.json
```

具体目录可因 notebook 类型不同而为空，但 summary 与 checks 必须说明为空原因。

### （二）不得进入结果包的内容

```text
raw dataset 文件；
processed dataset 大文件；
模型权重文件；
Hugging Face cache；
Torch cache；
临时解压目录；
/tmp；
未登记的 /content 临时文件；
__pycache__；
.git；
大型中间视频或 latent，除非 protocol 明确要求并在 artifact manifest 中登记。
```

### （三）打包格式

推荐格式：

```text
.tar.zst
```

若环境不支持 `zstd`，可退化为：

```text
.zip
```

但必须在 `run_summary.json` 中记录：

```text
archive_format
archive_size_bytes
archive_sha256
archive_created_at
archive_relpath
excluded_patterns
```

---

## 十二、Registry 更新规则

每个 notebook 完成后，必须向 family root 写入本次 registry update：

```text
registry_updates/result_registry_entry.json
```

并追加到全局：

```text
/content/drive/MyDrive/TSTW/registry/result_registry.jsonl
/content/drive/MyDrive/TSTW/registry/family_registry.jsonl
```

Registry entry 至少包含：

```json
{
  "family_id": "string",
  "workflow_key": "string",
  "step_key": "string|null",
  "run_mode": "debug|smoke|formal|release",
  "git_commit": "string",
  "processed_dataset_key": "string|null",
  "input_artifacts": [],
  "output_package": "string",
  "output_package_sha256": "string",
  "summary_path": "string",
  "checks_path": "string",
  "decision": "PASS|FAIL|INCONCLUSIVE",
  "blocking_reasons": [],
  "created_at": "ISO-8601"
}
```

---

## 十三、禁止事项

全项目 notebook 禁止以下行为：

```text
1. 在治理契约中硬编码某个具体阶段构建说明；
2. notebook 之间依赖内存对象、进程状态、/tmp 文件或 /content 未归档目录；
3. 从 Google Drive 直接高频读取 processed video 或 large latent；
4. 将模型文件保存到 Google Drive；
5. 将模型文件打包进 result package；
6. 使用未登记的模型 auto-download；
7. 使用未登记的 dataset split；
8. 将 raw dataset 当作正式实验输入；
9. 将临时 processed dataset 直接传给下游 notebook；
10. 手动拼接正式 tables；
11. 跳过 checks 直接 release；
12. 用 latest、final、best 等弱语义目录覆盖已有结果；
13. 不生成 FAMILY_ID 就写正式结果；
14. 下游 notebook 自动读取“最近一次结果”作为输入；
15. 在 family root 之外散落保存正式结果。
```

---

## 十四、最小合格 notebook 标准

一个 notebook 只有满足以下条件，才能视为符合本治理契约：

```text
1. 有明确 FAMILY_ID；
2. 有明确 WORKFLOW_KEY；
3. 有明确 run_mode；
4. 会话启动时不依赖任何 /content 历史状态；
5. 输入均来自 Drive 中已登记 artifact 或 processed dataset；
6. 模型均在本地会话显式下载或记录自动下载；
7. 输出均写入 family root；
8. 本次运行有 summary；
9. 本次运行有 checks；
10. 本次运行有 package；
11. package 有 sha256；
12. registry 有 entry；
13. 下游 notebook 可仅凭 family artifact 继续执行；
14. 不在治理契约中绑定具体阶段构建内容。
```

---

## 十五、最终约束结论

本项目 notebook 的总体构建原则为：

```text
Raw Dataset 是长期原始仓库；
Processed Dataset 是正式实验输入；
Session Model 是本次 Colab 会话资源；
Family Result 是所有测试与论文结果的唯一归档单元；
Notebook 之间彼此隔离；
跨 notebook 只通过已落盘 artifact handoff；
每次测试或 workflow 必须独立 FAMILY_ID 保存；
分步骤流程保存 steps/<STEP_KEY>/；
非分步骤流程保存单一结果包；
治理契约不显式说明任何具体阶段构建。
```

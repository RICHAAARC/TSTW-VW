# 文件组织契约

## 一、文档定位

本文档是项目全生命周期的文件组织约束契约，用于规定不同类型代码、配置、实验流程、Notebook、文档、测试、工具与发布资产在仓库中的归属边界。本文档不定义具体算法细节，不替代方法机制文档、实验协议文档、Notebook 构造文档或论文结果构建文档。

本文档的核心目标是将项目文件划分为四类：

```text
1. 最终发布版必须保留的核心方法与复现能力；
2. 最终发布版可保留但不属于 main 核心包的复现辅助能力；
3. 仅用于研究开发、Colab 执行和阶段性验证的内部 workflow；
4. 不应进入最终发布版的构建痕迹、历史材料、临时审计产物与占位实现。
```

本文档在全生命周期内约束以下目录：

```text
main/
configs/
experiments/
paper_workflow/
scripts/
tools/
tests/
docs/
audit_reports/
.codex/
examples/
release/
```

本文档遵循如下总体原则：

```text
main/ 只保存项目核心方法、核心协议、核心评估、训练和命令行复现能力；
paper_workflow/ 只保存 Colab 或 Notebook workflow，不属于最终发布版默认内容；
experiments/ 保存阶段性机制验证、论文实验协议与可选复现实验，不得反向污染 main/；
scripts/ 保存数据准备、结果检查、结果打包、release 生成等命令行辅助工具；
docs/builds/ 保存历史构建文档和阶段性说明，不作为 release 资产；
最终发布版默认通过命令行、配置文件和脚本复现，不依赖 Colab notebook。
```

---

## 二、全局文件边界原则

### （一）方法定义与执行环境分离

水印方法、VAE backend、视频处理、攻击模块、统计判决、records、thresholds、table rebuild、训练逻辑和正式评估指标属于方法与协议能力，应放在 `main/` 或由 `main/cli/` 暴露。

Colab 挂载 Google Drive、复制数据、复制模型、Notebook cell 编排、session manifest、Drive 打包和 Notebook 输出检查属于执行环境能力，应放在 `paper_workflow/` 或 `scripts/`，不得放在 `main/`。

禁止出现如下依赖方向：

```text
main/ → paper_workflow/
main/ → notebooks
main/ → Google Drive 固定路径
main/ → Colab 专用 API
main/ → docs/builds/
main/ → audit_reports/
```

允许出现如下依赖方向：

```text
paper_workflow/ → main/
experiments/ → main/
scripts/ → main/
tests/ → main/
tools/harness/ → main/
```

### （二）核心库与实验协议分离

`main/` 只表达“项目最终方法可以做什么”，不表达“某一次阶段性验证如何组织”。

因此，以下内容不得长期保留在 `main/` 中：

```text
单一机制验证 runner；
单一阶段 artifact builder；
Notebook 专用路径布局；
Colab 专用 manifest；
Drive 专用 packager；
为某个临时阶段服务的 placeholder backend；
为某个临时阶段服务的 random scaffold；
仅用于历史构建审计的 contract 文件。
```

如果某段代码可以被最终水印方法、训练、检测或评估长期复用，应抽象为通用模块保留在 `main/`。如果某段代码只服务某个机制验证流程，应放入 `experiments/`。如果某段代码只服务 Colab notebook，应放入 `paper_workflow/`。

### （三）Notebook 与发布复现分离

Notebook 是开发期和远程 GPU 环境下的 workflow 执行入口，不是最终发布版的默认复现入口。最终发布版应优先提供：

```text
命令行入口；
配置文件；
数据集准备脚本；
模型准备或模型下载说明；
评估脚本；
结果检查脚本；
结果打包脚本；
最小 demo。
```

Notebook 可以作为 tutorial 或开发辅助材料单独发布，但不得作为审稿人或复现者唯一入口。

### （四）原始数据、处理后数据与运行结果分离

原始数据不进入仓库。仓库只保存数据准备脚本、manifest schema、示例 manifest 和数据处理说明。

Google Drive 中的数据组织应遵守 Notebook 治理文档中的分层：

```text
Raw Dataset：/content/drive/MyDrive/Datasets/
Processed Dataset：/content/drive/MyDrive/TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/
Family Result：/content/drive/MyDrive/TSTW/results/<WORKFLOW_KEY>/<RUN_ID>_<UTC_TIME>_<SHORT_COMMIT>/
Session Model：Colab 本地会话缓存，不保存到 Google Drive 作为正式模型仓库。
```

仓库中的 `main/` 不得硬编码上述绝对路径。若需要读取数据，应通过配置、manifest 或命令行参数传入。

---

## 三、生命周期目录结构

### （一）开发研究仓库结构

完整研究仓库允许包含以下目录：

```text
.
├── main/
├── configs/
├── experiments/
├── paper_workflow/
├── scripts/
├── tools/
├── tests/
├── docs/
├── examples/
├── audit_reports/
└── .codex/
```

其中，`audit_reports/` 和 `.codex/` 只属于内部开发仓库，不进入最终发布版。

### （二）最终发布版推荐结构

最终发布版推荐结构如下：

```text
.
├── main/
│   ├── core/
│   ├── methods/
│   ├── video/
│   ├── vae/
│   ├── attacks/
│   ├── protocol/
│   ├── analysis/
│   ├── training/
│   └── cli/
├── configs/
│   ├── method/
│   ├── protocol/
│   ├── attacks/
│   ├── backend/
│   ├── data/
│   └── training/
├── scripts/
│   ├── prepare_datasets/
│   ├── prepare_models/
│   ├── run_reproduction/
│   └── package_results/
├── experiments/
│   ├── real_video_vae_latent_probe/
│   ├── paper_main_protocol/
│   └── paper_mechanism_protocol/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── reproduction/
├── docs/
│   ├── method.md
│   ├── reproduction.md
│   ├── dataset_preparation.md
│   ├── model_preparation.md
│   ├── release_boundary.md
│   └── file_organization.md
└── examples/
    └── minimal_demo/
```

需要注意：`paper_workflow/` 默认不进入最终发布版。如果需要公开 Notebook 教程，应放入 `examples/colab/`，并明确标注为 tutorial，而不是核心复现入口。

---

## 四、`main/` 目录契约

### （一）`main/` 的定义

`main/` 是项目核心 Python 包，表示最终水印方法、核心协议、核心评估和训练能力。`main/` 中的代码应满足以下条件之一：

```text
1. 属于水印方法本体；
2. 属于视频、VAE、攻击或数据处理的核心运行依赖；
3. 属于统计判决、records、thresholds、manifest 或 table rebuild 的核心协议；
4. 属于训练、检测、嵌入或评估的发布版功能；
5. 属于命令行复现入口；
6. 属于最终方法或最小 demo 的必要依赖。
```

`main/` 中代码不得满足以下特征：

```text
1. 只服务 Colab cell 编排；
2. 只服务 Google Drive 挂载或结果回传；
3. 只服务某个历史阶段构建；
4. 只服务 Codex 修复流程；
5. 只服务 Notebook 输出检查；
6. 只服务临时 scaffold、placeholder 或 random backend；
7. 只服务开发期审计报告生成。
```

### （二）推荐 `main/` 子目录职责

```text
main/core/
```

保存 digest、records、schema、manifest、registry、artifact trace 等核心治理能力。该目录不得出现 Colab、Drive、Notebook、FAMILY_ID 目录布局或阶段性 runner 语义。

```text
main/methods/
```

保存水印方法本体，例如 codebook、tubelet partition、embedding、synchronization、evidence、fusion、method interface。文件名不得使用 `placeholder`、`random`、`new`、`best`、`final_method` 等弱语义。

```text
main/video/
```

保存真实视频读写、帧预处理、视频 artifact metadata、dataset manifest 解析等通用能力。该目录可以处理 `.mp4`、帧采样、resize、fps、frame count 与 video digest，但不得硬编码 Drive 路径。

```text
main/vae/
```

保存 VAE backend 抽象、VAE registry、真实 VAE 实现、latent codec、模型 metadata 抽象。该目录可以支持本地模型路径或模型 ID，但不得承担 Colab 模型下载、Drive 复制或 session cache 管理。

```text
main/attacks/
```

保存真实攻击接口、压缩攻击、空间攻击、时间攻击、噪声攻击和攻击 registry。最终发布版中默认 registry 不应以 tensor scaffold 或 placeholder attack 作为 formal 默认路径。

```text
main/protocol/
```

保存 split、event plan、calibration、detection、evaluation、output layout 等通用协议能力。该目录不得保存单一阶段 runner 的全部编排逻辑。若某个 runner 只服务机制验证，应迁移到 `experiments/`。

```text
main/analysis/
```

保存质量指标、时序指标、table builder、report builder、failure case exporter 等通用评估与重建能力。该目录中默认正式入口应使用真实指标，不应以 placeholder metric 作为 formal 默认。

```text
main/training/
```

保存训练相关的模型、loss、dataset wrapper、trainer 和 checkpoint metadata。若当前项目尚未训练，可保留为空目录或暂不创建。

```text
main/cli/
```

保存发布版命令行入口，例如 embed、detect、evaluate、train、prepare_dataset 或 run_eval。命令行入口应是最终发布版复现的首选方式。

### （三）当前代码迁移约束

当前项目中以下路径不应长期保留在 `main/`：

```text
main/colab/
main/protocol/real_video_vae_latent_runner.py
main/protocol/real_video_vae_latent_paths.py 中的 colab_* 路径字段
main/analysis/real_video_vae_latent_artifacts.py
main/backends/synthetic_video_latent.py
main/backends/synthetic_latent_backend_random.py
main/vae/video_vae_backend_placeholder.py
main/attacks/identity_attack_placeholder.py
main/methods/temporal_tubelet_watermark/method_placeholder.py
main/methods/temporal_tubelet_watermark/synthetic_tubelet_sync_contract.py
```

处理原则如下：

```text
1. 通用能力提取后留在 main/；
2. 阶段性流程迁移到 experiments/；
3. Colab 会话能力迁移到 paper_workflow/；
4. 命令行辅助能力迁移到 scripts/ 或 main/cli/；
5. placeholder 与 random 实现默认不进入最终发布版。
```

---

## 五、`configs/` 目录契约

### （一）配置文件定位

`configs/` 保存最终方法与正式复现实验所需的配置，不保存某次 Notebook 的临时 override，不保存 Google Drive 绝对路径，不保存 session-only 模型缓存路径。

推荐结构：

```text
configs/
├── method/
├── protocol/
├── attacks/
├── backend/
├── data/
├── training/
├── schema/
└── release/
```

### （二）配置进入发布版的条件

配置进入最终发布版必须满足：

```text
1. 文件名使用机制语义；
2. 配置键遵守字段注册与命名治理；
3. 不包含本地绝对路径；
4. 不包含 Google Drive 个人路径；
5. 不包含 Notebook cell 临时变量；
6. 不依赖历史 stage 编号；
7. 不以 placeholder / random 配置作为 formal 默认。
```

### （三）阶段性配置处理

机制验证或阶段性实验配置应放入：

```text
experiments/<experiment_key>/configs/
```

若某个配置已成为最终论文复现 protocol 的一部分，可以复制或提升到顶层 `configs/`，但必须去掉阶段性、Notebook 专用和 placeholder 语义。

---

## 六、`experiments/` 目录契约

### （一）`experiments/` 的定义

`experiments/` 保存研究验证流程、论文实验协议、消融实验、机制验证 runner、实验专用 artifact builder 和实验级配置。它可以进入最终发布版，但不属于 `main/` 核心方法包。

推荐结构：

```text
experiments/
├── synthetic_tubelet_sync_probe/
├── real_video_vae_latent_probe/
├── trajectory_statistic_probe/
├── trajectory_aware_sampling_probe/
├── paper_main_protocol/
└── paper_mechanism_protocol/
```

### （二）实验目录允许包含的内容

```text
runner.py
artifact_builder.py
configs/
README.md
checks.py
make_tables.py
make_report.py
```

实验目录可以调用 `main/`，但 `main/` 不得调用 `experiments/`。

### （三）实验目录与发布版关系

最终发布版可以选择保留 `experiments/` 中与论文复现直接相关的实验，例如 `paper_main_protocol/` 和 `paper_mechanism_protocol/`。早期机制验证目录可以作为 appendix reproduction 保留，也可以在 minimal release 中剔除。

判定规则如下：

```text
若实验是论文主结论、附录结论或关键机制存在性证明的一部分，则可进入发布版；
若实验只是内部工程阶段检查、scaffold 验证或历史构建流程，则不进入 minimal release；
若实验 runner 中包含 Notebook、Drive、Colab 专用逻辑，则必须先剥离后才能进入发布版。
```

---

## 七、`paper_workflow/` 目录契约

### （一）目录定位

`paper_workflow/` 保存 Colab notebook、Notebook session 工具、Google Drive handoff、family result 编排、shard 合并、Notebook 检查和 Notebook 打包流程。其存在原因是开发者本地没有真实 GPU 环境，需要通过 Colab 验证核心代码和实验流程。

`paper_workflow/` 不属于最终发布版默认内容。

### （二）允许包含的内容

```text
paper_workflow/
├── <StageX_Purpose>.ipynb
├── colab_utils/
├── notebook_utils/
├── workflow_configs/
├── workflow_docs/
├── workflow_tests/
└── README.md
```

其中，`colab_utils/` 可以包含：

```text
runtime_check.py
drive_packager.py
tar_zst_packager.py
session_manifest.py
family_registry_utils.py
```

其中，`notebook_utils/` 可以包含：

```text
real_video_vae_latent_notebook_helper.py
```

命名与归属规则如下：

```text
1. `paper_workflow/` 根下的 governed notebook 使用 stage-free `snake_case` 语义命名，当前固定为 `build_processed_real_video_dataset.ipynb`、`run_real_video_vae_latent_probe.ipynb` 与 `run_baseline_comparison_gate.ipynb`。
2. notebook-specific helper 若存在，必须位于 `paper_workflow/notebook_utils/`，并使用 stage-free `snake_case`。
3. 仅有跨 notebook 共享价值的 helper 才能留在 `paper_workflow/colab_utils/`，并保持通用 snake_case 命名。
4. 不得把单一 notebook 的兼容 wrapper 伪装成 `colab_utils/` 下的共享工具，也不得在 `paper_workflow/` 路径中保留任何数字阶段缩写形式的弱编号文件名。
```

### （三）禁止内容

`paper_workflow/` 中不得定义最终方法逻辑，例如：

```text
watermark embedding；
watermark detection；
VAE encode / decode 算法；
attack 实现；
threshold calibration；
正式 metrics 计算；
正式 table builder；
训练 loss；
模型结构。
```

这些逻辑必须位于 `main/`，由 Notebook 调用。

### （四）Notebook 进入公开版本的条件

Notebook 只有在作为 tutorial 或 demo 时才可进入公开版本，并应迁移到：

```text
examples/colab/
```

公开 Notebook 必须声明：

```text
1. 该 Notebook 是辅助教程，不是核心复现入口；
2. 命令行复现入口位于 main/cli/ 或 scripts/；
3. Notebook 不保存模型权重到 Google Drive；
4. Notebook 结果必须通过正式 checker 验证。
```

---

## 八、`scripts/` 目录契约

### （一）目录定位

`scripts/` 保存最终发布版可保留的命令行辅助工具。它不同于 `main/cli/`：

```text
main/cli/：面向方法功能的正式入口；
scripts/：面向仓库操作、数据准备、模型准备、runtime profiling、结果检查、结果打包和 release 生成的辅助入口。
```

### （二）推荐结构

```text
scripts/
├── prepare_datasets/
│   └── build_processed_real_video_dataset.py
├── prepare_models/
│   └── prepare_session_autoencoder_kl.py
├── check_results/
│   ├── real_video_vae_latent_output_checker.py
│   ├── check_real_video_vae_latent_outputs.py
│   └── summarize_run_failures.py
├── profile_runtime/
│   ├── capture_colab_environment.py
│   ├── profile_run_timing.py
│   ├── summarize_run_timing.py
│   ├── profile_gpu_runtime.py
│   ├── summarize_gpu_profile.py
│   ├── estimate_real_video_vae_latent_run_scale.py
│   ├── watch_real_video_vae_latent_progress.py
│   ├── profile_drive_io.py
│   └── recommend_runtime_parameters.py
└── package_results/
  ├── drive_packager.py
  ├── tar_zst_packager.py
  ├── package_real_video_vae_latent_outputs.py
  └── package_real_video_vae_latent_tar_zst.py
```

### （三）脚本约束

`scripts/` 可以读取用户提供的本地路径、数据集路径和模型路径，但必须通过命令行参数传入，不得硬编码个人机器路径或 Google Drive 路径。

`scripts/` 进入发布版的条件是：

```text
1. 可通过命令行运行；
2. 不依赖 Notebook cell 状态；
3. 不依赖 Colab 专用 API；
4. 输出 records、tables、reports 或 packages 时遵守 main/core 与 main/analysis 的正式 schema；
5. 可在 README 或 reproduction 文档中被审稿人执行。
```

---

## 九、`tools/` 与 `.codex/` 目录契约

### （一）`tools/` 的定位

`tools/` 保存工程审计、仓库检查、静态扫描、schema 验证和发布前检查工具。`tools/harness/` 可以调用 `main/`，但 `main/` 不得调用 `tools/`。

`tools/` 是否进入最终发布版取决于 release 类型：

```text
完整研究发布版：可以保留 tools/harness/ 中与审稿复现有关的检查工具；
最小方法发布版：可以剔除 tools/harness/，只保留必要的 scripts/check_outputs.py；
内部开发版：保留完整 tools/。
```

### （二）`.codex/` 的定位

`.codex/` 只属于内部开发、自动修复和代码审计工作流，不进入最终发布版。任何最终方法、实验、训练或复现能力不得依赖 `.codex/`。

---

## 十、`tests/` 目录契约

### （一）测试分层

当前研究仓库的测试构建规则以 `docs/test_case_constraints.md` 为准。受治理测试结构固定为：

```text
tests/
├── constraints/
├── functional/
├── integration/
├── helpers/
├── fixtures/
└── conftest.py
```

其中：

```text
constraints/：命名、边界、schema、字段、文档、配置、Notebook contract、formal rule 等轻量约束测试；
functional/：纯函数、mock backend、tiny fixture、轻量 I/O、registry、metric、packager contract 等 quick 功能测试；
integration/：runner、run_root、records/tables/reports rebuild、真实 mp4/ffmpeg、smoke、slow 与 formal gate 测试；
helpers/：测试共享 helper，不得以 test_ 开头；
fixtures/：极小 checked-in fixture，不保存正式输出。
```

`tests/` 根目录不得直接新增 `test_*.py`。新增测试必须先判断属于 `constraints/`、`functional/` 还是 `integration/`。

### （二）默认 pytest 口径

默认 `pytest -q` 只执行：

```text
constraint or unit or quick
```

并默认排除：

```text
integration
smoke
slow
formal
```

`pyproject.toml` 必须声明完整 marker 集合：`unit`、`constraint`、`quick`、`integration`、`smoke`、`slow`、`formal`。runner-backed、formal、smoke、broad attack matrix 和重型 artifact rebuild 测试不得通过缺省 marker 混入默认测试。

### （三）发布版测试选择

最终发布版默认保留：

```text
tests/constraints/
tests/functional/
tests/integration/
```

可按 release 类型剔除内部 notebook、Drive、harness-only 约束测试，但剔除前必须保证核心方法、协议、复现 CLI 和 artifact rebuild 仍有对应发布版测试覆盖。

### （四）测试命名约束

测试文件名必须使用机制语义，不得使用弱阶段编号。推荐示例：

```text
test_real_video_vae_latent_backend.py
test_fixed_low_fpr_calibration.py
test_temporal_sync_detection.py
test_video_compression_attack.py
test_quality_metrics_rebuild.py
```

不推荐：

```text
test_stage2.py  # 禁止：弱阶段编号
test_p2_runner.py  # 禁止：弱版本后缀
test_final.py
test_new_method.py
```

测试输出必须使用 `tmp_path` 或 `tmp_path_factory`，不得写入 checked-in `outputs/`、仓库根目录临时文件、Google Drive 或 `/content/drive/` 路径。

---

## 十一、`docs/` 目录契约

### （一）文档分类

推荐结构：

```text
docs/
├── method.md
├── reproduction.md
├── dataset_preparation.md
├── model_preparation.md
├── release_boundary.md
├── file_organization.md
├── naming_governance.md
├── placeholder_random_governance.md
├── notebook_construction_governance.md
├── protocol_artifact_schema.md
└── builds/
```

### （二）`docs/builds/` 定位

`docs/builds/` 保存历史构建说明、阶段性修复文档、Codex prompt、Notebook 构建文档和中间状态说明。该目录允许保留历史阶段命名和弱阶段描述，但不作为最终 release asset。

`docs/builds/` 中内容不得被 `main/`、`experiments/` 或 `scripts/` 作为运行时输入。

### （三）发布文档

最终发布版至少应包含：

```text
README.md
docs/method.md
docs/reproduction.md
docs/dataset_preparation.md
docs/model_preparation.md
docs/release_boundary.md
docs/file_organization.md
```

Notebook 相关治理文档可保留在完整研究仓库中，但 minimal release 可以剔除。

---

## 十二、`examples/` 与 `release/` 目录契约

### （一）`examples/`

`examples/` 保存最小 demo、命令行示例和可选 tutorial。推荐结构：

```text
examples/
├── minimal_demo/
├── command_line_reproduction/
└── colab/
```

其中，`examples/colab/` 只在明确公开 Notebook tutorial 时使用。默认 release 不依赖该目录。

### （二）`release/`

当前生命周期中不得提前创建 `minimal_release/` 或 release artifact 目录。只有当 governed records、manifests、tables、audits 与复现脚本成熟后，才允许进入 release extraction。

进入 release extraction 后，可生成：

```text
release/
├── method_core/
├── protocol_core/
├── minimal_demo/
├── configs/
├── scripts/
└── release_manifest.json
```

release extraction 必须保持对 governed configs、records 与 manifests 的可追溯性。

---

## 十三、发布边界分类表

| 类型 | 默认位置 | 是否属于 main | 是否进入最终发布版 | 说明 |
|---|---|---:|---:|---|
| 水印方法本体 | `main/methods/` | 是 | 是 | codebook、embedding、sync、evidence、fusion |
| 视频 IO | `main/video/` | 是 | 是 | `.mp4` 读取、帧标准化、视频 artifact |
| VAE backend | `main/vae/` | 是 | 是 | 真实 VAE 接口和实现 |
| 攻击实现 | `main/attacks/` | 是 | 是 | 压缩、空间、时间、噪声攻击 |
| 统计判决 | `main/protocol/` | 是 | 是 | split、calibration、threshold、evaluation |
| 正式指标 | `main/analysis/` | 是 | 是 | quality、temporal、tables、reports |
| 命令行入口 | `main/cli/` | 是 | 是 | embed、detect、evaluate、train |
| 数据准备脚本 | `scripts/prepare_datasets/` | 否 | 是 | 供复现者处理数据 |
| 结果打包脚本 | `scripts/package_results/` | 否 | 是 | 命令行打包，不依赖 Colab |
| 机制验证 runner | `experiments/` | 否 | 可选 | 与论文复现相关时保留 |
| 论文主实验协议 | `experiments/paper_*` | 否 | 是 | 若支撑论文结果，应保留 |
| Colab notebook | `paper_workflow/` | 否 | 默认否 | 可作为 tutorial 单独公开 |
| Colab 工具 | `paper_workflow/colab_utils/` | 否 | 默认否 | Drive、session、Notebook checker |
| Notebook 专用 helper | `paper_workflow/notebook_utils/` | 否 | 默认否 | 单 notebook / 单阶段 wrapper |
| Harness 审计 | `tools/harness/` | 否 | 可选 | 完整研究版可保留，minimal release 可剔除 |
| 历史构建文档 | `docs/builds/` | 否 | 否 | 不作为 release asset |
| Codex 约束 | `.codex/` | 否 | 否 | 内部开发专用 |
| 审计报告 | `audit_reports/` | 否 | 否 | 生成物，不进 release |
| 原始数据 | 仓库外 | 否 | 否 | 只提供下载和处理脚本 |
| 模型权重 | 仓库外 | 否 | 否 | 只提供模型准备说明和 manifest |

---

## 十四、当前项目的具体迁移判定

### （一）应保留在 `main/` 的当前文件

```text
main/core/digest.py
main/core/manifest.py
main/core/records.py
main/core/registry.py
main/core/schema.py
main/core/tensor_artifact.py
main/methods/temporal_tubelet_watermark/codebook.py
main/methods/temporal_tubelet_watermark/embedding.py
main/methods/temporal_tubelet_watermark/evidence.py
main/methods/temporal_tubelet_watermark/fusion.py
main/methods/temporal_tubelet_watermark/interfaces.py
main/methods/temporal_tubelet_watermark/synchronization.py
main/methods/temporal_tubelet_watermark/tubelet_partition.py
main/video/video_io.py
main/video/frame_preprocess.py
main/video/video_artifact.py
main/video/dataset_manifest.py
main/vae/vae_backend.py
main/vae/vae_registry.py
main/vae/diffusers_autoencoder_kl_framewise.py
main/vae/vae_tensor_codec.py
main/attacks/compression.py
main/attacks/spatial.py
main/attacks/temporal.py
main/attacks/video_attack_interfaces.py
main/attacks/video_noise.py
main/protocol/calibrator.py
main/protocol/detector_runner.py
main/protocol/evaluator.py
main/protocol/event_builder.py
main/protocol/split_builder.py
main/analysis/quality_metrics.py
main/analysis/real_video_quality_metrics.py
main/analysis/real_video_temporal_metrics.py
main/analysis/table_builder.py
main/analysis/report_builder.py
main/analysis/failure_case_exporter.py
main/analysis/curve_builder.py
main/analysis/figure_builder.py
main/analysis/temporal_metrics.py
```

其中，`quality_metrics.py` 与 `temporal_metrics.py` 需要确保 formal 默认使用真实指标，placeholder 仅作为显式 smoke 或 legacy 模式存在。

### （二）应从 `main/` 迁出的当前文件

```text
main/colab/drive_packager.py
main/colab/notebook_result_checker.py
main/colab/runtime_check.py
main/colab/tar_zst_packager.py
main/protocol/real_video_vae_latent_runner.py
main/protocol/real_video_vae_latent_paths.py
main/analysis/real_video_vae_latent_artifacts.py
main/backends/synthetic_video_latent.py
main/backends/synthetic_latent_backend_random.py
main/methods/temporal_tubelet_watermark/synthetic_tubelet_sync_contract.py
```

推荐迁移目标：

```text
main/colab/*
→ paper_workflow/colab_utils/*

main/protocol/real_video_vae_latent_runner.py
→ experiments/real_video_vae_latent_probe/runner.py

main/protocol/real_video_vae_latent_paths.py
→ experiments/real_video_vae_latent_probe/output_layout.py
  或抽象后迁入 main/protocol/output_layout.py

main/analysis/real_video_vae_latent_artifacts.py
→ experiments/real_video_vae_latent_probe/artifact_builder.py

main/backends/synthetic_video_latent.py
→ experiments/synthetic_tubelet_sync_probe/backend.py

main/backends/synthetic_latent_backend_random.py
→ experiments/protocol_skeleton/backend_random.py

main/methods/temporal_tubelet_watermark/synthetic_tubelet_sync_contract.py
→ experiments/synthetic_tubelet_sync_probe/contract.py
```

### （三）应重命名或清理的当前文件

```text
main/methods/temporal_tubelet_watermark/method_placeholder.py
→ main/methods/temporal_tubelet_watermark/method.py

main/attacks/real_video_attack_registry.py
→ main/attacks/registry.py

main/attacks/identity_attack_placeholder.py
→ experiments/protocol_skeleton/identity_attack.py
  或删除出 release

main/vae/video_vae_backend_placeholder.py
→ experiments/protocol_skeleton/video_vae_backend_placeholder.py
  或删除出 release

main/video/dataset_localizer.py
→ scripts/prepare_datasets/dataset_localizer.py
  或保留为 main/video/dataset_resolver.py，前提是完全去 Colab / Drive 语义

main/vae/model_localizer.py
→ scripts/prepare_models/model_resolver.py
  或保留为 main/vae/model_resolver.py，前提是完全去 Colab / Drive 语义
```

---

## 十五、迁移顺序约束

### （一）第一步：迁移 Colab 工具

先迁移 `main/colab/`，因为该步骤不改变核心算法结果。

```text
main/colab/*
→ paper_workflow/colab_utils/*
```

同步更新：

```text
paper_workflow/*.ipynb
tests/workflow/*
```

禁止在该步骤中修改方法、VAE、攻击、检测或阈值逻辑。

### （二）第二步：核心路径去 Colab 命名

将核心 artifact 字段中的 `colab_*` 改为中性命名：

```text
colab_runtime_manifest → runtime_manifest
colab_runtime_config → runtime_config
colab_result_checker → result_checker
```

Notebook 可以额外写入 `colab_session_manifest`，但该字段不得成为 core protocol 的必需路径。

### （三）第三步：阶段性 runner 迁入 `experiments/`

将 `real_video_vae_latent_runner.py` 和对应 artifact builder 迁入 `experiments/real_video_vae_latent_probe/`。通用逻辑提取到 `main/protocol/` 和 `main/analysis/`。

### （四）第四步：补齐发布版 CLI

新增或完善：

```text
main/cli/embed.py
main/cli/detect.py
main/cli/evaluate.py
main/cli/train.py
```

在 CLI 可复现前，不应删除内部 Notebook workflow。

### （五）第五步：清理 placeholder 与 random scaffold

在真实路径完全可运行后，将 placeholder 和 random scaffold 移出 release 默认路径。若仍需保留用于测试，应放入 `experiments/protocol_skeleton/` 或 `tests/fixtures/`。

### （六）第六步：执行 release extraction

只有在正式论文协议、records、tables、reports、audits 和命令行复现稳定后，才允许生成 release 目录或 minimal release 包。

---

## 十六、阻断违规规则

以下情况应视为文件组织阻断违规：

```text
1. main/ 中出现 Colab 专用 API import；
2. main/ 中硬编码 /content/drive/MyDrive/ 路径；
3. main/ 中出现 notebook_result_checker、drive_packager、colab_runtime_manifest 等会话工具；
4. paper_workflow/ 中定义水印嵌入、检测、攻击或指标算法；
5. experiments/ 中的阶段 runner 被 main/ 反向 import；
6. release 默认入口依赖 paper_workflow/；
7. final 或 formal 配置默认使用 placeholder backend；
8. formal records 中出现未登记 placeholder 或 random 字段；
9. docs/builds/ 被运行时模块读取；
10. `.codex/` 或 audit_reports/ 被 release 代码依赖；
11. 原始数据、模型权重或个人 Drive 路径进入仓库；
12. 通过 Notebook 手工拼接正式 tables、figures 或 reports。
```

---

## 十七、审查清单

每次新增文件、移动文件或准备 release 前，应回答以下问题：

```text
1. 该文件是否属于最终方法本体？若是，应放在 main/。
2. 该文件是否只服务某个机制验证或论文实验协议？若是，应放在 experiments/。
3. 该文件是否只服务 Colab 或 Notebook 会话？若是，应放在 paper_workflow/。
4. 该文件是否是数据准备、结果检查或结果打包脚本？若是，应放在 scripts/。
5. 该文件是否是历史构建材料？若是，应放在 docs/builds/，不进入 release。
6. 该文件是否是内部自动修复或审计辅助？若是，应放在 .codex/ 或 tools/，并默认不进入 minimal release。
7. 该文件是否包含 placeholder 或 random 语义？若是，是否已登记，并且是否被排除在 formal claim 之外？
8. 该文件是否硬编码了本地、Drive、Colab 或个人路径？若是，不得放入 main/。
9. 该文件是否被最终命令行复现依赖？若是，应确保它不依赖 Notebook 状态。
10. 删除 paper_workflow/ 后，项目是否仍能通过命令行完成最终方法复现？若否，release 边界尚未合格。
```

---

## 十八、最终判定口径

项目文件组织达标的判定标准为：

```text
main/ 可以独立表达最终方法、核心协议、评估指标和训练能力；
paper_workflow/ 可以完全删除而不影响最终发布版命令行复现；
experiments/ 可以调用 main/ 复现实验，但 main/ 不依赖 experiments/；
scripts/ 可以完成数据准备、模型准备、结果检查和打包；
docs/builds/、audit_reports/、.codex/ 可以完全删除而不影响发布版运行；
formal records、tables、figures、reports 均由正式 builder 生成，不依赖 Notebook 手工拼接；
最终发布版不包含 raw dataset、模型权重、个人路径、Colab session 状态或历史构建痕迹。
```

在该标准下，Colab 仅是开发期 GPU 执行环境，机制验证仅是研究流程，`main/` 才是最终方法和复现能力的核心边界。

## Stage-Two Real-Video Result Layout

For `real_video_vae_latent_probe`, the governed Google Drive result layout is:

```text
/content/drive/MyDrive/TSTW/results/<WORKFLOW_KEY>/<RUN_ID>_<UTC_TIME>_<SHORT_COMMIT>/
```

The legacy generic layout below is forbidden for this stage-two notebook workflow:

```text
/content/drive/MyDrive/TSTW/results/<WORKFLOW_KEY>/<RUN_ID>_<UTC_TIME>_<SHORT_COMMIT>/
```

`FAMILY_ID` and `PROCESSED_DATASET_KEY` values used by governed notebooks must use single-underscore separators as separators. The following style is valid:

```text
real_video_vae_latent_probe_formal_davis2017_trainval480p_utc_time_short_commit
real_video_vae_latent_probe_davis2017_trainval480p_256x256_32f_8fps_freeze001
```

Double-underscore separators are forbidden for notebook result identities; governed result identities must use the single-underscore style shown above.

The run notebook must not create the Google Drive family result directory during workspace preparation. It must first write runner outputs, checker outputs, mechanism summaries, package archives, and notebook final summaries into the Colab session-local family root, then copy the completed family result into the Google Drive result layout above. This prevents failed formal runs from leaving empty family result folders on Google Drive.


# 阶段 2 notebook 构建方法说明

## 一、文件定位

本文档用于指导 Codex 构建本项目的阶段 2 Colab notebook。阶段 2 的工程目标是构建并运行 `real_video_vae_latent_probe`，即在真实视频经 VAE encode、decode、attack 与 re-encode 后，验证阶段 1 已形成的 `frame_prc`、`tubelet_only` 与 `tubelet_sync` 三类方法变体是否仍可在 fixed low-FPR protocol 下稳定运行。

本文档不是算法机制重写说明，也不是论文实验结果说明。Codex 的任务是根据本文档构建可执行、可复现、可归档、符合全局 notebook 治理契约的阶段 2 notebook 与必要的 notebook 支撑脚本。

阶段 2 notebook 必须继承项目级 notebook 总体治理契约，尤其遵守以下原则：

```text
1. 所有 notebook 均视为彼此隔离的 Colab 会话；
2. 跨 notebook handoff 只能通过 Google Drive 中已落盘、已登记、已校验的 artifact；
3. 不允许依赖上一个 notebook 的内存对象、进程状态、/tmp 文件、/content 临时目录或模型缓存；
4. Raw Dataset 只保存在 /content/drive/MyDrive/Datasets/；
5. Processed Dataset 作为正式实验输入，保存在 /content/drive/MyDrive/TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/；
6. 所有模型文件均为 session-only，只能下载到 Colab 本地会话目录，不保存到 Google Drive；
7. 除 raw dataset、processed dataset 与长期 registry 外，所有配置快照、日志、记录、检查、表格、报告、模型 session manifest 与结果包均必须归入 /content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/；
8. 每次测试、每个阶段运行、每个 shard、每个合并结果均必须拥有明确的 FAMILY_ID 或归属到明确的 FAMILY_ID。
```

---

## 二、阶段 2 的总体 workflow 划分

阶段 2 不应由一个 notebook 同时承担“数据切片”和“正式实验运行”。应至少拆分为两个彼此隔离的 notebook：

```text
1. Build_Processed_Dataset_Stage2_Colab.ipynb
   职责：从 Raw Dataset 构建阶段 2 的 processed dataset。

2. Run_Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb
   职责：读取阶段 2 processed dataset，下载 session-only 模型，运行阶段 2 实验，生成 records、thresholds、tables、reports、checks 与结果包。
```

可选地，如果阶段 2 后续扩展为多 shard 运行，可再新增：

```text
3. Merge_Stage2_Family_Results_Colab.ipynb
   职责：只读取多个 shard package，合并 records、tables、checks 与 reports，并生成 family-level release package。
```

需要注意：`Build_Processed_Dataset_Stage2_Colab.ipynb` 的输出是长期 processed dataset，不属于某一次正式实验结果本体；但该 notebook 自身的构建日志、检查报告、dataset summary 与 registry update 仍必须落入某个 `FAMILY_ID` 结果目录。`Run_Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb` 的输出才是阶段 2 实验结果包。

---

## 三、统一身份键设计

### （一）`PROCESSED_DATASET_KEY`

阶段 2 processed dataset 应使用明确且稳定的 `PROCESSED_DATASET_KEY`。推荐格式如下：

```text
stage02_real_video_vae_latent_probe__davis2017_trainval480p__256x256__32f__8fps__freeze001
```

若加入 UCF101 扩展数据，可新增独立 key：

```text
stage02_real_video_vae_latent_probe__ucf101_subset__256x256__32f__8fps__freeze001
```

不允许使用弱语义名称：

```text
dataset
processed
stage2_latest
test_data
final_data
new_processed
```

阶段 2 首轮 Codex 只需构建 DAVIS 2017 的 processed dataset 支持；UCF101 可作为扩展配置预留，但不应作为首轮 formal 的强依赖。

### （二）`FAMILY_ID`

每次 notebook 运行必须生成或读取 `FAMILY_ID`。推荐格式如下：

```text
stage02_real_video_vae_latent_probe__<RUN_MODE>__<PROCESSED_DATASET_KEY>__<UTC_TIME>__<SHORT_COMMIT>
```

示例：

```text
stage02_real_video_vae_latent_probe__smoke__davis2017_trainval480p_256x256_32f_8fps__20260510T180000Z__a1b2c3d
```

`FAMILY_ID` 必须写入：

```text
family_manifest.json
family_summary.json
family_checks.json
step_manifest.json
run_manifest.json
session_model_manifest.json
result package filename
registry entry
```

### （三）`STEP_KEY`

阶段 2 workflow 内推荐使用以下 `STEP_KEY`：

```text
step00_bootstrap
step01_prepare_processed_dataset
step02_run_real_video_vae_latent_probe
step03_rebuild_tables_and_reports
step04_validate_outputs
step05_pack_family_result
```

若采用两个 notebook，则第一个 notebook 覆盖 `step00_bootstrap` 与 `step01_prepare_processed_dataset`，第二个 notebook 覆盖 `step02` 至 `step05`。

---

## 四、Google Drive 与 Colab 本地目录规则

### （一）Google Drive 固定目录

阶段 2 notebook 必须使用以下目录：

```text
/content/drive/MyDrive/
├── Datasets/
│   ├── DAVIS_2017/
│   │   └── raw/
│   │       └── DAVIS-2017-trainval-480p.zip
│   ├── UCF101/
│   │   └── raw/
│   └── MSR_VTT/
│       └── raw/
└── TSTW/
    ├── datasets/
    │   ├── processed/
    │   │   └── <PROCESSED_DATASET_KEY>/
    │   └── registry/
    │       └── dataset_registry.json
    ├── configs/
    ├── results/
    │   └── families/
    │       └── <FAMILY_ID>/
    └── registry/
        ├── family_registry.jsonl
        ├── result_registry.jsonl
        └── drive_state.json
```

禁止将模型文件写入以下目录：

```text
/content/drive/MyDrive/Models/
/content/drive/MyDrive/TSTW/models/
/content/drive/MyDrive/TSTW/model_cache/
```

若历史 Drive 中已有 `Models/` 目录，阶段 2 notebook 不得读取该目录作为正式模型来源，也不得向该目录写入文件。

### （二）Colab 本地运行目录

每个 notebook 必须在本地重新创建工作区：

```text
/content/TSTW_runtime/
├── repo/
├── datasets/
│   └── <PROCESSED_DATASET_KEY>/
├── raw_work/
├── session_models/
├── model_cache/
├── runs/
│   └── <RUN_ID>/
├── packages/
└── logs/
```

该目录只在当前 Colab 会话中有效。任何下游 notebook 不得假设该目录仍然存在。

---

## 五、Notebook 1：Processed Dataset 构建 notebook

### （一）推荐文件名

```text
paper_workflow/Build_Processed_Dataset_Stage2_Colab.ipynb
```

### （二）职责范围

该 notebook 只负责从 Raw Dataset 构建阶段 2 processed dataset。

允许执行：

```text
1. 挂载 Google Drive；
2. 拉取项目代码；
3. 检查 raw dataset 是否存在；
4. 将 raw zip 复制到 /content 本地；
5. 解压 DAVIS 2017；
6. 从 DAVIS sequence 中按固定规则切出 32-frame clips；
7. 统一 fps、resolution、codec 与命名；
8. 计算每个 processed video 的 sha256；
9. 生成 dev / calibration / test split；
10. 保存 processed videos 到 TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/；
11. 生成 dataset_manifest.json、split_manifest.json、sha256_manifest.json、processed_dataset_summary.json；
12. 构建 processed dataset cache package；
13. 更新 dataset_registry.json；
14. 将 notebook 自身的日志、检查和 summary 写入 FAMILY_ID 结果目录。
```

禁止执行：

```text
1. 不加载 VAE；
2. 不加载 LPIPS、CLIP、RAFT 或任何模型；
3. 不嵌入水印；
4. 不运行 video attack；
5. 不运行 detector；
6. 不生成 thresholds；
7. 不生成 main_tpr_fpr_table.csv；
8. 不生成论文结果报告；
9. 不把 processed dataset 只保存在 /content；
10. 不依赖随机切片。
```

### （三）固定 cell 顺序

Codex 必须按以下 cell 顺序构建 notebook：

```text
00_runtime_mode_and_user_config
01_mount_google_drive
02_create_or_load_family_id
03_prepare_local_workspace
04_clone_or_update_repository
05_install_dataset_processing_dependencies
06_validate_raw_dataset_presence
07_copy_raw_dataset_to_local
08_extract_raw_dataset_to_local
09_build_processed_clips_deterministically
10_write_processed_dataset_to_drive
11_compute_processed_dataset_digests
12_build_split_and_dataset_manifests
13_validate_processed_dataset
14_update_dataset_registry
15_pack_processed_dataset_build_records
16_print_final_summary
```

### （四）用户配置 cell 必须包含的变量

`00_runtime_mode_and_user_config` 必须集中定义：

```python
RUN_MODE = "smoke"  # "smoke" or "formal"
PROJECT_GIT_URL = "<repo_url>"
PROJECT_BRANCH = "main"
FAMILY_ID = None  # None means auto-generate
WORKFLOW_KEY = "processed_dataset_build"
PROCESSED_DATASET_KEY = "stage02_real_video_vae_latent_probe__davis2017_trainval480p__256x256__32f__8fps__freeze001"
RAW_DATASET_ROOT = "/content/drive/MyDrive/Datasets"
TSTW_DRIVE_ROOT = "/content/drive/MyDrive/TSTW"
LOCAL_RUNTIME_ROOT = "/content/TSTW_runtime"
SOURCE_DATASET_NAME = "DAVIS_2017"
SOURCE_ARCHIVE_RELPATH = "DAVIS_2017/raw/DAVIS-2017-trainval-480p.zip"
FRAME_COUNT = 32
TARGET_FPS = 8
TARGET_RESOLUTION = [256, 256]
SPATIAL_POLICY = "resize_shorter_side_then_center_crop"
TEMPORAL_POLICY = "middle_32_frames"
CODEC = "libx264"
CRF = 18
DEV_CLIPS_SMOKE = 2
CALIBRATION_CLIPS_SMOKE = 4
TEST_CLIPS_SMOKE = 4
DEV_CLIPS_FORMAL = 10
CALIBRATION_CLIPS_FORMAL = 40
TEST_CLIPS_FORMAL = 40
```

### （五）切片规则

Codex 必须实现确定性切片。推荐规则如下：

```text
1. 对 DAVIS 每个 sequence 按字典序排序；
2. 读取 JPEGImages/480p/<sequence>/ 下的帧；
3. 若帧数小于 FRAME_COUNT，则 formal 模式丢弃该 sequence，smoke 模式允许跳过但必须记录；
4. 若帧数大于等于 FRAME_COUNT，则选取 middle 32 frames；
5. spatial 处理采用 resize shorter side then center crop 到 256×256；
6. 不允许随机 crop；
7. 不允许随机 temporal sampling；
8. 不允许数据增强；
9. 输出 mp4 文件名必须稳定；
10. split 分配必须确定性，不能依赖 Python hash 随机化。
```

推荐输出命名：

```text
videos/davis_<sequence>__middle32__256x256__8fps.mp4
```

### （六）Processed Dataset 输出结构

该 notebook 必须写入：

```text
/content/drive/MyDrive/TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/
├── videos/
│   ├── davis_<sequence>__middle32__256x256__8fps.mp4
│   └── ...
├── manifests/
│   ├── dataset_manifest.json
│   ├── split_manifest.json
│   ├── sha256_manifest.json
│   └── source_trace_manifest.json
├── checks/
│   ├── processed_dataset_checks.json
│   └── split_leakage_checks.json
├── cache/
│   └── <PROCESSED_DATASET_KEY>.tar.zst
└── processed_dataset_summary.json
```

`dataset_manifest.json` 至少包含：

```json
{
  "processed_dataset_key": "stage02_real_video_vae_latent_probe__davis2017_trainval480p__256x256__32f__8fps__freeze001",
  "source_dataset": "DAVIS_2017",
  "source_archive_relpath": "DAVIS_2017/raw/DAVIS-2017-trainval-480p.zip",
  "frame_count": 32,
  "fps": 8,
  "resolution": [256, 256],
  "temporal_policy": "middle_32_frames",
  "spatial_policy": "resize_shorter_side_then_center_crop",
  "samples": [
    {
      "video_source_id": "davis_bear__middle32__256x256__8fps",
      "source_sequence": "bear",
      "source_frame_start": 10,
      "source_frame_end": 41,
      "split": "calibration",
      "processed_relpath": "videos/davis_bear__middle32__256x256__8fps.mp4",
      "frame_count": 32,
      "fps": 8,
      "resolution": [256, 256],
      "video_sha256": "sha256..."
    }
  ]
}
```

### （七）Family 结果记录

虽然 processed dataset 本体长期保存于 `TSTW/datasets/processed/`，但该 notebook 必须将构建过程记录写入：

```text
/content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/
├── family_manifest.json
├── family_summary.json
├── family_checks.json
└── steps/
    └── step01_prepare_processed_dataset/
        ├── step_manifest.json
        ├── logs/
        ├── checks/
        ├── summaries/
        └── packages/
            └── step01_prepare_processed_dataset.tar.zst
```

该 step package 不应重复打包完整 processed videos，但必须包含 processed dataset manifest、summary、checks、registry update record 与构建日志。

---

## 六、Notebook 2：阶段 2 实验运行 notebook

### （一）推荐文件名

```text
paper_workflow/Run_Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb
```

### （二）职责范围

该 notebook 负责读取阶段 2 processed dataset，并运行 real video VAE latent probe。

允许执行：

```text
1. 挂载 Google Drive；
2. 创建或读取 FAMILY_ID；
3. 拉取项目代码；
4. 安装依赖；
5. 将 processed dataset cache 复制并解压到 /content/TSTW_runtime/datasets/<PROCESSED_DATASET_KEY>/；
6. 校验 processed dataset manifest 与 sha256；
7. 在 Colab 本地 session 下载 VAE、LPIPS 或其他运行所需模型；
8. 记录 session_model_manifest.json；
9. 运行阶段 2 runner；
10. 生成 records、thresholds、tables、figures、reports、checks；
11. 执行结果一致性检查；
12. 打包 family step result；
13. 更新 family registry 与 result registry。
```

禁止执行：

```text
1. 不从 Raw Dataset 临时切片；
2. 不修改 processed dataset；
3. 不将模型文件保存到 Google Drive；
4. 不直接从 Google Drive 高频读取 mp4 或 latent；
5. 不手动拼接正式 tables；
6. 不绕过 records 写 thresholds；
7. 不依赖上一个 notebook 的 /content、/tmp、HF cache、torch cache 或内存对象；
8. 不把模型文件打包进 family result；
9. 不在 test split 上更新 threshold、embedding margin、sync search range 或 fusion rule。
```

### （三）固定 cell 顺序

Codex 必须按以下 cell 顺序构建 notebook：

```text
00_runtime_mode_and_user_config
01_mount_google_drive
02_create_or_load_family_id
03_prepare_local_workspace
04_clone_or_update_repository
05_install_runtime_dependencies
06_copy_and_validate_processed_dataset
07_download_session_models_to_local
08_check_gpu_and_runtime
09_verify_repository_contract
10_run_stage2_smoke_or_formal
11_rebuild_tables_and_reports
12_validate_stage2_outputs
13_pack_family_step_result
14_update_family_and_result_registry
15_print_final_summary
```

### （四）用户配置 cell 必须包含的变量

```python
RUN_MODE = "smoke"  # "smoke" or "formal"
PROJECT_GIT_URL = "<repo_url>"
PROJECT_BRANCH = "main"
FAMILY_ID = None  # None means auto-generate
WORKFLOW_KEY = "detection_evaluation"
STEP_KEY = "step02_run_real_video_vae_latent_probe"
PROCESSED_DATASET_KEY = "stage02_real_video_vae_latent_probe__davis2017_trainval480p__256x256__32f__8fps__freeze001"
TSTW_DRIVE_ROOT = "/content/drive/MyDrive/TSTW"
LOCAL_RUNTIME_ROOT = "/content/TSTW_runtime"
USE_GPU_REQUIRED_FOR_FORMAL = True
TARGET_FPR = 0.001
METHOD_VARIANTS = ["frame_prc", "tubelet_only", "tubelet_sync"]
ATTACK_MATRIX_KEY_SMOKE = "real_video_attack_smoke_matrix"
ATTACK_MATRIX_KEY_FORMAL = "real_video_attack_matrix"
VAE_MODEL_ID = "stabilityai/sd-vae-ft-mse"
VAE_MODEL_REVISION = "main"
ALLOW_LPIPS_TORCHVISION_BACKBONE_AUTO_DOWNLOAD = True
INCLUDE_MODEL_FILES_IN_RESULT_PACKAGE = False
```

### （五）Processed Dataset 读取规则

实验 notebook 必须读取：

```text
/content/drive/MyDrive/TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/cache/<PROCESSED_DATASET_KEY>.tar.zst
```

然后复制到本地：

```text
/content/TSTW_runtime/datasets/<PROCESSED_DATASET_KEY>/
```

本地解压后必须校验：

```text
1. dataset_manifest.json 存在；
2. split_manifest.json 存在；
3. sha256_manifest.json 存在；
4. dev / calibration / test 均非空；
5. sample id 无重复；
6. 同一 processed video 不跨 split；
7. 每个 video 文件存在且 sha256 匹配；
8. frame_count、fps、resolution 与 manifest 一致。
```

禁止实验 notebook 扫描 raw dataset 或自行决定 split。

### （六）Session-only 模型下载规则

阶段 2 实验 notebook 需要 VAE 与质量指标模型。所有模型相关文件只能下载到：

```text
/content/TSTW_runtime/session_models/
/content/TSTW_runtime/model_cache/
/root/.cache/huggingface/
/root/.cache/torch/
```

不得保存到 Google Drive。Notebook 必须包含显式模型下载 cell：

```text
07_download_session_models_to_local
```

该 cell 必须完成：

```text
1. 明确列出本次需要的模型角色；
2. 明确列出 repo_id、revision、下载方式、local path；
3. 下载 VAE 到 /content/TSTW_runtime/session_models/；
4. 允许 LPIPS backbone 由 torchvision 或 lpips 在 Colab 本地自动下载；
5. 记录模型下载、加载和 cache 事实；
6. 生成 run_root/artifacts/session_model_manifest.json；
7. 生成 run_root/logs/session_model_download.log。
```

`session_model_manifest.json` 至少包含：

```json
{
  "model_policy": "session_only_no_drive_model_storage",
  "models": [
    {
      "model_role": "stage2_vae",
      "repo_id": "stabilityai/sd-vae-ft-mse",
      "revision": "main",
      "local_path": "/content/TSTW_runtime/session_models/stabilityai_sd-vae-ft-mse",
      "load_api": "AutoencoderKL.from_pretrained",
      "saved_to_drive": false,
      "included_in_result_package": false
    },
    {
      "model_role": "lpips_quality_metric",
      "source": "lpips_and_torchvision_runtime_cache",
      "allow_torchvision_backbone_auto_download": true,
      "local_cache_policy": "session_only",
      "saved_to_drive": false,
      "included_in_result_package": false
    }
  ]
}
```

Formal result package 不得包含：

```text
*.pth
*.pt
*.ckpt
*.safetensors
*.bin
/root/.cache/huggingface/
/root/.cache/torch/
/content/TSTW_runtime/session_models/
/content/TSTW_runtime/model_cache/
```

### （七）阶段 2 runner 调用规则

Codex 应优先调用项目正式 runner，不应在 notebook 中重写实验逻辑。推荐命令形式如下：

```bash
python -m main.protocol.stage2_runner \
  --run-mode "$RUN_MODE" \
  --family-id "$FAMILY_ID" \
  --run-root "/content/TSTW_runtime/runs/${FAMILY_ID}" \
  --processed-dataset-root "/content/TSTW_runtime/datasets/${PROCESSED_DATASET_KEY}" \
  --processed-dataset-key "$PROCESSED_DATASET_KEY" \
  --protocol-config configs/protocol/real_video_vae_latent_probe.json \
  --backend-config configs/backend/real_video_vae_latent.json \
  --attack-matrix "$ATTACK_MATRIX_CONFIG" \
  --target-fpr "$TARGET_FPR" \
  --method-variants frame_prc tubelet_only tubelet_sync \
  --session-model-manifest "/content/TSTW_runtime/runs/${FAMILY_ID}/artifacts/session_model_manifest.json"
```

如果仓库暂时没有 `main.protocol.stage2_runner`，Codex 可以新增该 CLI，但不得把 runner 逻辑直接写在 notebook cell 中。

### （八）阶段 2 输出目录

阶段 2 runner 的本地输出必须为：

```text
/content/TSTW_runtime/runs/<FAMILY_ID>/
├── records/
│   └── event_scores.jsonl
├── thresholds/
│   └── thresholds.json
├── artifacts/
│   ├── run_manifest.json
│   ├── session_model_manifest.json
│   ├── dataset_input_manifest.json
│   ├── artifact_manifest.json
│   └── runtime_config_snapshot.json
├── tables/
│   ├── main_tpr_fpr_table.csv
│   ├── ablation_table.csv
│   ├── real_video_attack_breakdown.csv
│   ├── quality_table.csv
│   └── temporal_consistency_table.csv
├── figures/
├── reports/
│   └── vae_latent_probe_report.md
├── checks/
│   └── stage2_output_checks.json
├── failure_case_gallery/
└── logs/
```

然后 notebook 将该 run root 打包并保存到：

```text
/content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/steps/step02_run_real_video_vae_latent_probe/packages/<FAMILY_ID>__step02_run_real_video_vae_latent_probe.tar.zst
```

同时写入：

```text
/content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/family_manifest.json
/content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/family_summary.json
/content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/family_checks.json
/content/drive/MyDrive/TSTW/results/families/<FAMILY_ID>/steps/step02_run_real_video_vae_latent_probe/step_manifest.json
```

---

## 七、阶段 2 实验语义约束

Codex 构建 notebook 时必须保持阶段 2 实验边界。

### （一）允许的证据链

阶段 2 只允许：

```text
S_tubelet
S_sync
S_final
```

`S_traj` 必须存在但为 `null`：

```json
{
  "evidence_scores": {
    "S_tubelet": 0.0,
    "S_sync": 0.0,
    "S_traj": null,
    "S_final": 0.0
  },
  "disabled_evidence": ["trajectory"]
}
```

### （二）禁止内容

阶段 2 notebook 不得引入：

```text
1. Flow Matching trajectory statistic；
2. DiT sampling hook；
3. trajectory-aware embedding；
4. real video generation pipeline；
5. Wan2.1 / CogVideoX / SVD 作为阶段 2 主实验模型；
6. test split threshold tuning；
7. attack-specific threshold；
8. 手动改表；
9. 失败样例静默过滤。
```

阶段 2 的 VAE 只用于真实视频 latent encode / decode / re-encode，不代表已经接入最终 DiT / Flow Matching 视频生成模型。

### （三）sample role 约束

阶段 2 records 必须包含：

```text
clean_negative
attacked_negative
watermarked_positive
attacked_positive
```

生成关系必须为：

```text
clean_negative：processed source video，不嵌入水印；
watermarked_positive：processed source video 经 VAE encode 后在 latent 中嵌入水印并 decode；
attacked_negative：clean_negative 经同一 attack matrix 攻击后再 re-encode；
attacked_positive：watermarked_positive 经同一 attack matrix 攻击后再 re-encode。
```

不得只攻击 positive，也不得只报告 positive。

### （四）threshold 约束

阶段 2 必须使用 fixed low-FPR protocol：

```text
1. threshold 只由 calibration split 的 clean_negative 与 attacked_negative 生成；
2. test split 不得参与 threshold；
3. 不允许 attack-specific threshold；
4. 不允许 method-specific 之外的隐式阈值回流；
5. threshold record 必须写入 target_fpr、calibration roles、record digest 与 threshold_id。
```

---

## 八、结果检查要求

`12_validate_stage2_outputs` cell 必须调用正式 checker，而不是手写零散检查。若仓库缺少 checker，Codex 应新增 CLI：

```text
main.colab.check_stage2_family_result
```

该 checker 必须检查：

```text
1. family_manifest.json 存在；
2. step_manifest.json 存在；
3. event_scores.jsonl 存在且非空；
4. thresholds.json 存在；
5. main_tpr_fpr_table.csv 存在；
6. ablation_table.csv 存在；
7. real_video_attack_breakdown.csv 存在；
8. quality_table.csv 存在；
9. temporal_consistency_table.csv 存在；
10. vae_latent_probe_report.md 存在；
11. session_model_manifest.json 存在且声明 saved_to_drive=false；
12. result package 不包含模型权重文件；
13. records 中 S_traj 全部为 null；
14. disabled_evidence 包含 trajectory；
15. attacked_negative_FPR 被报告；
16. clean_negative 与 attacked_negative 均参与 calibration threshold；
17. test split 未产生新 threshold；
18. table 可由 records 重建；
19. failure_case_gallery 存在或显式声明为空；
20. processed dataset digest 与输入 manifest 一致。
```

checker 输出：

```text
checks/stage2_output_checks.json
checks/stage2_blocking_reasons.json
family_checks.json
```

最终应打印：

```text
Stage2Decision: PASS / FAIL / INCONCLUSIVE
BlockingReasons: [...]
FamilyPackage: <path>
```

---

## 九、打包规则

阶段 2 打包必须遵守：

```text
1. 打包 records、thresholds、tables、figures、reports、checks、logs、manifest、配置快照、session_model_manifest；
2. 不打包 raw dataset；
3. 不打包 processed dataset 本体；
4. 不打包 session model 文件；
5. 不打包 Hugging Face cache；
6. 不打包 torch cache；
7. 不打包 /tmp；
8. 不打包 /content 中未登记目录。
```

推荐排除规则：

```text
--exclude='*.pth'
--exclude='*.pt'
--exclude='*.ckpt'
--exclude='*.safetensors'
--exclude='*.bin'
--exclude='session_models/**'
--exclude='model_cache/**'
--exclude='.cache/**'
--exclude='__pycache__/**'
--exclude='tmp/**'
```

`step_manifest.json` 必须记录被排除的模型目录与 processed dataset 目录，并说明其由 `session_model_manifest.json` 与 `dataset_input_manifest.json` 追溯。

---

## 十、Codex 必须新增或更新的文件

Codex 应根据真实仓库情况决定最小实现，但推荐至少新增或更新以下文件。

### （一）notebook 文件

```text
paper_workflow/Build_Processed_Dataset_Stage2_Colab.ipynb
paper_workflow/Run_Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb
```

可选：

```text
paper_workflow/Merge_Stage2_Family_Results_Colab.ipynb
```

### （二）Colab 支撑脚本

```text
main/colab/family_paths.py
main/colab/session_models.py
main/colab/package_family_result.py
main/colab/check_stage2_family_result.py
main/colab/notebook_contract_checks.py
```

### （三）processed dataset 构建脚本

```text
main/datasets/build_stage2_processed_dataset.py
main/datasets/processed_dataset_manifest.py
main/datasets/video_clip_builder.py
main/datasets/dataset_registry.py
```

### （四）阶段 2 runner 支撑

若已有 runner，则只更新 CLI 参数与 family package 输出；若没有，则新增：

```text
main/protocol/stage2_runner.py
```

### （五）测试文件

```text
tests/test_stage2_processed_dataset_notebook_contract.py
tests/test_stage2_run_notebook_contract.py
tests/test_family_id_result_packaging.py
tests/test_session_model_no_drive_storage.py
tests/test_processed_dataset_no_runtime_dependency.py
tests/test_stage2_output_checker_contract.py
```

---

## 十一、Codex 禁止修改的内容

Codex 不得为了构建 notebook 顺手修改以下内容：

```text
1. 不重写阶段 1 的 tubelet / sync 核心算法；
2. 不修改 fixed low-FPR 的统计语义；
3. 不把 trajectory evidence 接入阶段 2；
4. 不改变 sample role 定义；
5. 不改变 raw dataset 下载 notebook 的职责边界；
6. 不把模型权重保存到 Google Drive；
7. 不让实验 notebook 直接从 raw dataset 切片；
8. 不让 notebook 手动拼正式表格；
9. 不用 latest 文件或目录作为正式输入；
10. 不依赖 notebook cell 的隐藏状态作为跨步骤事实。
```

若必须修改核心代码以暴露 CLI 或支持 family package，必须保持最小变更，并新增测试证明没有破坏既有阶段 1 行为。

---

## 十二、最小验收标准

Codex 完成后，至少应能在 Colab 中执行以下流程。

### （一）Processed Dataset notebook 验收

```text
1. 从 /content/drive/MyDrive/Datasets/DAVIS_2017/raw/DAVIS-2017-trainval-480p.zip 读取 raw dataset；
2. 在 /content 本地解压和切片；
3. 生成 256×256、32f、8fps 的 DAVIS processed clips；
4. 保存到 /content/drive/MyDrive/TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/；
5. 生成 dataset_manifest.json、split_manifest.json、sha256_manifest.json；
6. 生成 cache tar.zst；
7. 更新 dataset_registry.json；
8. 生成 FAMILY_ID 下的 processed dataset build step package；
9. notebook 断开后，processed dataset 仍可由另一个 notebook 独立读取。
```

### （二）Stage 2 run notebook 验收

```text
1. 新会话中挂载 Drive；
2. 不依赖前一个 notebook 的 /content 或 /tmp；
3. 从 processed dataset cache 解压到本地；
4. 下载 VAE 与 LPIPS 相关 session model 到本地；
5. 不向 Google Drive 写入模型文件；
6. 运行阶段 2 smoke；
7. 生成 records、thresholds、tables、reports、checks；
8. checker 输出 PASS / FAIL / INCONCLUSIVE；
9. 结果包保存到 TSTW/results/families/<FAMILY_ID>/；
10. result package 不包含模型权重文件与 raw / processed dataset 本体。
```

---

## 十三、最终交付口径

Codex 最终应报告：

```text
1. 新增或修改了哪些 notebook；
2. 新增或修改了哪些支撑脚本；
3. notebook 是否遵守 FAMILY_ID 结果归档；
4. processed dataset 是否保存到 TSTW/datasets/processed/<PROCESSED_DATASET_KEY>/；
5. 模型是否仅 session-only；
6. 是否存在任何对 Google Drive Models 的写入；
7. 是否存在跨 notebook 依赖 /content、/tmp 或内存对象；
8. 是否所有 formal 输出均打包到 TSTW/results/families/<FAMILY_ID>/；
9. 哪些测试通过；
10. 若有未实现项，是否显式列为 BlockingReasons。
```

一句话要求：阶段 2 notebook 必须是一个可独立会话执行、可从 processed dataset manifest 恢复输入、可本地下载模型、可生成 family result package、可由 checker 审计的 Colab workflow，而不是依赖当前运行环境状态的临时脚本集合。

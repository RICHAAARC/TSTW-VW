# Notebook 构造约束说明

## 一、文件定位

本文档用于约束后续所有项目相关 Colab notebook 的构造方式。目标是保证 notebook 在 Google Colab 中稳定读取 Google Drive 中已经 bootstrap 完成的数据集、模型权重与运行配置，并将每次实验结果以完整归档包形式写回 Google Drive。

本文档适用于以下 notebook 类型：

```text
Drive bootstrap notebook
real_video_vae_latent_probe_completion_formal notebook
real_video_vae_latent_probe_smoke notebook
paper_formal notebook
trajectory_statistic_probe notebook
后续论文主实验 notebook
```

## 二、总体原则

### （一）代码来源原则

所有项目代码必须从 GitHub 拉取到 Colab 本地工作空间：

```text
/content/TSTW_runtime/repo
```

Google Drive 中不保存代码快照、不保存 commit 记录、不保存未打包 run 目录。Notebook 必须记录当前 Git commit、branch、repository URL 与 `git status --short`，并将其写入单次 run 包内部日志或 manifest。

### （二）数据读取原则

Google Drive 只作为长期存储层，正式实验不得高频逐个读取 Drive 中的 `.mp4` 文件。Notebook 必须执行：

```text
读取 TSTW/configs/<run_profile>/dataset_override.json
→ 定位 TSTW/datasets/cache/*.tar.zst
→ 复制 tar.zst 到 /content/TSTW_runtime/dataset_cache/
→ 解压到 /content/TSTW_runtime/datasets/real_video_probe/
→ 实验全程从 /content 本地盘读取视频
```

### （三）模型读取原则

模型权重保持在 Google Drive 既有位置，正式 notebook 从 `model_override.json` 读取模型位置，再复制到本地目录加载：

```text
/content/drive/MyDrive/Models/vae
/content/drive/MyDrive/Models/lpips
/content/drive/MyDrive/Models/clip
→ /content/TSTW_runtime/models/
```

### （四）结果写入原则

每次实验先写入本地：

```text
/content/TSTW_runtime/runs/<run_id>/
```

实验结束后只将归档结果写回 Drive：

```text
/content/drive/MyDrive/TSTW/results/<run_profile>/<run_id>.tar.zst
/content/drive/MyDrive/TSTW/results/<run_profile>/<run_id>_summary.json
/content/drive/MyDrive/TSTW/results/<run_profile>/<run_id>_checks.json
```

## 三、固定 Google Drive 目录结构

```text
/content/drive/MyDrive/
├── Models/
│   ├── inspyrenet/
│   ├── vae/
│   ├── lpips/
│   └── clip/
└── TSTW/
    ├── datasets/
    │   ├── raw/
    │   ├── prepared/
    │   ├── cache/
    │   └── manifests/
    ├── configs/
    │   ├── real_video_vae_latent_probe_smoke/
    │   ├── real_video_vae_latent_probe_completion_formal/
    │   └── paper_formal/
    ├── results/
    │   ├── smoke/
    │   ├── real_video_vae_latent_probe_completion_formal/
    │   └── paper_formal/
    └── registry/
        ├── dataset_registry.json
        ├── model_registry.json
        ├── drive_state.json
        ├── result_registry.jsonl
        └── last_bootstrap_summary.json
```

## 四、固定 Colab 本地工作空间

```python
DRIVE_ROOT = "/content/drive/MyDrive"
TSTW_ROOT = f"{DRIVE_ROOT}/TSTW"
MODELS_ROOT = f"{DRIVE_ROOT}/Models"

LOCAL_TSTW_ROOT = "/content/TSTW_runtime"
LOCAL_REPO_DIR = f"{LOCAL_TSTW_ROOT}/repo"
LOCAL_MODELS_DIR = f"{LOCAL_TSTW_ROOT}/models"
LOCAL_DATASET_CACHE_DIR = f"{LOCAL_TSTW_ROOT}/dataset_cache"
LOCAL_DATASET_DIR = f"{LOCAL_TSTW_ROOT}/datasets/real_video_probe"
LOCAL_RUNS_DIR = f"{LOCAL_TSTW_ROOT}/runs"
LOCAL_TMP_DIR = f"{LOCAL_TSTW_ROOT}/tmp"
```

## 五、固定 registry 与 override 文件

必须读取：

```text
/content/drive/MyDrive/TSTW/registry/dataset_registry.json
/content/drive/MyDrive/TSTW/registry/model_registry.json
/content/drive/MyDrive/TSTW/registry/drive_state.json
```

并读取 profile 级 override：

```text
/content/drive/MyDrive/TSTW/configs/real_video_vae_latent_probe_completion_formal/
├── runtime_override.json
├── dataset_override.json
└── model_override.json
```

## 六、数据集使用方法

默认数据集键建议使用语义化命名，例如：

```text
davis2017_480p_real_video_vae_latent_probe_completion_calib20_test20
```

数据流程：

```text
读取 dataset_override.json
→ 解析 cache_tar_path 与 cache_tar_sha256
→ 校验 Drive tar.zst 存在
→ 校验 sha256
→ 复制到 /content/TSTW_runtime/dataset_cache/
→ tar --zstd 解压到 /content/TSTW_runtime/datasets/real_video_probe/
→ 校验 mp4 数量与 dataset_manifest
→ 将本地 dataset root 写入 runtime config
```

## 七、模型使用方法

模型流程：

```text
读取 model_override.json
→ 解析 VAE / LPIPS / CLIP 的 drive_model_root
→ VAE 与 LPIPS 必须存在且非空
→ CLIP 可选
→ 复制到 /content/TSTW_runtime/models/
→ 运行时从本地 models 加载
```

普通 formal notebook 不负责下载模型。模型缺失时必须 fail-fast。

## 八、运行 profile 与 run_id 规范

允许 run profile：

```text
smoke
real_video_vae_latent_probe_completion_formal
paper_formal
```

run_id 规范：

```text
<construction_phase>__<run_profile>__<dataset_key_or_short_name>__<utc_time>__<short_commit>
```

示例：

```text
real_video_vae_latent_probe__real_video_vae_latent_probe_completion_formal__davis20_20__20260510_181200__a1b2c3d
```

禁止使用弱语义名称，如：`run1`、`probe_test_case`、`final`、`new_run`、`best_run`。

## 九、Notebook 标准 cell 顺序

```text
00_runtime_mode_and_user_config
01_mount_google_drive
02_read_drive_state_and_overrides
03_prepare_local_workspace
04_clone_or_update_repository
05_install_dependencies
06_copy_and_validate_dataset
07_copy_and_validate_models
08_check_gpu_and_runtime
09_verify_repository_contract
10_run_unit_tests_smoke
11_run_real_video_vae_latent_probe_completion_formal
12_rebuild_tables_and_reports
13_validate_formal_outputs
14_pack_run_to_drive
15_update_result_registry
16_print_final_summary
```

## 十、正式输出目录约束

本地 run root：

```text
/content/TSTW_runtime/runs/<run_id>/
```

Drive 结果目录：

```text
/content/drive/MyDrive/TSTW/results/<run_profile>/<run_id>.tar.zst
/content/drive/MyDrive/TSTW/results/<run_profile>/<run_id>_summary.json
/content/drive/MyDrive/TSTW/results/<run_profile>/<run_id>_checks.json
```

如项目打包器仍输出 `.zip`，必须额外生成 `.tar.zst` 作为 Drive 侧最终归档。

## 十一、Notebook 与正式产物边界

Notebook 不得直接写正式 `tables/` 或 `thresholds/` 文件。正式产物必须由仓库模块生成，例如：

```text
main.protocol.real_video_vae_latent_runner
main.analysis.real_video_vae_latent_artifacts
main.colab.notebook_result_checker
main.colab.drive_packager 或后续 tar_zst_packager
```

## 十二、formal 最低检查标准

formal 结束时必须执行：

```text
run_mode == formal
require_formal_pass_criteria == true
```

checks 目标：

```json
{
  "status": true,
  "RealVideoVaeLatentDecision": "PASS",
  "BlockingReasons": [],
  "NextAllowedStage": "trajectory_statistic_probe"
}
```

若为 `INCONCLUSIVE`，允许打包失败结果，但不得宣称阶段完成。

## 十三、日志与审计文件

必须写入 run root 并随 `.tar.zst` 一并归档：

```text
logs/colab.log
logs/pytest.log
logs/audit.log
logs/dependency_freeze.txt
logs/git_commit.txt
logs/git_status.txt
artifacts/colab_runtime_manifest.json
artifacts/config_snapshot/
artifacts/dataset_manifest_snapshot.json
artifacts/checks.json
```

## 十四、result registry 更新规范

每次写回 Drive 后，追加：

```text
/content/drive/MyDrive/TSTW/registry/result_registry.jsonl
```

条目建议：

```json
{
  "schema_version": "tstw_result_registry_entry.v1",
  "run_id": "...",
  "run_profile": "real_video_vae_latent_probe_completion_formal",
  "construction_phase": "real_video_vae_latent_probe",
  "dataset_key": "davis2017_480p_real_video_vae_latent_probe_completion_calib20_test20",
  "git_commit": "a1b2c3d",
  "archive_path": "...tar.zst",
  "summary_path": "..._summary.json",
  "checks_path": "..._checks.json",
  "decision": "PASS",
  "created_at": "ISO-8601"
}
```

## 十五、禁止事项

1. 禁止从 Google Drive 直接运行项目代码。
2. 禁止将未打包 run 目录写入 `TSTW/results/`。
3. 禁止单独写 `TSTW/logs/`、`TSTW/failure_cases/`、`TSTW/packed_runs/`。
4. 禁止正式实验逐个从 Drive 读取 `.mp4`。
5. 禁止正式实验随机抽样数据集。
6. 禁止 formal notebook 下载或替换数据集。
7. 禁止 formal notebook 下载或替换模型权重。
8. 禁止 notebook 直接写 `tables/` 或 `thresholds/`。
9. 禁止 test split 更新 threshold。
10. 禁止 attack-specific threshold。
11. 禁止将 smoke 结果标记为 completion。
12. 禁止在 formal checker 未通过时声称完成。

## 十六、最小运行伪代码

```python
# 1. mount drive
# 2. read drive_state, dataset_override, model_override, runtime_override
# 3. clone GitHub repo to /content/TSTW_runtime/repo
# 4. install dependencies
# 5. copy dataset tar.zst to /content/TSTW_runtime/dataset_cache
# 6. verify sha256 and extract dataset to /content/TSTW_runtime/datasets/real_video_probe
# 7. copy models from drive_model_root to /content/TSTW_runtime/models
# 8. run repository contract and audits
# 9. run formal runner
# 10. rebuild tables and reports by project builders
# 11. run notebook_result_checker with require_formal_pass_criteria=True
# 12. write logs and manifests into run_root
# 13. package run_root into tar.zst
# 14. write tar.zst, summary.json, checks.json to TSTW/results/<run_profile>/
# 15. append result_registry.jsonl
```

## 十七、兼容说明

当前 `main.colab.drive_packager` 仍以 `.zip` 为主。正式 notebook 必须保证 Drive 最终结果包含 `.tar.zst`；`.zip` 只能作为兼容副产物。

## 十八、最终约束摘要

```text
代码：GitHub → /content/TSTW_runtime/repo
数据：TSTW/datasets/cache/*.tar.zst → /content/TSTW_runtime/datasets/
模型：model_override.json 中的 Drive 位置 → /content/TSTW_runtime/models/
运行：/content/TSTW_runtime/runs/<run_id>/
结果：TSTW/results/<run_profile>/<run_id>.tar.zst + summary.json + checks.json
日志：进入 run_root/logs/，随 tar.zst 一起保存
失败样例：进入 run_root/failure_case_gallery/，随 tar.zst 一起保存
配置：读取 registry 与 override，不在 notebook 中硬编码正式路径
检查：formal 必须 require_formal_pass_criteria=True
边界：notebook 不直接写 tables/ 或 thresholds/
```

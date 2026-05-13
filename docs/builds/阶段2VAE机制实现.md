# 阶段 2 VAE 机制实现修复说明

## 一、任务定位

本文档用于指导 Codex 在当前项目中继续完成阶段 2 的 **VAE 机制有效性验证** 与 **结果治理收口**。当前阶段 2 已经完成 `Stage2ImplementationPass`，即真实视频 `.mp4`、真实 AutoencoderKL VAE、真实视频攻击、真实质量与时序指标入口、records / thresholds / tables / reports / checker / package 的 formal runtime 已经跑通。

但是，当前结果尚不能充分证明 `Stage2MechanismPass`，即不能证明 `tubelet + sync` 在真实视频 VAE latent 中已经稳定有效。当前需要将阶段 2 从“实现闭环通过”推进到“机制效果可审计、可校准、可判定”。

本次修复不进入阶段 3，不新增 trajectory evidence，不实现 Flow Matching trajectory statistic，不修改 DiT / Flow Matching 采样过程。所有变更必须围绕阶段 2：真实视频 VAE latent 中的 `frame_prc`、`tubelet_only`、`tubelet_sync` 机制审计与机制通过门禁。

---

## 二、当前已知状态

### （一）已完成内容

当前项目已经完成以下能力：

```text
真实 .mp4 输入；
真实 AutoencoderKL VAE encode / decode；
latent watermark embedding；
真实视频攻击，包括 H.264 / H.265 compression、空间攻击、时间攻击等；
attacked .mp4 re-encode；
真实 frame-level quality / temporal metrics 入口；
records、thresholds、tables、reports、failure gallery、checker、tar.zst package；
formal checker 返回 Stage2ImplementationPass 所需字段。
```

当前可以判定：

```text
Stage2ImplementationPass = true
```

### （二）尚未完成内容

当前不能判定：

```text
Stage2MechanismPass = true
```

原因包括：

```text
tubelet_only 尚未稳定优于 frame_prc；
tubelet_sync 尚未稳定优于 tubelet_only；
tubelet_sync 在部分时间攻击中的提升伴随 attacked-negative FPR 风险；
no_attack 下 tubelet_only / tubelet_sync 的 clean_positive_TPR 存在不足；
当前样本量偏小，统计波动较大；
当前 checker 将 implementation pass 与 mechanism pass 混在同一决策中；
LPIPS 尚未启用；
CLIP similarity 尚未启用；
motion consistency 尚未启用；
family_manifest.json 中 package format 与实际 tar.zst package 不一致；
family_id 中仍可能出现 utc_time__short_commit 字面占位符。
```

---

## 三、硬约束

### （一）文件组织约束

必须遵守当前项目文件组织边界：

```text
main/：只保留最终方法、核心协议、真实视频 / VAE / 攻击 / 指标、训练与 CLI 核心能力；
experiments/：承接阶段性 probe runner、artifact builder、机制审计与阶段 2 mechanism gate；
paper_workflow/：承接 Colab notebook 与 notebook helper，默认不进入最终 release；
scripts/：承接数据准备、模型准备、结果检查、结果打包、运行统计与辅助 CLI；
docs/：承接长期约束契约与构建说明。
```

本次不得新增：

```text
main/colab/
main/*stage2_notebook*
main/*gpu_profile*
main/*drive_packager*
```

### （二）阶段边界约束

本次只修阶段 2，不进入阶段 3。禁止新增或启用：

```text
S_traj 正式分数；
trajectory_statistic；
Flow Matching trajectory backend；
DiT sampling hook；
velocity projection；
trajectory-aware embedding；
tubelet_sync_trajectory_fusion 作为主方法。
```

阶段 2 records 中仍应保持：

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

### （三）统计协议约束

不得使用 test split 调整：

```text
threshold；
embedding_margin；
tubelet_length；
spatial_patch_size；
sync_weight；
fusion rule；
attack severity；
Stage2MechanismPass 判定阈值。
```

参数扫描只能作用于 dev / calibration，并且必须记录在 records、manifest、mechanism audit table 与 report 中。

---

## 四、总目标

本次变更完成后，项目应明确区分两个决策：

```text
Stage2ImplementationDecision = PASS / INCONCLUSIVE / FAIL
Stage2MechanismDecision = PASS / INCONCLUSIVE / FAIL
```

其中：

```text
Stage2ImplementationDecision
判断真实视频 VAE latent formal runtime 是否闭环。

Stage2MechanismDecision
判断 tubelet + sync 在真实视频 VAE latent 中是否具有稳定机制效果。
```

当前已有的 formal checker 可以继续作为 implementation gate，但必须新增 mechanism audit 与 mechanism gate。

---

## 五、需要修复的问题清单

### 问题 1：family manifest 中 package format 不一致

#### 现象

当前 family-level metadata 可能出现：

```json
{
  "package_format": "zip",
  "package_path": ".../real_video_vae_latent_probe_formal.zip"
}
```

但实际 package 为：

```text
real_video_vae_latent_probe_formal.tar.zst
```

#### 影响

该问题不会影响单次 formal run 的方法有效性，但会影响：

```text
family registry；
result registry；
自动索引；
后续阶段读取历史结果；
审稿复现时的 package path 解析。
```

#### 修复要求

修改 family manifest / summary / registry 生成逻辑，使 package metadata 以实际打包结果为准。

目标字段为：

```json
{
  "package_format": "tar.zst",
  "archive_format": "tar.zst",
  "package_path": ".../real_video_vae_latent_probe_formal.tar.zst",
  "archive_path": ".../real_video_vae_latent_probe_formal.tar.zst"
}
```

#### 建议修改位置

优先检查并修改：

```text
scripts/package_results/package_real_video_vae_latent_tar_zst.py
paper_workflow/notebook_utils/real_video_vae_latent_probe_workflow.py
paper_workflow/notebook_utils/*registry*.py
scripts/check_results/check_real_video_vae_latent_outputs.py
```

如果 family manifest 由 notebook helper 写出，则不要把逻辑迁入 `main/`。

#### 新增测试

新增或修改：

```text
tests/constraints/test_family_package_metadata_contract.py
```

测试要求：

```text
package_format 与实际文件后缀一致；
archive_format 与实际文件后缀一致；
package_path 指向真实存在的 .tar.zst；
不得出现 .zip 路径指向 .tar.zst package 的情况。
```

---

### 问题 2：family_id 中仍含有字面占位符

#### 现象

当前 family id 可能出现：

```text
real_video_vae_latent_probe__formal__davis2017_trainval480p__utc_time__short_commit
```

其中：

```text
utc_time
short_commit
```

仍是字面占位符，没有被实例化。

#### 影响

该问题会影响：

```text
family 级结果追踪；
不同运行之间的唯一性；
result registry append-only 语义；
后续阶段引用阶段 2 通过结果；
导师或审稿人检查时的可追溯性。
```

#### 修复要求

family id 必须由真实字段构成：

```text
<method_or_probe_name>__<run_mode>__<dataset_key>__<utc_timestamp>__<short_commit>
```

示例：

```text
real_video_vae_latent_probe__formal__davis2017_trainval480p__20260513T015116Z__ef99828
```

要求：

```text
不得出现 utc_time、short_commit、timestamp、commit 等字面模板占位符；
utc timestamp 使用 UTC，格式建议为 YYYYMMDDTHHMMSSZ；
short_commit 来自真实 git commit，建议 7 位；
若 git commit 不可用，必须写 unknown_commit 并在 manifest 中记录 reason，不得保留 short_commit 字面量。
```

#### 建议修改位置

优先检查：

```text
paper_workflow/notebook_utils/real_video_vae_latent_probe_workflow.py
scripts/package_results/package_real_video_vae_latent_tar_zst.py
scripts/profile_runtime/capture_colab_environment.py
```

#### 新增测试

新增：

```text
tests/constraints/test_family_id_materialization_contract.py
```

测试要求：

```text
family_id 不包含 utc_time；
family_id 不包含 short_commit；
family_id 不包含 template；
family_id 包含 UTC timestamp；
family_id 包含真实 short commit 或 unknown_commit；
family_id 与 summary / manifest / registry 一致。
```

---

### 问题 3：需要新增 Stage2MechanismAudit

#### 目标

新增机制审计模块，用于从已有 records / thresholds / tables 中判断真实视频 VAE latent 中 `tubelet + sync` 是否具有机制效果。

该模块不应重新运行 VAE，不应重新攻击视频，只分析既有产物。

#### 建议新增路径

```text
experiments/real_video_vae_latent_probe/mechanism_audit.py
scripts/check_results/check_stage2_mechanism_effect.py
```

其中：

```text
experiments/.../mechanism_audit.py
实现核心审计逻辑。

scripts/check_results/check_stage2_mechanism_effect.py
提供命令行入口，供 notebook 或手动运行使用。
```

不得放入：

```text
main/colab/
main/protocol/stage2_mechanism_audit.py
```

#### 输入

```text
--run-root outputs/runs/<run_id>
--target-fpr <float>
--mechanism-config configs/protocol/stage2_mechanism_gate.json
```

#### 输出

```text
tables/stage2_mechanism_audit_table.csv
tables/stage2_score_distribution_table.csv
tables/stage2_sync_gain_table.csv
reports/stage2_mechanism_audit_report.md
artifacts/stage2_mechanism_decision.json
```

#### `stage2_mechanism_audit_table.csv` 字段

必须至少包含：

```text
run_id
construction_phase
method_variant
base_method_variant
attack_name
sample_role
count
S_tubelet_mean
S_tubelet_std
S_sync_mean
S_sync_std
S_final_mean
S_final_std
decision_rate
clean_negative_FPR
attacked_negative_FPR
clean_positive_TPR
attacked_positive_TPR
local_clip_TPR
sync_alignment_error_mean
sync_peak_rank_median
quality_psnr_mean
quality_ssim_mean
temporal_consistency_score_mean
flicker_score_mean
```

#### `stage2_sync_gain_table.csv` 字段

必须至少包含：

```text
attack_name
metric_name
tubelet_only_value
tubelet_sync_value
sync_gain
negative_fpr_delta
positive_count
negative_count
mechanism_signal_status
```

其中：

```text
sync_gain = tubelet_sync.attacked_positive_TPR - tubelet_only.attacked_positive_TPR
negative_fpr_delta = tubelet_sync.attacked_negative_FPR - tubelet_only.attacked_negative_FPR
```

对于 score 层面，也应统计：

```text
S_final_gain = mean(S_final_tubelet_sync_positive) - mean(S_final_tubelet_only_positive)
S_sync_positive_negative_gap = mean(S_sync_positive) - mean(S_sync_negative)
```

---

### 问题 4：新增 Stage2MechanismDecision gate

#### 目标

新增机制层决策，不再将 implementation pass 与 mechanism pass 混为一个结论。

推荐输出：

```json
{
  "Stage2ImplementationDecision": "PASS",
  "Stage2MechanismDecision": "INCONCLUSIVE",
  "Stage2MechanismBlockingReasons": [
    "tubelet_only_not_above_frame_prc",
    "tubelet_sync_no_attack_positive_tpr_low",
    "attacked_negative_fpr_not_controlled",
    "sample_count_insufficient"
  ],
  "NextRecommendedAction": "stage2_mechanism_calibration_run"
}
```

#### 机制通过条件

新增配置：

```text
configs/protocol/stage2_mechanism_gate.json
```

建议内容：

```json
{
  "construction_phase": "real_video_vae_latent_probe",
  "minimum_positive_count_per_key": 20,
  "minimum_negative_count_per_key": 20,
  "required_main_variants": [
    "frame_prc",
    "tubelet_only",
    "tubelet_sync"
  ],
  "required_mechanism_attacks": [
    "no_attack",
    "temporal_crop",
    "frame_dropping",
    "local_clip",
    "h264_compression"
  ],
  "max_clean_negative_fpr": 0.05,
  "max_attacked_negative_fpr": 0.10,
  "min_no_attack_clean_positive_tpr": 0.50,
  "min_tubelet_only_gain_over_frame_prc": 0.00,
  "min_tubelet_sync_gain_over_tubelet_only_temporal": 0.10,
  "min_sync_positive_negative_score_gap": 0.05,
  "require_quality_not_collapsed": true,
  "min_watermarked_video_psnr": 20.0,
  "min_watermarked_video_ssim": 0.50
}
```

说明：

```text
这些数值是机制审计初始门槛，不是论文主实验最终阈值；
若当前 formal completion run 样本量不足，应返回 INCONCLUSIVE，而不是 FAIL；
若样本量足够但机制关系不成立，应返回 FAIL；
若实现不完整，应由 implementation gate 返回 FAIL。
```

#### 判定规则

```text
PASS：样本量足够，FPR 受控，tubelet / sync 机制关系成立；
INCONCLUSIVE：实现通过，但样本量不足或关键攻击覆盖不足，无法判定机制；
FAIL：样本量足够，但 tubelet / sync 机制关系不成立，或 FPR 明显失控。
```

---

### 问题 5：需要支持 dev / calibration 参数扫描

#### 目标

当前 `tubelet_only` 与 `tubelet_sync` 在 no_attack 下 clean positive 检测不足，需要支持受治理的参数扫描。

参数扫描必须仅在 dev / calibration split 上执行，不得使用 test split 调参。

#### 建议新增路径

```text
experiments/real_video_vae_latent_probe/mechanism_calibration_runner.py
configs/ablation/stage2_vae_mechanism_calibration_grid.json
scripts/check_results/select_stage2_mechanism_candidate.py
```

#### 参数网格

建议初始网格：

```json
{
  "construction_phase": "real_video_vae_latent_probe",
  "calibration_purpose": "stage2_mechanism_effect_calibration",
  "allowed_splits": ["dev", "calibration"],
  "forbidden_splits": ["test"],
  "grid": {
    "embedding_margin": [0.25, 0.5, 0.75, 1.0],
    "tubelet_length": [2, 4, 8],
    "spatial_patch_size": [[4, 4], [8, 8]],
    "sync_weight": [0.0, 0.25, 0.5],
    "sync_search_radius": [4, 8, 12]
  },
  "selection_metrics": [
    "no_attack_clean_positive_TPR",
    "clean_negative_FPR",
    "temporal_crop_sync_gain",
    "local_clip_sync_gain",
    "watermarked_video_psnr",
    "watermarked_video_ssim"
  ]
}
```

#### 输出

```text
tables/stage2_mechanism_calibration_grid.csv
reports/stage2_mechanism_calibration_report.md
artifacts/stage2_selected_mechanism_candidate.json
```

#### 候选选择规则

选择候选必须满足：

```text
clean_negative_FPR 不失控；
no_attack clean_positive_TPR 明显大于 0；
tubelet_sync 在 temporal_crop / local_clip 上相对 tubelet_only 有正增益；
watermarked_video_psnr / ssim 未崩坏；
参数选择只基于 dev / calibration。
```

然后将候选写入：

```text
configs/method/tubelet_sync_real_video_vae_candidate.json
```

不得直接覆盖原始：

```text
configs/method/tubelet_sync.json
```

除非后续已经完成正式冻结。

---

### 问题 6：需要启用 LPIPS

#### 目标

阶段 2 当前已经具备真实 frame-level PSNR / SSIM，但 LPIPS 尚未启用。需要将 LPIPS 纳入正式质量指标，至少在 formal / mechanism run 中可选启用，并在 paper_main 前作为默认质量指标启用。

#### 建议修改位置

```text
main/analysis/real_video_quality_metrics.py
main/analysis/quality_metrics.py
experiments/real_video_vae_latent_probe/runner.py
paper_workflow/notebook_utils/real_video_vae_latent_probe_workflow.py
scripts/check_results/real_video_vae_latent_output_checker.py
```

#### 配置字段

在 runtime config 或 protocol config 中新增：

```json
{
  "quality_metrics": {
    "enable_lpips": true,
    "lpips_backbone": "alex",
    "lpips_device": "cuda",
    "lpips_batch_size": 8,
    "lpips_required_for_formal": false,
    "lpips_required_for_paper_quality": true
  }
}
```

建议当前阶段设置：

```text
lpips_required_for_formal = false
lpips_required_for_paper_quality = true
```

原因是阶段 2 completion 已经通过；机制审计可先启用 LPIPS 作为质量约束，但不要让早期 debug run 因 LPIPS 依赖失败完全阻断。

#### records 字段

每条 record 中 `quality_metrics` 应包含：

```json
{
  "watermarked_video_lpips": 0.0,
  "lpips_backbone": "alex",
  "lpips_device": "cuda",
  "lpips_failure_reason": null
}
```

若 LPIPS 未启用，必须写：

```json
{
  "watermarked_video_lpips": null,
  "lpips_failure_reason": "lpips_disabled_by_config"
}
```

不得写成：

```text
lpips_placeholder
lpips_random
```

#### 新增测试

```text
tests/functional/test_real_video_lpips_metric_runtime.py
tests/constraints/test_stage2_lpips_metric_contract.py
```

测试要求：

```text
enable_lpips=false 时字段治理正确；
enable_lpips=true 且 LPIPS 可导入时能计算非空值；
formal / paper quality 配置能按 required flag 阻断或放行；
LPIPS 失败原因必须写入 records，不得静默跳过。
```

---

### 问题 7：需要启用 CLIP similarity

#### 目标

CLIP similarity 用于补充视频语义保持指标。阶段 2 机制审计不强制依赖 CLIP，但 paper_main 前应具备可启用路径。

#### 建议新增路径

```text
main/analysis/clip_similarity_metrics.py
```

或在：

```text
main/analysis/real_video_quality_metrics.py
```

中添加受治理的 CLIP metric backend。

#### 推荐实现

对视频进行帧采样，例如：

```text
sampled frames = first / middle / last 或 uniform 4 frames
```

分别计算 reference video 与 watermarked / attacked video 的 image embedding，求 cosine similarity 平均值。

配置字段：

```json
{
  "quality_metrics": {
    "enable_clip_similarity": true,
    "clip_model_id": "openai/clip-vit-base-patch32",
    "clip_device": "cuda",
    "clip_batch_size": 8,
    "clip_frame_sample_count": 4,
    "clip_required_for_formal": false,
    "clip_required_for_paper_quality": true
  }
}
```

#### records 字段

```json
{
  "clip_similarity_score": 0.0,
  "clip_model_id": "openai/clip-vit-base-patch32",
  "clip_frame_sample_count": 4,
  "clip_failure_reason": null
}
```

若未启用：

```json
{
  "clip_similarity_score": null,
  "clip_failure_reason": "clip_similarity_disabled_by_config"
}
```

#### 注意

不得将 CLIP 作为水印检测 evidence。CLIP 只属于 quality / semantic preservation metric，不得进入：

```text
S_tubelet
S_sync
S_final
threshold calibration
watermark decision
```

#### 新增测试

```text
tests/functional/test_clip_similarity_metric_runtime.py
tests/constraints/test_clip_similarity_not_detection_evidence.py
```

---

### 问题 8：需要启用 motion consistency

#### 目标

当前 temporal metrics 已有 flicker / frame-difference 类指标，但 motion consistency 尚未启用。需要添加可选 motion consistency 指标，用于衡量水印与攻击是否破坏运动结构。

#### 建议实现层级

分两层实现：

```text
Level 1：frame-difference motion proxy，轻量、默认可用；
Level 2：optical-flow motion consistency，后续可选启用。
```

当前阶段先实现 Level 1，并为 Level 2 预留接口。

#### 建议修改路径

```text
main/analysis/real_video_temporal_metrics.py
main/analysis/temporal_metrics.py
```

#### Level 1 指标

定义：

```text
motion_delta_ref[t] = frame_ref[t+1] - frame_ref[t]
motion_delta_cmp[t] = frame_cmp[t+1] - frame_cmp[t]
motion_consistency_score = 1 - normalized_mean_abs(motion_delta_ref - motion_delta_cmp)
```

约束：

```text
score 越高表示 motion consistency 越好；
需要裁剪到 [0, 1]；
必须记录 frame_count、normalization mode、failure reason。
```

#### 配置字段

```json
{
  "temporal_metrics": {
    "enable_motion_consistency": true,
    "motion_consistency_backend": "frame_difference_proxy",
    "motion_consistency_required_for_formal": false,
    "motion_consistency_required_for_paper_quality": true
  }
}
```

#### records 字段

```json
{
  "motion_consistency_score": 0.0,
  "motion_consistency_backend": "frame_difference_proxy",
  "motion_consistency_failure_reason": null
}
```

若未启用：

```json
{
  "motion_consistency_score": null,
  "motion_consistency_failure_reason": "motion_consistency_disabled_by_config"
}
```

#### 新增测试

```text
tests/functional/test_motion_consistency_metric_runtime.py
tests/constraints/test_motion_consistency_metric_contract.py
```

---

## 六、notebook 集成要求

### （一）保持两个 notebook，不新增第三个正式 notebook

仍使用：

```text
paper_workflow/build_processed_real_video_dataset.ipynb
paper_workflow/run_real_video_vae_latent_probe.ipynb
```

本次不得恢复旧 notebook：

```text
paper_workflow/Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb
```

### （二）在 run notebook 中新增机制审计 cell

在 formal checker 之后、packaging 之前，新增：

```text
Run Stage2MechanismAudit
```

伪代码：

```python
mechanism_summary = probe_workflow.run_stage2_mechanism_audit(
    run_root=RUN_ROOT,
    mechanism_config_path='configs/protocol/stage2_mechanism_gate.json',
)
mechanism_summary
```

要求：

```text
机制审计失败不得修改 implementation formal result；
机制审计应输出 Stage2MechanismDecision；
若 Stage2MechanismDecision != PASS，notebook 应继续打包结果，但最终 summary 必须清楚显示 mechanism 未通过；
是否阻断进入下一阶段由用户显式查看机制决策，不得只看 implementation PASS。
```

建议 notebook 最终输出：

```text
Stage2ImplementationDecision
Stage2MechanismDecision
NextAllowedStageByImplementation
NextAllowedStageByMechanism
RecommendedNextAction
```

### （三）在 run notebook 顶部配置区新增指标开关

新增：

```python
ENABLE_LPIPS = True
ENABLE_CLIP_SIMILARITY = False
ENABLE_MOTION_CONSISTENCY = True
LPIPS_REQUIRED_FOR_FORMAL = False
CLIP_REQUIRED_FOR_FORMAL = False
MOTION_CONSISTENCY_REQUIRED_FOR_FORMAL = False
```

说明：

```text
当前阶段 2 mechanism audit 建议启用 LPIPS 与 motion consistency；
CLIP 可默认关闭，等 paper_main quality run 前启用；
若启用 CLIP，需要确保 Colab 依赖与模型下载路径可用。
```

---

## 七、summary / manifest 字段要求

最终 run summary 必须包含：

```json
{
  "Stage2ImplementationDecision": "PASS",
  "Stage2MechanismDecision": "INCONCLUSIVE",
  "Stage2MechanismBlockingReasons": [],
  "Stage2MechanismWarnings": [],
  "NextAllowedStageByImplementation": "trajectory_statistic_probe",
  "NextAllowedStageByMechanism": "remain_in_real_video_vae_latent_probe",
  "RecommendedNextAction": "stage2_mechanism_calibration_run",
  "quality_metrics_enabled": {
    "psnr": true,
    "ssim": true,
    "lpips": true,
    "clip_similarity": false
  },
  "temporal_metrics_enabled": {
    "flicker_score": true,
    "motion_consistency": true
  }
}
```

family summary 必须包含：

```json
{
  "family_id": "real_video_vae_latent_probe__formal__davis2017_trainval480p__20260513T015116Z__ef99828",
  "package_format": "tar.zst",
  "archive_format": "tar.zst",
  "package_path": "...tar.zst",
  "archive_path": "...tar.zst"
}
```

---

## 八、测试清单

Codex 完成变更后，必须至少运行以下测试。

### （一）metadata 修复测试

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/constraints/test_family_package_metadata_contract.py \
  tests/constraints/test_family_id_materialization_contract.py
```

### （二）机制审计测试

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/functional/test_stage2_mechanism_audit.py \
  tests/constraints/test_stage2_mechanism_decision_contract.py
```

### （三）指标测试

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/functional/test_real_video_lpips_metric_runtime.py \
  tests/constraints/test_stage2_lpips_metric_contract.py \
  tests/functional/test_motion_consistency_metric_runtime.py \
  tests/constraints/test_motion_consistency_metric_contract.py \
  tests/constraints/test_clip_similarity_not_detection_evidence.py
```

若 CLIP runtime 暂不启用，可以先只运行 contract 测试，并将 runtime 测试标记为需要依赖。

### （四）notebook 合同测试

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/constraints/test_real_video_vae_latent_colab_notebook_contract.py \
  tests/constraints/test_notebook_naming_contract.py
```

### （五）阶段 2 smoke / formal 相关测试

```bash
PYTHONPATH=. python -m pytest -q -o addopts='' \
  tests/integration/test_real_video_records_schema_smoke.py \
  tests/integration/test_real_video_table_rebuild_smoke.py \
  tests/integration/test_real_video_vae_encode_decode_smoke.py
```

---

## 九、验收标准

本次修复完成后，必须满足以下条件。

### （一）Implementation 不回退

```text
Stage2ImplementationDecision 仍可为 PASS；
real mp4 runtime 不回退到 npy scaffold；
VAE backend 不回退到 placeholder；
video attack 不回退到 tensor attack；
quality / temporal metrics 不回退到 placeholder。
```

### （二）机制审计产物完整

必须生成：

```text
tables/stage2_mechanism_audit_table.csv
tables/stage2_score_distribution_table.csv
tables/stage2_sync_gain_table.csv
reports/stage2_mechanism_audit_report.md
artifacts/stage2_mechanism_decision.json
```

### （三）机制决策可区分

允许当前结果为：

```text
Stage2ImplementationDecision = PASS
Stage2MechanismDecision = INCONCLUSIVE
```

不允许继续只输出：

```text
RealVideoVaeLatentDecision = PASS
```

而不说明机制是否通过。

### （四）metadata 修复完成

```text
family_id 不含 utc_time / short_commit 字面占位符；
package_format 与实际 tar.zst 一致；
archive_path 与 package_path 指向真实 .tar.zst。
```

### （五）LPIPS / motion consistency 可启用

```text
LPIPS 可由配置启用；
motion consistency 可由配置启用；
CLIP similarity 至少有受治理的禁用与非 detection evidence 合同；
指标失败必须写入 failure_reason，不得静默跳过。
```

---

## 十、禁止事项

本次禁止：

```text
不进入阶段 3；
不新增 S_traj 正式分数；
不修改 Flow Matching / DiT 相关代码；
不把 LPIPS / CLIP / motion consistency 作为 watermark detection evidence；
不使用 test split 调参；
不把 notebook 临时变量写成正式表格；
不把机制 INCONCLUSIVE 伪装为 PASS；
不把 family metadata 问题用手工改 json 的方式绕过；
不将新增脚本放入 main/colab 或污染 main 核心方法边界。
```

---

## 十一、建议执行顺序

Codex 应按以下顺序执行：

```text
1. 修复 family package metadata 与 family_id materialization；
2. 新增 Stage2MechanismAudit 核心逻辑与 CLI；
3. 新增 Stage2MechanismDecision gate 与配置；
4. 将机制审计接入 run_real_video_vae_latent_probe notebook workflow；
5. 启用 LPIPS 的可选 runtime；
6. 启用 motion consistency 的 frame-difference proxy；
7. 增加 CLIP similarity 的受治理接口或禁用合同；
8. 更新 summary / manifest / report 输出；
9. 增加测试并运行验收命令。
```

完成后，项目状态应能够明确表达：

```text
Stage2ImplementationPass 已完成；
Stage2MechanismPass 是否完成，由新增机制审计 gate 独立判定；
若机制仍为 INCONCLUSIVE，则继续阶段 2 mechanism calibration run，而不是进入阶段 3。
```

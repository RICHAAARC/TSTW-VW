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

---

## 十二、2026-05-15 机制失败审查增补

本节用于增补本轮对 `tubelet_sync` 机制失败的定向审查结果。该审查基于既有 formal package 的 records 做离线重算与代码路径核对，不重新运行 VAE，不重建 attacked video，也不使用 test split 反向调参。

### （一）当前项目状态

当前项目状态可拆分为两层：

```text
Stage2ImplementationPass：已形成闭环，可视为完成；
Stage2MechanismPass：尚不能判定为通过，当前更接近 INCONCLUSIVE / FAIL 边界，需要先修机制缺陷再重跑 formal。
```

本轮审查时，`tubelet_sync` 在 formal package 中的主要表现为：

```text
shared threshold = 1.1；
overall test TPR = 0.042857；
overall test FPR = 0.042857；
temporal_crop：TPR = 0.0，FPR = 0.0；
frame_dropping：TPR = 0.0，FPR = 0.0；
local_clip：TPR = 0.15，FPR = 0.15。
```

这说明当前 formal failure 不是单纯“阈值太严”或“样本量太小”，而是存在明确的机制与代码层面控制项。

### （二）本轮离线审查结果

#### 1. 仅把 `sync_rescue_applied` gate 改严，无法救回 formal 结果

已对 `tubelet_sync` 扫描 36 组更严格的 gate 反事实，并按 formal 协议重新校准 shared threshold。结果是：

```text
没有一组 stricter rescue gate 能让 temporal_crop 或 frame_dropping 的 test TPR 从 0 回升；
所有这类反事实下，shared threshold 仍保持在 1.1。
```

因此，当前问题不能被解释为“gate 只要更严一点就行”。

#### 2. 当前 shared threshold 的首要钉死源是 local_clip calibration negative

calibration negative 的最高分样本中，存在一批 `local_clip` attacked-negative，表现为：

```text
S_tubelet = 1.0；
S_sync = 1.0；
S_payload_rescue_gain = 0.0；
S_final = 1.1。
```

这说明它们把阈值钉在 1.1 的原因不是 rescue，而是：

```text
S_final = S_tubelet + lambda_sync * max(0, S_sync)
```

中的无条件 sync 项。

#### 3. 诊断性反事实表明：如果先释放 local_clip 的阈值钉死，temporal_crop 与 frame_dropping 才有有限回升空间

在“仅对 calibration 的 local_clip attacked-negative 去掉人工 sync 顶格项”的诊断性反事实下：

```text
shared threshold：1.1 -> 1.044697；
temporal_crop：TPR = 0.1，FPR = 0.15；
frame_dropping：TPR = 0.05，FPR = 0.1。
```

这说明：

```text
local_clip 路径错误是当前 formal failure 的第一控制项；
只要它不修，其他 gate 调整几乎看不到收益；
但即使修掉 local_clip，当前 temporal_crop / frame_dropping 仍不会自然变成“通过”。
```

#### 4. 诊断性 rank gate 只能用于审计，不应直接作为运行时修复策略

在“先释放 local_clip 阈值钉死”的前提下，若继续施加更强的 margin/rank gate，最高可见到：

```text
shared threshold 降到 1.0；
temporal_crop TPR 可到 0.2；
但 frame_dropping TPR 仍可能维持 0.0。
```

但这里的 `sync_peak_rank` 依赖 ground-truth offset，仅适合做 audit 诊断，不适合直接进入运行时正式打分逻辑。也就是说，这组反事实用于说明“现有同步证据质量不足”，不应被当作正式实现方案。

### （三）根因判断

本轮审查后，可以将根因按控制强度排序为四层。

#### 根因 1：`reference_latent_shape` 在 real-video 路径上缺失传播，导致 local_clip 同步搜索退化

当前 source latent builder 生成 `mechanism_trace` 时，没有把 `reference_latent_shape` 写入 source sample。随后 attacked sample 与 reencoded sample 只是沿用既有 trace，因此缺失会一路传播到 detection。

这会导致 evidence 构建 reference descriptor 时退回到 `sample.latent_shape` 的兜底逻辑，从而在 local_clip attacked sample 上把同步搜索退化成错误的 reference family，对应的 candidate map 会系统性偏向伪峰，最终在 calibration negative 上形成 `S_tubelet = 1.0`、`S_sync = 1.0`、`S_final = 1.1` 的顶格样本。

该问题属于明确的代码级缺陷，而不是统计波动。

#### 根因 2：当前 fusion 只 gate rescue，不 gate sync 项本身

现有 `sync_rescue_fusion` 的结构本质上是：

```text
S_final = S_tubelet + gated_rescue_gain + lambda_sync * max(0, S_sync)
```

其中 `sync_rescue_applied` 只控制 `gated_rescue_gain`，并不控制 sync 项。因此：

```text
即使 rescue 被完全关掉，只要 S_sync 被错误地顶到 1.0，S_final 仍会被加到 1.1；
所以“只改 sync_rescue_applied gate”不会改变当前 shared threshold 被 local_clip 钉死的事实。
```

这解释了为什么前述 36 组 stricter rescue gate 反事实全部无效。

#### 根因 3：当前 sync candidate scoring 没有 coverage penalty，容易把稀疏重叠误判成高质量对齐

当前 `_score_alignment_candidate()` 的候选分数，实质上是对已匹配 tubelet projection 求均值；若某个 offset / scale 候选只在少量 tubelet 上偶然拿到很高投影，它仍可能得到很高的 candidate score。

当前实现缺少以下任一项：

```text
coverage ratio penalty；
minimum aligned-count gate；
best-vs-median 之外的 overlap consistency 约束。
```

这会直接放大 temporal_crop attacked-negative 的伪 rescue，也解释了为什么在 local_clip 阈值钉死被释放后，新的 calibration tail 又会被 temporal_crop negative 钉在约 1.044697。

#### 根因 4：frame_dropping 与当前 offset / scale 同步模型先验不匹配

`frame_dropping` attack 在参数层面提供的是 `kept_frame_indices`，同时显式给出：

```text
ground_truth_offset = None；
ground_truth_scale = None。
```

而当前 sync 搜索只能在：

```text
offset；
offset + scale
```

两类候选空间中寻找最佳对齐。

这意味着当前 `tubelet_sync` 的同步模型并不能表达“稀疏删帧导致的非均匀时间映射”。因此：

```text
gate 只能抑制假阳性；
但它不会凭空生成正确的 frame_dropping 对齐证据；
所以 frame_dropping 在本轮所有反事实中几乎都回不来。
```

#### 补充背景：source latent alias 仍是上游压力项，但不是当前第一修复顺序

此前已确认：no_attack clean-negative 的若干主导 alias family 在 source encoded latent 上已存在，reencode 主要起到放大与重排作用。该问题会持续抬高 clean-negative 上尾，但本轮 formal failure 的第一控制项仍是 local_clip 路径错误与 fusion / scoring 设计问题，而不是单独的 source alias。

### （四）最终修复方案

本轮建议采用“三层修复，逐层验证”的方案，而不是继续在现有 broken path 上做参数微调。

#### 第一层：先修 `reference_latent_shape` 传播链，解除 local_clip 伪峰

必须先修改以下路径：

```text
main/backends/real_video_vae_latent.py
在 source sample 的 mechanism_trace 中显式写入 reference_latent_shape；

experiments/real_video_vae_latent_probe/runner.py
在 _build_video_attack_sample() 与 _build_reencoded_sample() 中增加 setdefault 级别的防御性继承；

main/methods/temporal_tubelet_watermark/evidence.py
保留 fallback，但新增审计可见的 fallback 记录，避免以后静默退回 sample.latent_shape。
```

预期效果：

```text
local_clip calibration negative 不再系统性顶到 1.1；
shared threshold 应先从 1.1 释放；
之后再看其他攻击是否仍然压住 formal 表现。
```

这一层是必须项，不应跳过。

#### 第二层：把 sync 项与 rescue 一起纳入同一个“可观测置信度 gate”

当前不合理之处不是“是否有 gate”，而是 gate 只作用在 rescue，不作用在 sync 项。修复时应把两部分统一为：

```text
若 sync_confident = false：S_final = S_tubelet；
若 sync_confident = true：S_final = S_tubelet + rescue_gain + lambda_sync * S_sync。
```

其中 `sync_confident` 必须只依赖运行时可观测字段，不能依赖 ground truth。推荐优先使用：

```text
S_sync_positive_margin；
sync_alignment_coverage_ratio；
sync_alignment_matched_count。
```

不建议把 `sync_peak_rank` 直接接入正式打分，因为它依赖 benchmark 才知道的 ground-truth offset，仅适合 audit。

#### 第三层：在 sync candidate scoring 中加入 coverage penalty，压掉伪 rescue

建议将 `_score_alignment_candidate()` 从“纯均值”改成“均值 + coverage 约束”的形式，至少满足以下一项：

```text
candidate_score = mean_projection * coverage_ratio；
或 candidate_score 在 coverage_ratio 低于阈值时直接降权；
或 aligned_count 低于最小值时候选直接失效。
```

同时在 `mechanism_trace` 中补充：

```text
sync_alignment_matched_count；
sync_alignment_candidate_count；
sync_alignment_coverage_ratio；
sync_candidate_score_raw；
sync_candidate_score_penalized。
```

这样才能在不依赖 ground truth 的前提下，把 temporal_crop / frame_dropping 中“局部偶然高投影”的伪同步从 score 层面压掉。

#### 第四层：对 frame_dropping 采用“短期降 claim，长期换模型”的策略

在当前 offset / scale 同步模型下，不应指望通过 gate 微调就让 frame_dropping 变好。合理策略是：

```text
短期：把 frame_dropping 明确标记为当前 tubelet_sync 的未解决攻击，不作为已解决 supported claim；
中期：新增 deletion-aware 的同步搜索或等价的非均匀时间映射搜索，再重新评估该攻击；
在此之前，不使用 attack-specific threshold，不使用 test split 调参去“掩盖” frame_dropping 的结构性失配。
```

### （五）推荐执行顺序

本轮修复建议按以下顺序推进：

```text
1. 修复并测试 reference_latent_shape 传播链；
2. 重跑最小机制重算，确认 shared threshold 不再被 local_clip calibration negative 钉在 1.1；
3. 为 sync candidate 增加 coverage 相关 trace 字段；
4. 将 sync 项与 rescue 统一挂到基于 margin + coverage 的 observable confidence gate 下；
5. 仅使用 dev / calibration 选择 gate 参数；
6. 重跑 formal，重新审查 temporal_crop / frame_dropping / local_clip；
7. 若 frame_dropping 仍失败，则维持其 unresolved 状态，并单独立项 deletion-aware sync，而不是继续挤压 shared threshold。
```

### （六）本轮审查后的最终判断

截至 2026-05-15，可以给出以下结论：

```text
当前 tubelet_sync 的 formal failure 已可定位到明确根因；
第一根因是 local_clip 路径上的 reference_latent_shape 传播缺陷；
第二根因是 fusion 只 gate rescue、不 gate sync 项；
第三根因是 sync candidate scoring 缺少 coverage penalty；
frame_dropping 则属于当前同步模型与攻击类型的结构性失配。
```

因此，合理修复方案不是继续单独调 `sync_rescue_applied`，也不是直接改 shared threshold，而是：

```text
先修传播链；
再改 fusion gate 作用域；
再改 sync candidate scoring；
最后把 frame_dropping 作为单独的下一阶段机制任务处理。
```

---

## 十三、2026-05-15 性能优化审查增补

本节用于增补本轮对 formal package 运行性能的定向审查结果。该审查基于既有 package 中的 `runtime_profile/gpu_runtime_trace.csv`、`run_timing_summary.json`、artifact 体量统计与代码路径核对，不重新运行 VAE，不重建 attacked video，也不依赖 test split 反向调参。

### （一）当前项目性能状态

当前项目在性能层面同样可拆分为两层：

```text
Stage2ImplementationPass：实现闭环已形成，但 wall-clock 成本过高；
Stage2MechanismPass：尚未通过，同时当前性能状态已开始反过来限制机制迭代速度。
```

本轮审查时，最新 formal package 在 runtime profile 中的主要表现为：

```text
total_recorded_seconds = 11325.573497；
real_video_vae_latent_runner = 11311.526187；
gpu sample_count = 5585；
mean_gpu_util_percent = 1.442614；
median_gpu_util_percent = 0.0；
peak_gpu_util_percent = 16.0；
peak_memory_used_mb = 688.0；
low_utilization_ratio = 1.0。
```

同时，GPU burst 形态表现为：

```text
burst_count = 934；
mean_burst_seconds ≈ 2.807；
median_burst_seconds = 2；
max_burst_seconds = 8；
active_ratio ≈ 0.2347。
```

这说明当前 formal run 不是“GPU 已经吃满但总算力不够”，而是明显的“短 burst + 长空档”负载；当前瓶颈更像 runner 内部的大量串行 CPU / I/O work，而不是单纯的 VAE batch 太小。

### （二）本轮离线审查结果

#### 1. 当前 formal run 不是 GPU 饱和，而是串行 hot path 把 GPU 供给切碎

现有 `run_timing_summary.json` 只给出 5 个顶层事件，其中：

```text
model_preparation；
runtime_preflight；
real_video_vae_latent_runner；
table_and_report_rebuild；
formal_checker。
```

几乎全部耗时都落在 `real_video_vae_latent_runner`。但 `gpu_runtime_trace.csv` 中的 `event_tag` 全部为 `unlabeled`，因此当前 package 只能证明“runner 很慢”，不能直接把这3.15小时精确拆成 decode / attack / reencode / quality / temporal 五段。

#### 2. decode cache 已经生效，初始 VAE decode 不是第一瓶颈

本轮 package 内 artifact 体量统计为：

```text
decoded_videos = 621；
attacked_videos = 7000；
reencoded_latents = 7700；
watermarked_latents = 3080；
encoded_latents = 100。
```

这说明当前 decoded video cache 已明显摊薄了初始 decode 成本。相比之下，attack materialization、reencode 与其后的质量 / 时序后处理仍然在大规模重复发生，因此主瓶颈不再是“最前面的第一次 decode”。

#### 3. 当前更像是 attack + quality / temporal 后处理主导，其中 quality / temporal 更可疑

代码路径核对表明，当前每条 event 都按以下顺序串行执行：

```text
decode；
attack；
reencode；
quality metrics；
temporal metrics。
```

其中，`quality metrics` 与 `temporal metrics` 各自都会重新读取 reference / comparison video；`PSNR` / `SSIM` 当前走 CPU 路径；`LPIPS` 虽然走 GPU，但仍是“每次调用初始化模型 + 逐帧循环”的模式；`CLIP` 则尚未形成真实执行路径。也就是说，当前 runner 在 mp4 读盘、CPU 指标与小粒度 GPU 调用之间频繁切换，这正对应了前述“短 burst + 长空档”的 trace 形态。

#### 4. 继续调大 `vae_batch_size_frames`、`batch_size_frames` 与 `clip_batch_size`，不会直接救回 wall-clock

当前默认 formal clip 长度为32帧，而 VAE backend 的 batching 仅在“单个 clip 内按帧块切片”时生效。因此：

```text
当 batch_size_frames >= 32 后，再继续增大不会带来新的跨 clip batch；
gpu_profile_interval_seconds 只影响观测粒度，不会直接提速；
clip_batch_size 当前尚未进入真实 CLIP 执行路径；
lpips_batch_size 当前也尚未形成真正的 batched inference 控制项。
```

因此，当前 formal run 的低利用率不能通过“继续堆大 batch 参数”解决。

#### 5. attack-based split 不是首选分片单位，method-based split 更稳

records 统计显示：

```text
event_score_records = 9800；
local_clip = 2800；
其余每种 attack = 700。
```

这意味着 attack 维度并不完全均匀，`local_clip` 工作量明显更大；但 threshold 又是按 `method_variant` 独立校准的。因此：

```text
attack-based split 虽然可做，但会切穿单个 method 的 calibration / threshold 语义；
method-based split 更符合当前 runner 与 threshold 的组织方式。
```

### （三）根因判断

本轮审查后，可以将性能根因按控制强度排序为四层。

#### 根因 1：runner 仍是单进程、单事件串行闭环，GPU 空档无法被其他 clip 自动填满

当前 `real_video_vae_latent_runner` 的事件循环本质上是：

```text
一条 event 做完 decode / attack / reencode / quality / temporal；
再进入下一条 event。
```

在这种结构下，只要某一步骤落回 CPU / ffmpeg / 磁盘 I/O，GPU 就会空闲等待。由于当前没有“多 clip 并发补位”机制，L4 的绝大多数时间都会被浪费在阶段切换与串行等待上。

#### 根因 2：quality / temporal 路径重复读盘，且大量计算仍在 CPU 侧完成

当前质量与时序指标各自重复读取视频，并独立做后处理。这意味着：

```text
同一对 decoded / attacked video 会被 quality 读一次；
同一对 decoded / attacked video 会被 temporal 再读一次；
PSNR / SSIM 仍在 CPU 上按帧循环；
LPIPS 仍按调用级别重复初始化并逐帧执行。
```

这类路径不会持续压满 GPU，却会稳定拉长 wall-clock。

#### 根因 3：当前 clip 长度上限把单进程 VAE batching 的有效收益提前封顶

当前 formal dataset 的 frame count 固定为32，而 backend 的 encode / decode 只在单 clip 内部分帧切块。因此：

```text
batch_size_frames 从 8 提到 32 仍有意义；
batch_size_frames 从 32 再提到 128 / 256，执行语义几乎不变。
```

这意味着当前低 GPU 利用率不是因为“batch 还不够大”，而是因为“单个 clip 的天然工作量已经封顶”。

#### 根因 4：当前 runtime profile 中多个 knob 尚未真正进入有效执行路径

现有 profile 中的若干字段，当前并不是可靠的性能杠杆：

```text
clip_batch_size：当前没有真实 CLIP backend 与 batched CLIP inference；
lpips_batch_size：当前没有形成真实的 LPIPS batch 调度；
gpu_profile_interval_seconds：只影响采样可见性，不影响吞吐；
继续增大 vae_batch_size_frames / batch_size_frames：已被32帧 clip 上限吃掉。
```

因此，当前性能问题的核心不在“参数没调对”，而在“执行结构还没有给 GPU 足够连续的工作面”。

### （四）最终修复方案

本轮建议采用“先补可观测性、再补并行度、后补 hot path”的三层修复方案，而不是继续在当前串行路径上盲调 batch。

#### 第一层：先补 runner 内部可观测性，避免继续盲调

必须先修改以下路径：

```text
experiments/real_video_vae_latent_probe/runner.py
为 decode / attack / reencode / quality / temporal 增加子阶段 timing；

paper_workflow/notebook_utils/runtime_profile_workflow.py
增加 current_runtime_event_tag 的显式更新接口；

scripts/profile_runtime/summarize_run_timing.py
支持汇总 runner 子阶段事件，而不仅是 notebook 顶层事件。
```

预期效果：

```text
下一轮 formal package 能直接给出 decode / attack / reencode / quality / temporal 的占比；
GPU trace 不再全部是 unlabeled；
后续优化可以从“感觉像 I/O”升级为“有子阶段证据的定向修复”。
```

这一层是必须项，不应跳过。

#### 第二层：按 `method_variant` 做两路并行分片，优先吃掉 L4 的闲置算力

当前最现实、最可能直接缩短 wall-clock 的方案，不是继续增大 batch，而是把 formal run 从“单路长串行”改成“两路 method shard 并发”。推荐分片为：

```text
Shard A：frame_prc、tubelet_only、tubelet_sync；
Shard B：tubelet_only_lt01、tubelet_only_lt02、tubelet_only_lt08、tubelet_only_lt16。
```

推荐修改路径：

```text
paper_workflow/run_real_video_vae_latent_probe.ipynb
增加 method shard 配置与双 run_root 调度；

experiments/real_video_vae_latent_probe/runner.py
将现有 method_variants allowlist 暴露到 notebook / workflow 的正式调用路径；

paper_workflow/notebook_utils/real_video_vae_latent_probe_workflow.py
增加 shard 级 records / thresholds 合并与 rebuild 调度辅助；

scripts/check_results/* 或既有 rebuild 路径
复用 artifact builder / checker，从合并后的 governed records 重建 tables / reports。
```

预期效果：

```text
在不改变算法、不改 threshold 协议的前提下，提高 GPU 利用率并压缩墙钟时间；
由于 CPU / I/O 仍会竞争，不应宣称线性 2×；
但该方案是当前最接近“可立即落地”的 throughput 修复项。
```

#### 第三层：将 quality / temporal 改成“单次读盘、共享帧数据、共享模型”的后处理链

必须继续修改以下路径：

```text
main/analysis/real_video_quality_metrics.py
支持从已加载 frame tensor 直接计算，而不是强制内部再读 mp4；

main/analysis/real_video_temporal_metrics.py
支持复用同一份 reference / comparison frames；

experiments/real_video_vae_latent_probe/runner.py
将 decoded / attacked video 的帧数据在 quality 与 temporal 间共享；

main/analysis/real_video_quality_metrics.py
把 LPIPS 改成进程内单例模型 + batched frame inference，而不是逐调用初始化。
```

预期效果：

```text
减少重复 mp4 读盘；
减少 CPU frame-loop 开销；
给 GPU 更长、更连续的工作窗口；
为后续启用 CLIP 提供可复用的质量后处理通道。
```

#### 第四层：CLIP 路径应在性能基线稳定后再接入 batched GPU backend，而不是作为本轮提速主方案

当前 `CLIP similarity` 的主要问题是“治理口径与执行路径不一致”，而不是“它能立刻提速”。因此：

```text
CLIP 应修，但它属于 quality / semantic metric 修复，不属于当前首要吞吐修复；
若要接入，必须与 LPIPS 共用 batched quality backend 与共享 frame 采样路径；
不应在当前串行 hot path 尚未理顺时直接把 CLIP 叠加进去。
```

也就是说，本轮性能优化的主修复项是“并行度 + hot path”，而不是“先把 CLIP 打开”。

### （五）推荐执行顺序

本轮性能修复建议按以下顺序推进：

```text
1. 为 runner 增加 decode / attack / reencode / quality / temporal 子阶段 timing 与 GPU event tag；
2. 先在 proof / 小样本 formal 上验证 profiling 能区分子阶段；
3. 实现按 method_variant 的两路并行分片与结果合并；
4. 对比单路与双路的 wall-clock、GPU util、CPU util 与磁盘压力；
5. 将 quality / temporal 改成共享帧数据的单次读盘链路；
6. 将 LPIPS 改成 batched GPU inference；
7. 在性能基线稳定后，再把 CLIP 接到同一条 batched quality backend 上；
8. 重跑 formal，并重新审查机制迭代速度与 GPU 利用率是否得到实质改善。
```

### （六）本轮审查后的最终判断

截至 2026-05-15，可以给出以下结论：

```text
当前 real_video_vae_latent formal runtime 的主要性能问题不是 GPU 算力不足，而是 GPU 供给不足；
当前 wall-clock 更像被串行 runner、attack materialization、quality / temporal 后处理与重复读盘共同拉长；
继续增大 batch_size_frames、vae_batch_size_frames 或调整 profiler 采样频率，都不是当前第一修复方向；
当前最可行、最有希望直接缩短运行时间的方案，是按 method_variant 做两路并行分片；
随后必须把 quality / temporal 重构为共享帧数据与 batched GPU backend 的后处理链；
CLIP 应修，但它首先是治理与质量指标修复项，而不是当前首要吞吐修复项。
```

因此，本轮合理的性能修复方案不是继续在单路串行 formal run 上盲调 batch，也不是先把 `CLIP similarity` 打开，而是：

```text
先补 runner 内部可观测性；
再做 method-based 并行分片；
再重构 quality / temporal hot path；
最后再将 LPIPS / CLIP 纳入统一的 batched quality backend。
```

---

## 十四、2026-05-26 tl02 controlled validation 更新

本节用于补充 2026-05-26 最新一次 `tl02_controlled_validation` calibration-only 运行的正式判断，并据此更新下一步的修改优先级。

### （一）本次 tl02 运行的正式判断

本次 family 为：

```text
real_video_vae_latent_probe__formal__davis2017_trainval480p__20260526T012737Z__2e6f6bf
```

当前已回灌的 calibration 摘要位于：

```text
G:\我的云端硬盘\TSTW\results\families\real_video_vae_latent_probe__formal__davis2017_trainval480p__20260526T012737Z__2e6f6bf\stage2_calibration\stage2_mechanism_calibration_summary.json
```

该次运行的关键状态为：

```text
calibration_completion_status = anchor_only_partial_selection
selection_completion_status = incomplete_no_eligible_tubelet_sync_candidate
selection_blocking_reason = no_tubelet_sync_candidate_passes_selection_gate
search_stage_count = 2
search_terminated_early = false
selected_tubelet_only_candidate = tubelet_only_cal_tl02_sp04x04_w025
selected_tubelet_sync_candidate = null
```

这说明本次 `tl02` 结果不是“运行中断导致未定”，而是一次已完整执行完既定 2 个搜索阶段后的有效负结果。

其中，当前被选中的 `tubelet_only` anchor 指标为：

```text
no_attack_clean_negative_fpr = 0.0
no_attack_clean_positive_tpr = 0.05
temporal_crop_attacked_positive_tpr = 0.0
frame_dropping_attacked_positive_tpr = 0.1
local_clip_attacked_positive_tpr = 0.0
candidate_selection_status = weak_anchor_with_headroom
```

而当前 mechanism gate 对 anchor 的关键要求仍是：

```text
min_no_attack_clean_positive_tpr = 0.5
```

因此，这次 `tl02` 的主要结论不是“找不到好的 sync 参数”，而是：

```text
当前 tl02 anchor 本身就没有形成可用的 no_attack 正样本恢复能力；
在这样的 anchor 上继续做 sync 窄扫，不足以把 tubelet_sync 推到 eligible；
本次 sync_wide_scan 的 top rows 全部是 controlled but insufficient_signal，而不是 leakage-driven frontier。
```

当前最靠前的 `tubelet_sync` 窄扫候选虽然保持：

```text
fpr_controlled = true
quality_not_collapsed = true
negative_leakage_status = controlled
```

但同时仍然满足：

```text
selected_tubelet_sync_candidate = null
candidate_selection_status = insufficient_signal
local_clip_sync_gain = 0.0
temporal_crop_sync_gain = 0.0
mean_temporal_sync_gain <= 0.0
```

据此，当前应将 `tl02` 视为：

```text
一个已确认的 calibration-only 负结果；
一个可保留的 regression / forensics 锚点；
而不是下一轮 formal freeze 的候选方向。
```

### （二）对前述根因清单的当前状态修正

2026-05-15 审查结论中的若干代码级根因，在当前代码树中已经不再是“未修复状态”。

目前已可确认：

```text
reference_latent_shape 已在 source sample 的 mechanism_trace 中显式写入；
attacked sample 与 reencoded sample 路径也已做 setdefault 级别继承；
sync_rescue_fusion 已将 rescue gain 与 lambda_sync * S_sync 统一挂到 gate_sync；
sync candidate scoring 已具备 coverage_ratio、matched_count、sync_candidate_score_penalized 与 hybrid search 路径。
```

对应代码路径包括：

```text
main/backends/real_video_vae_latent.py
main/attacks/real_video_attack_registry.py
experiments/real_video_vae_latent_probe/runner.py
main/methods/temporal_tubelet_watermark/fusion.py
main/methods/temporal_tubelet_watermark/evidence.py
```

这意味着：

```text
2026-05-15 的“传播链缺失 / 只 gate rescue / 无 coverage penalty”应保留为历史根因说明；
但它们不再是 2026-05-26 这次 tl02 负结果的第一优先级解释。

```

当前更直接的解释是：

```text
在现有已修正的 sync 语义下，tl02 的 tubelet_only anchor 仍过弱；
anchor 无法先把 no_attack positive 拉出有效信号区间，导致 sync 也没有可审计的增益空间；
因此继续扩大 tl02 的 sync 参数网格，收益会非常低。
```

### （三）下一步明确修改方向

基于本次运行结果，当前不建议继续把 `tl02` 当作下一轮主要 calibration 候选，也不建议继续扩大 `tl02` 的 sync 网格。

当前更合理的下一步应明确切换为：

```text
先修 tubelet_only anchor 的 no_attack 正样本信号，再回到 sync。
```

具体而言，下一步修改方向应优先落在：

```text
main/methods/temporal_tubelet_watermark/evidence.py
```

并围绕以下两个局部面展开：

```text
_build_payload_coded_projections()
_build_tubelet_score()
```

目标不是继续调 `lambda_sync`、`sync_search_radius` 或 `min_sync_positive_margin`，而是先回答并修复：

```text
为什么在当前已修复传播链、已修复 sync gate、已接入 coverage penalty 的前提下，
tl02 的 tubelet_only anchor 在 dev / calibration 上仍只有 no_attack_clean_positive_tpr = 0.05。
```

因此，建议按以下顺序推进：

```text
1. 新增 tubelet_only / no_attack / watermarked_positive 的分布级取证，直接导出 S_tubelet、S_final、embedding support、tubelet_projection_coverage_ratio；
2. 检查 tl02 下 payload-coded projection 是否整体偏低，或 embedding support 是否被当前 score calibration 抵消；
3. 仅在 anchor 的 no_attack 正样本信号恢复到可用区间后，再重新评估是否值得继续做 tl02 sync 扫描；
4. 在此之前，将 tl02 保留为 regression / negative-control，而不是 formal freeze 候选。
```

当前一句话结论应固定为：

```text
先不要继续考虑 tl02 作为当前主候选方向；
下一步先修 tubelet_only anchor 的正样本恢复能力，再决定是否回到 tl02 的 sync 搜索。
```

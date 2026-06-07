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

### （四）selector 字段与 gate 语义修复回灌

在上述 `tl02_controlled_validation` 负结果之后，已完成一轮 selector 侧代码修复，用于排除候选选择路径本身继续混淆机制判断。修复范围限定在：

```text
scripts/check_results/select_stage2_mechanism_candidate.py
tests/functional/test_mechanism_candidate_selection.py
```

本轮修复确认并修正了三个 selector 级阻断项：

```text
1. `sync_confident` 的 canonical record 位置是 `mechanism_trace.sync_confident`，selector 现在优先读取该字段，顶层 `sync_confident` 仅作为 legacy fallback；
2. `tubelet_sync` 候选 eligibility 的 sync-confident negative tail 不再只统计 `local_clip`，而是统计所有 `attacked_negative`；
3. `tubelet_only` anchor 输出现在显式记录 `candidate_eligible`、`fpr_controlled` 与 `quality_not_collapsed`，弱 anchor 不再被误标为正式合格候选。
```

对应输出语义更新为：

```text
若 tubelet-only anchor 只满足 FPR 受控但不满足 mechanism gate，则 candidate_status = fpr_controlled_best_effort_candidate_selected；
若任何 attacked_negative record 出现 sync_confident = true，则对应 tubelet_sync row 的 candidate_eligible = false；
calibration grid / report 增加 sync_confident_attacked_negative_count，用于直接定位负样本 tail 是否阻断 sync 候选。
```

该修复不会改变 threshold calibration 协议，也不会使用 test split 参与参数选择。其作用是让后续 calibration 结果能清楚区分：

```text
代码层 selector / field 读取问题；
tubelet_only anchor 正样本信号不足；
tubelet_sync 参数搜索仍未找到 eligible candidate；
机制设计本身在某类攻击上存在结构性失配。
```

因此，在下一轮重跑后，如果仍出现：

```text
selected_tubelet_sync_candidate = null
selection_completion_status = incomplete_no_eligible_tubelet_sync_candidate
```

则应优先读取：

```text
sync_confident_attacked_negative_count
no_attack_clean_positive_tpr
mean_temporal_sync_gain
candidate_eligible
candidate_selection_status
```

若 `sync_confident_attacked_negative_count > 0`，说明候选仍被 attacked-negative sync tail 阻断；若该字段为0但 `no_attack_clean_positive_tpr < 0.5`，则仍应回到 tubelet_only anchor 正样本恢复能力，而不是继续扩大 sync 网格。

本轮验证结果为：

```text
python -m pytest -q tests/functional/test_mechanism_candidate_selection.py：12 passed；
python -m pytest -q：325 passed，67 deselected，3 warnings；
python tools/harness/run_all_audits.py：17 pass，0 fail。
```

### （五）当前状态保存（2026-05-27）

结论：**该结果只能判定为“部分合格”，不能判定为阶段 2 机制完整合格。**

## 1. 已合格部分：污染 / 漂移 bug 已被修复

本次结果中，之前的关键错误已经消失：

- `reference_latent_shape` 全部为：

```text
[32, 4, 32, 32]
```

- `payload_projection_count` 全部为：

```text
1024
```

这与 formal 配置一致：`256x256` 视频经 VAE 下采样 8 倍后得到 `32x32` latent。  
之前错误结果是 `[32,4,4,4]` 和 `payload_projection_count=16`，本次没有复现。

同时：

- `reference_latent_shape_source = mechanism_trace`
- `reference_latent_shape_fallback_used = False`
- `tubelet_projection_coverage_ratio = 1.0`
- `recomputed_delta_vs_recorded_S_tubelet = 0.0`

因此，**旧缓存污染、latent shape 漂移、fallback 伪造 shape 这类 bug 当前没有出现。**

## 2. tubelet_only anchor 取证：合格

选中的 tubelet-only anchor 为：

```text
tubelet_only_cal_tl02_sp04x04_w025
```

关键指标：

| 指标 | 数值 | 判断 |
|---|---:|---|
| clean negative FPR | 0.0 | 合格 |
| attacked negative FPR | 0.0 | 合格 |
| no_attack positive TPR | 1.0 | 合格 |
| temporal_crop positive TPR | 1.0 | 合格 |
| frame_dropping positive TPR | 1.0 | 合格 |
| local_clip positive TPR | 0.9875 | 合格 |
| dev watermarked_positive 决策 | 20/20 true | 合格 |
| clean_negative 决策 | 40/40 false | 合格 |

所以如果本次目标是：**验证 tubelet_only anchor 在修复 shape bug 后是否成立**，答案是：**合格**。

## 3. 不合格部分：tubelet_sync 机制目标未完成

总 summary 中：

```text
calibration_completion_status = anchor_only_partial_selection
selection_completion_status = incomplete_no_eligible_tubelet_sync_candidate
selection_blocking_reason = no_tubelet_sync_candidate_passes_selection_gate
selected_tubelet_sync_candidate = null
```

sync wide scan 中所有 top tubelet_sync candidate 都是：

```text
candidate_eligible = false
candidate_selection_status = insufficient_signal
sync_rescue_decision = FAIL
sync_leakage_decision = PASS
```

并且最佳 sync candidate 的增益为：

```text
temporal_crop_sync_gain = 0.0
local_clip_sync_gain = 0.0
mean_temporal_sync_gain = 0.0
```

也就是说：**sync 没有相对 tubelet_only 产生增益**。这不是缓存污染问题，而是当前实验设定下 tubelet_only anchor 已经接近饱和，sync 没有机会表现出 rescue gain。

## 4. 总体判断

| 审计目标 | 判断 |
|---|---|
| latent shape 污染是否修复 | 合格 |
| tubelet_only anchor 是否成立 | 合格 |
| stage 2 tubelet_sync 机制是否完成 | 不合格 |
| 是否可支持 “tubelet_sync beats tubelet_only” claim | 不可以 |
| 是否可以进入完整阶段 2 机制验收 | 不建议 |

## 5. 下一步建议

不要继续用当前同一组参数反复重跑期待 sync 入选。当前结果说明：

- bug 已修复；
- anchor 已过强；
- sync 没有增益空间。

下一步应改为：**设计一个不饱和的 anchor 场景**，让 temporal_crop 或 local_clip 下 tubelet_only 留出失败空间，再检验 tubelet_sync 是否能 rescue。当前结果适合作为“shape 修复 + tubelet_only anchor 成立”的证据，但不适合作为阶段 2 完整机制完成证据。

当前已推进的工程入口为 notebook 侧新增受治理 calibration target：

```text
tl02_unsaturated_anchor_validation
```

其目标是固定在 stage2 calibration-only 语境下，先构造非饱和 tubelet-only anchor（更长 tubelet、更粗 spatial patch、更保守 support 与中高 embedding margin），再在同一 anchor 签名下执行窄范围 `sync_wide_scan`，验证 `tubelet_sync` 是否出现可审计 rescue 增益。

### （六）当前状态保存（2026-06-03 unsaturated anchor probe 更新）

本次新增结果对应 family 为：

```text
real_video_vae_latent_probe__formal__davis2017_trainval480p__20260603T071820Z__e76625c
```

当前已回灌的 calibration 摘要位于：

```text
G:\我的云端硬盘\TSTW\results\families\real_video_vae_latent_probe__formal__davis2017_trainval480p__20260603T071820Z__e76625c\stage2_calibration\stage2_mechanism_calibration_summary.json
```

该次结果不是 formal 全量 family，也不是中途异常中断；它是 governed notebook 当前默认 target `tubelet_unsaturated_anchor_probe` 产生的一次 calibration-only anchor 探针快照。family 根目录只导出了：

```text
stage2_calibration/
```

其核心状态为：

```text
calibration_completion_status = anchor_only_partial_selection
calibration_blocking_reason = staged_search_missing_tubelet_sync_candidate
selection_completion_status = complete
search_stage_count = 1
selected_tubelet_sync_candidate = null
```

这表示本轮运行按设计完成了单阶段 `anchor_tubelet_only_wide` 搜索，并在 anchor-only 语义下正常结束；当前没有进入 `sync_wide_scan` / `sync_refine_scan`，因此该结果不能被解读为 stage 2 mechanism 完整通过，也不能被解读为 sync 候选搜索失败导致的异常中断。

## 1. 本次结果首先证明：anchor-only probe 路线已经跑通

本轮只运行了 1 个 search stage，并生成了 25 个 tubelet-only anchor variants。当前自动选中的 anchor 为：

```text
tubelet_only_cal_tl08_sp08x08_w010_em750
```

其关键指标为：

| 指标 | 数值 | 判断 |
|---|---:|---|
| no_attack clean negative FPR | 0.0 | 合格 |
| no_attack clean positive TPR | 1.0 | 合格 |
| max attacked negative FPR | 0.0 | 合格 |
| temporal_crop absolute TPR | 0.5 | 有信号 |
| local_clip absolute TPR | 1.0 | 已饱和 |
| temporal_crop anchor headroom | 0.5 | 仍有空间 |
| local_clip anchor headroom | 0.0 | 无空间 |

因此，这次结果至少可以支持以下两点：

- `tubelet_unsaturated_anchor_probe` 这条 notebook 默认 calibration-only 路线已经稳定落地；
- 当前网格中确实能找到 FPR 受控、质量未塌缩、且至少在部分 temporal attack 上保留 headroom 的 anchor。

## 2. 本次结果同时证明：当前网格里已经出现更像“非饱和 frontier”的候选

虽然自动选中的最强 anchor 是 `w010_em750`，但 top anchor 列表中已经出现更弱、也更适合作为后续 sync 验证起点的候选，例如：

```text
tubelet_only_cal_tl08_sp08x08_w005_em1000
```

其关键指标为：

| 指标 | 数值 | 判断 |
|---|---:|---|
| no_attack clean negative FPR | 0.0 | 合格 |
| no_attack clean positive TPR | 0.5 | 刚过 gate |
| max attacked negative FPR | 0.0 | 合格 |
| temporal_crop absolute TPR | 0.25 | 明显未饱和 |
| local_clip absolute TPR | 0.4375 | 明显未饱和 |
| temporal_crop anchor headroom | 0.75 | 空间较大 |
| local_clip anchor headroom | 0.5625 | 空间较大 |

这说明当前最重要的新结论不是“sync 仍然没跑”，而是：

```text
非饱和 anchor frontier 已经被成功扫到；
当前阻塞点开始从“有没有 headroom anchor”转移到“如何固定一个真正适合做 sync 验证的 anchor”。
```

换句话说，2026-05-27 的结论主要是“需要设计一个不饱和 anchor 场景”；而 2026-06-03 的新增结果已经把这个问题推进到下一步：

```text
不饱和 anchor 场景并非空想，当前网格里已经存在；
下一步不应继续只看 strongest anchor，而应显式固定 unsaturated frontier anchor 再跑 sync。
```

## 3. 当前总体判断

| 审计目标 | 判断 |
|---|---|
| anchor-only calibration probe 是否按设计完成 | 合格 |
| 当前 family 是否属于 formal 全量结果 | 否 |
| 当前结果是否已经给出 tubelet_sync 机制结论 | 否 |
| 当前结果是否证明 non-saturated anchor frontier 存在 | 是 |
| 当前 selector 是否已经把最适合 sync 验证的 unsaturated anchor 固定下来 | 否 |

因此，本轮结果的最准确定位应为：

```text
它不是阶段 2 机制完成证据；
它是“headroom anchor 已经出现”的证据；
它把下一步工作重点从“继续盲扫 anchor”收口到“固定 unsaturated anchor 后进入窄范围 sync_wide 验证”。
```

## 4. 下一步建议

当前最优先的后续方向应改写为：

```text
先固定 unsaturated frontier anchor，再执行 sync_wide_scan；
而不是继续沿用当前 strongest anchor，或直接把 anchor-only partial 结果误当成 mechanism 负结论。
```

更具体地说，下一步应优先推进：

- 在 notebook / workflow / selector 路径中增加“显式固定 unsaturated anchor”的受治理入口，而不是只返回 selection_score 最高的 strongest anchor；
- 以 `tubelet_only_cal_tl08_sp08x08_w005_em1000` 或同等 headroom 候选为起点，执行同一 anchor 签名下的窄范围 `sync_wide_scan`；
- 重点审计 `temporal_crop_sync_gain`、`local_clip_sync_gain`、`selected_tubelet_sync_candidate` 与 `candidate_eligible`，判断 sync 是否在非饱和 anchor 上首次出现可审计增益；
- 若固定 unsaturated anchor 后仍然 `local_clip_sync_gain = 0.0` 且 `selected_tubelet_sync_candidate = null`，则后续 root cause 应转回 sync evidence / scoring 本身，而不是继续扩大 anchor 网格。

当前一句话结论应更新为：

```text
本次结果仍然只能支持“部分合格，非阶段 2 机制完整合格”；
但它已经把后续方向明确收口到“固定非饱和 anchor，再做 sync 验证”，而不是继续泛化地重复扫 anchor。
```

---

## 十五、2026-06-04 搜索空间治理收口与 notebook 入口去参数化

本节用于登记 2026-06-03 至 2026-06-04 阶段 2 VAE mechanism calibration 的已确认负结果和当前代码治理结论。该内容只作为历史寻找记录保存, 不再作为默认运行路径。

### （一）已移出默认运行路径的参数方向

以下方向已经通过历史结果确认不适合作为下一轮默认搜索入口, 后续不应再由 notebook 默认进入:

```text
1. tl02_controlled_validation / tl02_unsaturated_anchor_validation:
   tl02 要么 anchor 过弱, 要么在修复 shape 污染后 tubelet_only 接近饱和, sync 没有可审计增益空间。

2. tubelet_unsaturated_anchor_probe 的单 anchor 窄扫:
   固定 tubelet_only_cal_tl08_sp08x08_w005_em1000 后, sync 只能得到 local_clip_sync_gain = 0.0625,
   temporal_crop_sync_gain = 0.0, mean_temporal_sync_gain = 0.020833, 不能通过 mechanism gate。

3. sync_refine_scan 作为默认第三阶段:
   历史结果中出现 selected_anchor_not_covered_by_sync_stage_records, 说明该 refine 路径可能在 seed 与 anchor 签名不一致时浪费运行资源。
   后续默认搜索不再包含该阶段, 只保留在需要专项诊断时手动恢复。

4. notebook 内部通过 stage2_calibration_target 生成 override grid:
   该方式曾因环境变量映射错误导致 manual config 显示正确但实际回退到基础 grid。
   后续 notebook 不再内置参数网格或 target 分支, 只读取仓库中的 calibration grid 配置文件。
```

### （二）当前默认搜索方案

当前默认配置收口到:

```text
configs/ablation/stage2_vae_mechanism_calibration_grid.json
```

该配置直接定义多 anchor frontier 与对应 sync 搜索阶段, notebook 不再生成临时 override grid。当前默认 anchor frontier 为:

```text
tubelet_only_cal_tl08_sp08x08_w005_em1000
tubelet_only_cal_tl08_sp08x08_w006_em1000
tubelet_only_cal_tl08_sp08x08_w007_em1000
tubelet_only_cal_tl08_sp08x08_w008_em1000
```

每个 anchor 后接一个 `tubelet_sync` 搜索阶段, 以减少重复修改 notebook 的风险, 并让每次参数调整只发生在仓库配置文件中。

### （三）notebook 入口治理结论

`paper_workflow/run_real_video_vae_latent_probe.ipynb` 当前只作为运行流程脚本:

```text
1. 设置 Colab / Drive / runtime / dataset / model 等运行环境;
2. 从仓库配置文件读取 stage2 mechanism calibration grid;
3. 调用 repository module 执行 runner、selector、forensics、packager;
4. 不再在 notebook 中显式保存 anchor 网格、sync 网格或 stage target 分支。
```

后续如果需要更换参数或搜索空间, 只修改:

```text
configs/ablation/stage2_vae_mechanism_calibration_grid.json
```

然后在 Colab 中重新拉取仓库代码即可运行, 不需要再手动编辑 notebook。该设计属于通用工程写法: notebook 保持为稳定入口, 参数搜索空间由仓库配置治理; 同时也属于本项目特定治理要求: formal 输出仍由 repository modules 生成, notebook 不直接写 records、thresholds、tables、reports。

## 十六、2026-06-05 本次 1540 候选搜索结果与后续收缩决策

### 16.1 本次结果目录

本次检查的结果目录为:

```text
G:\我的云端硬盘\TSTW\results\families\real_video_vae_latent_probe__formal__davis2017_trainval480p__20260604T013252Z__5977a65
```

该目录仅包含 `stage2_calibration/` 输出, 表明本次运行主要执行阶段 2 mechanism calibration 路径。最后关键文件写入时间为 2026-06-05 02:28:46, 结合 family id 中的 UTC 时间 `20260604T013252Z`, 本次运行耗时约 16小时56分钟。该耗时与实际生成的 1540 个 method variant 候选一致, 不属于卡死。

### 16.2 关键候选与指标

本次 broad search 的实际规模为:

```text
campaign_mode = staged_search
search_stage_count = 8
generated_method_variant_count = 1540
```

本次搜索已经找到一个受控 FPR 下具备 temporal crop 与 local clip 增益的 `tubelet_sync` 候选:

```text
tubelet_sync_cal_tl08_sp08x08_w005_em1000_sr08_ls025_mg000_cv062_mc01_cs350_frsync_rescue
```

该候选写入到:

```text
stage2_calibration\tubelet_sync_real_video_vae_candidate.json
```

其核心指标为:

```text
max_attacked_negative_fpr = 0.0
temporal_crop_sync_gain = 0.25
frame_dropping_sync_gain = 0.0
local_clip_sync_gain = 0.1875
mean_temporal_sync_gain = 0.145833
temporal_crop_attacked_positive_tpr = 0.25
local_clip_attacked_positive_tpr = 0.625
```

该候选对应的 anchor 为:

```text
tubelet_only_cal_tl08_sp08x08_w005_em1000
```

anchor 指标为:

```text
max_attacked_negative_fpr = 0.0
temporal_crop_attacked_positive_tpr = 0.0
frame_dropping_attacked_positive_tpr = 0.5
local_clip_attacked_positive_tpr = 0.4375
```

因此, 本次结果已经提供了阶段 2 机制证明所需的核心方向: 在 `w005` anchor 下, `tubelet_sync` 能够在 `max_attacked_negative_fpr = 0.0` 的条件下提升 temporal crop 与 local clip 的 attacked positive TPR。

### 16.3 失败路径与原因

本次 broad search 后续更高 support anchor 分支不再继续作为默认搜索路径:

```text
w006 sync: incomplete_no_eligible_tubelet_sync_candidate
w007 sync: incomplete_no_eligible_tubelet_sync_candidate
w008 sync: incomplete_no_eligible_tubelet_sync_candidate
```

其中 `w008` anchor 本身已经接近饱和:

```text
temporal_crop_attacked_positive_tpr = 0.5
frame_dropping_attacked_positive_tpr = 1.0
local_clip_attacked_positive_tpr = 1.0
max_attacked_negative_fpr = 0.0
```

该现象说明高 support anchor 的主要问题不是 FPR 失控, 而是 anchor 已经过强或局部饱和, 导致 sync 分支难以再形成可审计的增益。继续 broad search `w006 / w007 / w008` 会消耗大量时间, 并且会让最后失败 stage 覆盖前面已经成功的 `w005` sync 候选, 不利于完成阶段 2 机制证明。

### 16.4 后续收缩决策

默认搜索空间收缩为 `w005 focused refinement`:

1. 保留 `tubelet_only_cal_tl08_sp08x08_w005_em1000` 作为唯一 anchor。
2. 只围绕已成功的 `sync_rescue_fusion` 候选做局部精扫。
3. 移除默认路径中的 `w006 / w007 / w008` sync broad search。
4. 修正机制校准 summary 聚合逻辑: 如果任一 sync stage 已经选出合格 `selected_tubelet_sync_candidate`, 顶层 `calibration_completion_status` 应以该成功候选为准, 不得被后续失败 stage 覆盖。

预计下一次运行候选数将从 1540 降低到约 289 个, 运行时间应明显缩短, 同时更可能直接产出用于阶段 2 机制证明的稳定候选与完成状态。


## 十七、2026-06-05 focused refinement 完成结果与阶段 2 completion run 配置

### 17.1 最新结果目录

本次检查的结果目录为:

```text
G:\我的云端硬盘\TSTW\results\families\real_video_vae_latent_probe__formal__davis2017_trainval480p__20260605T010044Z__ea47560
```

该结果来自收缩后的 `w005 focused refinement` 搜索空间。相比上一轮 1540 个候选的 broad search, 本轮实际运行规模为:

```text
campaign_mode = staged_search
search_stage_count = 2
generated_method_variant_count = 289
```

顶层机制校准状态已经闭合:

```text
calibration_completion_status = complete
selection_completion_status = complete
calibration_blocking_reason = null
selection_blocking_reason = null
search_terminated_early = false
```

### 17.2 冻结的阶段 2 candidate

本轮选出的 candidate 为:

```text
tubelet_sync_cal_tl08_sp08x08_w005_em1000_sr08_ls015_mg000_cv062_mc01_cs250_frsync_rescue
```

关键参数为:

```text
tubelet_length = 8
spatial_patch_size = [8, 8]
embedding_projection_support_weight = 0.05
embedding_margin = 1.0
lambda_sync = 0.015
sync_search_radius = 8
min_sync_positive_margin = 0.0
min_sync_alignment_coverage_ratio = 0.0625
min_sync_alignment_matched_count = 1
min_sync_candidate_score = 0.25
fusion_rule = sync_rescue_fusion
```

其机制指标为:

```text
max_attacked_negative_fpr = 0.0
temporal_crop_sync_gain = 0.25
frame_dropping_sync_gain = 0.0
local_clip_sync_gain = 0.25
mean_temporal_sync_gain = 0.166667
temporal_crop_attacked_positive_tpr = 0.25
local_clip_attacked_positive_tpr = 0.6875
```

对应 anchor 为:

```text
tubelet_only_cal_tl08_sp08x08_w005_em1000
```

anchor 指标为:

```text
max_attacked_negative_fpr = 0.0
temporal_crop_attacked_positive_tpr = 0.0
frame_dropping_attacked_positive_tpr = 0.5
local_clip_attacked_positive_tpr = 0.4375
```

因此, focused refinement 结果证明: 在 FPR 保持为 0.0 的条件下, `tubelet_sync` 将 temporal crop 从 0.0 提升到 0.25, 将 local clip 从 0.4375 提升到 0.6875。

### 17.3 代码冻结决策

根据本轮结果, 项目默认配置进入阶段 2 completion run 路径:

1. `configs/method/tubelet_sync_real_video_vae_candidate.json` 保存原始校准 candidate, 用于追踪 candidate 身份与参数来源。
2. `configs/method/real_video_tubelet_sync_candidate_runtime.json` 使用相同参数作为 real-video formal completion run 的 `tubelet_sync` override 配置, 并保留 `method_variant = tubelet_sync`, 以便 mechanism audit 能够按主方法名聚合 records。
3. `configs/method/real_video_tubelet_only_anchor.json` 保存对应的 `w005` anchor 参数, 并通过 ablation `method_config_paths` 作为主 formal run 中的 `tubelet_only` 对照组。
4. `configs/ablation/real_video_vae_latent_ablation.json` 在 formal profile 中关闭 tubelet length sweep, 阶段 2 completion run 只运行 `frame_prc / tubelet_only / tubelet_sync` 三个主方法, 避免把额外 sweep 成本混入机制证明闭合测试。
5. `paper_workflow/run_real_video_vae_latent_probe.ipynb` 默认切换为主 formal completion run: 执行 main formal、跳过 calibration、要求 formal checker 与 stage 2 mechanism audit 均通过。

### 17.4 下一次运行目标

下一次 notebook 运行应产出完整 family 包, 而不只是 `stage2_calibration/` 快照。预期完成条件为:

```text
formal_validation_summary.status = true
Stage2MechanismDecision = PASS
selected_sync_method_variant = tubelet_sync
records / thresholds / tables / reports / manifest 均可重建
```

如果该 completion run 通过, 阶段 2 VAE 机制证明即可进入收尾整理与阶段推进评审。



## 十八、2026-06-05 formal completion 运行失败记录与候选状态回退

### 18.1 结果来源

本轮记录来自用户保存的 Colab runtime 压缩包:

```text
G:\我的云端硬盘\TSTW
esults\TSTW_runtime_runs_20260605_080700.zip
```

对应 run root 为:

```text
/content/TSTW_runtime/runs/real_video_vae_latent_probe_formal
```

本轮实际使用的 commit 为:

```text
9789775
```

该运行不是 workspace 准备失败, 也不是 runner 中途崩溃。主 formal runner 已经完成, 并产出了 records、thresholds、tables、reports、runtime manifest 与 artifact manifest。

### 18.2 formal checker 结果

`formal_validation_summary.json` 的核心结论为:

```text
status = false
record_count = 4200
threshold_count = 3
Stage2ImplementationDecision = INCONCLUSIVE
RealVideoVaeLatentDecision = INCONCLUSIVE
BlockingReasons = [clean_negative_fpr_controlled]
NextAllowedStage = remain_in_real_video_vae_latent_probe
```

required paths 全部存在:

```text
event_scores = true
thresholds = true
main_tpr_fpr_table = true
real_video_attack_breakdown = true
quality_table = true
temporal_consistency_table = true
real_video_vae_latent_governance_summary = true
report = true
runtime_manifest = true
artifact_manifest = true
```

因此, 该结果应登记为: 正式 completion run 产物完整, 但 formal gate 未通过。

### 18.3 关键指标

主表 `main_tpr_fpr_table.csv` 中与失败直接相关的指标为:

```text
frame_prc no_attack clean_negative_FPR = 0.0
frame_prc no_attack clean_positive_TPR = 1.0

tubelet_only no_attack clean_negative_FPR = 0.05
tubelet_only no_attack clean_positive_TPR = 0.4

tubelet_sync no_attack clean_negative_FPR = 0.05
tubelet_sync no_attack clean_positive_TPR = 0.4
```

由于 formal gate 使用 `target_fpr = 0.001`, `tubelet_only` 与 `tubelet_sync` 在 test clean_negative 上出现 1/20 false positive, 导致 empirical clean FPR 为 0.05, 从而触发 `clean_negative_fpr_controlled` 阻断。

机制审计文件 `stage2_mechanism_decision.json` 的核心结论为:

```text
Stage2MechanismDecision = INCONCLUSIVE
SyncRescueDecision = FAIL
SyncLeakageDecision = PASS
SyncCandidateSelectionStatus = insufficient_signal
RecommendedNextAction = stage2_implementation_fix
```

机制阻断原因为:

```text
sync_positive_negative_score_gap_low
tubelet_only_no_attack_positive_tpr_low
tubelet_only_not_above_frame_prc
tubelet_sync_no_attack_positive_tpr_low
tubelet_sync_not_above_tubelet_only_temporal
```

关键机制指标为:

```text
tubelet_only_gain_over_frame_prc = -0.1725
tubelet_sync_gain_over_tubelet_only_temporal = 0.016667
sync_positive_negative_score_gap = -0.000995
```

按 attack 展开的同步增益显示:

```text
temporal_crop: tubelet_only = 0.2, tubelet_sync = 0.2, sync_gain = 0.0
local_clip: tubelet_only = 0.2125, tubelet_sync = 0.2625, sync_gain = 0.05
frame_dropping: tubelet_only = 0.45, tubelet_sync = 0.45, sync_gain = 0.0
```

该结果说明: focused refinement 中的 candidate 在小样本校准集上出现了正向趋势, 但在 formal 样本量与完整 test split 下未能稳定复现阶段 2 机制证明所需的分离度、no-attack 正样本召回和同步救援增益。

### 18.4 候选状态修正

上一节第 17 节将 `tubelet_sync_cal_tl08_sp08x08_w005_em1000_sr08_ls015_mg000_cv062_mc01_cs250_frsync_rescue` 作为 completion run 候选冻结。根据本轮 formal completion 结果, 该判断需要回退为:

```text
候选状态 = calibration_candidate_not_formal_passed
是否可作为阶段 2 完成证明默认 candidate = false
是否保留为历史搜索记录 = true
是否建议原样重跑 = false
```

该候选仍有历史价值: 它说明 `local_clip` 上存在少量 sync 增益, 且同步泄漏没有失控。但它不能支撑阶段 2 completion claim, 因为 formal 结果同时暴露了 clean FPR、no-attack positive TPR、sync score gap 和 temporal attack sync gain 不足。

### 18.5 工程结论

1. notebook 的 formal checker 报错是预期行为, 不是 notebook cell bug。
2. 本轮运行已完成产物生成, 失败发生在正式门禁判断阶段。
3. 之前小样本通过不能视为阶段 2 机制成立, 只能视为候选方向提示。
4. 后续不应原样重复运行该 candidate。
5. 下一步应转向 formal-sample-aware 的小范围机制诊断, 优先修复正负分离度与 no-attack 正样本召回, 再重新执行完整 completion run。


## 十九、2026-06-05 配置清理与下一轮 formal-sample-aware 诊断搜索决策

### 19.1 清理原因

上一轮 formal completion run 已证明 `tubelet_sync_cal_tl08_sp08x08_w005_em1000_sr08_ls015_mg000_cv062_mc01_cs250_frsync_rescue` 不能作为阶段 2 完成证明候选。若继续把它保留为仓库默认 candidate, 后续 notebook 会反复进入已验证失败路径, 造成时间和算力浪费。

因此本次将失败候选从默认运行配置中移除。失败窗口、候选参数和 formal 失败指标仅保留在本文档第 17 节和第 18 节作为历史搜索记录。

### 19.2 已清理的默认路径

本次配置决策为:

```text
删除失败候选的默认 method override
删除失败候选作为 mechanism default candidate 的登记
删除失败候选 runtime config 与 anchor config
notebook 默认不再运行 completion formal gate
notebook 默认进入 20 样本机制诊断校准
```

具体含义为:

1. `configs/ablation/real_video_vae_latent_ablation.json` 不再引用失败候选的 `method_config_paths`。
2. `configs/ablation/real_video_vae_latent_ablation.json` 不再登记 `mechanism_default_candidate_method_config_path`。
3. `configs/method/real_video_tubelet_only_anchor.json`、`configs/method/real_video_tubelet_sync_candidate_runtime.json`、`configs/method/tubelet_sync_real_video_vae_candidate.json` 不再作为默认静态配置保留。
4. 下一轮 calibration 若发现新候选, 可重新生成 `configs/method/tubelet_sync_real_video_vae_candidate.json`; 生成前该文件不代表已通过 formal 的 candidate。

### 19.3 下一轮搜索口径

下一轮搜索改为 formal-sample-aware 诊断搜索:

```text
samples_per_role_override = 20
run_main_formal = false
run_stage2_mechanism_calibration = true
reset_stage2_mechanism_calibration_run_root = true
require_stage2_mechanism_pass = false
run_stage2_local_clip_sync_forensics = true
package_non_formal_audit_bundle = true
```

这一配置的目标不是直接宣布阶段 2 通过, 而是在 formal 样本量下筛掉小样本假阳性候选, 输出可用于判断下一步的 candidate grid、diagnostics、forensics 和 non-formal audit bundle。

### 19.4 新的候选选择门槛

下一轮校准将 formal 已知失败条件提前纳入选择门槛:

```text
max_clean_negative_fpr = 0.0
max_attacked_negative_fpr = 0.0
min_no_attack_clean_positive_tpr = 0.5
min_mean_temporal_sync_gain = 0.05
min_tubelet_sync_gain_over_tubelet_only_temporal = 0.1
min_sync_positive_negative_score_gap = 0.05
```

这些门槛的设计目的在于: 不再允许 clean negative FPR = 0.05 的候选进入 completion 候选池, 也不再允许 no-attack 正样本召回不足或 sync gain 只在小样本局部成立的候选进入默认完成路径。

### 19.5 收缩后的搜索空间

下一轮 anchor 诊断空间为:

```text
tubelet_length = [4, 8, 16]
spatial_patch_size = [[4, 4], [8, 8]]
embedding_projection_support_weight = [0.03, 0.05, 0.07]
embedding_margin = [0.8, 1.0, 1.2]
```

下一轮 sync 诊断空间为:

```text
lambda_sync = [0.01, 0.015, 0.025, 0.04]
sync_search_radius = [6, 8, 10]
min_sync_positive_margin = [0.0, 0.02]
min_sync_alignment_coverage_ratio = [0.0625, 0.125]
min_sync_alignment_matched_count = [1, 2]
min_sync_candidate_score = [0.25, 0.35, 0.45]
fusion_rule = sync_rescue_fusion
```

该搜索空间属于诊断性收缩搜索, 而不是重新扩大盲搜。其重点是检查是否存在同时满足低 FPR、no-attack 正样本召回和 temporal/local clip sync gain 的参数区域。


## 二十、2026-06-06 `TSTW_runtime_runs_20260606_053856` 中断运行判断与 runner 修正依据

### 20.1 结果位置与完成状态

本次检查对象为:

```text
G:\我的云端硬盘\TSTW\results\TSTW_runtime_runs_20260606_053856.zip
```

该压缩包中未发现完整的 `stage2_mechanism_calibration_summary.json`。从 runtime 记录判断, 本次运行已经完成 `formal_anchor_diag`, 随后进入 `formal_sync_diag`, 并在 sync 阶段被手动中断。

关键耗时为:

```text
formal_anchor_diag runner = 18962.64053 秒, 约 5.27 小时
formal_sync_diag runner = 55443.279297 秒, 约 15.40 小时, KeyboardInterrupt 中断
```

因此, 本次运行不是正常完成的阶段 2 机制证明结果, 而是一次具有诊断价值的 partial run。其主要价值在于确认当前搜索瓶颈已经前移到 anchor 阶段。

### 20.2 anchor 阶段诊断结论

`formal_anchor_diag` 的 grid 规模为 54 行。聚合结果显示:

```text
eligible anchors = 0
FPR controlled anchors = 0
max_attacked_negative_fpr = 0.025, 覆盖全部 anchor rows
no_attack_clean_negative_fpr = 0.0 或 0.025
no_attack_clean_positive_tpr 最大约 0.75
```

相对较好的方向集中在:

```text
tubelet_length = 4
embedding_projection_support_weight = 0.07
embedding_margin = 1.0 或 1.2
spatial_patch_size = [4, 4] 或 [8, 8]
```

但所有 anchor 至少存在 `1/40` 的 attacked-negative 误报, 即 `max_attacked_negative_fpr = 0.025`。在当前 strict gate 要求 `max_attacked_negative_fpr = 0.0` 的条件下, 这些 anchor 均不能成为 eligible candidate。

### 20.3 为什么 sync 阶段属于白跑

本轮运行中 `formal_sync_diag` 已经继续运行约 15.40 小时, 但 anchor 阶段没有任何 eligible candidate。此时继续 sync 搜索的工程价值很低, 原因是:

1. sync 阶段需要依赖可接受的 tubelet-only anchor 作为机制锚点。
2. anchor 的 attacked-negative FPR 已经泄漏, sync 搜索即使产生局部增益, 也无法直接补足 strict low-FPR 门槛。
3. 当前阶段 2 的机制证明目标要求低 FPR 与同步救援同时成立, 不能用 FPR 不合格的 anchor 作为完成证明基础。

因此, 当 anchor 阶段没有 eligible candidate 时, runner 应提前停止, 并输出可审计的 partial summary, 而不是继续进入长时间 sync 搜索。

### 20.4 本次代码修正决策

根据本次 partial run, 项目代码采用两项修正:

```text
1. calibration runner 支持 threshold_protocol_overrides
2. calibration runner 支持 strict_anchor_required_before_sync early-stop
```

第一项修正用于在 calibration grid 中提高 threshold guard band, 使下一轮搜索可以尝试压低 attacked-negative FPR 泄漏。该 override 只允许修改 guard band 与验证 profile 相关字段, 不允许修改 calibration split、negative roles、test threshold update 或 attack-specific threshold 等固定低 FPR 协议语义。

第二项修正用于在 anchor 阶段无 eligible candidate 时提前停止, 避免再次浪费约 15 小时进入 sync 阶段。该行为属于工程效率修正, 不改变阶段 2 机制证明的科学判定标准。

### 20.5 下一轮运行预期

下一轮运行应优先验证 guard band 是否能把 attacked-negative FPR 从 `0.025` 压到 `0.0`。预期分为两种情况:

1. 若 anchor 仍无 eligible candidate, runner 将在 `formal_anchor_diag` 后 early-stop, 并输出 partial summary 指明 FPR 泄漏仍未解决。
2. 若 anchor 出现 eligible candidate, runner 才会进入 `formal_sync_diag`, 用于验证 temporal crop 或 local clip 下的 sync rescue gain 是否能支撑阶段 2 机制证明。

因此, 后续不应继续扩大 sync 搜索作为首要方向。当前首要方向是用更严格的 threshold guard band 和已收缩的 anchor 搜索空间解决 attacked-negative FPR 泄漏。


## 二十一、2026-06-07 `20260606T091150Z__0b83ee9` anchor-first 诊断结果与下一轮搜索收缩

### 21.1 结果位置

本次检查对象为:

```text
G:\我的云端硬盘\TSTW\results\families\real_video_vae_latent_probe__formal__davis2017_trainval480p__20260606T091150Z__0b83ee9
G:\我的云端硬盘\TSTW\results\TSTW_runtime_runs_20260606_143444.zip
```

本次运行仅产出 `stage2_calibration/` 与 non-formal audit bundle, 未进入主 formal completion。该行为符合当前阶段的诊断目标。

### 21.2 runner 路径判断

本次机制校准 summary 的关键状态为:

```text
calibration_completion_status = anchor_only_partial_selection
calibration_blocking_reason = selected_tubelet_only_candidate_not_eligible_for_sync
selection_completion_status = complete
selection_blocking_reason = null
search_terminated_early = true
terminated_before_stage_name = formal_sync_diag
search_stage_count = 1
generated_method_variant_count = 55
selected_tubelet_sync_candidate = null
```

该结果说明两项工程修正均已生效:

```text
threshold_protocol_overrides 已进入临时 protocol 配置
strict_anchor_required_before_sync 已阻止无效 sync 搜索
```

因此, 本次不是 notebook 错误, 也不是异常中断。runner 已经在 anchor 不合格时正确 early-stop, 避免再次白跑约 15 小时 sync 阶段。

### 21.3 本次最优 anchor 与指标

本次选出的 best-effort anchor 为:

```text
tubelet_only_cal_tl04_sp04x04_w007_em1000
```

其核心指标为:

```text
candidate_eligible = false
fpr_controlled = true
quality_not_collapsed = true
no_attack_clean_negative_fpr = 0.0
max_attacked_negative_fpr = 0.0
no_attack_clean_positive_tpr = 0.3
temporal_crop_attacked_positive_tpr = 0.1
frame_dropping_attacked_positive_tpr = 0.3
local_clip_attacked_positive_tpr = 0.05
```

该结果相对于上一轮 `max_attacked_negative_fpr = 0.025` 的状态有明确进展: attacked-negative FPR 泄漏已经被压到 `0.0`。但该 anchor 仍不能进入 sync, 因为 no-attack clean positive TPR 只有 `0.3`, 低于阶段 2 当前候选门槛。

### 21.4 当前瓶颈变化

根据本次结果, 阶段 2 的首要瓶颈已经从:

```text
attacked-negative FPR 泄漏
```

转移为:

```text
strict threshold 下 positive signal 不足
```

这意味着后续不应扩大 sync 搜索。sync 搜索必须依赖 eligible tubelet-only anchor, 而当前最接近可用的 anchor 是 `tubelet_length = 4`, `embedding_projection_support_weight = 0.07`, `embedding_margin = 1.0 或 1.2`, `spatial_patch_size = [4, 4] 或 [8, 8]` 这一邻域。

### 21.5 下一轮配置决策

下一轮配置收缩为 `tl04 high-support anchor recovery`:

```text
tubelet_length = [4]
spatial_patch_size = [[4, 4], [8, 8]]
embedding_projection_support_weight = [0.07, 0.08, 0.09, 0.10, 0.12]
embedding_margin = [1.0, 1.2]
```

该搜索空间的目标是验证更高 support weight 是否能够在保持 `max_attacked_negative_fpr = 0.0` 的同时, 将 `no_attack_clean_positive_tpr` 从 `0.3` 推高到 `0.5` 或以上。

若下一轮 anchor 仍未 eligible, runner 会继续在 anchor 后 early-stop。若下一轮 anchor 变为 eligible, 才进入紧凑 sync 搜索。sync 搜索空间同步收缩为:

```text
lambda_sync = [0.01, 0.015, 0.025]
sync_search_radius = [6, 8]
min_sync_positive_margin = [0.0, 0.02]
min_sync_alignment_coverage_ratio = [0.0625]
min_sync_alignment_matched_count = [1]
min_sync_candidate_score = [0.25, 0.35]
fusion_rule = sync_rescue_fusion
```

该配置属于诊断性高命中率搜索, 不是重新 broad search。其判断逻辑是: 先确认 anchor positive signal 是否可恢复; 若可恢复, 再用较小 sync 网格验证是否存在 temporal crop 或 local clip 的同步救援增益。

### 21.6 运行时间预估

本次 anchor stage 55 个候选耗时约 5.33 小时。下一轮 anchor stage 约为 20 个候选加 frame baseline, 因此若 anchor 仍不通过, 预计耗时为:

```text
约 2-3 小时
```

若 anchor 通过并进入紧凑 sync stage, sync 网格约 24 个候选, 预计总耗时为:

```text
约 4-7 小时
```

若 Colab Drive I/O、视频攻击物化或 L4 资源波动较大, 实际时间可能上浮到:

```text
约 8-10 小时
```

但按照当前 early-stop 与收缩后的搜索空间, 正常情况下不应再次出现 20 小时以上仍无结论的运行。


## 二十二、2026-06-07 `20260606T182709Z__c28e2c4` 结果判断与 sync-rescuable anchor 策略

### 22.1 结果位置

本次检查对象为:

```text
G:\我的云端硬盘\TSTW\results\families\real_video_vae_latent_probe__formal__davis2017_trainval480p__20260606T182709Z__c28e2c4
G:\我的云端硬盘\TSTW\results\TSTW_runtime_runs_20260606_231452.zip
```

本次运行已经完成两个 staged search:

```text
formal_anchor_diag
formal_sync_diag
```

顶层状态为:

```text
calibration_completion_status = anchor_only_partial_selection
calibration_blocking_reason = no_tubelet_sync_candidate_passes_selection_gate
selection_completion_status = incomplete_no_eligible_tubelet_sync_candidate
search_terminated_early = false
search_stage_count = 2
generated_method_variant_count = 45
selected_tubelet_sync_candidate = null
```

这说明 runner 路径正确: anchor 已通过, 因此进入 sync; 但 sync 未通过机制选择门槛。

### 22.2 本次关键进展

本次最优 anchor 为:

```text
tubelet_only_cal_tl04_sp04x04_w012_em1000
```

核心指标为:

```text
candidate_eligible = true
fpr_controlled = true
quality_not_collapsed = true
no_attack_clean_negative_fpr = 0.0
max_attacked_negative_fpr = 0.0
no_attack_clean_positive_tpr = 0.9
temporal_crop_attacked_positive_tpr = 0.8
frame_dropping_attacked_positive_tpr = 0.85
local_clip_attacked_positive_tpr = 0.75
```

该结果证明上一轮的 positive signal recovery 方向有效: 高 support weight 能在 strict FPR 下恢复 anchor positive TPR。

### 22.3 当前失败原因

sync stage 24 个候选全部未通过:

```text
candidate_eligible = false, 24 / 24
fpr_controlled = true, 24 / 24
negative_leakage_status = controlled, 24 / 24
sync_rescue_decision = FAIL, 24 / 24
candidate_selection_status = insufficient_signal, 24 / 24
```

典型 sync 指标为:

```text
temporal_crop_sync_gain = 0.0
local_clip_sync_gain = 0.0
mean_temporal_sync_gain = 0.016667
```

该现象说明 `w012` anchor 已经过强。它本身已经达到 `temporal_crop_attacked_positive_tpr = 0.8` 与 `local_clip_attacked_positive_tpr = 0.75`, 留给 sync rescue 的 headroom 不足, 因此不适合作为阶段 2 同步机制增益证明的 anchor。

### 22.4 下一轮代码与配置决策

本次将 selector 与 grid 更新为 `sync_rescuable_anchor` 策略。该策略的目标不是选择最强 anchor, 而是选择:

```text
FPR 受控
candidate_eligible = true
no_attack clean positive TPR 达标
但 temporal_crop / local_clip 仍保留足够 headroom
```

当前默认策略参数为:

```text
min_no_attack_clean_positive_tpr = 0.5
max_no_attack_clean_positive_tpr = 0.8
target_no_attack_clean_positive_tpr = 0.6
min_temporal_crop_anchor_headroom = 0.45
min_local_clip_anchor_headroom = 0.45
```

基于本次 anchor grid, 该策略会优先选择类似 `w009` 的 anchor:

```text
no_attack_clean_positive_tpr = 0.6
max_attacked_negative_fpr = 0.0
temporal_crop_attacked_positive_tpr = 0.35
local_clip_attacked_positive_tpr = 0.4
```

它比 `w012` 更适合验证 sync rescue, 因为它已经满足 anchor 合格门槛, 但仍保留 temporal/local clip 提升空间。

### 22.5 下一轮搜索空间

下一轮 anchor 搜索空间保持在 `tl04` 的可用邻域:

```text
tubelet_length = [4]
spatial_patch_size = [[4, 4], [8, 8]]
embedding_projection_support_weight = [0.08, 0.09, 0.10]
embedding_margin = [1.0, 1.2]
```

下一轮 sync 搜索空间扩大到较紧凑但更有覆盖度的范围:

```text
lambda_sync = [0.005, 0.01, 0.015, 0.025, 0.04]
sync_search_radius = [6, 8, 10]
min_sync_positive_margin = [0.0, 0.01, 0.02]
min_sync_alignment_coverage_ratio = [0.03125, 0.0625, 0.125]
min_sync_alignment_matched_count = [1]
min_sync_candidate_score = [0.15, 0.25, 0.35]
fusion_rule = sync_rescue_fusion
```

该配置的预期是: 用 `w009 / w010` 这类有 headroom 的 eligible anchor 进入 sync, 而不是继续围绕过强的 `w012` 做无增益搜索。

### 22.6 运行时间预估

上一轮实际耗时为:

```text
formal_anchor_diag ≈ 1.96 小时
formal_sync_diag ≈ 2.79 小时
总计 ≈ 4.75 小时
```

下一轮 anchor 候选数约 12 个, sync 候选数约 135 个。由于 sync 阶段可复用已物化的攻击与 latent 产物, 预计耗时为:

```text
约 6-10 小时
```

若 Colab Drive I/O 或检测循环较慢, 可能上浮到:

```text
约 10-12 小时
```

正常情况下仍不应回到 20 小时以上无结论的状态。

## 23. 2026-06-08 中断包 `TSTW_runtime_runs_20260607_224048.zip` 诊断

### 23.1 结论

本次运行在约 16 小时后被人工中断，运行包位于:

```text
G:\我的云端硬盘\TSTW\results\TSTW_runtime_runs_20260607_224048.zip
```

该包没有产出完整的阶段 2 机制证明结果。缺失的关键产物包括:

```text
stage2_mechanism_calibration_summary.json
stage2_mechanism_calibration_timing_summary.json
formal_sync_diag/records/event_scores.jsonl
formal_sync_diag/tables/stage2_mechanism_calibration_grid.csv
formal_sync_diag/runtime_profile/run_timing_summary.json
```

因此, 本次结果不能用于判定阶段 2 机制证明通过或失败, 只能作为一次中断诊断记录。

### 23.2 已完成部分

`formal_anchor_diag` 已完整完成, 总记录耗时约 2842.96 秒, 即约 47.4 分钟。anchor 阶段成功选中了固定目标邻域内的候选:

```text
tubelet_only_cal_tl04_sp04x04_w009_em1000
no_attack_clean_positive_tpr = 0.6
max_attacked_negative_fpr = 0.0
temporal_crop_anchor_headroom = 0.65
local_clip_anchor_headroom = 0.6
```

该候选仍然是当前阶段 2 收尾测试的合理 anchor, 因为它已经满足 FPR 约束和 clean positive TPR 下限, 同时保留了 temporal crop 与 local clip 的可提升空间。

### 23.3 中断原因

`formal_sync_diag` 已进入检测与质量指标循环, 但在写出 `event_scores.jsonl` 和聚合表之前被中断。其 `run_timing_events.jsonl` 显示:

```text
runner_detect invocation_count = 120120
runner_detect elapsed_seconds = 12380.67 秒, 约 3.44 小时
runner_quality_metrics invocation_count = 120120
runner_quality_metrics elapsed_seconds = 1294.75 秒, 约 21.6 分钟
```

这说明主要问题不是 notebook cell 或 GPU 假死, 而是 sync 搜索空间过大, 且当前 runner 在 sync stage 完成前没有可复用的中间 records checkpoint。中断发生在 records 写出之前, 所以无法从该包恢复完整 sync 选择结果。

### 23.4 搜索空间修正

本次后续构建不再继续使用 405 级别的 sync 搜索空间。该窗口已登记为失败运行窗口, 后续仅作为历史记录保留。

新的默认策略改为固定已验证 anchor, 并只运行收缩后的 sync rescue 完成测试:

```text
anchor_selection_policy = fixed_unsaturated_anchor
fixed_tubelet_only_anchor = tl04, spatial_patch_size [4, 4], support_weight 0.09, embedding_margin 1.0
lambda_sync = [0.01, 0.025, 0.04]
sync_search_radius = [6, 8]
min_sync_positive_margin = [0.0, 0.01]
min_sync_alignment_coverage_ratio = [0.03125, 0.0625]
min_sync_alignment_matched_count = [1]
min_sync_candidate_score = [0.15, 0.25]
```

该配置对应 48 个 sync 方法配置, 相比原先 405 个方法配置减少约 88.1%。其目标不是继续广泛搜索, 而是验证已知合理 anchor 下是否能稳定产出阶段 2 机制证明闭环。

### 23.5 下一次运行预期

若 Colab 能复用已经物化的 dataset、攻击视频与 latent 缓存, 预计下一次运行时间约为:

```text
2-4 小时
```

若 Drive I/O 较慢或缓存未命中, 预计上浮到:

```text
4-6 小时
```

若超过 8 小时仍未写出 `formal_sync_diag/runtime_profile/run_timing_events.jsonl` 的新事件, 应优先中断并检查运行路径, 不建议再次等待到 16 小时。

# Protocol Artifact Schema

本文档冻结 `synthetic_tubelet_sync_probe` 阶段的 protocol artifact schema。该冻结覆盖 schema、字段集合、相对输出布局，以及 stage-one 的 mechanism trace 与重建产物；协议运行时契约可以位于 `main/core/`、`main/protocol/` 与 `main/analysis/`，但外层治理门禁仍必须保留在 `tools/harness/`、`.codex/`、`tests/` 与 docs 中。

## Governed Config Entry

正式 schema config 入口为 `configs/schema/protocol_artifact_schema.json`。

## Output Layout

| layout_field | relative_path | notes |
| --- | --- | --- |
| event_scores_path | records/event_scores.jsonl | 冻结 event-level score records 的相对输出位置。 |
| thresholds_path | thresholds/thresholds.json | 冻结 threshold artifact 的相对输出位置。 |
| run_manifest_path | artifacts/run_manifest.json | 冻结 run manifest 的相对输出位置。 |
| main_metrics_path | tables/main_tpr_fpr_table.csv | 冻结主指标表的相对输出位置。 |
| ablation_table_path | tables/ablation_table.csv | 冻结消融表的相对输出位置。 |
| local_clip_curve_path | tables/local_clip_curve.csv | 冻结 local clip 曲线表的相对输出位置。 |
| temporal_attack_curve_path | tables/temporal_attack_curve.csv | 冻结 temporal attack 曲线表的相对输出位置。 |
| tubelet_length_ablation_path | tables/tubelet_length_ablation.csv | 冻结 tubelet length 消融表的相对输出位置。 |
| report_path | reports/method_validation_report.md | 冻结方法验证报告的相对输出位置。 |

## Event Score Record

| field_name | required | notes |
| --- | --- | --- |
| run_id | yes | 运行级唯一标识。 |
| event_id | yes | event-level 记录标识。 |
| sample_id | yes | 样本标识。 |
| split | yes | 必须来自 `dev`、`calibration`、`test`。 |
| sample_role | yes | 必须来自四个受治理角色。 |
| method_family | yes | 方法家族语义名。 |
| method_variant | yes | 机制语义变体名。 |
| attack_name | yes | 攻击名或 identity placeholder 攻击名。 |
| attack_params | yes | 攻击参数容器。 |
| target_fpr | yes | 当前协议目标 FPR。 |
| threshold_id | yes | 校准前允许为空值编码。 |
| input_artifact_trace | yes | 长期输入 artifact trace 容器；后续阶段优先基于该字段扩展。 |
| latent_backend_name | yes | 阶段 0 random backend 的兼容字段，必须与 `input_artifact_trace.backend_name` 一致。 |
| latent_backend_status | yes | 阶段 0 random backend 的兼容字段，必须与 `input_artifact_trace.backend_status` 一致。 |
| latent_tensor_digest_random | yes | 阶段 0 random latent digest 兼容字段，必须与 `input_artifact_trace.artifact_digest` 一致。 |
| latent_generation_seed_random | yes | 阶段 0 random latent seed 兼容字段，必须与 `input_artifact_trace.generation_seed_random` 一致。 |
| evidence_scores | yes | 中间证据分数字段容器。 |
| disabled_evidence | yes | 显式记录禁用 evidence。 |
| decision | yes | 检测决策布尔值。 |
| failure_reason | yes | 失败原因，允许空值编码。 |
| mechanism_trace | yes | stage-one 机制 trace 容器，记录 artifact、embedding、sync 与 attack 诊断。 |
| placeholder_fields | yes | 显式列出当前记录中的 placeholder 语义字段。 |
| random_fields | yes | 显式列出当前记录中的 random trace 字段。 |

### Mechanism Trace Fields

| field_name | required | notes |
| --- | --- | --- |
| construction_phase | yes | 当前阶段固定为 `synthetic_tubelet_sync_probe`。 |
| latent_backend_name | yes | 生成 tensor artifact 的 backend 名称。 |
| reference_latent_shape | yes | 攻击前参考 latent shape，用于 sync search。 |
| latent_shape | yes | 当前 artifact 的实际 latent shape。 |
| latent_artifact_relpath | yes | 当前 artifact 的相对路径。 |
| latent_artifact_digest | yes | 当前 artifact 的文件 digest。 |
| tubelet_length | yes | 当前 method variant 使用的 tubelet 长度。 |
| spatial_patch_size | yes | 当前 tubelet 的空间 patch 尺寸。 |
| partition_digest | yes | tubelet partition digest。 |
| embedding_rule | yes | 当前阶段固定为 `projection_margin` 或空值编码。 |
| embedding_margin | yes | projection-margin 的最小投影间隔或空值编码。 |
| mean_projection_before | yes | embedding 前平均 coded projection 或空值编码。 |
| mean_projection_after | yes | embedding 后平均 coded projection 或空值编码。 |
| mean_embedding_delta_norm | yes | embedding 平均增量范数或空值编码。 |
| codebook_digest | yes | tubelet direction codebook digest。 |
| sync_code_digest | yes | synchronization code digest。 |
| payload_digest | yes | payload sign digest。 |
| sync_search_enabled | yes | 是否启用 offset search。 |
| sync_estimated_offset | yes | 检测得到的同步偏移，可为空。 |
| sync_ground_truth_offset | yes | 攻击物化的真实偏移，可为空。 |
| sync_alignment_error | yes | 对齐误差，可为空。 |
| sync_peak_rank | yes | ground-truth 偏移在 search 中的 rank，可为空。 |
| sync_search_space_size | yes | offset search 候选总数，可为空。 |
| sync_search_space_digest | yes | offset search score map 的 digest，可为空。 |
| clip_length | yes | local clip 或 crop 长度，可为空。 |

### Input Artifact Trace Fields

| field_name | required | notes |
| --- | --- | --- |
| artifact_kind | yes | 当前阶段固定写为 `latent_tensor`，但字段语义为长期输入 artifact 类型。 |
| backend_name | yes | 输入 artifact backend 名称。 |
| backend_status | yes | 输入 artifact backend 状态。 |
| artifact_digest | yes | 输入 artifact 的 digest。 |
| generation_seed_random | yes | 输入 artifact 的随机生成种子；后缀保持 `_random`。 |

### Evidence Score Fields

| field_name | required | notes |
| --- | --- | --- |
| S_tubelet | yes | tubelet evidence 分数，允许空值编码。 |
| S_sync | yes | sync evidence 分数，允许空值编码。 |
| S_traj | yes | trajectory evidence 分数，允许空值编码。 |
| S_final | yes | 最终检测分数。 |

## Threshold Record

| field_name | required | notes |
| --- | --- | --- |
| threshold_id | yes | 语义化 threshold 标识。 |
| run_id | yes | 对应运行标识。 |
| method_family | yes | 方法家族语义名。 |
| method_variant | yes | 机制语义变体名。 |
| score_name | yes | 当前阶段固定为 `S_final`。 |
| target_fpr | yes | 当前协议目标 FPR。 |
| calibration_split | yes | 当前阶段固定为 `calibration`。 |
| calibration_negative_roles | yes | 必须同时覆盖 `clean_negative` 与 `attacked_negative`。 |
| threshold_value | yes | 校准得到的阈值。 |
| threshold_quantile | yes | 阈值分位点。 |
| num_calibration_negatives | yes | 校准负样本数。 |
| threshold_source_record_digest | yes | 绑定 calibration negative records 的可审计 digest。 |
| fusion_rule | yes | 预声明的融合规则标识。 |
| created_at | yes | ISO-8601 时间戳。 |

## Run Manifest Record

| field_name | required | notes |
| --- | --- | --- |
| run_id | yes | 运行级唯一标识。 |
| created_at | yes | ISO-8601 时间戳。 |
| construction_phase | yes | 当前阶段固定为 `protocol_skeleton`。 |
| protocol_name | yes | 当前协议固定为 `fixed_low_fpr_calibrated_detection`。 |
| method_config_digest | yes | 方法配置摘要。 |
| protocol_config_digest | yes | 协议配置摘要。 |
| attack_matrix_digest | yes | 攻击矩阵或 placeholder 攻击配置摘要。 |
| ablation_config_digest | yes | 消融配置摘要。 |
| records_digest | yes | records 摘要。 |
| thresholds_digest | yes | thresholds 摘要。 |
| tables_digest | yes | tables 摘要。 |
| figures_digest_placeholder | yes | 当前阶段 figures 未实现时的 placeholder digest 字段。 |
| placeholder_fields | yes | manifest 中显式列出的 placeholder 语义字段。 |
| random_fields | yes | manifest 中显式列出的 random trace 字段。 |

## Table Columns

### Main Metrics Table

| column_name | required | notes |
| --- | --- | --- |
| run_id | yes | 运行级唯一标识。 |
| method_family | yes | 方法家族语义名。 |
| method_variant | yes | 机制语义变体名。 |
| target_fpr | yes | 当前协议目标 FPR。 |
| threshold_id | yes | 使用的 threshold 标识。 |
| split | yes | 当前统计对应 split。 |
| attack_name | yes | 对应攻击名。 |
| clean_negative_count | yes | clean negative 样本数。 |
| attacked_negative_count | yes | attacked negative 样本数。 |
| watermarked_positive_count | yes | watermarked positive 样本数。 |
| attacked_positive_count | yes | attacked positive 样本数。 |
| clean_negative_FPR | yes | clean negative FPR。 |
| attacked_negative_FPR | yes | attacked negative FPR。 |
| clean_positive_TPR | yes | clean positive TPR。 |
| attacked_positive_TPR | yes | attacked positive TPR。 |

### Ablation Table

| column_name | required | notes |
| --- | --- | --- |
| run_id | yes | 运行级唯一标识。 |
| method_family | yes | 方法家族语义名。 |
| method_variant | yes | 机制语义变体名。 |
| enabled_tubelet_evidence | yes | 是否启用 tubelet evidence。 |
| enabled_sync_evidence | yes | 是否启用 sync evidence。 |
| enabled_trajectory_evidence | yes | 是否启用 trajectory evidence。 |
| fusion_rule | yes | 预声明融合规则。 |
| threshold_id | yes | 使用的 threshold 标识。 |
| clean_negative_FPR | yes | clean negative FPR。 |
| attacked_negative_FPR | yes | attacked negative FPR。 |
| clean_positive_TPR | yes | clean positive TPR。 |
| attacked_positive_TPR | yes | attacked positive TPR。 |

### Curve Tables

`local_clip_curve.csv` 必须至少包含 `run_id`、`method_variant`、`clip_length`、`local_clip_TPR`、`local_clip_FPR`、`positive_count`、`negative_count` 与 `threshold_id`。

`temporal_attack_curve.csv` 必须至少包含 `run_id`、`method_variant`、`attack_name`、`attack_strength`、`sample_role`、`TPR`、`FPR`、`count` 与 `threshold_id`。

`tubelet_length_ablation.csv` 必须至少包含 `run_id`、`method_variant`、`tubelet_length`、`attack_name`、`attacked_positive_TPR`、`attacked_negative_FPR`、`sync_alignment_error_mean` 与 `sync_peak_rank_median`。

## Stage Boundary

- 当前文档冻结 schema 和路径，不声明任何具有方法性能意义的正式实验结论。
- 当前阶段允许 synthetic tensor runtime 在临时输出路径下写出 records、thresholds、manifest、tables、curves 与 report，用于验证协议可执行性。
- `input_artifact_trace` 与 `mechanism_trace` 是当前阶段的长期 trace 字段；`latent_*_random` 字段作为兼容 trace 字段继续保留。
- 当前阶段不得通过 notebook、终端脚本或临时文件绕过这些 schema 约束写入正式结果。
- 进入下一阶段前，records、thresholds、manifest 与 tables 的真实实现必须继续遵守本文件和 `configs/schema/protocol_artifact_schema.json` 的冻结口径。
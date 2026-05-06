# Protocol Artifact Schema

本文档冻结 `protocol_skeleton` 阶段的 protocol artifact schema skeleton。该冻结只覆盖 schema、字段集合与相对输出布局，不代表当前阶段已经实现真实 `RecordWriter`、`ThresholdCalibrator`、`ProtocolRunner` 或 `TableBuilder`。

## Governed Config Entry

正式 schema config 入口为 `configs/schema/protocol_artifact_schema.json`。

## Output Layout

| layout_field | relative_path | notes |
| --- | --- | --- |
| event_scores_path | records/event_scores.jsonl | 冻结 event-level score records 的相对输出位置。 |
| thresholds_path | thresholds/thresholds.json | 冻结 threshold artifact 的相对输出位置。 |
| run_manifest_path | artifacts/run_manifest.json | 冻结 run manifest 的相对输出位置。 |
| main_metrics_path | tables/main_metrics.csv | 冻结主指标表的相对输出位置。 |
| ablation_table_path | tables/ablation_table.csv | 冻结消融表的相对输出位置。 |

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
| evidence_scores | yes | 中间证据分数字段容器。 |
| disabled_evidence | yes | 显式记录禁用 evidence。 |
| decision | yes | 检测决策布尔值。 |
| failure_reason | yes | 失败原因，允许空值编码。 |
| placeholder_fields | yes | 显式列出当前记录中的 placeholder 语义字段。 |
| random_fields | yes | 显式列出当前记录中的 random trace 字段。 |

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

## Stage Boundary

- 当前文档只冻结 schema 和路径，不声明任何真实实验结果。
- 当前阶段不得通过 notebook、终端脚本或临时文件绕过这些 schema 约束写入正式结果。
- 进入下一阶段前，records、thresholds、manifest 与 tables 的真实实现必须继续遵守本文件和 `configs/schema/protocol_artifact_schema.json` 的冻结口径。
# Field Registry

Registry constraint: `docs/field_registry.md` 是 governed field 的唯一登记表。新增 governed field 必须先登记，再进入 `configs/**`、records、thresholds、manifest、tables、reports、Python dict key、测试 fixture 与 Markdown 代码块示例。未登记字段视为阻断违规。

| field_name | category | required_suffix | allowed_in_records | allowed_in_claims | replacement_required | description |
| --- | --- | --- | --- | --- | --- | --- |
| project_stage | protocol | none | true | false | false | Semantic project stage identifier for governed protocol progression. |
| legacy_stage_id | compatibility | none | true | false | false | Compatibility-only legacy stage field; it must not drive formal naming. |
| core_boundary_policy | governance | none | false | false | false | Declared boundary policy that separates outer governance gates from core runtime candidates. |
| governance_layer_paths | governance | none | false | false | false | Paths reserved for outer governance gates and excluded from runtime core extraction. |
| protocol_core_candidate_paths | governance | none | false | false | false | Paths eligible for future protocol_core extraction. |
| method_core_candidate_paths | governance | none | false | false | false | Paths eligible for future method_core extraction. |
| forbidden_runtime_imports | governance | none | false | false | false | Import roots that runtime code under `main/` must not depend on. |
| minimal_demo_excluded_paths | governance | none | false | false | false | Paths that must remain outside the future `minimal_demo` extraction boundary. |
| protocol_runtime_objects | protocol | none | false | false | false | Declared protocol runtime object roster for the protocol skeleton code scaffold. |
| supported_method_variants | protocol | none | false | false | false | Declared method variants that the protocol skeleton runtime must support. |
| run_id | protocol | none | true | false | false | Stable run identifier for governed runtime artifacts. |
| event_id | protocol | none | true | false | false | Stable event identifier for governed event-level records. |
| sample_id | protocol | none | true | false | false | Stable sample identifier used across splits and method variants. |
| split | protocol | none | true | false | false | Governed split field for event-level records. |
| sample_role | protocol | none | true | false | false | Governed sample role field for event-level records. |
| method_variant_placeholder | placeholder | _placeholder | true | false | true | Placeholder method variant for protocol skeleton only. |
| latent_backend_placeholder | placeholder | _placeholder | true | false | true | Placeholder latent backend entry; it must be replaced before formal method claims. |
| watermark_method_placeholder | placeholder | _placeholder | true | false | true | Placeholder watermark method entry for bootstrap-only configs. |
| trajectory_backend_placeholder | placeholder | _placeholder | true | false | true | Placeholder trajectory backend entry reserved for later stages. |
| quality_metric_placeholder | placeholder | _placeholder | true | false | true | Placeholder quality metric field for future governed replacement. |
| target_fpr_placeholder | placeholder | _placeholder | true | false | true | Placeholder target FPR field used before full threshold materialization. |
| target_fpr | protocol | none | true | false | false | Materialized target FPR used by protocol skeleton runtime runtime records and tables. |
| validation_target_fpr | protocol | none | true | false | false | Profile-scoped validation FPR target used for closure and proof reports when strict `target_fpr` is intentionally deferred. |
| calibration_negative_min_samples_per_role_by_profile | protocol | none | true | false | false | Profile-scoped lower bound for calibration negative sample counts so proof and formal tiers can widen calibration tails without inflating dev or test coverage. |
| threshold_quantile_rule | protocol | none | true | false | false | Declared quantile rule for calibration-only threshold construction. |
| allow_attack_specific_threshold | protocol | none | true | false | false | Boolean field that blocks attack-specific threshold divergence. |
| method_family | protocol | none | true | false | false | Stable method family identifier for protocol skeleton runtime records and configs. |
| method_variant | protocol | none | true | false | false | Stable method variant identifier used by protocol skeleton runtime configs and event records. |
| base_method_variant | protocol | none | true | false | false | Primary method variant from which a derived ablation variant inherits its mechanism semantics. |
| derived_variant | protocol | none | true | false | false | Boolean marker that distinguishes primary method variants from derived ablation variants. |
| ablation_axis | protocol | none | true | false | false | Nullable axis name for derived ablation variants; current stage uses `tubelet_length`. |
| method_status | protocol | none | true | false | false | Protocol Skeleton method status field describing placeholder or random scaffold semantics. |
| enable_frame_prc | protocol | none | true | false | false | Boolean switch reserved for the frame-wise baseline in the synthetic tubelet sync method-entry configs. |
| enable_tubelet | protocol | none | true | false | false | Boolean switch reserved for tubelet evidence enablement in the synthetic tubelet sync method-entry configs. |
| enable_sync | protocol | none | true | false | false | Boolean switch reserved for temporal synchronization enablement in the synthetic tubelet sync method-entry configs. |
| enable_trajectory | protocol | none | true | false | false | Boolean switch reserved for trajectory evidence enablement in the synthetic tubelet sync method-entry configs. |
| tubelet_length | protocol | none | true | false | false | Reserved tubelet-length field used by the synthetic tubelet sync method-entry configs. |
| enabled_evidence | protocol | none | true | false | false | Evidence enablement container that freezes which evidence branches are active. |
| fusion_rule | protocol | none | true | false | false | Stable fusion rule identifier used by protocol skeleton runtime threshold and method configs. |
| lambda_sync | protocol | none | true | false | false | Configured sync-rescue fusion weight applied to calibrated synchronization margin. |
| score_calibration | protocol | none | true | false | false | Governed method-config container for profile-independent score calibration parameters used by the synthetic tubelet sync probe. |
| embedding_projection_support_weight | protocol | none | true | false | false | Auditable score-calibration weight that maps recorded projection-margin embedding support into the synthetic_tubelet_sync_probe tubelet projection score. |
| sync_search | protocol | none | true | false | false | Governed method-config container for offset and optional scale synchronization search parameters. |
| offset_search_min | protocol | none | true | false | false | Minimum candidate offset for governed synchronization search. |
| offset_search_max | protocol | none | true | false | false | Maximum candidate offset for governed synchronization search. |
| enable_scale_search | protocol | none | true | false | false | Boolean switch allowing offset-scale candidate synchronization search on speed-change samples. |
| scale_candidates | protocol | none | true | false | false | Governed positive scale candidates used by speed-change synchronization search. |
| scale_search_snap_radius | protocol | none | true | false | false | Maximum frame-start snap radius used when mapping scaled observed tubelets to reference descriptors. |
| coverage_penalty_enabled | protocol | none | true | false | false | Boolean switch enabling coverage-penalized synchronization candidate scoring. |
| min_sync_positive_margin | protocol | none | true | false | false | Minimum observable synchronization positive margin required by sync confidence gating. |
| min_sync_alignment_coverage_ratio | protocol | none | true | false | false | Minimum observable synchronization coverage ratio required by sync confidence gating. |
| min_sync_alignment_matched_count | protocol | none | true | false | false | Minimum observable matched tubelet count required by sync confidence gating. |
| attack_name | protocol | none | true | false | false | Attack identifier written into protocol skeleton runtime event records. |
| attack_params | protocol | none | true | false | false | Attack parameter object written into protocol skeleton runtime event records. |
| score_name | protocol | none | true | false | false | Governed score identifier used by threshold records. |
| threshold_id | protocol | none | true | false | false | Stable threshold identifier used by protocol skeleton runtime threshold and event records. |
| input_artifact_trace | protocol | none | true | false | false | Long-lived input artifact trace container for governed event records. |
| artifact_kind | protocol | none | true | false | false | Semantic kind of governed input artifact persisted inside `input_artifact_trace`. |
| backend_name | protocol | none | true | false | false | Backend identifier persisted inside `input_artifact_trace`. |
| backend_status | protocol | none | true | false | false | Backend status persisted inside `input_artifact_trace`. |
| artifact_digest | trace | none | true | false | false | Digest of the governed input artifact persisted inside `input_artifact_trace`. |
| generation_seed_random | random | _random | true | false | false | Random seed field inside `input_artifact_trace`; the `_random` suffix is retained for reproducibility semantics. |
| latent_backend_name | protocol | none | true | false | false | Protocol Skeleton compatibility field mirroring `input_artifact_trace.backend_name` in governed event records. |
| latent_backend_status | protocol | none | true | false | false | Protocol Skeleton compatibility field mirroring `input_artifact_trace.backend_status` in governed event records. |
| latent_seed_random | random | _random | true | false | false | Random latent seed field; seed semantics are explicit in the field name. |
| latent_generation_seed_random | random | _random | true | false | false | Protocol Skeleton compatibility seed field mirroring `input_artifact_trace.generation_seed_random`. |
| latent_tensor_digest_random | random | _digest_random | true | false | false | Protocol Skeleton compatibility digest field mirroring `input_artifact_trace.artifact_digest`. |
| score_generation_seed_random | random | _random | true | false | false | Seed field for deterministic protocol skeleton runtime random evidence score generation. |
| prg_direction_seed_random | random | _random | true | false | false | Random PRG direction seed field; seed semantics are explicit in the field name. |
| sync_code_seed_random | random | _random | true | false | false | Random sync code seed field; seed semantics are explicit in the field name. |
| payload_bits_random | random | _random | true | false | false | Random payload bits field; it requires a paired seed or digest field for reproducibility. |
| payload_bits_digest_random | random | _digest_random | true | false | false | Digest-tracked random payload field; digest semantics are self-contained. |
| protocol_name | protocol | none | true | false | false | Frozen protocol identifier for the fixed low-FPR calibrated detector skeleton. |
| construction_phase | protocol | none | true | false | false | Semantic construction phase identifier aligned with the active governed stage. |
| target_construction_phase | protocol | none | true | false | false | Reserved next-stage construction phase identifier used by support configs and project contract while the active project stage remains `synthetic_tubelet_sync_probe`. |
| latent_distribution | protocol | none | true | false | false | Governed latent distribution identifier reserved for the synthetic tubelet sync probe entry config. |
| latent_shape | protocol | none | true | false | false | Reserved latent-shape container for the synthetic video latent support config. |
| latent_generation_seed | protocol | none | true | false | false | Reserved deterministic seed field for the synthetic video latent support config. |
| latent_storage | artifact_layout | none | true | false | false | Reserved latent artifact storage policy for the synthetic tubelet sync probe support config. |
| attack_matrix_name | protocol | none | true | false | false | Stable attack-matrix identifier used by support configs and later stage-specific attack registries. |
| attacks | protocol | none | true | false | false | Ordered attack-entry container used by the reserved temporal attack matrix config. |
| required_method_variants | protocol | none | true | false | false | Ordered method-variant roster that the synthetic tubelet sync protocol support config requires. |
| required_output_tables | artifact_layout | none | true | false | false | Ordered table roster required by the reserved synthetic tubelet sync protocol support config. |
| mechanism_trace_required | protocol | none | true | false | false | Boolean field that freezes the requirement for `mechanism_trace` before synthetic_tubelet_sync_probe runtime promotion. |
| ablation_name | protocol | none | true | false | false | Stable ablation identifier for governed comparison configs. |
| shared_protocol_name | protocol | none | true | false | false | Stable shared protocol identifier carried by ablation support configs. |
| shared_attack_matrix_name | protocol | none | true | false | false | Stable shared attack-matrix identifier carried by ablation support configs. |
| shared_target_fpr | protocol | none | true | false | false | Materialized shared target FPR reserved by the synthetic tubelet sync ablation support config. |
| shared_table_builder_name | protocol | none | true | false | false | Stable shared table-builder identifier reserved by the synthetic tubelet sync ablation support config. |
| record_schema_name | schema | none | true | false | false | Canonical event score record schema identifier for protocol artifact governance. |
| threshold_schema_name | schema | none | true | false | false | Canonical threshold record schema identifier for protocol artifact governance. |
| manifest_schema_name | schema | none | true | false | false | Canonical run manifest schema identifier for protocol artifact governance. |
| event_scores_path | artifact_layout | none | false | false | false | Relative layout path for governed event-level score records. |
| thresholds_path | artifact_layout | none | false | false | false | Relative layout path for governed threshold records. |
| run_manifest_path | artifact_layout | none | false | false | false | Relative layout path for the governed run manifest. |
| main_metrics_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt main metrics table. |
| ablation_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt ablation table. |
| local_clip_curve_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt local-clip curve table. |
| temporal_attack_curve_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt temporal-attack curve table. |
| tubelet_length_ablation_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt tubelet-length ablation table. |
| sync_peak_examples_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt sync peak examples figure. |
| report_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt method validation report. |
| threshold_source_record_digest | trace | none | true | false | false | Digest field that binds threshold materialization to an ordered calibration-negative source payload including event_id, sample_id, split, sample_role, method_variant, attack_name, and S_final. |
| runtime_profile | protocol | none | true | false | false | Active runtime profile recorded in threshold and report artifacts so closure, proof, and formal tiers can be interpreted under distinct coverage and validation rules. |
| calibration_split | protocol | none | true | false | false | Governed calibration split identifier written into threshold records. |
| calibration_negative_roles | protocol | none | true | false | false | Governed calibration negative role list written into threshold records. |
| threshold_value | protocol | none | true | false | false | Materialized threshold value for a governed threshold record. |
| threshold_quantile | protocol | none | true | false | false | Materialized threshold quantile used to build a governed threshold record. |
| sync_threshold_guard_band_multiplier | protocol | none | true | false | false | Profile-scoped guard-band multiplier applied to sync-enabled threshold calibration to reduce attacked-negative tail leakage under small calibration sample counts. |
| tubelet_length_threshold_guard_band_multiplier_by_profile | protocol | none | true | false | false | Profile-scoped tubelet-length guard-band map that raises thresholds for long tubelet variants using calibration-negative dispersion only. |
| tubelet_length_threshold_guard_band_multiplier | protocol | none | true | false | false | Materialized tubelet-length guard-band multiplier recorded in threshold records for auditability of long-tubelet calibration penalties. |
| applied_threshold_guard_band_multiplier | protocol | none | true | false | false | Materialized guard-band multiplier actually applied to `threshold_value`, defined as the maximum of sync and tubelet-length calibration penalties. |
| num_calibration_negatives | protocol | none | true | false | false | Count of calibration-negative records used during threshold materialization. |
| disabled_evidence | protocol | none | true | false | false | Explicit list of evidence branches disabled for a governed event record. |
| decision | protocol | none | true | false | false | Detection decision field for a governed event record. |
| failure_reason | protocol | none | true | false | false | Failure reason field for a governed event record. |
| mechanism_trace | protocol | none | true | false | false | Governed mechanism trace container written into synthetic_tubelet_sync_probe event records. |
| reference_latent_shape | protocol | none | true | false | false | Reference latent shape used to preserve the pre-attack synchronization search space. |
| latent_artifact_relpath | artifact_layout | none | true | false | false | Relative path to the persisted tensor artifact used by embedding, attack, and detection. |
| latent_artifact_digest | trace | none | true | false | false | File digest of the persisted tensor artifact currently used by the event record. |
| partition_digest | trace | none | true | false | false | Digest of the governed tubelet partition layout. |
| embedding_rule | protocol | none | true | false | false | Stable embedding rule identifier for the synthetic_tubelet_sync_probe projection-margin mechanism. |
| embedding_margin | protocol | none | true | false | false | Minimum coded projection margin enforced by the synthetic_tubelet_sync_probe embedding rule. |
| mean_projection_before | protocol | none | true | false | false | Mean coded tubelet projection before projection-margin embedding. |
| mean_projection_after | protocol | none | true | false | false | Mean coded tubelet projection after projection-margin embedding. |
| mean_embedding_delta_norm | protocol | none | true | false | false | Mean projection-margin delta norm applied during embedding. |
| codebook_digest | trace | none | true | false | false | Digest of the deterministic tubelet direction codebook. |
| sync_code_digest | trace | none | true | false | false | Digest of the deterministic synchronization code sequence. |
| payload_digest | trace | none | true | false | false | Digest of the payload sign assignments used by the synthetic_tubelet_sync_probe method. |
| sync_search_enabled | protocol | none | true | false | false | Boolean field recording whether synchronization search was active for detection. |
| sync_estimated_offset | protocol | none | true | false | false | Estimated synchronization offset selected by the synthetic_tubelet_sync_probe detector. |
| sync_ground_truth_offset | protocol | none | true | false | false | Ground-truth offset materialized by governed temporal attacks when available. |
| sync_alignment_error | protocol | none | true | false | false | Absolute error between estimated and ground-truth synchronization offset. |
| sync_peak_rank | protocol | none | true | false | false | Rank position of the ground-truth offset within the governed search scores. |
| sync_search_space_size | protocol | none | true | false | false | Candidate count of the governed synchronization offset search space. |
| sync_search_space_digest | trace | none | true | false | false | Digest of the governed synchronization search-space score map. |
| sync_estimated_scale | protocol | none | true | false | false | Estimated temporal scale selected by offset-scale synchronization search. |
| sync_ground_truth_scale | protocol | none | true | false | false | Ground-truth temporal scale materialized by governed temporal attacks when available. |
| sync_scale_error | protocol | none | true | false | false | Absolute error between estimated and ground-truth temporal scale when both are available. |
| sync_alignment_mode | protocol | none | true | false | false | Synchronization search mode used for the event, either offset or offset_scale. |
| S_payload_unaligned | protocol | none | true | false | false | Payload-only score before synchronization alignment, mapped to `S_tubelet` for sync-rescue records. |
| S_payload_aligned | protocol | none | true | false | false | Payload evidence score after applying the estimated synchronization alignment. |
| S_payload_rescue_gain | protocol | none | true | false | false | Non-negative score gain from aligned payload evidence over unaligned payload evidence. |
| S_final_before_rescue | protocol | none | true | false | false | Final-score baseline before gated sync rescue is applied. |
| S_final_after_rescue | protocol | none | true | false | false | Final score after applying the gated aligned-payload rescue rule. |
| rescue_gain_clipped | protocol | none | true | false | false | Boolean trace field indicating whether the payload rescue gain was clipped before fusion. |
| S_sync_peak_best | protocol | none | true | false | false | Best raw synchronization candidate score before positive-margin calibration. |
| S_sync_peak_second_or_median | protocol | none | true | false | false | Second-best or median synchronization score used as the peak-margin baseline. |
| S_sync_peak_margin | protocol | none | true | false | false | Raw difference between best synchronization peak and its comparison baseline. |
| S_sync_positive_margin | protocol | none | true | false | false | Non-negative calibrated synchronization peak margin mapped to `S_sync`. |
| sync_alignment_matched_count | protocol | none | true | false | false | Count of observed tubelets matched to reference descriptors for the selected synchronization candidate. |
| sync_alignment_candidate_count | protocol | none | true | false | false | Reference descriptor count used as the denominator for synchronization candidate coverage. |
| sync_alignment_coverage_ratio | protocol | none | true | false | false | Matched-count ratio for the selected synchronization candidate; larger indicates broader alignment support. |
| sync_candidate_score_raw | protocol | none | true | false | false | Unpenalized mean payload projection for the selected synchronization candidate. |
| sync_candidate_score_penalized | protocol | none | true | false | false | Coverage-penalized synchronization candidate score used for candidate ranking. |
| sync_confident | protocol | none | true | false | false | Boolean gate indicating whether observable sync margin, coverage, and matched-count criteria allow sync evidence in fusion. |
| sync_confidence_failure_reason | protocol | none | true | false | false | Semicolon-separated observable reasons explaining why synchronization confidence did not pass. |
| sync_confidence_gate_rule | protocol | none | true | false | false | 阶段 2 sync rescue 使用的置信 gate 规则, 当前唯一允许值为 `aligned_payload_safety_gate`. |
| sync_confidence_min_margin | protocol | none | true | false | false | Configured minimum `S_sync_positive_margin` required for sync confidence. |
| sync_confidence_min_coverage_ratio | protocol | none | true | false | false | Configured minimum synchronization alignment coverage ratio required for sync confidence. |
| sync_confidence_min_matched_count | protocol | none | true | false | false | Configured minimum matched tubelet count required for sync confidence. |
| sync_confidence_min_payload_rescue_gain | protocol | none | true | false | false | `aligned_payload_safety_gate` 要求的最小 payload rescue gain. |
| sync_confidence_min_aligned_payload_score | protocol | none | true | false | false | `aligned_payload_safety_gate` 要求的最小 aligned payload score. |
| min_payload_rescue_gain | threshold | none | true | false | false | 阶段 2 calibration grid 中用于生成 `sync_confidence_min_payload_rescue_gain` 的搜索参数. |
| min_aligned_payload_score | threshold | none | true | false | false | 阶段 2 calibration grid 中用于生成 `sync_confidence_min_aligned_payload_score` 的搜索参数. |
| aligned_payload_clean_negative_fpr | table | none | true | false | false | selector 聚合的 no-attack clean negative aligned-payload 过阈率. |
| aligned_payload_attacked_negative_fpr | table | none | true | false | false | selector 聚合的 attacked negative aligned-payload 过阈率上界. |
| aligned_payload_positive_tpr | table | none | true | false | false | selector 聚合的 no-attack positive aligned-payload 过阈率. |
| aligned_payload_temporal_crop_tpr | table | none | true | false | false | selector 聚合的 temporal-crop positive aligned-payload 过阈率. |
| aligned_payload_local_clip_tpr | table | none | true | false | false | selector 聚合的 local-clip positive aligned-payload 过阈率. |
| sync_rescue_applied_positive_rate | table | none | true | false | false | selector 聚合的 positive 样本 sync rescue 实际启用比例. |
| sync_rescue_applied_attacked_negative_rate | table | none | true | false | false | selector 聚合的 attacked negative 样本 sync rescue 实际启用比例上界. |
| calibration_negative_count | table | none | true | false | false | Count of calibration negative samples used by selector-level negative safety. |
| attacked_calibration_negative_count | table | none | true | false | false | Count of attacked calibration negative samples used by selector-level negative safety. |
| negative_rescue_over_threshold_count | table | none | true | false | false | calibration negative 中 sync rescue 后 `S_final` 过阈的样本数. |
| negative_rescue_over_threshold_rate | table | none | true | false | false | Rate of calibration negative samples crossing threshold after gated sync rescue. |
| upper_confidence_bound_for_negative_rescue_rate | table | none | true | false | false | Wilson upper confidence bound for the calibration negative rescue-over-threshold rate. |
| selector_split_policy | protocol | none | true | false | false | Split policy declared by the selector, expected to be `dev_calibration_only` for stage-two candidate selection. |
| test_split_used_for_selection | protocol | none | true | false | false | Boolean selector audit field indicating whether test records entered candidate selection. |
| aligned_payload_negative_safety_status | table | none | true | false | false | 方法级 negative safety gate 状态, `PASS` 表示没有 calibration negative 被 rescue 过阈. |
| aligned_payload_clean_negative_over_threshold_count | table | none | true | false | false | clean negative 中 aligned-payload score 过阈的样本数. |
| aligned_payload_attacked_negative_over_threshold_count | table | none | true | false | false | attacked negative 中 aligned-payload score 过阈的样本数. |
| reference_latent_shape_source | protocol | none | true | false | false | Source label for `reference_latent_shape`, either governed trace or sample-shape fallback. |
| reference_latent_shape_fallback_used | protocol | none | true | false | false | Boolean audit field indicating whether detection had to fall back to the observed sample latent shape. |
| tubelet_projection_matched_count | protocol | none | true | false | false | Count of observed tubelets matched to reference descriptors for unaligned tubelet evidence. |
| tubelet_projection_candidate_count | protocol | none | true | false | false | Reference descriptor count used as the denominator for unaligned tubelet evidence coverage. |
| tubelet_projection_coverage_ratio | protocol | none | true | false | false | Matched-count ratio for unaligned tubelet evidence; positive evidence is coverage-penalized under partial clips. |
| tubelet_coverage_penalty_enabled | protocol | none | true | false | false | Boolean trace field indicating whether positive tubelet evidence uses coverage-penalized scoring. |
| sync_rescue_applied | protocol | none | true | false | false | Boolean trace field showing whether sync-rescue gain was gated into the final score. |
| clip_length | protocol | none | true | false | false | Materialized local-clip or crop length recorded in the synthetic_tubelet_sync_probe mechanism trace. |
| created_at | protocol | none | true | false | false | ISO-8601 timestamp field for governed threshold and manifest records. |
| table_builder_name | protocol | none | false | false | false | Stable table builder identifier for protocol skeleton runtime ablation governance. |
| placeholder_fields | governance | none | true | false | false | Explicit list of placeholder-bound fields carried by governed records or manifests. |
| random_fields | governance | none | true | false | false | Explicit list of random-trace fields carried by governed records or manifests. |
| watermark_payload_placeholder | placeholder | _placeholder | true | false | true | Placeholder payload field used by the empty watermark scaffold. |
| sync_alignment_placeholder | placeholder | _placeholder | true | false | true | Placeholder synchronization field used by protocol skeleton runtime methods without real sync logic. |
| trajectory_observation_placeholder | placeholder | _placeholder | true | false | true | Placeholder trajectory field used when trajectory evidence is absent in stage 0. |
| method_config_digest | trace | none | true | false | false | Digest of the governed method config used to rebuild run provenance. |
| protocol_config_digest | trace | none | true | false | false | Digest of the governed protocol config used to rebuild run provenance. |
| attack_matrix_digest | trace | none | true | false | false | Digest of the governed attack matrix or attack placeholder config. |
| ablation_config_digest | trace | none | true | false | false | Digest of the governed ablation config used to rebuild comparison provenance. |
| records_digest | trace | none | true | false | false | Digest of the governed event-level record set. |
| thresholds_digest | trace | none | true | false | false | Digest of the governed threshold artifact set. |
| tables_digest | trace | none | true | false | false | Digest of the governed table artifact set. |
| figures_digest | trace | none | true | false | false | Digest of the governed figure artifact set. |
| shared_target_fpr_placeholder | placeholder | _placeholder | true | false | true | Placeholder field that freezes the shared ablation target FPR before runtime materialization. |
| shared_table_builder_placeholder | placeholder | _placeholder | true | false | true | Placeholder field that freezes a shared table builder contract for future ablations. |
| attack_matrix_placeholder | placeholder | _placeholder | true | false | true | Placeholder field that freezes the protocol skeleton runtime attack matrix skeleton. |
| attack_name_placeholder | placeholder | _placeholder | true | false | true | Placeholder attack name field for the governed identity attack skeleton. |
| attack_params_placeholder | placeholder | _placeholder | true | false | true | Placeholder attack parameter container for the governed identity attack skeleton. |
| shared_attack_matrix_required | governance | none | true | false | false | Boolean governance field that blocks per-variant attack matrix divergence. |
| real_video_vae_latent_outputs | protocol | none | true | false | false | Declared output-toggle container for the real_video_vae_latent_probe real-video VAE latent scaffold. |
| video_source_id | protocol | none | true | false | false | Stable video-source identifier recorded in real_video_vae_latent_probe mechanism traces. |
| video_source_relpath | artifact_layout | none | true | false | false | Relative path to the persisted source video artifact for real_video_vae_latent_probe records. |
| video_source_digest | trace | none | true | false | false | File digest of the persisted source video artifact for real_video_vae_latent_probe records. |
| video_frame_count | protocol | none | true | false | false | Frame count of the persisted real_video_vae_latent_probe video artifact. |
| video_fps | protocol | none | true | false | false | Declared frame rate of the persisted real_video_vae_latent_probe video artifact. |
| video_resolution | protocol | none | true | false | false | Declared `[height, width]` resolution of the persisted real_video_vae_latent_probe video artifact. |
| vae_backend_name | protocol | none | true | false | false | Stage-two VAE backend identifier recorded in mechanism traces and runtime manifests. |
| vae_backend_version | protocol | none | true | false | false | Stage-two VAE backend version string recorded in mechanism traces and runtime manifests. |
| vae_config_digest | trace | none | true | false | false | Digest of the placeholder real_video_vae_latent_probe VAE configuration payload. |
| vae_encode_mode | protocol | none | true | false | false | Declared real_video_vae_latent_probe VAE encode mode. |
| vae_decode_mode | protocol | none | true | false | false | Declared real_video_vae_latent_probe VAE decode mode. |
| encoded_latent_relpath | artifact_layout | none | true | false | false | Relative path to the encoded latent artifact in the real_video_vae_latent_probe scaffold. |
| encoded_latent_digest | trace | none | true | false | false | Digest of the encoded latent artifact in the real_video_vae_latent_probe scaffold. |
| watermarked_latent_relpath | artifact_layout | none | true | false | false | Relative path to the copied watermarked latent artifact in the real_video_vae_latent_probe scaffold. |
| watermarked_latent_digest | trace | none | true | false | false | Digest of the copied watermarked latent artifact in the real_video_vae_latent_probe scaffold. |
| decoded_video_relpath | artifact_layout | none | true | false | false | Relative path to the decoded placeholder video artifact in the real_video_vae_latent_probe scaffold. |
| decoded_video_digest | trace | none | true | false | false | Digest of the decoded placeholder video artifact in the real_video_vae_latent_probe scaffold. |
| attacked_video_relpath | artifact_layout | none | true | false | false | Relative path to the attacked placeholder video artifact in the real_video_vae_latent_probe scaffold. |
| attacked_video_digest | trace | none | true | false | false | Digest of the attacked placeholder video artifact in the real_video_vae_latent_probe scaffold. |
| reencoded_latent_relpath | artifact_layout | none | true | false | false | Relative path to the re-encoded latent artifact in the real_video_vae_latent_probe scaffold. |
| reencoded_latent_digest | trace | none | true | false | false | Digest of the re-encoded latent artifact in the real_video_vae_latent_probe scaffold. |
| cross_event_vae_batching_enabled | protocol | none | true | false | false | Boolean mechanism-trace field indicating whether the runner used cross-event VAE batching for decode and encode scheduling. |
| cross_event_vae_decode_effective_batch_size | protocol | none | true | false | false | Per-record diagnostic field recording the effective decode request batch size used by cross-event VAE batching. |
| cross_event_vae_encode_effective_batch_size | protocol | none | true | false | false | Per-record diagnostic field recording the effective encode request batch size used by cross-event VAE batching. |
| cross_event_vae_batching_fallback_count | protocol | none | true | false | false | Per-record diagnostic count of CUDA OOM fallback steps used by cross-event VAE batching. |
| cross_event_vae_batching_fallback_reason | protocol | none | true | false | false | Nullable per-record diagnostic reason for cross-event VAE batching fallback; it is not method evidence. |
| quality_metrics | protocol | none | true | false | false | Top-level real_video_vae_latent_probe quality-metrics payload written into event records. |
| temporal_metrics | protocol | none | true | false | false | Top-level real_video_vae_latent_probe temporal-metrics payload written into event records. |
| vae_reconstruction_psnr | protocol | none | true | false | false | Placeholder-derived PSNR summary used by the real_video_vae_latent_probe scaffold quality payload. |
| vae_reconstruction_ssim | protocol | none | true | false | false | Placeholder-derived SSIM summary used by the real_video_vae_latent_probe scaffold quality payload. |
| watermarked_video_psnr | protocol | none | true | false | false | Placeholder-derived PSNR summary for decoded or attacked comparison videos in stage two. |
| watermarked_video_ssim | protocol | none | true | false | false | Placeholder-derived SSIM summary for decoded or attacked comparison videos in stage two. |
| watermarked_video_lpips | protocol | none | true | false | false | Reserved LPIPS field; the current real_video_vae_latent_probe scaffold records it as disabled. |
| lpips_backbone | protocol | none | true | false | false | LPIPS backbone identifier used when LPIPS quality scoring is enabled. |
| lpips_device | protocol | none | true | false | false | Requested LPIPS device label recorded for auditability of quality scoring. |
| clip_similarity_score | protocol | none | true | false | false | Reserved CLIP-similarity field; the current real_video_vae_latent_probe scaffold records it as disabled. |
| clip_model_id | protocol | none | true | false | false | CLIP model identifier reserved for semantic preservation scoring and excluded from detection evidence. |
| clip_frame_sample_count | protocol | none | true | false | false | Number of frames reserved for CLIP-similarity frame sampling when enabled. |
| disabled_quality_metrics | protocol | none | true | false | false | Explicit list of quality metrics disabled in the current real_video_vae_latent_probe scaffold. |
| quality_failure_reason | protocol | none | true | false | false | Recorded reason when a placeholder quality threshold is violated in stage two. |
| lpips_failure_reason | protocol | none | true | false | false | Explicit LPIPS failure or disablement reason recorded in stage-two real-video quality payloads. |
| clip_failure_reason | protocol | none | true | false | false | Explicit CLIP-similarity failure or disablement reason recorded in stage-two real-video quality payloads. |
| temporal_consistency_score | protocol | none | true | false | false | Placeholder-derived temporal consistency score computed from video artifacts. |
| flicker_score | protocol | none | true | false | false | Placeholder-derived flicker score computed from frame-difference deltas. |
| motion_consistency_score | protocol | none | true | false | false | Reserved motion-consistency field; the current real_video_vae_latent_probe scaffold records it as disabled. |
| motion_consistency_backend | protocol | none | true | false | false | Motion-consistency backend identifier; current lightweight implementation uses `frame_difference_proxy`. |
| motion_consistency_frame_count | protocol | none | true | false | false | Aligned frame count used by the motion-consistency metric. |
| motion_consistency_normalization_mode | protocol | none | true | false | false | Normalization rule used by the motion-consistency metric. |
| disabled_temporal_metrics | protocol | none | true | false | false | Explicit list of temporal metrics disabled in the current real_video_vae_latent_probe scaffold. |
| motion_consistency_failure_reason | protocol | none | true | false | false | Explicit motion-consistency failure or disablement reason recorded in stage-two real-video temporal payloads. |
| artifact_manifest_path | artifact_layout | none | false | false | false | Relative layout path for the real_video_vae_latent_probe artifact manifest. |
| colab_runtime_manifest_path | artifact_layout | none | false | false | false | Relative layout path for the real_video_vae_latent_probe runtime manifest. |
| colab_real_video_vae_latent_runtime_config_path | artifact_layout | none | false | false | false | Relative layout path for the real_video_vae_latent_probe runtime-config manifest. |
| notebook_entrypoint_present | governance | none | false | false | false | Boolean runtime-manifest field indicating whether the governed real_video_vae_latent_probe Colab notebook entrypoint exists in the repository at run time. |
| git_commit | trace | none | false | false | false | Source commit identifier recorded in the real_video_vae_latent_probe Colab runtime manifest when provided by the notebook runtime config. |
| runtime_config_digest | trace | none | false | false | false | Digest of the persisted real_video_vae_latent_probe Colab runtime-config payload recorded in the run manifest for rebuild provenance. |
| real_video_attack_breakdown_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt real_video_vae_latent_probe real-video attack breakdown table. |
| quality_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt real_video_vae_latent_probe quality table. |
| temporal_consistency_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt real_video_vae_latent_probe temporal consistency table. |
| real_video_vae_latent_governance_summary_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt real_video_vae_latent_probe governance summary table. |
| stage2_mechanism_audit_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-two mechanism audit table. |
| stage2_score_distribution_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-two score-distribution table. |
| stage2_sync_gain_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-two sync-gain table. |
| quality_robustness_tradeoff_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt real_video_vae_latent_probe quality-robustness tradeoff figure. |
| stage2_mechanism_report_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-two mechanism audit report. |
| stage2_mechanism_decision_path | artifact_layout | none | false | false | false | Relative layout path for the persisted stage-two mechanism decision artifact. |
| calibration_purpose | protocol | none | false | false | false | Semantic calibration intent label recorded by stage-two mechanism calibration configs and candidate artifacts. |
| config_purpose | governance | none | false | false | false | Human-readable purpose note for governed configs; it documents operator intent without changing runtime semantics. |
| selected_tubelet_only_candidate | protocol | none | false | false | false | Top-level artifact field carrying the governed tubelet-only calibration candidate selected from dev and calibration records only. |
| tubelet_sync_scan_seed | protocol | none | false | false | false | Top-level artifact field describing the governed sync-parameter search seed derived from the selected tubelet-only calibration candidate. |
| selected_tubelet_sync_candidate | protocol | none | false | false | false | Top-level artifact field carrying the governed tubelet-sync calibration candidate selected from actual scan records under the selected tubelet-only seed parameters. |
| method_variants_summary | governance | none | false | false | false | Comma-separated method-variant summary emitted by the real_video_vae_latent_probe governance summary table and consumed by the real_video_vae_latent_probe report. |
| attack_names_summary | governance | none | false | false | false | Comma-separated attack-name summary emitted by the real_video_vae_latent_probe governance summary table and consumed by the real_video_vae_latent_probe report. |
| target_fprs_summary | governance | none | false | false | false | Comma-separated target-FPR summary emitted by the real_video_vae_latent_probe governance summary table and consumed by the real_video_vae_latent_probe report. |
| event_record_count | protocol | none | false | false | false | Count of real_video_vae_latent_probe event score records summarized by the governance summary table. |
| threshold_record_count | protocol | none | false | false | false | Count of real_video_vae_latent_probe threshold records summarized by the governance summary table. |
| clean_negative_fpr_controlled | governance | none | false | false | false | Boolean summary flag indicating whether clean-negative FPR stays within the governed target across rebuilt main metrics rows. |
| attacked_negative_fpr_reported | governance | none | false | false | false | Boolean summary flag indicating whether attacked-negative FPR is materialized for every real_video_vae_latent_probe attack breakdown row. |
| quality_table_non_empty | governance | none | false | false | false | Boolean summary flag indicating that the rebuilt real_video_vae_latent_probe quality table contains governed rows. |
| quality_metrics_runtime | governance | none | false | false | false | Quality-metrics runtime label emitted by the real_video_vae_latent_probe governance summary table and consumed by the real_video_vae_latent_probe report. |
| temporal_table_non_empty | governance | none | false | false | false | Boolean summary flag indicating that the rebuilt real_video_vae_latent_probe temporal consistency table contains governed rows. |
| temporal_metrics_runtime | governance | none | false | false | false | Temporal-metrics runtime label emitted by the real_video_vae_latent_probe governance summary table and consumed by the real_video_vae_latent_probe report. |
| records_to_tables | governance | none | false | false | false | Boolean summary flag indicating that governed real_video_vae_latent_probe records are sufficient to rebuild tables. |
| records_to_report | governance | none | false | false | false | Boolean summary flag indicating that governed real_video_vae_latent_probe records are sufficient to rebuild the report. |
| records_to_failure_gallery | governance | none | false | false | false | Boolean summary flag indicating that governed real_video_vae_latent_probe records are sufficient to rebuild the failure-case gallery. |
| real_video_vae_latent_decision | governance | none | false | false | false | Structured real_video_vae_latent_probe governance decision written into the governance summary table and mirrored by the Markdown report. |
| blocking_reasons | governance | none | false | false | false | Semicolon-separated blocking reasons explaining the current real_video_vae_latent_probe governance decision. |
| next_allowed_stage | governance | none | false | false | false | Governed next-stage recommendation emitted by the real_video_vae_latent_probe governance summary table. |
| Stage2ImplementationDecision | governance | none | false | false | false | Separate implementation-completion decision emitted by the stage-two mechanism audit and family summaries. |
| Stage2MechanismDecision | governance | none | false | false | false | Mechanism-evidence decision emitted by the stage-two mechanism audit and family summaries. |
| Stage2MechanismBlockingReasons | governance | none | false | false | false | Ordered blocking-reason list explaining why the stage-two mechanism decision is not PASS. |
| Stage2MechanismWarnings | governance | none | false | false | false | Ordered warning list emitted by the stage-two mechanism audit when optional metrics or gates are not fully enabled. |
| SyncRescueDecision | governance | none | false | false | false | Separate stage-two rescue decision recording whether governed sync rescue evidence passes independently of leakage control. |
| SyncLeakageDecision | governance | none | false | false | false | Separate stage-two leakage decision recording whether governed sync leakage remains PASS, RISK, or FAIL independently of rescue evidence. |
| SyncCandidateSelectionStatus | governance | none | false | false | false | Stage-two sync selection status summarizing whether the observed sync behavior is eligible, rescue_with_leakage, saturated_anchor_no_increment, or insufficient_signal. |
| SyncAbsoluteRescueStatus | governance | none | false | false | false | Stage-two sync absolute-rescue status summarizing which governed attacks achieve the configured absolute rescue TPR threshold. |
| SyncIncrementalGainStatus | governance | none | false | false | false | Stage-two sync incremental-gain status summarizing whether governed attacks show positive gain, saturated no-gain, no gain, or negative gain against the anchor. |
| SyncNegativeLeakageStatus | governance | none | false | false | false | Stage-two sync negative-leakage status summarizing whether attacked-negative leakage is controlled, at risk, or exceeded. |
| selection_completion_status | governance | none | false | false | false | Selector summary status recording whether the requested stage completed or ended as an anchor-only partial result due to missing compatible sync rows. |
| selection_blocking_reason | governance | none | false | false | false | Selector summary reason explaining why a requested stage ended without a selected tubelet-sync candidate. |
| selection_blocking_details | governance | none | false | false | false | Selector summary payload recording the selected anchor signature and observed sync-stage signatures when compatibility filtering yields no rows. |
| calibration_completion_status | governance | none | false | false | false | Calibration runner summary status recording whether a flat or staged search completed with a final sync candidate or only an anchor-level partial conclusion. |
| calibration_blocking_reason | governance | none | false | false | false | Calibration runner summary reason explaining why a staged or flat search ended without a final sync candidate. |
| calibration_blocking_details | governance | none | false | false | false | Calibration runner summary payload forwarding the selector-side blocking details for incomplete staged or flat conclusions. |
| search_terminated_early | governance | none | false | false | false | Calibration runner boolean indicating that staged search stopped before all configured stages because a required sync candidate was unavailable. |
| terminated_before_stage_name | governance | none | false | false | false | Calibration runner field recording which downstream stage was skipped after staged search terminated early. |
| NextAllowedStageByImplementation | governance | none | false | false | false | Next-stage recommendation implied by the implementation-completion decision. |
| NextAllowedStageByMechanism | governance | none | false | false | false | Next-stage recommendation implied by the mechanism-evidence decision. |
| RecommendedNextAction | governance | none | false | false | false | Human-facing recommended next action emitted by the stage-two mechanism audit. |
| quality_metrics_enabled | governance | none | false | false | false | Stage-two mechanism-audit summary container recording which governed quality metrics were enabled at runtime. |
| temporal_metrics_enabled | governance | none | false | false | false | Stage-two mechanism-audit summary container recording which governed temporal metrics were enabled at runtime. |
| sample_count_summary | governance | none | false | false | false | Stage-two mechanism-audit summary container recording per-key sample-count sufficiency thresholds and shortages. |
| mechanism_metrics | governance | none | false | false | false | Stage-two mechanism-audit summary container recording key gain, gap, and quality summary metrics. |
| minimum_positive_count_per_key | governance | none | true | false | false | Mechanism-gate minimum required positive sample count for each `(method_variant, attack_name)` key. |
| minimum_negative_count_per_key | governance | none | true | false | false | Mechanism-gate minimum required negative sample count for each `(method_variant, attack_name)` key. |
| required_main_variants | governance | none | true | false | false | Ordered primary method variants that must be present before the stage-two mechanism gate can PASS. |
| required_mechanism_attacks | governance | none | true | false | false | Ordered attack roster that must be covered before the stage-two mechanism gate can PASS. |
| sync_gain_policy | governance | none | true | false | false | Governed sync-gain aggregation policy used to interpret required sync rescue attacks as all-of, any-of, or any-of plus mean floor. |
| required_sync_gain_attacks | governance | none | true | false | false | Ordered governed attack subset used when evaluating sync rescue gain and saturation semantics. |
| stage2_mechanism_protocol | governance | none | true | false | false | 阶段 2 机制证明协议, 当前唯一允许值为 `aligned_payload_safety`. |
| min_required_sync_gain_attack_count | governance | none | true | false | false | Minimum number of governed sync rescue attacks that must show positive gain under the configured sync_gain_policy. |
| max_clean_negative_fpr | governance | none | true | false | false | Maximum allowed clean-negative FPR used by the stage-two mechanism gate. |
| max_attacked_negative_fpr | governance | none | true | false | false | Maximum allowed attacked-negative FPR used by the stage-two mechanism gate. |
| min_mean_temporal_sync_gain | governance | none | true | false | false | Optional governed mean temporal sync-gain floor that may complement any-of-k sync rescue gating. |
| min_no_attack_clean_positive_tpr | governance | none | true | false | false | Minimum required no-attack clean-positive TPR used by the stage-two mechanism gate. |
| min_tubelet_only_gain_over_frame_prc | governance | none | true | false | false | Minimum required gain of `tubelet_only` over `frame_prc` used by the stage-two mechanism gate. |
| min_tubelet_sync_gain_over_tubelet_only_temporal | governance | none | true | false | false | Minimum required temporal gain of `tubelet_sync` over `tubelet_only` used by the stage-two mechanism gate. |
| sync_gain_saturation_threshold | governance | none | true | false | false | Governed attacked-positive TPR threshold used to classify an anchor as saturated for sync incremental-gain semantics. |
| absolute_rescue_tpr_threshold | governance | none | true | false | false | Governed attacked-positive TPR threshold used to declare absolute rescue success for sync semantics. |
| leakage_exceeded_multiplier | governance | none | true | false | false | Governed multiplier above max_attacked_negative_fpr used to distinguish leakage_risk from leakage_exceeded. |
| require_quality_not_collapsed | governance | none | true | false | false | Boolean mechanism-gate flag requiring stage-two quality metrics to stay above configured floors. |
| min_watermarked_video_psnr | governance | none | true | false | false | Minimum watermarked-video PSNR floor used by the stage-two mechanism gate. |
| min_watermarked_video_ssim | governance | none | true | false | false | Minimum watermarked-video SSIM floor used by the stage-two mechanism gate. |
| video_vae_backend_placeholder | placeholder | _placeholder | true | false | true | Placeholder VAE backend field reserved while the repository remains under synthetic_tubelet_sync_probe governance. |
| clip_similarity_placeholder | placeholder | _placeholder | true | false | true | Placeholder field representing disabled CLIP-similarity support in the real_video_vae_latent_probe scaffold. |
| motion_consistency_placeholder | placeholder | _placeholder | true | false | true | Placeholder field representing disabled motion-consistency support in the real_video_vae_latent_probe scaffold. |
| trajectory_backend_name | protocol | none | true | false | false | Stage-three trajectory backend identifier used by the surrogate reconstruction support config and runtime config manifest. |
| trajectory_source_kind | protocol | none | true | false | false | Stage-three trajectory source identifier recorded in method configs and mechanism traces. |
| formal_trajectory_source_status | protocol | none | true | false | false | Stage-three status field indicating whether the trajectory source is missing, non-formal, or a ready formal candidate. |
| trajectory_source_provenance_digest | protocol | none | true | false | false | Digest provenance for a stage-three trajectory source, anchored to the frozen upstream dependency when available. |
| stage2_frozen_baseline_manifest_digest | governance | none | true | false | false | Digest of the validated stage-two frozen baseline manifest injected into stage-three formal source candidate records. |
| stage2_frozen_baseline_record_count | governance | none | true | false | false | Number of event-score records validated in the stage-two frozen baseline package used by stage-three replay. |
| stage2_frozen_baseline_threshold_count | governance | none | true | false | false | Number of threshold records validated in the stage-two frozen baseline package used by stage-three replay. |
| trajectory_statistic_kind | protocol | none | true | false | false | Stage-three trajectory statistic identifier recorded in method configs and mechanism traces. |
| trajectory_control_kind | protocol | none | true | false | false | Governed trajectory control identifier recorded in method configs and mechanism traces. |
| trajectory_time_grid | protocol | none | true | false | false | Ordered interpolation time grid used by stage-three surrogate trajectory reconstruction and recorded in mechanism traces. |
| trajectory_weight | protocol | none | true | false | false | Linear fusion weight applied to `S_traj` when baseline evidence remains enabled. |
| allow_stage2_incomplete_scaffold | governance | none | true | false | false | Boolean protocol guard allowing the stage-three scaffold to run while stage-two formal closure remains incomplete. |
| require_frozen_stage2_baseline_for_formal | governance | none | true | false | false | Boolean protocol guard requiring frozen stage-two baselines before any stage-three formal promotion. |
| record_runtime_breakdown | governance | none | true | false | false | Boolean trajectory-backend support field enabling per-record runtime breakdown persistence. |
| fail_on_positive_only_artifact_access | governance | none | true | false | false | Boolean trajectory-backend support field forbidding reconstruction paths that depend on positive-only artifacts. |
| S_traj | protocol | none | true | false | false | Stage-three trajectory evidence score written into `evidence_scores`; larger indicates stronger trajectory evidence. |
| trajectory_valid_segment_ratio | protocol | none | true | false | false | Ratio of valid consecutive trajectory segments contributing to the stage-three statistic. |
| trajectory_projection_count | protocol | none | true | false | false | Count of projection evaluations contributing to the stage-three trajectory statistic. |
| S_traj_velocity | protocol | none | true | false | false | Velocity-projection component of the stage-three trajectory statistic; larger indicates stronger evidence. |
| S_traj_displacement | protocol | none | true | false | false | Displacement component of the stage-three trajectory statistic recorded for auditability. |
| trajectory_curvature_residual | protocol | none | true | false | false | Curvature residual summary recorded for auditability of non-linear surrogate motion. |
| trajectory_backend_status | protocol | none | true | false | false | Stage-three trajectory backend status recorded in `mechanism_trace`. |
| trajectory_fail_reason | protocol | none | true | false | false | Nullable stage-three trajectory failure reason recorded in `mechanism_trace` when reconstruction or scoring is unavailable. |
| trajectory_control_scores | protocol | none | true | false | false | Mapping from governed control kinds to control trajectory scores for stage-three auditability. |
| trajectory_runtime_ms | protocol | none | true | false | false | End-to-end stage-three trajectory runtime in milliseconds recorded per event. |
| trajectory_reconstruction_ms | protocol | none | true | false | false | Trajectory reconstruction runtime in milliseconds recorded per event. |
| trajectory_scoring_ms | protocol | none | true | false | false | Trajectory scoring runtime in milliseconds recorded per event. |
| trajectory_ablation_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-three trajectory ablation table. |
| score_correlation_matrix_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-three score-correlation matrix table. |
| trajectory_gain_by_attack_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-three trajectory gain-by-attack table. |
| trajectory_control_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-three trajectory control table. |
| runtime_breakdown_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-three trajectory runtime-breakdown table. |
| trajectory_probe_report_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt stage-three trajectory probe report. |
| trajectory_mechanism_decision_path | artifact_layout | none | false | false | false | Relative layout path for the persisted stage-three trajectory mechanism-decision artifact. |
| stage2_frozen_baseline_manifest_path | artifact_layout | none | false | false | false | Relative layout path for the frozen stage-two baseline manifest consumed by the trajectory statistic probe. |
| stage2_frozen_baseline_handoff_path | artifact_layout | none | false | false | false | Drive family-result path for the Colab handoff JSON that tells users which stage-two frozen baseline package to download. |
| left_score_name | protocol | none | false | false | false | Left score identifier used by rebuilt stage-three score-correlation rows. |
| right_score_name | protocol | none | false | false | false | Right score identifier used by rebuilt stage-three score-correlation rows. |
| correlation_value | protocol | none | false | false | false | Correlation summary value emitted by rebuilt stage-three score-correlation rows. |
| record_count | protocol | none | false | false | false | Count of records contributing to a rebuilt stage-three summary row. |
| baseline_attacked_positive_TPR | protocol | none | false | false | false | Baseline attacked-positive TPR used by rebuilt stage-three trajectory gain rows. |
| delta_traj | protocol | none | false | false | false | Incremental attacked-positive TPR gain contributed by a trajectory-enabled variant over its baseline. |
| baseline_attacked_positive_margin | protocol | none | false | false | false | Mean baseline attacked-positive `S_final - threshold` margin used when TPR is saturated. |
| attacked_positive_margin | protocol | none | false | false | false | Mean trajectory-enabled attacked-positive `S_final - threshold` margin used when TPR is saturated. |
| delta_positive_margin_traj | protocol | none | false | false | false | Incremental attacked-positive score-margin gain contributed by a trajectory-enabled variant over its baseline. |
| Stage3ImplementationDecision | governance | none | false | false | false | Implementation-completion decision emitted by the stage-three trajectory mechanism audit. |
| Stage3MechanismDecision | governance | none | false | false | false | Mechanism-evidence decision emitted by the stage-three trajectory mechanism audit. |
| Stage2DependencyStatus | governance | none | false | false | false | Stage-three mechanism-audit field recording whether the prerequisite stage-two gate has passed. |
| Stage2FrozenBaselineManifest | governance | none | false | false | false | Frozen stage-two baseline manifest status emitted after the trajectory dependency loader validates the package. |
| Stage3MechanismBlockingReasons | governance | none | false | false | false | Mechanism-specific blocking reasons that keep stage-three trajectory evidence from becoming a formal PASS. |
| TrajectoryMechanismGateSummary | governance | none | false | false | false | Stage-three mechanism gate summary containing gain, negative-leakage, control, and runtime gate decisions. |
| trajectory_gain_gate | governance | none | false | false | false | Stage-three gate field indicating whether trajectory-enabled variants provide positive incremental gain. |
| trajectory_negative_leakage_gate | governance | none | false | false | false | Stage-three gate field indicating whether clean and attacked negative FPR remain under the governed target. |
| trajectory_control_gate | governance | none | false | false | false | Stage-three gate field indicating whether trajectory controls fail to reproduce the main trajectory gain. |
| trajectory_runtime_gate | governance | none | false | false | false | Stage-three gate field indicating whether trajectory runtime records are complete and within the configured bound. |
| trajectory_formal_runtime_profile_gate | governance | none | false | false | false | Stage-three gate field requiring formal runtime profiles before the mechanism decision can become PASS. |
| max_negative_leakage_increase_over_baseline | protocol | none | false | false | false | Stage-three negative-leakage metric measuring whether trajectory-enabled variants increase negative decisions over the frozen baseline. |
| max_ablation_negative_leakage_increase | protocol | none | false | false | false | Stage-three diagnostic metric reporting `traj_only` ablation leakage separately from fused candidate leakage. |
| mean_abs_main_trajectory_score | protocol | none | false | false | false | Mean absolute main trajectory score used as the denominator for control suppression audit. |
| control_suppression_ratio | protocol | none | false | false | false | Ratio between mean absolute control score and mean absolute main trajectory score for stage-three control audit. |
| baseline_construction_phase | governance | none | false | false | false | Construction phase recorded in the frozen baseline run manifest. |
| baseline_root | governance | none | false | false | false | Runtime path to the frozen baseline output root used by the replay runner. |
| baseline_run_id | governance | none | false | false | false | Run identifier copied from the frozen baseline run manifest. |
| baseline_records_digest | governance | none | false | false | false | Digest of frozen baseline event score records used to prove read-only dependency identity. |
| baseline_thresholds_digest | governance | none | false | false | false | Digest of frozen baseline threshold records used to prove read-only dependency identity. |
| baseline_run_manifest_digest | governance | none | false | false | false | Digest of the frozen baseline run manifest used to prove read-only dependency identity. |
| baseline_mechanism_decision_digest | governance | none | false | false | false | Digest of the frozen baseline mechanism decision artifact used to prove gate identity. |
| baseline_record_count | governance | none | false | false | false | Count of frozen baseline event records accepted by the dependency loader. |
| baseline_threshold_count | governance | none | false | false | false | Count of frozen baseline threshold records accepted by the dependency loader. |
| handoff_kind | governance | none | false | false | false | Handoff JSON kind identifying the package as a stage-two frozen baseline for trajectory statistic replay. |
| required_relpaths | governance | none | false | false | false | Relative paths that must exist after extracting the stage-two frozen baseline archive for the stage-three loader. |
| recommended_local_baseline_root | governance | none | false | false | false | Human-readable instruction for selecting the extracted run root as the local frozen baseline root. |
| TrajectoryLeakageSummary | governance | none | false | false | false | Stage-three mechanism-audit summary container for negative leakage rates. |
| TrajectoryGainSummary | governance | none | false | false | false | Stage-three mechanism-audit summary container for trajectory incremental gain. |
| TrajectoryCorrelationSummary | governance | none | false | false | false | Stage-three mechanism-audit summary container for control-score magnitude and enabled-variant coverage. |
| TrajectoryControlSummary | governance | none | false | false | false | Stage-three mechanism-audit summary container for control-score audit coverage. |
| TrajectoryRuntimeOverheadSummary | governance | none | false | false | false | Stage-three mechanism-audit summary container for runtime overhead. |
| NextAllowedStageByTrajectory | governance | none | false | false | false | Next-stage recommendation implied by the stage-three trajectory mechanism audit. |
| max_delta_traj | governance | none | false | false | false | Maximum observed stage-three trajectory gain across rebuilt comparison rows. |
| mean_delta_traj | governance | none | false | false | false | Mean stage-three trajectory gain across rebuilt comparison rows. |
| max_positive_margin_delta_traj | governance | none | false | false | false | Maximum positive score-margin gain used as complementary stage-three gain evidence when baseline TPR is saturated. |
| mean_positive_margin_delta_traj | governance | none | false | false | false | Mean positive score-margin gain used as complementary stage-three gain evidence when baseline TPR is saturated. |
| gain_evidence_kind | governance | none | false | false | false | Stage-three gain evidence mode indicating whether gain was judged by TPR only or by TPR plus positive score margin. |
| mean_abs_control_score | governance | none | false | false | false | Mean absolute control-score magnitude reported by the stage-three mechanism audit. |
| trajectory_enabled_variant_count | governance | none | false | false | false | Count of trajectory-enabled method variants included in the stage-three mechanism audit. |
| control_score_count | governance | none | false | false | false | Count of control-score observations summarized by the stage-three mechanism audit. |
| max_abs_control_score | governance | none | false | false | false | Maximum absolute control-score magnitude reported by the stage-three mechanism audit. |
| mean_trajectory_runtime_ms | governance | none | false | false | false | Mean per-event trajectory runtime reported by the stage-three mechanism audit. |
| runtime_record_count | governance | none | false | false | false | Count of runtime observations summarized by the stage-three mechanism audit. |

## Notes

- All `*_placeholder` fields require replacement before any supported claim can rely on them.
- All `*_random` fields must carry seed or digest traceability.
- Current stage freezes schema, layout, and placeholder / random runtime scaffolding only; it does not register any real algorithm field as claim-supporting.
| vae_reconstruction_psnr_finite_mean | table | none | true | false | false | VAE reconstruction PSNR finite-only mean used to separate ordinary finite quality from positive-infinity perfect reconstruction cases. |
| vae_reconstruction_psnr_finite_count | table | none | true | false | false | Count of finite VAE reconstruction PSNR values contributing to `vae_reconstruction_psnr_finite_mean`. |
| vae_reconstruction_psnr_inf_count | table | none | true | false | false | Count of positive-infinity VAE reconstruction PSNR values in quality tables. |
| vae_reconstruction_psnr_total_count | table | none | true | false | false | Count of numeric VAE reconstruction PSNR values, including finite and positive-infinity values. |
| watermarked_video_psnr_finite_mean | table | none | true | false | false | Watermarked-video PSNR finite-only mean used by quality tables and tradeoff figures when regular finite values are available. |
| watermarked_video_psnr_finite_count | table | none | true | false | false | Count of finite watermarked-video PSNR values contributing to `watermarked_video_psnr_finite_mean`. |
| watermarked_video_psnr_inf_count | table | none | true | false | false | Count of positive-infinity watermarked-video PSNR values in quality tables. |
| watermarked_video_psnr_total_count | table | none | true | false | false | Count of numeric watermarked-video PSNR values, including finite and positive-infinity values. |
| quality_psnr_finite_mean | table | none | true | false | false | Stage-two mechanism audit finite-only PSNR mean for the grouped `watermarked_video_psnr` field. |
| quality_psnr_finite_count | table | none | true | false | false | Stage-two mechanism audit count of finite grouped PSNR values. |
| quality_psnr_inf_count | table | none | true | false | false | Stage-two mechanism audit count of positive-infinity grouped PSNR values. |
| quality_psnr_total_count | table | none | true | false | false | Stage-two mechanism audit count of numeric grouped PSNR values. |
| mean_watermarked_video_psnr_finite | table | none | true | false | false | Stage-two mechanism decision finite-only mean of positive watermarked-video PSNR values. |
| profiling_status | runtime_profile | none | true | false | false | GPU runtime profiling status; expected values include `sampled`, `unavailable`, and `not_sampled`. |
| profiling_failure_reason | runtime_profile | none | true | false | false | Reason explaining why GPU profiling did not produce usable samples. |
| usable_sample_count | runtime_profile | none | true | false | false | Count of GPU runtime trace samples with usable GPU utilization values. |
| unavailable_sample_count | runtime_profile | none | true | false | false | Count of GPU runtime trace samples that explicitly report unavailable or failed GPU sampling. |

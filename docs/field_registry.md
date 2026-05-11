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
| S_sync_peak_best | protocol | none | true | false | false | Best raw synchronization candidate score before positive-margin calibration. |
| S_sync_peak_second_or_median | protocol | none | true | false | false | Second-best or median synchronization score used as the peak-margin baseline. |
| S_sync_peak_margin | protocol | none | true | false | false | Raw difference between best synchronization peak and its comparison baseline. |
| S_sync_positive_margin | protocol | none | true | false | false | Non-negative calibrated synchronization peak margin mapped to `S_sync`. |
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
| quality_metrics | protocol | none | true | false | false | Top-level real_video_vae_latent_probe quality-metrics payload written into event records. |
| temporal_metrics | protocol | none | true | false | false | Top-level real_video_vae_latent_probe temporal-metrics payload written into event records. |
| vae_reconstruction_psnr | protocol | none | true | false | false | Placeholder-derived PSNR summary used by the real_video_vae_latent_probe scaffold quality payload. |
| vae_reconstruction_ssim | protocol | none | true | false | false | Placeholder-derived SSIM summary used by the real_video_vae_latent_probe scaffold quality payload. |
| watermarked_video_psnr | protocol | none | true | false | false | Placeholder-derived PSNR summary for decoded or attacked comparison videos in stage two. |
| watermarked_video_ssim | protocol | none | true | false | false | Placeholder-derived SSIM summary for decoded or attacked comparison videos in stage two. |
| watermarked_video_lpips | protocol | none | true | false | false | Reserved LPIPS field; the current real_video_vae_latent_probe scaffold records it as disabled. |
| clip_similarity_score | protocol | none | true | false | false | Reserved CLIP-similarity field; the current real_video_vae_latent_probe scaffold records it as disabled. |
| disabled_quality_metrics | protocol | none | true | false | false | Explicit list of quality metrics disabled in the current real_video_vae_latent_probe scaffold. |
| quality_failure_reason | protocol | none | true | false | false | Recorded reason when a placeholder quality threshold is violated in stage two. |
| temporal_consistency_score | protocol | none | true | false | false | Placeholder-derived temporal consistency score computed from video artifacts. |
| flicker_score | protocol | none | true | false | false | Placeholder-derived flicker score computed from frame-difference deltas. |
| motion_consistency_score | protocol | none | true | false | false | Reserved motion-consistency field; the current real_video_vae_latent_probe scaffold records it as disabled. |
| disabled_temporal_metrics | protocol | none | true | false | false | Explicit list of temporal metrics disabled in the current real_video_vae_latent_probe scaffold. |
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
| quality_robustness_tradeoff_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt real_video_vae_latent_probe quality-robustness tradeoff figure. |
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
| video_vae_backend_placeholder | placeholder | _placeholder | true | false | true | Placeholder VAE backend field reserved while the repository remains under synthetic_tubelet_sync_probe governance. |
| clip_similarity_placeholder | placeholder | _placeholder | true | false | true | Placeholder field representing disabled CLIP-similarity support in the real_video_vae_latent_probe scaffold. |
| motion_consistency_placeholder | placeholder | _placeholder | true | false | true | Placeholder field representing disabled motion-consistency support in the real_video_vae_latent_probe scaffold. |

## Notes

- All `*_placeholder` fields require replacement before any supported claim can rely on them.
- All `*_random` fields must carry seed or digest traceability.
- Current stage freezes schema, layout, and placeholder / random runtime scaffolding only; it does not register any real algorithm field as claim-supporting.

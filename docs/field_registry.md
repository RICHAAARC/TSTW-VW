# Field Registry

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
| target_fpr | protocol | none | true | false | false | Materialized target FPR used by stage-0 runtime records and tables. |
| validation_target_fpr | protocol | none | true | false | false | Profile-scoped validation FPR target used for closure and proof reports when strict `target_fpr` is intentionally deferred. |
| calibration_negative_min_samples_per_role_by_profile | protocol | none | true | false | false | Profile-scoped lower bound for calibration negative sample counts so proof and formal tiers can widen calibration tails without inflating dev or test coverage. |
| threshold_quantile_rule | protocol | none | true | false | false | Declared quantile rule for calibration-only threshold construction. |
| allow_attack_specific_threshold | protocol | none | true | false | false | Boolean field that blocks attack-specific threshold divergence. |
| method_family | protocol | none | true | false | false | Stable method family identifier for stage-0 records and configs. |
| method_variant | protocol | none | true | false | false | Stable method variant identifier used by stage-0 configs and event records. |
| base_method_variant | protocol | none | true | false | false | Primary method variant from which a derived ablation variant inherits its mechanism semantics. |
| derived_variant | protocol | none | true | false | false | Boolean marker that distinguishes primary method variants from derived ablation variants. |
| ablation_axis | protocol | none | true | false | false | Nullable axis name for derived ablation variants; current stage uses `tubelet_length`. |
| method_status | protocol | none | true | false | false | Stage-0 method status field describing placeholder or random scaffold semantics. |
| enable_frame_prc | protocol | none | true | false | false | Boolean switch reserved for the frame-wise baseline in the synthetic tubelet sync method-entry configs. |
| enable_tubelet | protocol | none | true | false | false | Boolean switch reserved for tubelet evidence enablement in the synthetic tubelet sync method-entry configs. |
| enable_sync | protocol | none | true | false | false | Boolean switch reserved for temporal synchronization enablement in the synthetic tubelet sync method-entry configs. |
| enable_trajectory | protocol | none | true | false | false | Boolean switch reserved for trajectory evidence enablement in the synthetic tubelet sync method-entry configs. |
| tubelet_length | protocol | none | true | false | false | Reserved tubelet-length field used by the synthetic tubelet sync method-entry configs. |
| enabled_evidence | protocol | none | true | false | false | Evidence enablement container that freezes which evidence branches are active. |
| fusion_rule | protocol | none | true | false | false | Stable fusion rule identifier used by stage-0 threshold and method configs. |
| attack_name | protocol | none | true | false | false | Attack identifier written into stage-0 event records. |
| attack_params | protocol | none | true | false | false | Attack parameter object written into stage-0 event records. |
| score_name | protocol | none | true | false | false | Governed score identifier used by threshold records. |
| threshold_id | protocol | none | true | false | false | Stable threshold identifier used by stage-0 threshold and event records. |
| input_artifact_trace | protocol | none | true | false | false | Long-lived input artifact trace container for governed event records. |
| artifact_kind | protocol | none | true | false | false | Semantic kind of governed input artifact persisted inside `input_artifact_trace`. |
| backend_name | protocol | none | true | false | false | Backend identifier persisted inside `input_artifact_trace`. |
| backend_status | protocol | none | true | false | false | Backend status persisted inside `input_artifact_trace`. |
| artifact_digest | trace | none | true | false | false | Digest of the governed input artifact persisted inside `input_artifact_trace`. |
| generation_seed_random | random | _random | true | false | false | Random seed field inside `input_artifact_trace`; the `_random` suffix is retained for reproducibility semantics. |
| latent_backend_name | protocol | none | true | false | false | Stage-0 compatibility field mirroring `input_artifact_trace.backend_name` in governed event records. |
| latent_backend_status | protocol | none | true | false | false | Stage-0 compatibility field mirroring `input_artifact_trace.backend_status` in governed event records. |
| latent_seed_random | random | _random | true | false | false | Random latent seed field; seed semantics are explicit in the field name. |
| latent_generation_seed_random | random | _random | true | false | false | Stage-0 compatibility seed field mirroring `input_artifact_trace.generation_seed_random`. |
| latent_tensor_digest_random | random | _digest_random | true | false | false | Stage-0 compatibility digest field mirroring `input_artifact_trace.artifact_digest`. |
| score_generation_seed_random | random | _random | true | false | false | Seed field for deterministic stage-0 random evidence score generation. |
| prg_direction_seed_random | random | _random | true | false | false | Random PRG direction seed field; seed semantics are explicit in the field name. |
| sync_code_seed_random | random | _random | true | false | false | Random sync code seed field; seed semantics are explicit in the field name. |
| payload_bits_random | random | _random | true | false | false | Random payload bits field; it requires a paired seed or digest field for reproducibility. |
| payload_bits_digest_random | random | _digest_random | true | false | false | Digest-tracked random payload field; digest semantics are self-contained. |
| protocol_name | protocol | none | true | false | false | Frozen protocol identifier for the fixed low-FPR calibrated detector skeleton. |
| construction_phase | protocol | none | true | false | false | Semantic construction phase identifier aligned with the active governed stage. |
| target_construction_phase | protocol | none | true | false | false | Reserved next-stage construction phase identifier used by support configs while the active project stage remains `protocol_skeleton`. |
| latent_distribution | protocol | none | true | false | false | Governed latent distribution identifier reserved for the synthetic tubelet sync probe entry config. |
| latent_shape | protocol | none | true | false | false | Reserved latent-shape container for the synthetic video latent support config. |
| latent_generation_seed | protocol | none | true | false | false | Reserved deterministic seed field for the synthetic video latent support config. |
| latent_storage | artifact_layout | none | true | false | false | Reserved latent artifact storage policy for the synthetic tubelet sync probe support config. |
| attack_matrix_name | protocol | none | true | false | false | Stable attack-matrix identifier used by support configs and later stage-specific attack registries. |
| attacks | protocol | none | true | false | false | Ordered attack-entry container used by the reserved temporal attack matrix config. |
| required_method_variants | protocol | none | true | false | false | Ordered method-variant roster that the synthetic tubelet sync protocol support config requires. |
| required_output_tables | artifact_layout | none | true | false | false | Ordered table roster required by the reserved synthetic tubelet sync protocol support config. |
| mechanism_trace_required | protocol | none | true | false | false | Boolean field that freezes the requirement for `mechanism_trace` before stage-1 runtime promotion. |
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
| mechanism_trace | protocol | none | true | false | false | Governed mechanism trace container written into stage-one event records. |
| reference_latent_shape | protocol | none | true | false | false | Reference latent shape used to preserve the pre-attack synchronization search space. |
| latent_artifact_relpath | artifact_layout | none | true | false | false | Relative path to the persisted tensor artifact used by embedding, attack, and detection. |
| latent_artifact_digest | trace | none | true | false | false | File digest of the persisted tensor artifact currently used by the event record. |
| partition_digest | trace | none | true | false | false | Digest of the governed tubelet partition layout. |
| embedding_rule | protocol | none | true | false | false | Stable embedding rule identifier for the stage-one projection-margin mechanism. |
| embedding_margin | protocol | none | true | false | false | Minimum coded projection margin enforced by the stage-one embedding rule. |
| mean_projection_before | protocol | none | true | false | false | Mean coded tubelet projection before projection-margin embedding. |
| mean_projection_after | protocol | none | true | false | false | Mean coded tubelet projection after projection-margin embedding. |
| mean_embedding_delta_norm | protocol | none | true | false | false | Mean projection-margin delta norm applied during embedding. |
| codebook_digest | trace | none | true | false | false | Digest of the deterministic tubelet direction codebook. |
| sync_code_digest | trace | none | true | false | false | Digest of the deterministic synchronization code sequence. |
| payload_digest | trace | none | true | false | false | Digest of the payload sign assignments used by the stage-one method. |
| sync_search_enabled | protocol | none | true | false | false | Boolean field recording whether synchronization search was active for detection. |
| sync_estimated_offset | protocol | none | true | false | false | Estimated synchronization offset selected by the stage-one detector. |
| sync_ground_truth_offset | protocol | none | true | false | false | Ground-truth offset materialized by governed temporal attacks when available. |
| sync_alignment_error | protocol | none | true | false | false | Absolute error between estimated and ground-truth synchronization offset. |
| sync_peak_rank | protocol | none | true | false | false | Rank position of the ground-truth offset within the governed search scores. |
| sync_search_space_size | protocol | none | true | false | false | Candidate count of the governed synchronization offset search space. |
| sync_search_space_digest | trace | none | true | false | false | Digest of the governed synchronization search-space score map. |
| clip_length | protocol | none | true | false | false | Materialized local-clip or crop length recorded in the stage-one mechanism trace. |
| created_at | protocol | none | true | false | false | ISO-8601 timestamp field for governed threshold and manifest records. |
| table_builder_name | protocol | none | false | false | false | Stable table builder identifier for stage-0 ablation governance. |
| placeholder_fields | governance | none | true | false | false | Explicit list of placeholder-bound fields carried by governed records or manifests. |
| random_fields | governance | none | true | false | false | Explicit list of random-trace fields carried by governed records or manifests. |
| watermark_payload_placeholder | placeholder | _placeholder | true | false | true | Placeholder payload field used by the empty watermark scaffold. |
| sync_alignment_placeholder | placeholder | _placeholder | true | false | true | Placeholder synchronization field used by stage-0 methods without real sync logic. |
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
| attack_matrix_placeholder | placeholder | _placeholder | true | false | true | Placeholder field that freezes the stage-0 attack matrix skeleton. |
| attack_name_placeholder | placeholder | _placeholder | true | false | true | Placeholder attack name field for the governed identity attack skeleton. |
| attack_params_placeholder | placeholder | _placeholder | true | false | true | Placeholder attack parameter container for the governed identity attack skeleton. |
| shared_attack_matrix_required | governance | none | true | false | false | Boolean governance field that blocks per-variant attack matrix divergence. |

## Notes

- All `*_placeholder` fields require replacement before any supported claim can rely on them.
- All `*_random` fields must carry seed or digest traceability.
- Current stage freezes schema, layout, and placeholder / random runtime scaffolding only; it does not register any real algorithm field as claim-supporting.

# Field Registry

| field_name | category | required_suffix | allowed_in_records | allowed_in_claims | replacement_required | description |
| --- | --- | --- | --- | --- | --- | --- |
| project_stage | protocol | none | true | false | false | Semantic project stage identifier for governed protocol progression. |
| legacy_stage_id | compatibility | none | true | false | false | Compatibility-only legacy stage field; it must not drive formal naming. |
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
| threshold_quantile_rule | protocol | none | true | false | false | Declared quantile rule for calibration-only threshold construction. |
| allow_attack_specific_threshold | protocol | none | true | false | false | Boolean field that blocks attack-specific threshold divergence. |
| method_family | protocol | none | true | false | false | Stable method family identifier for stage-0 records and configs. |
| method_variant | protocol | none | true | false | false | Stable method variant identifier used by stage-0 configs and event records. |
| method_status | protocol | none | true | false | false | Stage-0 method status field describing placeholder or random scaffold semantics. |
| enabled_evidence | protocol | none | true | false | false | Evidence enablement container that freezes which evidence branches are active. |
| fusion_rule | protocol | none | true | false | false | Stable fusion rule identifier used by stage-0 threshold and method configs. |
| attack_name | protocol | none | true | false | false | Attack identifier written into stage-0 event records. |
| attack_params | protocol | none | true | false | false | Attack parameter object written into stage-0 event records. |
| score_name | protocol | none | true | false | false | Governed score identifier used by threshold records. |
| threshold_id | protocol | none | true | false | false | Stable threshold identifier used by stage-0 threshold and event records. |
| latent_backend_name | protocol | none | true | false | false | Stable stage-0 latent backend identifier. |
| latent_backend_status | protocol | none | true | false | false | Status field for the stage-0 latent backend scaffold. |
| latent_seed_random | random | _random | true | false | false | Random latent seed field; seed semantics are explicit in the field name. |
| latent_generation_seed_random | random | _random | true | false | false | Seed field for deterministic stage-0 latent sample generation. |
| latent_tensor_digest_random | random | _digest_random | true | false | false | Digest field for stage-0 synthetic latent sample identity. |
| score_generation_seed_random | random | _random | true | false | false | Seed field for deterministic stage-0 random evidence score generation. |
| prg_direction_seed_random | random | _random | true | false | false | Random PRG direction seed field; seed semantics are explicit in the field name. |
| sync_code_seed_random | random | _random | true | false | false | Random sync code seed field; seed semantics are explicit in the field name. |
| payload_bits_random | random | _random | true | false | false | Random payload bits field; it requires a paired seed or digest field for reproducibility. |
| payload_bits_digest_random | random | _digest_random | true | false | false | Digest-tracked random payload field; digest semantics are self-contained. |
| protocol_name | protocol | none | true | false | false | Frozen protocol identifier for the fixed low-FPR calibrated detector skeleton. |
| construction_phase | protocol | none | true | false | false | Semantic construction phase identifier aligned with the active governed stage. |
| record_schema_name | schema | none | true | false | false | Canonical event score record schema identifier for protocol artifact governance. |
| threshold_schema_name | schema | none | true | false | false | Canonical threshold record schema identifier for protocol artifact governance. |
| manifest_schema_name | schema | none | true | false | false | Canonical run manifest schema identifier for protocol artifact governance. |
| event_scores_path | artifact_layout | none | false | false | false | Relative layout path for governed event-level score records. |
| thresholds_path | artifact_layout | none | false | false | false | Relative layout path for governed threshold records. |
| run_manifest_path | artifact_layout | none | false | false | false | Relative layout path for the governed run manifest. |
| main_metrics_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt main metrics table. |
| ablation_table_path | artifact_layout | none | false | false | false | Relative layout path for the rebuilt ablation table. |
| threshold_source_record_digest | trace | none | true | false | false | Digest field that binds threshold materialization to calibration-negative source records. |
| calibration_split | protocol | none | true | false | false | Governed calibration split identifier written into threshold records. |
| calibration_negative_roles | protocol | none | true | false | false | Governed calibration negative role list written into threshold records. |
| threshold_value | protocol | none | true | false | false | Materialized threshold value for a governed threshold record. |
| threshold_quantile | protocol | none | true | false | false | Materialized threshold quantile used to build a governed threshold record. |
| num_calibration_negatives | protocol | none | true | false | false | Count of calibration-negative records used during threshold materialization. |
| disabled_evidence | protocol | none | true | false | false | Explicit list of evidence branches disabled for a governed event record. |
| decision | protocol | none | true | false | false | Detection decision field for a governed event record. |
| failure_reason | protocol | none | true | false | false | Failure reason field for a governed event record. |
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
| figures_digest_placeholder | placeholder | _placeholder | true | false | true | Placeholder digest field for figures that are intentionally absent in protocol_skeleton. |
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

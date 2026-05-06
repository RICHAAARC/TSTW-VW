# Field Registry

| field_name | category | required_suffix | allowed_in_records | allowed_in_claims | replacement_required | description |
| --- | --- | --- | --- | --- | --- | --- |
| project_stage | protocol | none | true | false | false | Semantic project stage identifier for governed protocol progression. |
| legacy_stage_id | compatibility | none | true | false | false | Compatibility-only legacy stage field; it must not drive formal naming. |
| method_variant_placeholder | placeholder | _placeholder | true | false | true | Placeholder method variant for protocol skeleton only. |
| latent_backend_placeholder | placeholder | _placeholder | true | false | true | Placeholder latent backend entry; it must be replaced before formal method claims. |
| watermark_method_placeholder | placeholder | _placeholder | true | false | true | Placeholder watermark method entry for bootstrap-only configs. |
| trajectory_backend_placeholder | placeholder | _placeholder | true | false | true | Placeholder trajectory backend entry reserved for later stages. |
| quality_metric_placeholder | placeholder | _placeholder | true | false | true | Placeholder quality metric field for future governed replacement. |
| target_fpr_placeholder | placeholder | _placeholder | true | false | true | Placeholder target FPR field used before full threshold materialization. |
| latent_seed_random | random | _random | true | false | false | Random latent seed field; seed semantics are explicit in the field name. |
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
| placeholder_fields | governance | none | true | false | false | Explicit list of placeholder-bound fields carried by governed records or manifests. |
| random_fields | governance | none | true | false | false | Explicit list of random-trace fields carried by governed records or manifests. |
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
- Current stage freezes schema and layout only; it does not register any real algorithm field as claim-supporting.

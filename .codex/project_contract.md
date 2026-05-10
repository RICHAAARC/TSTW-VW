# Project Contract

## Long-Term Goal

鏈」鐩殑闀挎湡鐩爣鏄€愰樁娈垫瀯寤轰竴涓潰鍚?DiT / Flow Matching 瑙嗛鐢熸垚妯″瀷鐨勬椂绌哄悓姝ヨ建杩规按鍗扮爺绌舵鏋讹紝骞朵互缁熶竴 records銆乼hresholds銆乼ables銆乵anifest 鍗忚鏀拺鍚庣画鏈哄埗楠岃瘉涓庤鏂囧疄楠屻€?

## Current Stage

- `project_stage`: `synthetic_tubelet_sync_probe`
- `target_construction_phase`: `real_video_vae_latent_probe`
- 褰撳墠闃舵鍏佽鍦ㄦ棦鏈?protocol core 涓婅繍琛?synthetic video latent銆乼emporal attack matrix 涓?`frame_prc` / `tubelet_only` / `tubelet_sync` 涓変釜姝ｅ紡 method variant銆?
- 褰撳墠闃舵鍏佽瀹炵幇 synthetic / placeholder 椹卞姩鐨勬渶灏?mechanism runtime锛岀敤浜庡喕缁?records銆乼hresholds銆乵anifest銆乼able rebuild 涓庢満鍒惰拷韪彛寰勩€?
- 褰撳墠闃舵鍏佽淇濈暀鍗曚竴 `paper_workflow/Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb` 浣滀负 stage-two transition-preparation 鐨勮繙绋?GPU entrypoint锛屼絾鍏惰亴璐ｄ粎闄愪簬鐜鍑嗗銆侀厤缃啓鍏ャ€佹ā鍧楄皟鐢ㄣ€佺粨鏋滄鏌ヤ笌缁撴灉鎵撳寘銆?
- 褰撳墠闃舵涓嶅緱杩涘叆鐪熷疄 watermark 绠楁硶瀹炵幇銆佺湡瀹?DiT / Flow Matching / VAE 鎺ュ叆銆佺湡瀹炶棰戠敓鎴愭祦绋嬨€?

## Ordered Semantic Stages

1. `protocol_skeleton`
2. `synthetic_tubelet_sync_probe`
3. `real_video_vae_latent_probe`
4. `trajectory_statistic_probe`
5. `trajectory_aware_sampling_probe`
6. `full_paper_protocol`
7. `minimal_release_extraction`

## Core Method Objects

1. `temporal_synchronized_tubelet_code`
2. `flow_matching_trajectory_statistic`
3. `fixed_low_fpr_calibrated_detector`

## Protocol Skeleton Runtime Objects

1. `latent_backend`
2. `watermark_method`
3. `evidence_extractor`
4. `protocol_runner`
5. `threshold_calibrator`
6. `record_writer`
7. `ablation_runner`
8. `table_builder`
9. `manifest_builder`

## Protocol Skeleton Bootstrap Method Variants

1. `empty_watermark_method_placeholder`
2. `random_score_detector_random`

## Evidence Types

1. `tubelet_evidence`
2. `sync_evidence`
3. `trajectory_evidence`
4. `final_evidence`

## Sample Roles

1. `clean_negative`
2. `attacked_negative`
3. `watermarked_positive`
4. `attacked_positive`

## Splits

1. `dev`
2. `calibration`
3. `test`

## Fixed Low-FPR Protocol Rules

1. Thresholds must be calibrated only on `calibration` split data.
2. Calibration negatives must include both `clean_negative` and `attacked_negative`.
3. `test` split must not update thresholds, fusion rules, or calibration statistics.
4. Supported claims must map to tables, curves, or audit-approved evidence outputs.
5. Placeholder fields must never support supported claims.
6. Tables, figures, and reports must remain rebuildable from governed records and manifests.
7. Protocol skeleton runtime outputs must follow the governed `records/`, `thresholds/`, `artifacts/`, and `tables/` layout.

## Core Boundary / Gate Layering

1. Runtime protocol contracts may exist in `main/core/`, `main/protocol/`, and `main/analysis/`; they define split semantics, record schema, threshold calibration, manifests, and rebuildable tables.
2. Outer governance gates may exist only in `tools/harness/`, `.codex/`, `tests/`, and governed docs; they include naming governance, stage progression guards, notebook bypass audits, and skill-file audits.
3. `main/` must not import `tools/harness` or `tests`, and future Codex changes must not move audit logic into runtime protocol code.
4. Governance gates are not part of `method_core`, and future `minimal_release_extraction` must exclude governance harnesses, build-time docs, and audit reports.
5. `protocol_core` must stay method-family agnostic and must not hard-code a specific method factory or a specific latent backend implementation.

## Blocking Governance Rules

### Naming Governance

- All formal names must use `snake_case`.
- Global weak naming such as `stage0`, `stage1`, `stage2`, `stage_0`, `stage_1`, `stage_2`, `stage-0`, `stage-1`, `stage-2`, `*_v1`, `*_v2`, `*_v3`, `*_p0`, `*_p1`, and `*_p2` are blocking violations.
- Future Codex changes must not introduce weak semantic names such as `stage1`, `stage2`, `v1`, or `p1` for formal files, fields, configs, reports, or method variants.
- `method_variant` must use mechanism semantics; `full`, `default`, `new`, `old`, `best`, and `final_method` are blocking violations.

### Placeholder And Random Governance

- Placeholder fields must end with `_placeholder`.
- Random trace fields must end with `_random` or `_digest_random`.
- Every `*_random` field must be reproducible through a seed field, a digest field, or a `*_digest_random` self-contained digest.
- Placeholder fields cannot appear in supported claims.
- New governed fields must be registered in `docs/field_registry.md`.

## Current-Stage Prohibitions

1. Do not implement real watermark embedding or detection algorithms.
2. Do not integrate real DiT backends, Flow Matching backends, or video VAE backends.
3. Do not create notebook-only protocol logic; the governed stage-two Colab entrypoint may exist only when it delegates formal outputs to repository modules.
4. Do not check in formal experiment outputs under `outputs/`; protocol skeleton runtime tests may use temporary output roots or ephemeral `outputs/runs` paths.
5. Do not bypass harness audits or pytest gates.

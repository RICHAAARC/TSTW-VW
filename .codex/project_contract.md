# Project Contract

## Long-Term Goal

本项目的长期目标是逐阶段构建一个面向 DiT / Flow Matching 视频生成模型的时空同步轨迹水印研究框架，并以统一 records、thresholds、tables、manifest 协议支撑后续机制验证与论文实验。

## Current Stage

- `project_stage`: `protocol_skeleton`
- 当前阶段允许构建阶段 0 所需的 `main/` 代码骨架、配置、文档、审计与测试。
- 当前阶段允许实现 placeholder / random 驱动的最小 protocol runtime，用于冻结 records、thresholds、manifest 与 table rebuild 口径。
- 当前阶段不得进入真实算法实现、真实模型接入、真实视频生成流程。

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

## Stage-0 Runtime Skeleton

1. `latent_backend`
2. `watermark_method`
3. `evidence_extractor`
4. `protocol_runner`
5. `threshold_calibrator`
6. `record_writer`
7. `ablation_runner`
8. `table_builder`
9. `manifest_builder`

## Stage-0 Method Variants

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
7. Stage-0 runtime outputs must follow the governed `records/`, `thresholds/`, `artifacts/`, and `tables/` layout.

## Blocking Governance Rules

### Naming Governance

- All formal names must use `snake_case`.
- Stage names such as `stage_0`, `stage_1`, `*_v1`, `*_v2`, `*_p0`, and `*_p1` are blocking violations.
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
3. Do not create notebook-only protocol logic.
4. Do not check in formal experiment outputs under `outputs/`; stage-0 tests may use temporary output roots or ephemeral `outputs/runs` paths.
5. Do not bypass harness audits or pytest gates.

# Project Contract

## Long-Term Goal

本项目的长期目标是逐阶段构建一个面向 DiT / Flow Matching 视频生成模型的时空同步轨迹水印研究框架，并以统一 records、thresholds、tables、manifest 协议支撑后续机制验证与论文实验。

## Current Stage

- `project_stage`: `synthetic_tubelet_sync_probe`
- `target_construction_phase`: `real_video_vae_latent_probe`
- 当前阶段允许在既有 protocol core 上运行 synthetic video latent、temporal attack matrix 与 `frame_prc` / `tubelet_only` / `tubelet_sync` 三个正式 method variant。
- 当前阶段允许实现 synthetic / placeholder 驱动的最小 mechanism runtime，用于冻结 records、thresholds、manifest、table rebuild 与机制追踪口径。
- 当前阶段允许保留单一 `paper_workflow/Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb` 作为 stage-two transition-preparation 的远程 GPU entrypoint，但其职责仅限于环境准备、配置写入、模块调用、结果检查与结果打包。
- 当前阶段不得进入真实 watermark 算法实现、真实 DiT / Flow Matching / VAE 接入、真实视频生成流程。

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
- Global weak naming patterns (regex-based) such as `stage[0-9]+` (stage0, stage1, stage999), `stage_[0-9]+`, `stage-[0-9]+`, `*_v[0-9]+` (*_v1, *_v999), `*_p[0-9]+` (*_p0, *_p999), `test_stage[0-9]+_*`, and `run_stage[0-9]+_*` are blocking violations that apply to any present and future version number.
- Future Codex changes must not introduce weak semantic names for formal files, fields, configs, reports, or method variants.
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

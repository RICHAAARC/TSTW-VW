# Project Contract

## Long-Term Goal

本项目的长期目标是逐阶段构建一个面向 DiT / Flow Matching 视频生成模型的时空同步轨迹水印研究框架，并以统一 records、thresholds、tables、manifest 协议支撑后续机制验证与论文实验。

## Current Stage

- `project_stage`: `paper_artifact_gate`
- `target_construction_phase`: `submission_readiness_gate`
- 当前阶段的文件组织边界以 `docs/file_organization.md` 为准：`main/` 仅保留核心方法、核心协议、核心评估与 CLI 能力；阶段性 runner 位于 `experiments/`；跨 notebook 共享的 Colab / Notebook session 工具位于 `paper_workflow/colab_utils/` 或 `scripts/`；单 notebook 或单阶段专用 helper 位于 `paper_workflow/notebook_utils/`。
- 当前阶段允许在既有 protocol core 上运行 synthetic video latent、temporal attack matrix 与 `frame_prc` / `tubelet_only` / `tubelet_sync` 三个正式 method variant。
- 当前阶段允许实现 synthetic / placeholder 驱动的最小 mechanism runtime，用于冻结 records、thresholds、manifest、table rebuild 与机制追踪口径。
- 当前阶段允许保留受治理的 notebook entrypoints：`paper_workflow/build_processed_real_video_dataset.ipynb` 只负责 raw dataset 到 processed dataset 的构建，`paper_workflow/run_real_video_vae_latent_probe.ipynb` 只负责 processed dataset 与 session model 驱动的 runner / checker / package 调度，`paper_workflow/run_baseline_comparison_gate.ipynb` 只负责 `baseline_comparison_gate` 的 Colab 冷启动 smoke 调度。
- 当前阶段不得进入真实 watermark 算法实现、真实 DiT / Flow Matching / VAE 接入、真实视频生成流程。

## Ordered Semantic Stages

1. `protocol_skeleton`
2. `synthetic_tubelet_sync_probe`
3. `real_video_vae_latent_probe`
4. `baseline_comparison_gate`
5. `paper_artifact_gate`
6. `submission_readiness_gate`
7. `minimal_release_extraction`

### Current Submission-Workflow Alignment

- `synthetic_tubelet_sync_probe` is the closed synthetic mechanism proof stage.
- `real_video_vae_latent_probe` is the closed real-video VAE formal evidence stage, backed by the canonical formal package under `TSTW/results/real_video_vae_latent_probe_stage2_final_formal_audit/real_video_vae_latent_probe_formal_20260611T012845Z_2dbc783/`.
- `baseline_comparison_gate` is the closed external-baseline comparison stage. It compares `tubelet_sync` against `external_videoseal`, `external_rivagan`, and `external_hidden_framewise` under the same split, attack matrix, fixed-FPR calibration, records, tables, and report contracts.
- `paper_artifact_gate` is now the active governed project stage. It owns submission figure data, paper tables, cross-baseline summaries, and claim-audit materialization from governed stage-two and baseline-comparison artifacts.
- `submission_readiness_gate` is the next pre-release paper-readiness gate before `minimal_release_extraction`.
- `trajectory_statistic_probe` and `trajectory_aware_sampling_probe` are deferred research-extension stages and are not part of the current submission-critical stage order.

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

## Test Case Construction Governance

1. Test construction, migration, splitting, merging, markers, fixtures, and runtime-cost classification must follow `docs/test_case_constraints.md`.
2. The governed test directory structure is `tests/constraints/`, `tests/functional/`, `tests/integration/`, with support code in `tests/helpers/` and tiny checked-in fixtures in `tests/fixtures/`.
3. `pytest -q` must default to `constraint`, `unit`, or `quick` tests and must exclude `integration`, `smoke`, `slow`, and `formal` tests unless explicitly selected.
4. Root-level `tests/test_*.py` files are forbidden; every test file must first be classified by validation target and runtime cost.
5. Constraint tests must stay static or lightweight and must not instantiate runners, call `ffmpeg`, write mp4 files, or load VAE/model resources.
6. Functional tests may use tiny fixtures, mock backends, and lightweight temporary I/O; runner-backed, artifact-rebuild, formal, and broad matrix paths belong in `tests/integration/`.
7. Integration tests must carry the `integration` marker; key end-to-end paths also carry `smoke`, formal gate paths carry `formal`, and broad or long paths carry `slow`.
8. Test outputs must use `tmp_path` or `tmp_path_factory`; checked-in formal experiment outputs under `outputs/` remain forbidden.

## Core Boundary / Gate Layering

1. Runtime protocol contracts may exist in `main/core/`, `main/protocol/`, and `main/analysis/`; they define split semantics, record schema, threshold calibration, manifests, and rebuildable tables.
2. Stage-specific runners, experiment artifact builders, and synthetic probe contracts do not belong to `protocol_core`; they must live in `experiments/` and consume `main/` through one-way imports only.
3. Colab / Notebook session wrappers, runtime preflight, reusable Drive packagers, and shared notebook checkers do not belong to `main/`; shared helpers must live in `paper_workflow/colab_utils/` or `scripts/`, while notebook-specific or stage-specific helper wrappers must live in `paper_workflow/notebook_utils/`.
4. Outer governance gates may exist only in `tools/harness/`, `.codex/`, `tests/`, and governed docs; they include naming governance, stage progression guards, notebook bypass audits, file-organization audits, and skill-file audits.
5. `main/` must not import `tools/harness`, `tests`, `paper_workflow`, or `experiments`, and future Codex changes must not move audit logic into runtime protocol code.
6. Governance gates are not part of `method_core`, and future `minimal_release_extraction` must exclude governance harnesses, build-time docs, and audit reports.
7. `protocol_core` must stay method-family agnostic and must not hard-code a specific method factory or a specific latent backend implementation.

## Blocking Governance Rules

### Naming Governance

- All formal names must use `snake_case`.
- Governed notebook entrypoints under `paper_workflow/` must also use `snake_case` semantic names. The current governed notebook entrypoints are `build_processed_real_video_dataset.ipynb`, `run_real_video_vae_latent_probe.ipynb`, and `run_baseline_comparison_gate.ipynb`.
- Governed notebook entrypoints must not append `_Colab`, `_Notebook`, or `Run_` naming noise.
- `paper_workflow/notebook_utils/` 与 `paper_workflow/colab_utils/` 中的 helper 模块都必须使用 `snake_case` 语义命名，且不得使用任何数字阶段缩写、下划线阶段缩写、连字符阶段缩写或 PascalCase 数字阶段缩写形式的弱阶段编号。
- Global weak naming patterns (regex-based) such as `stage[0-9]+` (stage0, stage1, stage999), `stage_[0-9]+`, `stage-[0-9]+`, `*_v[0-9]+` (*_v1, *_v999), `*_p[0-9]+` (*_p0, *_p999), `test_stage[0-9]+_*`, and `run_stage[0-9]+_*` are blocking violations that apply to any present and future version number.
- Future Codex changes must not introduce weak semantic names for formal files, fields, configs, reports, or method variants.
- `method_variant` must use mechanism semantics; `full`, `default`, `new`, `old`, `best`, and `final_method` are blocking violations.

### Placeholder And Random Governance

- Placeholder fields must end with `_placeholder`.
- Random trace fields must end with `_random` or `_digest_random`.
- Every `*_random` field must be reproducible through a seed field, a digest field, or a `*_digest_random` self-contained digest.
- Placeholder fields cannot appear in supported claims.
- New governed fields must be registered in `docs/field_registry.md`.

### Text Encoding Governance

- Checked-in governed text files under `AGENTS.md`, `README.md`, `.gitignore`, `pyproject.toml`, `sitecustomize.py`, `.codex/`, `configs/`, `docs/`, `experiments/`, `main/`, `paper_workflow/`, `scripts/`, `tests/`, and `tools/` must use `UTF-8`.
- Runtime code, harness code, scripts, and tests must explicitly pass `encoding="utf-8"` when repository text I/O APIs support an explicit text encoding.
- Introducing non-`UTF-8` checked-in text files, or relying on local code-page defaults that can reintroduce mojibake, is a blocking violation.
- Project build, notebook, and local development entrypoints must preserve `UTF-8` from editor save, shell startup, Python subprocess I/O, JSON serialization, and test/audit execution.
- Windows development shells must be initialized with UTF-8 console input/output and should set `PYTHONUTF8=1` plus `PYTHONIOENCODING=utf-8` before repository scripts are launched.

## Current-Stage Prohibitions

1. Do not replace the governed internal method variants `frame_prc`, `tubelet_only`, or `tubelet_sync` with an external baseline.
2. Do not use external baseline outputs to support a superiority claim unless the baseline has a recorded license/source/model digest, a governed adapter, fixed-FPR calibration, and aligned attack-matrix records.
3. Do not integrate real DiT, Flow Matching generation, or uncontrolled real video generation backends in `baseline_comparison_gate`.
4. Do not create notebook-only protocol logic; baseline comparison must delegate records, thresholds, tables, reports, and package checks to repository modules.
5. Do not check in formal experiment outputs under `outputs/`; runtime tests must use temporary output roots or ephemeral paths.
6. Do not bypass harness audits, pytest gates, package checks, or claim-audit review.

## Stage-Two Notebook Result Naming And Drive Materialization

- The governed stage-two notebooks must use single-underscore result identifiers for `FAMILY_ID` templates and `PROCESSED_DATASET_KEY` values. Double-underscore separator forms are forbidden for notebook result identities. Valid examples include `real_video_vae_latent_probe_formal_davis2017_trainval480p_utc_time_short_commit` and `real_video_vae_latent_probe_davis2017_trainval480p_256x256_32f_8fps_freeze001`.
- `run_real_video_vae_latent_probe.ipynb` must write its primary run outputs and family package into the Colab session-local runtime first, then materialize the completed family result into `/content/drive/MyDrive/TSTW/results/<WORKFLOW_KEY>/<RUN_ID>_<UTC_TIME>_<SHORT_COMMIT>/` only after the runner, checker, mechanism audit, and packaging steps succeed.
- Notebook workspace preparation must not create an empty Google Drive family result directory before the formal run has produced packageable outputs.
- Stage-two final formal notebook defaults must enable CLIP similarity evidence by setting `TSTW_ENABLE_CLIP_SIMILARITY=1`, while debug review presets may explicitly disable it to control runtime cost.
- If full-run GPU profiling returns `not_sampled`, the notebook may run a separately labeled lightweight GPU profiling smoke fallback to verify the sampling chain without rerunning the formal experiment.



### 2026-06-11 Stage-Two Run Directory Naming Update

- Stage-two real-video notebook Drive materialization must use `/content/drive/MyDrive/TSTW/results/<WORKFLOW_KEY>/<RUN_ID>_<UTC_TIME>_<SHORT_COMMIT>/`.
- `RUN_ID` for Drive and local family result directories must be materialized from `TSTW_RUN_ID_TEMPLATE` or the default `<base_run_id>_utc_time_short_commit`, using the same UTC timestamp and short commit as the formal family identity.
- The fixed session `RUN_ROOT` may remain `/content/TSTW_runtime/runs/real_video_vae_latent_probe_formal`; only the family result directory identity receives the timestamp and commit suffix.


## Baseline Comparison Gate Contract

- Active baseline names are `external_videoseal`, `external_rivagan`, and `external_hidden_framewise`.
- Baseline comparison 的 Drive 结果必须使用 per-baseline 组织结构: `TSTW/results/baseline_comparison_gate/<baseline>/comparison_smoke/<RUN_ID>/` 保存轻量 comparison smoke; `TSTW/results/baseline_comparison_gate/<baseline>/real_smoke/<RUN_ID>/` 保存真实 baseline smoke; `TSTW/results/baseline_comparison_gate/<baseline>/formal_inputs/<RUN_ID>/` 保存该 baseline 使用的输入契约; `TSTW/results/baseline_comparison_gate/<baseline>/scoring_plans/<RUN_ID>/` 保存该 baseline 的 scoring plan; `TSTW/results/baseline_comparison_gate/<baseline>/shard_runs/<RUN_ID>/` 保存该 baseline 的 shard run; `TSTW/results/baseline_comparison_gate/<baseline>/shard_aggregated/<RUN_ID>/` 保存该 baseline 的 shard aggregation。
- 每个单 baseline formal input、scoring plan 和 shard run 结果包都必须包含 `configs/baseline_comparison_formal_input_contract.json` 快照, 使单独下载某个 baseline 结果目录时仍可独立审计。
- Every baseline must use the same real-video processed dataset identity, split semantics, attack matrix, target-FPR calibration rule, and table/report rebuild contract as the canonical `real_video_vae_latent_probe` formal package.
- Baseline records must preserve `baseline_name`, `baseline_family`, `baseline_score`, `baseline_raw_detector_output`, `decision`, `failure_reason`, `quality_metrics`, `temporal_metrics`, `runtime_metrics`, and `baseline_trace`.
- `baseline_trace` must include source digest, model digest, adapter version, score mapping rule, unsupported attack reason when applicable, and license or availability status.
- A baseline with incomplete legal, model, environment, or attack support may appear only in `baseline_limitation_report.md`; it must not support a positive superiority claim.
- Passing this gate requires `baseline_comparison_table.csv`, `baseline_attack_breakdown.csv`, `baseline_threshold_table.csv`, `baseline_runtime_table.csv`, `baseline_limitation_report.md`, and a claim-audit update showing that all supported baseline claims map to governed artifacts.

## Paper Artifact Gate Contract

- `paper_artifact_gate` must consume only governed stage-two aggregation packages and governed per-baseline `baseline_comparison_gate/<baseline>/shard_aggregated/` results.
- It may generate paper-facing tables, figure data, reports, manifests, and claim-audit tables under `TSTW/results/paper_artifact_gate/<RUN_ID>/`.
- Paper artifacts must remain rebuildable from the source records, tables, thresholds, reports, and manifests recorded in `artifacts/paper_artifact_gate_manifest.json`.
- Manual paper table assembly is forbidden; cross-baseline and sync-gain tables must be generated by repository code.
- Supported claims must map to `tables/paper_method_comparison_table.csv`, `tables/paper_sync_gain_table.csv`, `tables/paper_external_baseline_table.csv`, `figure_data/`, or `claim_audit/paper_claim_audit.csv`.
- Passing this gate requires `paper_method_comparison_table.csv`, `paper_attack_breakdown_table.csv`, `paper_sync_gain_table.csv`, `paper_external_baseline_table.csv`, `paper_roc_auc_table.csv`, `paper_quality_table.csv`, `paper_runtime_efficiency_table.csv`, `paper_visual_example_figure_data.csv`, exported PNG/PDF paper figures including the visual example grid when shard-run videos are available, `paper_claim_audit.csv`, `paper_submission_gap_audit.csv`, `paper_figure_manifest.json`, and `paper_artifact_gate_manifest.json`.

## Shard Notebook Split Contract

- shard run 与 shard aggregation 必须拆分为独立 Notebook: `run_real_video_vae_latent_probe.ipynb` 与 `run_baseline_comparison_gate.ipynb` 只负责分片运行, `aggregate_real_video_vae_latent_probe_shards.ipynb` 与 `aggregate_baseline_comparison_gate_shards.ipynb` 只负责聚合分片结果。

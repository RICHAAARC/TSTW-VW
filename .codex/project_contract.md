# Project Contract

## Long-Term Goal

本项目的长期目标是逐阶段构建一个面向 DiT / Flow Matching 视频生成模型的时空同步轨迹水印研究框架，并以统一 records、thresholds、tables、manifest 协议支撑后续机制验证与论文实验。

## Current Stage

- `project_stage`: `synthetic_tubelet_sync_probe`
- `target_construction_phase`: `real_video_vae_latent_probe`
- 当前阶段的文件组织边界以 `docs/file_organization.md` 为准：`main/` 仅保留核心方法、核心协议、核心评估与 CLI 能力；阶段性 runner 位于 `experiments/`；跨 notebook 共享的 Colab / Notebook session 工具位于 `paper_workflow/colab_utils/` 或 `scripts/`；单 notebook 或单阶段专用 helper 位于 `paper_workflow/notebook_utils/`。
- 当前阶段允许在既有 protocol core 上运行 synthetic video latent、temporal attack matrix 与 `frame_prc` / `tubelet_only` / `tubelet_sync` 三个正式 method variant。
- 当前阶段允许实现 synthetic / placeholder 驱动的最小 mechanism runtime，用于冻结 records、thresholds、manifest、table rebuild 与机制追踪口径。
- 当前阶段允许保留受治理的 notebook entrypoint workflow：`paper_workflow/build_processed_real_video_dataset.ipynb` 只负责 raw dataset 到 processed dataset 的构建，`paper_workflow/run_real_video_vae_latent_probe.ipynb` 只负责 processed dataset 与 session model 驱动的 runner / checker / package 调度，`paper_workflow/run_trajectory_statistic_probe.ipynb` 只负责 Colab GPU 环境中的 trajectory formal replay CLI 调度与整体 run package handoff。
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
- Governed notebook entrypoints under `paper_workflow/` must also use `snake_case` semantic names, and the current governed notebook workflow is frozen to `build_processed_real_video_dataset.ipynb`, `run_real_video_vae_latent_probe.ipynb`, and `run_trajectory_statistic_probe.ipynb`.
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

1. Do not implement real watermark embedding or detection algorithms.
2. Do not integrate real DiT backends, Flow Matching backends, or video VAE backends.
3. Do not create notebook-only protocol logic; governed Colab entrypoints may exist only when they delegate formal outputs to repository modules, and `run_trajectory_statistic_probe.ipynb` may only call repository helper / CLI code for GPU validation.
4. Do not check in formal experiment outputs under `outputs/`; protocol skeleton runtime tests may use temporary output roots or ephemeral `outputs/runs` paths.
5. Do not bypass harness audits or pytest gates.

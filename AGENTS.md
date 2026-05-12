# Repository Agent Contract

1. Before any modification, read `.codex/project_contract.md`.
2. Before any modification, read the relevant skill file under `.codex/skills/`.
3. This repository is now in the governed `synthetic_tubelet_sync_probe` stage.
4. Current-stage runtime work may use synthetic video latent data, the governed temporal attack matrix, and the formal method variants `frame_prc`, `tubelet_only`, and `tubelet_sync`.
5. Current-stage runtime work may implement only the minimum synthetic / placeholder-driven mechanism runtime needed to freeze records, thresholds, manifests, table rebuilds, and mechanism traces.
6. Real DiT, Flow Matching, video VAE, real video generation, and real watermark algorithm integration are forbidden in the current stage.
7. Bypassing harness audits is forbidden.
8. Ambiguous stage naming patterns such as `*_v[0-9]+`, `*_p[0-9]+`, `stage[0-9]+`, `stage_[0-9]+`, `stage-[0-9]+`, `test_stage[0-9]+_*`, or `run_stage[0-9]+_*` are forbidden throughout governed code, notebook, script, and helper paths.
9. All placeholder fields must end with `_placeholder`.
10. All random-trace fields must end with `_random` or `_digest_random`.
11. Placeholder fields cannot support supported claims; supported claims must map to governed records, thresholds, tables, curves, reports, or manifests.
12. Checked-in formal experiment outputs under `outputs/` are forbidden in the current stage; runtime tests should use temporary output roots or ephemeral paths.
13. A governed two-notebook workflow may exist for transition preparation: `paper_workflow/build_processed_real_video_dataset.ipynb` and `paper_workflow/run_real_video_vae_latent_probe.ipynb` must delegate formal outputs to repository modules and must not direct-write records, thresholds, tables, figures, or reports.
14. Current result status: synthetic_tubelet_sync_probe primary proof and formal runs can close `primary_stage1_completion_pass`, `primary_strict_target_fpr_pass`, rebuildability, and the governed temporal-crop/local-clip sync-rescue gain. Tiny remains engineering smoke only, checked-in formal outputs under `outputs/` remain forbidden, and speed-change scale search is implemented but not validated as a resolved attack. Progression to `real_video_vae_latent_probe` still requires an explicit governed stage-transition decision based on fresh proof/formal records with `primary_stage1_completion_pass=true`, `tubelet_sync_beats_tubelet_only_under_temporal_crop_or_local_clip=true`, `primary_strict_target_fpr_pass=true`, and records-to-tables/curves/report all true.
15. Test additions, migrations, markers, fixtures, and output paths must follow `docs/test_case_constraints.md`; root-level `tests/test_*.py` files are forbidden, and default pytest must stay limited to `constraint`, `unit`, or `quick` tests.
16. Task completion requires running `pytest -q` when available, or `python -m pytest -q` when the pytest console script is unavailable, and `python tools/harness/run_all_audits.py`.

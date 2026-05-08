# Repository Agent Contract

1. Before any modification, read `.codex/project_contract.md`.
2. Before any modification, read the relevant skill file under `.codex/skills/`.
3. This repository is now in the governed `synthetic_tubelet_sync_probe` stage.
4. Current-stage runtime work may use synthetic video latent data, the governed temporal attack matrix, and the formal method variants `frame_prc`, `tubelet_only`, and `tubelet_sync`.
5. Current-stage runtime work may implement only the minimum synthetic / placeholder-driven mechanism runtime needed to freeze records, thresholds, manifests, table rebuilds, and mechanism traces.
6. Real DiT, Flow Matching, video VAE, real video generation, and real watermark algorithm integration are forbidden in the current stage.
7. Bypassing harness audits is forbidden.
8. Ambiguous stage naming such as `*_v1`, `*_v2`, `*_p0`, `*_p1`, `stage_0`, or `stage_1` is forbidden.
9. All placeholder fields must end with `_placeholder`.
10. All random-trace fields must end with `_random` or `_digest_random`.
11. Placeholder fields cannot support supported claims; supported claims must map to governed records, thresholds, tables, curves, reports, or manifests.
12. Checked-in formal experiment outputs under `outputs/` are forbidden in the current stage; runtime tests should use temporary output roots or ephemeral paths.
13. Current result status: the synthetic tubelet/sync engineering loop, artifact rebuild path, proof profile, and formal profile are implemented and audit-tested. Current mechanism evidence does not yet support a completed stage-1 claim: recent proof/formal reruns can generate complete records, tables, curves, figures, and `method_validation_report.md`, and `tubelet_sync` does not show attacked-negative FPR loss of control, but `closure_target_pass` is not stable and Tubelet+Sync does not consistently beat `tubelet_only` under temporal crop or local clip. Progression to `real_video_vae_latent_probe` is not yet eligible; it requires an explicit governed stage-transition decision after the stage-1 mechanism checks pass under governed records.
14. Task completion requires running `pytest -q` when available, or `python -m pytest -q` when the pytest console script is unavailable, and `python tools/harness/run_all_audits.py`.

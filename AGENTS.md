# Repository Agent Contract

1. Before any modification, read `.codex/project_contract.md`.
2. Before any modification, read the relevant skill file under `.codex/skills/`.
3. This repository is now in the governed `protocol_skeleton` stage; stage-0 code skeletons under `main/`, `configs/`, `docs/`, `tools/`, and `tests/` are allowed, but only for placeholder / random protocol scaffolding.
4. Real DiT or Flow Matching integration is forbidden in the current stage.
5. Real watermark algorithm implementation is forbidden in the current stage.
6. Bypassing harness audits is forbidden.
7. Ambiguous stage naming such as `*_v1`, `*_v2`, `*_p0`, `*_p1`, `stage_0`, or `stage_1` is forbidden.
8. All placeholder fields must end with `_placeholder`.
9. All random-trace fields must end with `_random` or `_digest_random`.
10. Checked-in formal experiment outputs under `outputs/` are forbidden in the current stage; runtime tests should use temporary output roots or ephemeral paths.
11. Task completion requires running `pytest -q` and `python tools/harness/run_all_audits.py`.

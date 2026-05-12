# Test Fixtures

This directory is reserved for small, checked-in test fixtures only.

Allowed fixture classes:

- `static`: tiny JSON, Markdown, or schema samples for constraint tests.
- `tiny_video`: minimal video/frame payloads for quick functional tests.
- `mock_model`: fake model metadata or mock backend payloads.
- `run_roots`: tiny synthetic run-root examples that do not contain formal outputs.

Generated artifacts must use `tmp_path` or `tmp_path_factory`, not this directory.

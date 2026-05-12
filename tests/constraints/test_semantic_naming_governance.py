"""
File purpose: Validate semantic naming governance rules.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

from pathlib import Path

from tools.harness.lib.naming_rules import (
    find_forbidden_version_like_names,
    find_forbidden_weak_stage_names,
    validate_path_name_semantics,
)


def test_reject_forbidden_weak_path_names() -> None:
    assert validate_path_name_semantics(Path("main/protocol/stage2_runner.py"))
    assert validate_path_name_semantics(Path("main/analysis/stage2_artifacts.py"))
    assert validate_path_name_semantics(Path("tests/test_stage2_records_schema.py"))
    assert validate_path_name_semantics(Path("tools/harness/run_stage1_profile.py"))


def test_reject_forbidden_weak_text_names() -> None:
    assert "stage1" in find_forbidden_weak_stage_names("stage1 temporal attack")
    assert "stage_2" in find_forbidden_weak_stage_names("stage_2 temporal attack")
    assert "protocol_skeleton_v1" in find_forbidden_version_like_names("protocol_skeleton_v1")


def test_accept_semantic_names() -> None:
    assert validate_path_name_semantics(Path("experiments/real_video_vae_latent_probe/runner.py")) == []
    assert validate_path_name_semantics(Path("experiments/real_video_vae_latent_probe/artifact_builder.py")) == []
    assert validate_path_name_semantics(Path("tests/test_real_video_vae_latent_records_schema.py")) == []
    assert validate_path_name_semantics(Path("tools/harness/run_synthetic_tubelet_sync_profile.py")) == []


def test_allow_compatibility_and_technical_versions() -> None:
    assert find_forbidden_version_like_names("schema_version") == []
    assert find_forbidden_version_like_names("compatibility_version") == []
    assert find_forbidden_version_like_names("legacy_stage_id") == []
    assert find_forbidden_version_like_names("Python 3.11") == []
    assert find_forbidden_version_like_names("CUDA 12.1") == []

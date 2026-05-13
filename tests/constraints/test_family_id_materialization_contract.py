"""
文件用途：验证 family_id 模板占位符会被物化为真实 UTC 时间与 short commit。
File purpose: Validate that family-id template placeholders are materialized into UTC timestamp and short commit.
Module type: General module
"""

from __future__ import annotations

import re

import pytest

from paper_workflow.notebook_utils.real_video_vae_latent_probe_workflow import (
    materialize_family_id,
)


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_materialize_family_id_replaces_template_placeholders() -> None:
    """Validate family-id template tokens are replaced.

    Args:
        None.

    Returns:
        None.
    """
    family_id = materialize_family_id(
        family_id_template=(
            "real_video_vae_latent_probe__formal__davis2017_trainval480p__"
            "utc_time__short_commit"
        ),
        git_commit="ef99828abc123456",
        utc_timestamp="2026-05-13T01:51:16Z",
    )

    assert "utc_time" not in family_id
    assert "short_commit" not in family_id
    assert "template" not in family_id
    assert family_id.endswith("__20260513T015116Z__ef99828")
    assert re.fullmatch(
        r"real_video_vae_latent_probe__formal__davis2017_trainval480p__\d{8}T\d{6}Z__[a-z0-9_]+",
        family_id,
    )


def test_materialize_family_id_uses_unknown_commit_when_git_commit_missing() -> None:
    """Validate missing git commit materializes to unknown_commit.

    Args:
        None.

    Returns:
        None.
    """
    family_id = materialize_family_id(
        family_id_template="probe__formal__dataset__utc_time__short_commit",
        git_commit="",
        utc_timestamp="20260513T015116Z",
    )

    assert family_id.endswith("__20260513T015116Z__unknown_commit")
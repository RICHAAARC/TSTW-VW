"""
文件用途：提供测试套件共享 fixture。
File purpose: Provide shared fixtures for the layered test suite.
Module type: Test support module
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def session_tmp_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return the session-scoped temporary root for reusable test artifacts."""
    return tmp_path_factory.mktemp("tstw_session_artifacts")

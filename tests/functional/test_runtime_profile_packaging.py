"""
文件用途：验证结果打包器会纳入 runtime_profile 目录。
File purpose: Validate that packagers include the runtime_profile directory.
Module type: Functional test module
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.package_results.package_real_video_vae_latent_outputs import (
    _append_runtime_profile_to_zip,
)


pytestmark = pytest.mark.quick


@pytest.mark.unit
def test_runtime_profile_packaging_appends_runtime_profile_tree_to_zip(tmp_path: Path) -> None:
    """Validate runtime_profile artifacts are appended into the compatibility zip.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    runtime_profile_dir = run_root / "runtime_profile"
    runtime_profile_dir.mkdir(parents=True, exist_ok=True)
    (runtime_profile_dir / "runtime_profile_plan.json").write_text("{}\n", encoding="utf-8")
    (runtime_profile_dir / "gpu_runtime_summary.json").write_text("{}\n", encoding="utf-8")
    zip_path = tmp_path / "family.zip"

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED):
        pass

    _append_runtime_profile_to_zip(
        zip_path=zip_path,
        run_root=run_root,
    )

    with zipfile.ZipFile(zip_path, mode="r") as archive:
        names = sorted(archive.namelist())

    assert f"{run_root.name}/runtime_profile/runtime_profile_plan.json" in names
    assert f"{run_root.name}/runtime_profile/gpu_runtime_summary.json" in names

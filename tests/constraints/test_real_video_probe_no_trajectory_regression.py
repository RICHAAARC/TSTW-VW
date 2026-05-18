"""
文件用途：验证 real_video_vae_latent_probe 默认路径未被 trajectory scaffold 污染。
File purpose: Validate that the real_video_vae_latent_probe default path remains free of trajectory scaffold pollution.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

from main.core.registry import load_json_config


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


ROOT = Path(__file__).resolve().parents[2]


def test_default_method_variants_keep_trajectory_disabled() -> None:
    """Validate that the checked-in default method variants still disable trajectory evidence.

    Args:
        None.

    Returns:
        None.
    """
    for method_variant in ("frame_prc", "tubelet_only", "tubelet_sync"):
        method_config = load_json_config(ROOT / "configs" / "method" / f"{method_variant}.json")
        assert method_config["enable_trajectory"] is False


def test_real_video_probe_runtime_files_do_not_import_trajectory_scaffold() -> None:
    """Validate that the real-video probe runtime files do not import trajectory scaffold modules.

    Args:
        None.

    Returns:
        None.
    """
    runtime_files = [
        ROOT / "experiments" / "real_video_vae_latent_probe" / "runner.py",
        ROOT / "experiments" / "real_video_vae_latent_probe" / "artifact_builder.py",
        ROOT / "main" / "backends" / "real_video_vae_latent.py",
    ]
    forbidden_import_snippets = [
        "import main.trajectory",
        "from main.trajectory",
        "import experiments.trajectory_statistic_probe",
        "from experiments.trajectory_statistic_probe",
    ]
    for file_path in runtime_files:
        text = file_path.read_text(encoding="utf-8")
        for forbidden_import_snippet in forbidden_import_snippets:
            assert forbidden_import_snippet not in text
"""
文件用途：验证 family package metadata 与实际 canonical archive 一致。
File purpose: Validate that family package metadata matches the canonical tar.zst archive.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.package_results.package_real_video_vae_latent_tar_zst as tar_packager_module

from scripts.package_results.package_real_video_vae_latent_tar_zst import (
    package_real_video_vae_latent_tar_zst,
)


pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_family_package_metadata_uses_tar_zst_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate canonical family metadata points at the tar.zst package.

    Args:
        tmp_path: Temporary output root.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    for relative_path in (
        "records",
        "thresholds",
        "tables",
        "figures",
        "reports",
        "failure_case_gallery",
        "logs",
        "artifacts",
        "runtime_profile",
    ):
        (run_root / relative_path).mkdir(parents=True, exist_ok=True)
    (run_root / "artifacts" / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": "real_video_vae_latent_probe_formal",
                "construction_phase": "real_video_vae_latent_probe",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "artifacts" / "stage2_mechanism_decision.json").write_text(
        json.dumps(
            {
                "Stage2ImplementationDecision": "PASS",
                "Stage2MechanismDecision": "INCONCLUSIVE",
                "Stage2MechanismBlockingReasons": ["sample_count_insufficient"],
                "NextAllowedStageByImplementation": "trajectory_statistic_probe",
                "NextAllowedStageByMechanism": "remain_in_real_video_vae_latent_probe",
                "RecommendedNextAction": "stage2_mechanism_calibration_run"
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    family_root = tmp_path / "family"

    monkeypatch.setattr(
        tar_packager_module,
        "check_real_video_vae_latent_outputs",
        lambda **kwargs: {
            "run_id": "real_video_vae_latent_probe_formal",
            "construction_phase": "real_video_vae_latent_probe",
            "RealVideoVaeLatentDecision": "PASS",
            "status": True,
            "formal_checks": {"status": True},
        },
    )

    package_real_video_vae_latent_tar_zst(
        run_root=run_root,
        family_root=family_root,
        require_formal_pass_criteria=False,
    )

    family_manifest = json.loads((family_root / "family_manifest.json").read_text(encoding="utf-8"))
    family_summary = json.loads((family_root / "family_summary.json").read_text(encoding="utf-8"))

    assert family_manifest["package_format"] == "tar.zst"
    assert family_manifest["archive_format"] == "tar.zst"
    assert family_manifest["package_path"].endswith(".tar.zst")
    assert family_manifest["archive_path"].endswith(".tar.zst")
    assert Path(family_manifest["package_path"]).name == "real_video_vae_latent_probe_formal.tar.zst"
    assert family_summary["package_format"] == "tar.zst"
    assert family_summary["archive_format"] == "tar.zst"
    assert family_summary["package_path"].endswith(".tar.zst")
    assert family_summary["archive_path"].endswith(".tar.zst")
    assert family_summary["Stage2ImplementationDecision"] == "PASS"
    assert family_summary["Stage2MechanismDecision"] == "INCONCLUSIVE"
    assert family_summary["RecommendedNextAction"] == "stage2_mechanism_calibration_run"

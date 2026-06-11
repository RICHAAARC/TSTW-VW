"""验证阶段二 real-video VAE 结果包输入检查器。"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from experiments.baseline_comparison_gate.stage_two_package import (
    extract_stage_two_zip_package,
    inspect_stage_two_package,
)

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def write_fake_stage_two_package(root: Path, *, lpips: bool = True, clip: bool = True) -> Path:
    """写出一个最小阶段二结果包, 用于测试检查逻辑而不携带真实实验数据。"""
    package_root = root / "real_video_vae_latent_probe_formal_20260611T012845Z_2dbc783"
    packages = package_root / "packages"
    packages.mkdir(parents=True)
    family_checks = {
        "status": True,
        "formal_checks": {
            "status": True,
            "lpips_evidence_available": lpips,
        },
        "stage2_mechanism_summary": {
            "run_id": "real_video_vae_latent_probe_formal",
            "Stage2ImplementationDecision": "PASS",
            "Stage2MechanismDecision": "PASS",
            "quality_metrics_enabled": {
                "psnr": True,
                "ssim": True,
                "lpips": lpips,
                "clip_similarity": clip,
            },
        },
    }
    family_manifest = {"family_id": "real_video_vae_latent_probe_formal_20260611T012845Z_2dbc783"}
    family_summary = {
        "family_id": family_manifest["family_id"],
        "formal_validation_summary": {"record_count": 4200, "threshold_count": 3},
    }
    (package_root / "family_checks.json").write_text(json.dumps(family_checks), encoding="utf-8")
    (package_root / "family_manifest.json").write_text(json.dumps(family_manifest), encoding="utf-8")
    (package_root / "family_summary.json").write_text(json.dumps(family_summary), encoding="utf-8")

    archive_path = packages / "real_video_vae_latent_probe_formal.zip"
    prefix = "real_video_vae_latent_probe_formal"
    required_files = [
        "records/event_scores.jsonl",
        "thresholds/thresholds.json",
        "tables/main_tpr_fpr_table.csv",
        "tables/real_video_attack_breakdown.csv",
        "tables/quality_table.csv",
        "tables/temporal_consistency_table.csv",
        "artifacts/run_manifest.json",
        "artifacts/runtime_config.json",
        "artifacts/artifact_manifest.json",
        "artifacts/runtime_manifest.json",
    ]
    with zipfile.ZipFile(archive_path, "w") as archive:
        for relative_path in required_files:
            archive.writestr(f"{prefix}/{relative_path}", "{}\n")
    return package_root


def test_stage_two_package_inspection_accepts_ready_package(tmp_path: Path) -> None:
    """确认 LPIPS、CLIP 和关键文件齐全的阶段二包可作为阶段三输入。"""
    package_root = write_fake_stage_two_package(tmp_path)

    summary = inspect_stage_two_package(package_root)

    assert summary["package_ready_for_baseline_comparison"] is True
    assert summary["rerun_real_video_vae_required"] is False
    assert summary["record_count"] == 4200
    assert summary["threshold_count"] == 3
    assert all(summary["required_paths"].values())


def test_stage_two_package_inspection_rejects_missing_clip(tmp_path: Path) -> None:
    """确认 CLIP similarity 未启用时不能进入正式 baseline comparison。"""
    package_root = write_fake_stage_two_package(tmp_path, clip=False)

    summary = inspect_stage_two_package(package_root)

    assert summary["package_ready_for_baseline_comparison"] is False
    assert summary["rerun_real_video_vae_required"] is True
    assert summary["metrics_ready"] is False


def test_stage_two_package_extracts_zip_to_session_root(tmp_path: Path) -> None:
    """确认检查通过后可以把 zip 兼容包解压到会话本地目录。"""
    package_root = write_fake_stage_two_package(tmp_path)
    extract_root = tmp_path / "session_inputs"

    summary = extract_stage_two_zip_package(package_root=package_root, extract_root=extract_root)

    extracted_root = Path(summary["extracted_package_root"])
    assert summary["extracted"] is True
    assert (extracted_root / "records" / "event_scores.jsonl").exists()

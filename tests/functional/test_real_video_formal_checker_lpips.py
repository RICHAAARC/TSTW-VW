"""
文件用途：验证 real_video_vae_latent_probe formal checker 的 LPIPS 证据门禁。
File purpose: Validate the LPIPS evidence gate in the real-video VAE latent formal checker.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.quick]

from main.core.digest import compute_file_digest
from scripts.check_results.real_video_vae_latent_output_checker import (
    _perform_formal_checks,
)


def test_formal_checker_blocks_missing_lpips_evidence(tmp_path: Path) -> None:
    """验证 formal checker 会阻断缺失 LPIPS 数值证据的结果。

    Args:
        tmp_path: 临时运行目录。

    Returns:
        None.
    """
    record = _build_formal_checker_record(tmp_path, watermarked_video_lpips=None)

    checks = _perform_formal_checks(
        event_score_records=[record],
        artifact_manifest=_build_artifact_manifest(),
        run_manifest={"placeholder_fields": [], "random_fields": ["latent_generation_seed_random"]},
        run_root=tmp_path,
        require_formal_pass_criteria=True,
        real_video_vae_latent_decision="PASS",
        next_allowed_stage="trajectory_statistic_probe",
    )

    assert checks["status"] is False
    assert checks["has_real_quality_metrics"] is True
    assert checks["lpips_evidence_available"] is False
    assert checks["details"]["lpips_record_count"] == 0


def test_formal_checker_accepts_numeric_lpips_evidence(tmp_path: Path) -> None:
    """验证 formal checker 在其他 formal 条件满足时接受数值型 LPIPS 证据。

    Args:
        tmp_path: 临时运行目录。

    Returns:
        None.
    """
    record = _build_formal_checker_record(tmp_path, watermarked_video_lpips=0.123)

    checks = _perform_formal_checks(
        event_score_records=[record],
        artifact_manifest=_build_artifact_manifest(),
        run_manifest={"placeholder_fields": [], "random_fields": ["latent_generation_seed_random"]},
        run_root=tmp_path,
        require_formal_pass_criteria=True,
        real_video_vae_latent_decision="PASS",
        next_allowed_stage="trajectory_statistic_probe",
    )

    assert checks["status"] is True
    assert checks["lpips_evidence_available"] is True
    assert checks["details"]["lpips_record_count"] == 1


def test_formal_checker_rejects_boolean_lpips_evidence(tmp_path: Path) -> None:
    """验证 formal checker 不接受布尔型 LPIPS 字段作为数值证据。

    Args:
        tmp_path: 临时运行目录。

    Returns:
        None.
    """
    record = _build_formal_checker_record(tmp_path, watermarked_video_lpips=True)

    checks = _perform_formal_checks(
        event_score_records=[record],
        artifact_manifest=_build_artifact_manifest(),
        run_manifest={"placeholder_fields": [], "random_fields": ["latent_generation_seed_random"]},
        run_root=tmp_path,
        require_formal_pass_criteria=True,
        real_video_vae_latent_decision="PASS",
        next_allowed_stage="trajectory_statistic_probe",
    )

    assert checks["status"] is False
    assert checks["lpips_evidence_available"] is False
    assert checks["details"]["lpips_record_count"] == 0


def _build_formal_checker_record(
    run_root: Path,
    *,
    watermarked_video_lpips: float | bool | None,
) -> dict[str, object]:
    """构造满足 formal checker 其他条件的最小 event record。

    Args:
        run_root: 临时运行目录。
        watermarked_video_lpips: 要写入记录的 LPIPS 数值或 None。

    Returns:
        可直接传入 formal checker 的 event record。
    """
    reencoded_path = run_root / "artifacts" / "latents" / "sample_reencoded.npy"
    reencoded_path.parent.mkdir(parents=True, exist_ok=True)
    reencoded_path.write_bytes(b"reencoded-latent")
    return {
        "attack_name": "h264_compression",
        "mechanism_trace": {
            "video_runtime_status": "real_mp4_runtime",
            "vae_backend_name": "diffusers_autoencoder_kl_framewise",
            "quality_metrics_runtime": "real_video_frame_metrics",
            "temporal_metrics_runtime": "real_video_frame_metrics",
            "video_container": "mp4",
            "attacked_video_relpath": "artifacts/videos/sample_attacked.mp4",
            "reencoded_latent_relpath": "artifacts/latents/sample_reencoded.npy",
            "reencoded_latent_digest": compute_file_digest(reencoded_path),
        },
        "quality_metrics": {
            "watermarked_video_lpips": watermarked_video_lpips,
        },
    }


def _build_artifact_manifest() -> list[dict[str, object]]:
    """构造包含真实 mp4 artifact 的最小 manifest。

    Args:
        None.

    Returns:
        artifact manifest entries。
    """
    return [
        {
            "artifact_kind": "attacked_video",
            "relpath": "artifacts/videos/sample_attacked.mp4",
        }
    ]

"""
文件用途：验证 real-video VAE latent run scale estimator 的输出合同。
File purpose: Validate output contracts for the real-video VAE latent run scale estimator.
Module type: Functional test module
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.profile_runtime.estimate_real_video_vae_latent_run_scale import (
    estimate_real_video_vae_latent_run_scale,
)


pytestmark = pytest.mark.quick

ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_run_scale_estimator_reports_event_and_split_counts(tmp_path: Path) -> None:
    """Validate the estimator reports event counts and split counts.

    Args:
        tmp_path: Temporary test root.

    Returns:
        None.
    """
    dataset_manifest = tmp_path / "dataset_manifest.json"
    attack_matrix = tmp_path / "attack_matrix.json"
    ablation_config = tmp_path / "ablation_config.json"
    output_json = tmp_path / "runtime_profile" / "run_scale_estimate.json"

    _write_json(
        dataset_manifest,
        {
            "samples": [
                {"sample_id": "a", "split": "calibration"},
                {"sample_id": "b", "split": "test"},
                {"sample_id": "c", "split": "test"},
            ]
        },
    )
    _write_json(attack_matrix, {"attacks": [{"name": "identity"}, {"name": "crop"}]})
    _write_json(
        ablation_config,
        {
            "method_variants_by_profile": {
                "formal": ["frame_prc", "tubelet_sync"],
            }
        },
    )

    payload = estimate_real_video_vae_latent_run_scale(
        dataset_manifest=dataset_manifest,
        attack_matrix=attack_matrix,
        ablation_config=ablation_config,
        runtime_profile="formal",
        output_json=output_json,
    )

    assert payload["status"] is True
    assert payload["video_count_total"] == 3
    assert payload["video_count_by_split"] == {"calibration": 1, "test": 2}
    assert payload["attack_count"] == 2
    assert payload["method_variant_count"] == 2
    assert payload["estimated_event_count"] == 18
    assert output_json.exists()


def test_run_scale_estimator_cli_fails_for_missing_inputs(tmp_path: Path) -> None:
    """Validate the CLI returns a non-zero exit code when required inputs are missing.

    Args:
        tmp_path: Temporary test root.

    Returns:
        None.
    """
    output_json = tmp_path / "runtime_profile" / "run_scale_estimate.json"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.profile_runtime.estimate_real_video_vae_latent_run_scale",
            "--dataset-manifest",
            str(tmp_path / "missing_dataset_manifest.json"),
            "--attack-matrix",
            str(tmp_path / "missing_attack_matrix.json"),
            "--ablation-config",
            str(tmp_path / "missing_ablation_config.json"),
            "--runtime-profile",
            "formal",
            "--output-json",
            str(output_json),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert completed.returncode == 1
    assert payload["status"] is False
    assert "missing_required_config:dataset_manifest" in payload["warnings"]

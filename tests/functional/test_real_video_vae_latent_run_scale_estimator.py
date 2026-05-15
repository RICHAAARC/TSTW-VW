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


def test_run_scale_estimator_reports_runner_semantic_counts_and_time_window(tmp_path: Path) -> None:
    """Validate the estimator exposes runner-aware counts for notebook planning.

    Args:
        tmp_path: Temporary test root.

    Returns:
        None.
    """
    dataset_manifest = tmp_path / "dataset_manifest.json"
    attack_matrix = tmp_path / "attack_matrix.json"
    ablation_root = tmp_path / "configs" / "ablation"
    method_root = tmp_path / "configs" / "method"
    protocol_root = tmp_path / "configs" / "protocol"
    ablation_config = ablation_root / "ablation_config.json"
    protocol_config = protocol_root / "protocol_config.json"
    output_json = tmp_path / "runtime_profile" / "run_scale_estimate.json"

    _write_json(
        dataset_manifest,
        {
            "samples": [
                {"sample_id": "dev_a", "split": "dev"},
                {"sample_id": "cal_a", "split": "calibration"},
                {"sample_id": "test_a", "split": "test"},
            ]
        },
    )
    _write_json(
        attack_matrix,
        {
            "attack_names_by_profile": {
                "formal": ["no_attack", "h264_compression", "local_clip"],
            },
            "attacks": [
                {"attack_name": "no_attack", "attack_params": {}},
                {"attack_name": "h264_compression", "attack_params": {"crf": 28}},
                {"attack_name": "local_clip", "attack_params": {"clip_lengths": [4, 8]}},
            ],
        },
    )
    _write_json(method_root / "tubelet_only.json", {"tubelet_length": 4})
    _write_json(
        ablation_config,
        {
            "method_variants": ["frame_prc", "tubelet_only", "tubelet_sync"],
            "method_variants_by_profile": {
                "formal": ["frame_prc", "tubelet_only", "tubelet_sync"],
            },
            "tubelet_length_sweep_variant": "tubelet_only",
            "tubelet_length_sweep_formal": [1, 2, 4, 8],
        },
    )
    _write_json(
        protocol_config,
        {
            "splits": ["dev", "calibration", "test"],
            "sample_roles": [
                "clean_negative",
                "attacked_negative",
                "watermarked_positive",
                "attacked_positive",
            ],
            "samples_per_role_by_profile": {"formal": 20},
        },
    )

    payload = estimate_real_video_vae_latent_run_scale(
        dataset_manifest=dataset_manifest,
        attack_matrix=attack_matrix,
        ablation_config=ablation_config,
        runtime_profile="formal",
        output_json=output_json,
        protocol_config=protocol_config,
        samples_per_role_override=1,
        execution_runtime_profile="l4_debug",
        batch_size_frames=4,
    )

    assert payload["status"] is True
    assert payload["runner_estimate_mode"] == "runner_semantics"
    assert payload["runtime_splits"] == ["dev", "calibration", "test"]
    assert payload["runtime_sample_roles"] == [
        "clean_negative",
        "attacked_negative",
        "watermarked_positive",
        "attacked_positive",
    ]
    assert payload["resolved_samples_per_role"] == 1
    assert payload["runner_method_variant_count"] == 6
    assert payload["runner_attack_case_count"] == 4
    assert payload["runner_no_attack_case_count"] == 1
    assert payload["runner_attacked_case_count"] == 3
    assert payload["runner_estimated_event_count"] == 144
    assert payload["runner_estimated_decode_video_count"] == 72
    assert payload["runner_estimated_attack_video_count"] == 108
    assert payload["estimated_runner_minutes_mid"] > 0.0
    assert payload["estimated_runner_minutes_upper"] >= payload["estimated_runner_minutes_mid"]
    assert payload["estimated_colab_total_minutes_upper"] > payload["estimated_runner_minutes_upper"]
    assert payload["runner_scale_label"] in {"short_run", "medium_run", "multi_hour_run", "long_run"}
    assert payload["colab_total_scale_label"] in {"short_run", "medium_run", "multi_hour_run", "long_run"}


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

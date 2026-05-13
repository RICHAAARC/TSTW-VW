"""
文件用途：估算 real-video VAE latent probe 的运行规模。
File purpose: Estimate the execution scale of the real-video VAE latent probe workflow.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.profile_runtime import write_json_file


def estimate_real_video_vae_latent_run_scale(
    *,
    dataset_manifest: str | Path,
    attack_matrix: str | Path,
    ablation_config: str | Path,
    runtime_profile: str,
    output_json: str | Path,
) -> dict[str, Any]:
    """功能：估算 real-video VAE latent run 的规模。

    Estimate the scale of the real-video VAE latent run without instantiating the runner.

    Args:
        dataset_manifest: Dataset manifest path.
        attack_matrix: Attack-matrix path.
        ablation_config: Ablation-config path.
        runtime_profile: Runtime profile label.
        output_json: Output JSON path.

    Returns:
        The scale-estimation payload.
    """
    warnings: list[str] = []
    required_paths = {
        "dataset_manifest": Path(dataset_manifest),
        "attack_matrix": Path(attack_matrix),
        "ablation_config": Path(ablation_config),
    }
    missing_requirements = [name for name, path in required_paths.items() if not path.exists()]
    if missing_requirements:
        payload = {
            "status": False,
            "runtime_profile": runtime_profile,
            "dataset_manifest": str(required_paths["dataset_manifest"]),
            "attack_matrix": str(required_paths["attack_matrix"]),
            "ablation_config": str(required_paths["ablation_config"]),
            "warnings": [f"missing_required_config:{name}" for name in missing_requirements],
        }
        write_json_file(output_json, payload)
        return payload

    dataset_manifest_payload = json.loads(required_paths["dataset_manifest"].read_text(encoding="utf-8"))
    attack_matrix_payload = json.loads(required_paths["attack_matrix"].read_text(encoding="utf-8"))
    ablation_payload = json.loads(required_paths["ablation_config"].read_text(encoding="utf-8"))

    samples = dataset_manifest_payload.get("samples", [])
    attacks = attack_matrix_payload.get("attacks", [])
    method_variants_by_profile = ablation_payload.get("method_variants_by_profile", {})
    method_variants = method_variants_by_profile.get(runtime_profile) or ablation_payload.get("method_variants", [])

    if not isinstance(samples, list):
        samples = []
        warnings.append("dataset_manifest_samples_invalid")
    if not isinstance(attacks, list):
        attacks = []
        warnings.append("attack_matrix_attacks_invalid")
    if not isinstance(method_variants, list):
        method_variants = []
        warnings.append("ablation_method_variants_invalid")

    video_count_by_split: dict[str, int] = {}
    for sample in samples:
        split = str(sample.get("split", "unknown"))
        video_count_by_split[split] = video_count_by_split.get(split, 0) + 1

    video_count_total = sum(video_count_by_split.values())
    calibration_count = video_count_by_split.get("calibration", 0)
    test_count = video_count_by_split.get("test", 0)
    attack_count = len(attacks)
    method_variant_count = len(method_variants)

    if calibration_count == 0:
        warnings.append("missing_calibration_split")
    if test_count == 0:
        warnings.append("missing_test_split")
    if attack_count == 0:
        warnings.append("attack_matrix_is_empty")
    if method_variant_count == 0:
        warnings.append("method_variants_is_empty")

    estimated_event_count = video_count_total * max(method_variant_count, 1) * (attack_count + 1)
    estimated_decode_video_count = test_count * max(method_variant_count, 1) * (attack_count + 1)
    estimated_attack_video_count = test_count * max(method_variant_count, 1) * attack_count
    estimated_reencode_latent_count = estimated_attack_video_count
    estimated_quality_metric_pairs = estimated_decode_video_count

    if estimated_event_count < 200:
        scale_label = "debug_small"
    elif estimated_event_count < 2000:
        scale_label = "formal_small"
    elif estimated_event_count < 8000:
        scale_label = "formal_medium"
    else:
        scale_label = "formal_large"

    payload = {
        "status": True,
        "dataset_manifest": str(required_paths["dataset_manifest"]),
        "runtime_profile": runtime_profile,
        "video_count_total": video_count_total,
        "video_count_by_split": video_count_by_split,
        "method_variant_count": method_variant_count,
        "attack_count": attack_count,
        "estimated_event_count": estimated_event_count,
        "estimated_decode_video_count": estimated_decode_video_count,
        "estimated_attack_video_count": estimated_attack_video_count,
        "estimated_reencode_latent_count": estimated_reencode_latent_count,
        "estimated_quality_metric_pairs": estimated_quality_metric_pairs,
        "scale_label": scale_label,
        "warnings": warnings,
    }
    write_json_file(output_json, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    """功能：执行运行规模估算 CLI。

    Execute the run-scale estimation CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Estimate the real-video VAE latent run scale.",
    )
    parser.add_argument("--dataset-manifest", required=True)
    parser.add_argument("--attack-matrix", required=True)
    parser.add_argument("--ablation-config", required=True)
    parser.add_argument("--runtime-profile", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args(argv)
    payload = estimate_real_video_vae_latent_run_scale(
        dataset_manifest=args.dataset_manifest,
        attack_matrix=args.attack_matrix,
        ablation_config=args.ablation_config,
        runtime_profile=args.runtime_profile,
        output_json=args.output_json,
    )
    return 0 if payload.get("status", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())

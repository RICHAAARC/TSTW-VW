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


LEGACY_SAMPLE_ROLES = [
    "clean_negative",
    "attacked_negative",
    "watermarked_positive",
    "attacked_positive",
]
ATTACK_FREE_SAMPLE_ROLES = {"clean_negative", "watermarked_positive"}
ATTACKED_SAMPLE_ROLES = {"attacked_negative", "attacked_positive"}
AUDITED_L4_FORMAL_BASELINE_EVENT_COUNT = 9800
AUDITED_L4_FORMAL_BASELINE_RUNNER_SECONDS = 11311.526187

EXECUTION_RUNTIME_PROFILE_MULTIPLIERS: dict[str, float] = {
    "l4_debug": 1.25,
    "l4_smoke": 1.10,
    "l4_formal": 1.0,
}

EXECUTION_RUNTIME_PROFILE_COLD_START_SECONDS: dict[str, tuple[float, float]] = {
    "l4_debug": (600.0, 1800.0),
    "l4_smoke": (720.0, 2100.0),
    "l4_formal": (900.0, 2400.0),
}


def _resolve_profile_string_list(
    profile_mapping: dict[str, Any] | None,
    runtime_profile: str,
    fallback_values: list[str],
) -> list[str]:
    """功能：解析 profile 相关的字符串列表。 

    Resolve a runtime-profile dependent string list.

    Args:
        profile_mapping: Optional profile-to-list mapping.
        runtime_profile: Runtime profile label.
        fallback_values: Fallback list when no profile-specific value exists.

    Returns:
        The resolved normalized string list.
    """
    candidate_values: Any = fallback_values
    if isinstance(profile_mapping, dict) and runtime_profile in profile_mapping:
        candidate_values = profile_mapping[runtime_profile]
    if not isinstance(candidate_values, list):
        return []
    normalized_values: list[str] = []
    for value in candidate_values:
        normalized_value = str(value).strip()
        if normalized_value:
            normalized_values.append(normalized_value)
    return normalized_values


def _expand_attack_case_count(attack_name: str, attack_params: dict[str, Any]) -> int:
    """功能：估算单个攻击条目的展开 case 数。 

    Estimate the expanded attack-case count for a single attack entry.

    Args:
        attack_name: Attack name.
        attack_params: Attack parameter payload.

    Returns:
        The positive expanded-case count.
    """
    if attack_name == "local_clip":
        clip_lengths = attack_params.get("clip_lengths")
        if isinstance(clip_lengths, list):
            normalized_lengths = {
                int(clip_length)
                for clip_length in clip_lengths
                if isinstance(clip_length, int) or str(clip_length).strip().isdigit()
            }
            if normalized_lengths:
                return len(normalized_lengths)
    return 1


def _resolve_runtime_method_variants(
    *,
    ablation_payload: dict[str, Any],
    ablation_config_path: Path,
    runtime_profile: str,
    warnings: list[str],
) -> list[str]:
    """功能：解析 runner 真实使用的方法变体列表。 

    Resolve the effective runtime method variants used by the runner.

    Args:
        ablation_payload: Parsed ablation payload.
        ablation_config_path: Ablation-config path.
        runtime_profile: Runtime profile label.
        warnings: Warning accumulator.

    Returns:
        The resolved method-variant names.
    """
    configured_method_variants = ablation_payload.get("method_variants_by_profile", {}).get(
        runtime_profile,
        ablation_payload.get("method_variants", []),
    )
    if not isinstance(configured_method_variants, list):
        warnings.append("ablation_method_variants_invalid")
        return []
    method_variants = [
        str(method_variant).strip()
        for method_variant in configured_method_variants
        if str(method_variant).strip()
    ]
    sweep_variant = str(ablation_payload.get("tubelet_length_sweep_variant", "") or "").strip()
    sweep_lengths = ablation_payload.get(f"tubelet_length_sweep_{runtime_profile}", [])
    if not sweep_variant or not isinstance(sweep_lengths, list):
        return method_variants

    method_config_path = ablation_config_path.parent.parent / "method" / f"{sweep_variant}.json"
    if not method_config_path.exists():
        warnings.append(f"missing_method_config_for_sweep:{sweep_variant}")
        return method_variants

    method_config_payload = json.loads(method_config_path.read_text(encoding="utf-8"))
    default_tubelet_length = int(method_config_payload.get("tubelet_length", 0) or 0)
    for tubelet_length in sweep_lengths:
        try:
            normalized_tubelet_length = int(tubelet_length)
        except (TypeError, ValueError):
            warnings.append(f"invalid_tubelet_length_in_sweep:{tubelet_length}")
            continue
        if normalized_tubelet_length == default_tubelet_length:
            continue
        method_variants.append(f"{sweep_variant}_lt{normalized_tubelet_length:02d}")
    return method_variants


def _resolve_runner_estimate(
    *,
    dataset_manifest_payload: dict[str, Any],
    attack_matrix_payload: dict[str, Any],
    ablation_payload: dict[str, Any],
    ablation_config_path: Path,
    protocol_payload: dict[str, Any],
    runtime_profile: str,
    samples_per_role_override: int | None,
    warnings: list[str],
) -> dict[str, Any]:
    """功能：按 runner 真实口径估算 event 规模。 

    Estimate the event scale using the runner's split-role-attack semantics.

    Args:
        dataset_manifest_payload: Parsed dataset-manifest payload.
        attack_matrix_payload: Parsed attack-matrix payload.
        ablation_payload: Parsed ablation payload.
        ablation_config_path: Ablation-config path.
        protocol_payload: Parsed protocol payload.
        runtime_profile: Runtime profile label.
        samples_per_role_override: Optional explicit sample-count override.
        warnings: Warning accumulator.

    Returns:
        The runner-aware scale estimate payload.
    """
    manifest_samples = dataset_manifest_payload.get("samples", [])
    if not isinstance(manifest_samples, list):
        warnings.append("dataset_manifest_samples_invalid")
        manifest_samples = []
    manifest_splits = sorted(
        {
            str(sample.get("split", "")).strip()
            for sample in manifest_samples
            if isinstance(sample, dict) and str(sample.get("split", "")).strip()
        }
    )

    configured_splits = _resolve_profile_string_list(
        protocol_payload.get("splits_by_profile"),
        runtime_profile,
        [str(value) for value in protocol_payload.get("splits", [])],
    )
    runtime_splits = [split_name for split_name in configured_splits if split_name in manifest_splits]
    if not runtime_splits:
        warnings.append("runner_estimate_runtime_splits_empty")

    runtime_sample_roles = _resolve_profile_string_list(
        protocol_payload.get("sample_roles_by_profile"),
        runtime_profile,
        [str(value) for value in protocol_payload.get("sample_roles", LEGACY_SAMPLE_ROLES)],
    )
    if not runtime_sample_roles:
        warnings.append("runner_estimate_runtime_sample_roles_empty")

    profile_samples_per_role = protocol_payload.get("samples_per_role_by_profile", {})
    if samples_per_role_override is None:
        resolved_samples_per_role = profile_samples_per_role.get(runtime_profile, 1)
    else:
        resolved_samples_per_role = samples_per_role_override
    try:
        resolved_samples_per_role = int(resolved_samples_per_role)
    except (TypeError, ValueError):
        warnings.append("runner_estimate_samples_per_role_invalid")
        resolved_samples_per_role = 1
    if resolved_samples_per_role < 1:
        warnings.append("runner_estimate_samples_per_role_invalid")
        resolved_samples_per_role = 1

    method_variants = _resolve_runtime_method_variants(
        ablation_payload=ablation_payload,
        ablation_config_path=ablation_config_path,
        runtime_profile=runtime_profile,
        warnings=warnings,
    )
    method_variant_count = max(len(method_variants), 1)

    attacks = attack_matrix_payload.get("attacks", [])
    if not isinstance(attacks, list):
        warnings.append("attack_matrix_attacks_invalid")
        attacks = []
    allowed_attack_names = _resolve_profile_string_list(
        attack_matrix_payload.get("attack_names_by_profile"),
        runtime_profile,
        [
            str(attack_entry.get("attack_name", attack_entry.get("name", ""))).strip()
            for attack_entry in attacks
            if isinstance(attack_entry, dict)
        ],
    )
    allowed_attack_name_set = set(allowed_attack_names)

    expanded_attack_case_names: list[str] = []
    no_attack_case_count = 0
    attacked_case_count = 0
    for attack_entry in attacks:
        if not isinstance(attack_entry, dict):
            warnings.append("attack_matrix_entry_invalid")
            continue
        attack_name = str(attack_entry.get("attack_name", attack_entry.get("name", ""))).strip()
        if not attack_name:
            warnings.append("attack_matrix_attack_name_missing")
            continue
        if allowed_attack_name_set and attack_name not in allowed_attack_name_set:
            continue
        attack_params = attack_entry.get("attack_params", {})
        if not isinstance(attack_params, dict):
            warnings.append(f"attack_params_invalid:{attack_name}")
            attack_params = {}
        expanded_case_count = _expand_attack_case_count(attack_name, attack_params)
        if attack_name == "local_clip" and isinstance(attack_params.get("clip_lengths"), list):
            for clip_length in attack_params["clip_lengths"]:
                try:
                    expanded_attack_case_names.append(f"local_clip_len_{int(clip_length):02d}")
                except (TypeError, ValueError):
                    warnings.append(f"invalid_local_clip_length:{clip_length}")
        else:
            expanded_attack_case_names.extend([attack_name] * expanded_case_count)
        if attack_name == "no_attack":
            no_attack_case_count += expanded_case_count
        else:
            attacked_case_count += expanded_case_count

    clean_role_count = sum(
        sample_role in ATTACK_FREE_SAMPLE_ROLES for sample_role in runtime_sample_roles
    )
    attacked_role_count = sum(
        sample_role in ATTACKED_SAMPLE_ROLES for sample_role in runtime_sample_roles
    )
    if clean_role_count > 0 and no_attack_case_count == 0:
        warnings.append("runner_estimate_missing_no_attack_case")
    if attacked_role_count > 0 and attacked_case_count == 0:
        warnings.append("runner_estimate_missing_attacked_cases")

    split_count = len(runtime_splits)
    runner_estimated_event_count = (
        split_count
        * resolved_samples_per_role
        * method_variant_count
        * (
            clean_role_count * no_attack_case_count
            + attacked_role_count * attacked_case_count
        )
    )
    runner_estimated_decode_video_count = (
        split_count
        * resolved_samples_per_role
        * method_variant_count
        * len(runtime_sample_roles)
    )
    runner_estimated_attack_video_count = (
        split_count
        * resolved_samples_per_role
        * method_variant_count
        * attacked_role_count
        * attacked_case_count
    )
    return {
        "runtime_splits": runtime_splits,
        "runtime_sample_roles": runtime_sample_roles,
        "resolved_samples_per_role": resolved_samples_per_role,
        "runtime_method_variants": method_variants,
        "runner_method_variant_count": method_variant_count,
        "expanded_attack_case_names": expanded_attack_case_names,
        "runner_attack_case_count": no_attack_case_count + attacked_case_count,
        "runner_no_attack_case_count": no_attack_case_count,
        "runner_attacked_case_count": attacked_case_count,
        "runner_estimated_event_count": runner_estimated_event_count,
        "runner_estimated_decode_video_count": runner_estimated_decode_video_count,
        "runner_estimated_attack_video_count": runner_estimated_attack_video_count,
        "runner_estimated_reencode_latent_count": runner_estimated_attack_video_count,
        "runner_estimated_quality_metric_pairs": runner_estimated_event_count,
    }


def _resolve_execution_runtime_multiplier(execution_runtime_profile: str | None) -> float:
    """功能：根据执行 profile 解析 wall-clock 调整系数。 

    Resolve a wall-clock multiplier from the execution runtime profile.

    Args:
        execution_runtime_profile: Execution runtime-profile name.

    Returns:
        The conservative timing multiplier.
    """
    normalized_profile = str(execution_runtime_profile or "").strip().lower()
    if normalized_profile in EXECUTION_RUNTIME_PROFILE_MULTIPLIERS:
        return EXECUTION_RUNTIME_PROFILE_MULTIPLIERS[normalized_profile]
    if "a100" in normalized_profile:
        return 0.55
    if "l4" in normalized_profile:
        return 1.0
    return 1.10


def _resolve_batch_size_multiplier(batch_size_frames: int | None) -> float:
    """功能：根据 batch 大小解析保守时间修正。 

    Resolve a conservative timing penalty from the effective frame batch size.

    Args:
        batch_size_frames: Effective VAE frame batch size.

    Returns:
        The multiplicative timing adjustment.
    """
    if batch_size_frames is None:
        return 1.0
    normalized_batch_size = max(1, int(batch_size_frames))
    saturated_batch_size = min(normalized_batch_size, 32)
    if saturated_batch_size >= 32:
        return 1.0
    return min(1.60, max(1.0, (32.0 / float(saturated_batch_size)) ** 0.25))


def _estimate_runner_time_range(
    *,
    runner_estimated_event_count: int,
    execution_runtime_profile: str | None,
    batch_size_frames: int | None,
) -> dict[str, Any]:
    """功能：根据审计基线估算 runner 的 wall-clock 区间。 

    Estimate the runner wall-clock window from the governed audit baseline.

    Args:
        runner_estimated_event_count: Runner-aware event count.
        execution_runtime_profile: Execution runtime-profile name.
        batch_size_frames: Effective frame batch size.

    Returns:
        The runner timing estimate payload.
    """
    if runner_estimated_event_count < 1:
        return {
            "estimated_runner_seconds_lower": 0.0,
            "estimated_runner_seconds_mid": 0.0,
            "estimated_runner_seconds_upper": 0.0,
            "estimated_runner_minutes_lower": 0.0,
            "estimated_runner_minutes_mid": 0.0,
            "estimated_runner_minutes_upper": 0.0,
        }

    execution_multiplier = _resolve_execution_runtime_multiplier(execution_runtime_profile)
    batch_size_multiplier = _resolve_batch_size_multiplier(batch_size_frames)
    estimated_runner_seconds_mid = (
        AUDITED_L4_FORMAL_BASELINE_RUNNER_SECONDS
        * (float(runner_estimated_event_count) / float(AUDITED_L4_FORMAL_BASELINE_EVENT_COUNT))
        * execution_multiplier
        * batch_size_multiplier
    )
    estimated_runner_seconds_lower = estimated_runner_seconds_mid * 0.80
    estimated_runner_seconds_upper = estimated_runner_seconds_mid * 1.25
    return {
        "estimated_runner_seconds_lower": round(estimated_runner_seconds_lower, 3),
        "estimated_runner_seconds_mid": round(estimated_runner_seconds_mid, 3),
        "estimated_runner_seconds_upper": round(estimated_runner_seconds_upper, 3),
        "estimated_runner_minutes_lower": round(estimated_runner_seconds_lower / 60.0, 2),
        "estimated_runner_minutes_mid": round(estimated_runner_seconds_mid / 60.0, 2),
        "estimated_runner_minutes_upper": round(estimated_runner_seconds_upper / 60.0, 2),
    }


def _estimate_colab_total_time_range(
    *,
    execution_runtime_profile: str | None,
    runner_seconds_lower: float,
    runner_seconds_mid: float,
    runner_seconds_upper: float,
) -> dict[str, Any]:
    """功能：为 Colab 冷启动提供总耗时区间估算。 

    Estimate the end-to-end Colab wall-clock window including cold-start overhead.

    Args:
        execution_runtime_profile: Execution runtime-profile name.
        runner_seconds_lower: Lower-bound runner estimate.
        runner_seconds_mid: Mid-point runner estimate.
        runner_seconds_upper: Upper-bound runner estimate.

    Returns:
        The Colab total-time estimate payload.
    """
    normalized_profile = str(execution_runtime_profile or "").strip().lower()
    cold_start_seconds_lower, cold_start_seconds_upper = EXECUTION_RUNTIME_PROFILE_COLD_START_SECONDS.get(
        normalized_profile,
        (600.0, 2100.0),
    )
    estimated_colab_total_seconds_lower = runner_seconds_lower + cold_start_seconds_lower
    estimated_colab_total_seconds_mid = runner_seconds_mid + ((cold_start_seconds_lower + cold_start_seconds_upper) / 2.0)
    estimated_colab_total_seconds_upper = runner_seconds_upper + cold_start_seconds_upper
    return {
        "estimated_cold_start_seconds_lower": round(cold_start_seconds_lower, 3),
        "estimated_cold_start_seconds_upper": round(cold_start_seconds_upper, 3),
        "estimated_colab_total_seconds_lower": round(estimated_colab_total_seconds_lower, 3),
        "estimated_colab_total_seconds_mid": round(estimated_colab_total_seconds_mid, 3),
        "estimated_colab_total_seconds_upper": round(estimated_colab_total_seconds_upper, 3),
        "estimated_colab_total_minutes_lower": round(estimated_colab_total_seconds_lower / 60.0, 2),
        "estimated_colab_total_minutes_mid": round(estimated_colab_total_seconds_mid / 60.0, 2),
        "estimated_colab_total_minutes_upper": round(estimated_colab_total_seconds_upper / 60.0, 2),
    }


def _planning_label(total_seconds: float) -> str:
    """功能：按 timing summary 口径输出规划标签。 

    Classify a wall-clock estimate using the governed timing labels.

    Args:
        total_seconds: Estimated total seconds.

    Returns:
        The governed planning label.
    """
    if total_seconds < 1800.0:
        return "short_run"
    if total_seconds < 7200.0:
        return "medium_run"
    if total_seconds < 28800.0:
        return "multi_hour_run"
    return "long_run"


def estimate_real_video_vae_latent_run_scale(
    *,
    dataset_manifest: str | Path,
    attack_matrix: str | Path,
    ablation_config: str | Path,
    runtime_profile: str,
    output_json: str | Path,
    protocol_config: str | Path | None = None,
    samples_per_role_override: int | None = None,
    execution_runtime_profile: str | None = None,
    batch_size_frames: int | None = None,
) -> dict[str, Any]:
    """功能：估算 real-video VAE latent run 的规模。

    Estimate the scale of the real-video VAE latent run without instantiating the runner.

    Args:
        dataset_manifest: Dataset manifest path.
        attack_matrix: Attack-matrix path.
        ablation_config: Ablation-config path.
        runtime_profile: Runtime profile label.
        output_json: Output JSON path.
        protocol_config: Optional protocol-config path for runner-aware estimation.
        samples_per_role_override: Optional runner sample-count override.
        execution_runtime_profile: Optional execution runtime-profile name.
        batch_size_frames: Optional effective VAE frame batch size.

    Returns:
        The scale-estimation payload.
    """
    warnings: list[str] = []
    required_paths = {
        "dataset_manifest": Path(dataset_manifest),
        "attack_matrix": Path(attack_matrix),
        "ablation_config": Path(ablation_config),
    }
    protocol_config_path = Path(protocol_config) if protocol_config is not None else None
    if protocol_config_path is not None:
        required_paths["protocol_config"] = protocol_config_path
    missing_requirements = [name for name, path in required_paths.items() if not path.exists()]
    if missing_requirements:
        payload = {
            "status": False,
            "runtime_profile": runtime_profile,
            "dataset_manifest": str(required_paths["dataset_manifest"]),
            "attack_matrix": str(required_paths["attack_matrix"]),
            "ablation_config": str(required_paths["ablation_config"]),
            "protocol_config": str(protocol_config_path) if protocol_config_path is not None else None,
            "warnings": [f"missing_required_config:{name}" for name in missing_requirements],
        }
        write_json_file(output_json, payload)
        return payload

    dataset_manifest_payload = json.loads(required_paths["dataset_manifest"].read_text(encoding="utf-8"))
    attack_matrix_payload = json.loads(required_paths["attack_matrix"].read_text(encoding="utf-8"))
    ablation_payload = json.loads(required_paths["ablation_config"].read_text(encoding="utf-8"))
    protocol_payload = (
        json.loads(protocol_config_path.read_text(encoding="utf-8"))
        if protocol_config_path is not None
        else {}
    )

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

    runner_estimate_payload: dict[str, Any] = {}
    if protocol_config_path is not None:
        runner_estimate_payload = _resolve_runner_estimate(
            dataset_manifest_payload=dataset_manifest_payload,
            attack_matrix_payload=attack_matrix_payload,
            ablation_payload=ablation_payload,
            ablation_config_path=required_paths["ablation_config"],
            protocol_payload=protocol_payload,
            runtime_profile=runtime_profile,
            samples_per_role_override=samples_per_role_override,
            warnings=warnings,
        )
        runner_timing_payload = _estimate_runner_time_range(
            runner_estimated_event_count=int(
                runner_estimate_payload.get("runner_estimated_event_count", 0) or 0
            ),
            execution_runtime_profile=execution_runtime_profile,
            batch_size_frames=batch_size_frames,
        )
        colab_total_timing_payload = _estimate_colab_total_time_range(
            execution_runtime_profile=execution_runtime_profile,
            runner_seconds_lower=float(
                runner_timing_payload.get("estimated_runner_seconds_lower", 0.0) or 0.0
            ),
            runner_seconds_mid=float(
                runner_timing_payload.get("estimated_runner_seconds_mid", 0.0) or 0.0
            ),
            runner_seconds_upper=float(
                runner_timing_payload.get("estimated_runner_seconds_upper", 0.0) or 0.0
            ),
        )
        runner_estimate_payload.update(runner_timing_payload)
        runner_estimate_payload.update(colab_total_timing_payload)
        runner_estimate_payload["runner_scale_label"] = _planning_label(
            float(runner_timing_payload.get("estimated_runner_seconds_mid", 0.0) or 0.0)
        )
        runner_estimate_payload["colab_total_scale_label"] = _planning_label(
            float(colab_total_timing_payload.get("estimated_colab_total_seconds_mid", 0.0) or 0.0)
        )

    payload = {
        "status": True,
        "dataset_manifest": str(required_paths["dataset_manifest"]),
        "runtime_profile": runtime_profile,
        "protocol_config": str(protocol_config_path) if protocol_config_path is not None else None,
        "execution_runtime_profile": execution_runtime_profile,
        "batch_size_frames": batch_size_frames,
        "samples_per_role_override": samples_per_role_override,
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
        "runner_estimate_mode": "runner_semantics" if protocol_config_path is not None else "legacy_manifest_count",
        "timing_baseline_source": "docs/builds/阶段2VAE机制实现.md#十三、2026-05-15-性能优化审查增补",
    }
    payload.update(runner_estimate_payload)
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
    parser.add_argument("--protocol-config", default=None)
    parser.add_argument("--samples-per-role", type=int, default=None)
    parser.add_argument("--execution-runtime-profile", default=None)
    parser.add_argument("--batch-size-frames", type=int, default=None)
    args = parser.parse_args(argv)
    payload = estimate_real_video_vae_latent_run_scale(
        dataset_manifest=args.dataset_manifest,
        attack_matrix=args.attack_matrix,
        ablation_config=args.ablation_config,
        runtime_profile=args.runtime_profile,
        output_json=args.output_json,
        protocol_config=args.protocol_config,
        samples_per_role_override=args.samples_per_role,
        execution_runtime_profile=args.execution_runtime_profile,
        batch_size_frames=args.batch_size_frames,
    )
    return 0 if payload.get("status", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())

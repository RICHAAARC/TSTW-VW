"""
文件用途：运行阶段 2 机制校准参数扫描，并写出候选 method config。
File purpose: Run the stage-two mechanism calibration sweep and materialize a candidate method config.
Module type: General module
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
from pathlib import Path
from typing import Any

from experiments.real_video_vae_latent_probe.runner import RealVideoVaeLatentRunner
from main.core.registry import load_json_config
from scripts.check_results.select_stage2_mechanism_candidate import (
    select_stage2_mechanism_candidate,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRID_CONFIG_PATH = (
    ROOT / "configs" / "ablation" / "stage2_vae_mechanism_calibration_grid.json"
)
DEFAULT_PROTOCOL_CONFIG_PATH = (
    ROOT / "configs" / "protocol" / "real_video_vae_latent_probe.json"
)
DEFAULT_BACKEND_CONFIG_PATH = ROOT / "configs" / "backend" / "real_video_vae_latent.json"
DEFAULT_ATTACK_MATRIX_PATH = ROOT / "configs" / "attacks" / "real_video_attack_matrix.json"
DEFAULT_ABLATION_CONFIG_PATH = (
    ROOT / "configs" / "ablation" / "real_video_vae_latent_ablation.json"
)
DEFAULT_MECHANISM_CONFIG_PATH = ROOT / "configs" / "protocol" / "stage2_mechanism_gate.json"
DEFAULT_OUTPUT_METHOD_CONFIG_PATH = (
    ROOT / "configs" / "method" / "tubelet_sync_real_video_vae_candidate.json"
)


def run_stage2_mechanism_calibration(
    *,
    run_root: str | Path,
    run_mode: str = "formal",
    runtime_profile: str = "formal",
    grid_config_path: str | Path = DEFAULT_GRID_CONFIG_PATH,
    protocol_config_path: str | Path = DEFAULT_PROTOCOL_CONFIG_PATH,
    backend_config_path: str | Path = DEFAULT_BACKEND_CONFIG_PATH,
    attack_matrix_path: str | Path = DEFAULT_ATTACK_MATRIX_PATH,
    ablation_config_path: str | Path = DEFAULT_ABLATION_CONFIG_PATH,
    mechanism_config_path: str | Path = DEFAULT_MECHANISM_CONFIG_PATH,
    dataset_manifest_path: str | Path | None = None,
    runtime_config_path: str | Path | None = None,
    samples_per_role: int | None = None,
    batch_size_frames: int | None = None,
    output_method_config_path: str | Path = DEFAULT_OUTPUT_METHOD_CONFIG_PATH,
) -> dict[str, Any]:
    """功能：运行阶段 2 机制校准参数扫描。

    Run the governed stage-two mechanism calibration sweep.

    Args:
        run_root: Calibration run-root path.
        run_mode: Governed run mode passed to the runner.
        runtime_profile: Runtime profile label used for the scan.
        grid_config_path: Calibration-grid config path.
        protocol_config_path: Base protocol config path.
        backend_config_path: Backend config path.
        attack_matrix_path: Attack-matrix config path.
        ablation_config_path: Base ablation config path.
        mechanism_config_path: Mechanism-gate config path.
        dataset_manifest_path: Optional dataset manifest path.
        runtime_config_path: Optional runtime-config path.
        samples_per_role: Optional sample-count override.
        batch_size_frames: Optional frame-batch override.
        output_method_config_path: Candidate method-config output path.

    Returns:
        A governed calibration summary payload.
    """
    run_root_path = Path(run_root)
    grid_config_file = _resolve_path(grid_config_path)
    protocol_config_file = _resolve_path(protocol_config_path)
    backend_config_file = _resolve_path(backend_config_path)
    attack_matrix_file = _resolve_path(attack_matrix_path)
    ablation_config_file = _resolve_path(ablation_config_path)
    mechanism_config_file = _resolve_path(mechanism_config_path)
    output_method_config_file = _resolve_output_path(output_method_config_path)
    dataset_manifest_file = None if dataset_manifest_path is None else Path(dataset_manifest_path)
    runtime_config_file = None if runtime_config_path is None else Path(runtime_config_path)

    grid_config = load_json_config(grid_config_file)
    protocol_config = load_json_config(protocol_config_file)
    base_ablation_config = load_json_config(ablation_config_file)
    frame_prc_template = load_json_config(ROOT / "configs" / "method" / "frame_prc.json")
    tubelet_only_template = load_json_config(ROOT / "configs" / "method" / "tubelet_only.json")
    tubelet_sync_template = load_json_config(ROOT / "configs" / "method" / "tubelet_sync.json")
    allowed_splits = _read_string_list(grid_config, "allowed_splits")
    forbidden_splits = _read_string_list(grid_config, "forbidden_splits")
    if set(allowed_splits) & set(forbidden_splits):
        raise ValueError("allowed_splits and forbidden_splits must not overlap")
    if "test" not in forbidden_splits:
        raise ValueError("forbidden_splits must include test")

    calibration_workspace_root = run_root_path / "artifacts" / "mechanism_calibration_workspace"
    method_config_root = calibration_workspace_root / "method_configs"
    method_config_root.mkdir(parents=True, exist_ok=True)
    temp_protocol_config_path = (
        calibration_workspace_root / "real_video_vae_mechanism_calibration_protocol.json"
    )
    temp_ablation_config_path = (
        calibration_workspace_root / "real_video_vae_mechanism_calibration_ablation.json"
    )
    calibration_summary_path = (
        run_root_path / "artifacts" / "stage2_mechanism_calibration_summary.json"
    )

    calibration_protocol_config = _build_calibration_protocol_config(
        protocol_config=protocol_config,
        runtime_profile=runtime_profile,
        allowed_splits=allowed_splits,
    )
    generated_method_configs = _build_generated_method_configs(
        grid_config=grid_config,
        frame_prc_template=frame_prc_template,
        tubelet_only_template=tubelet_only_template,
        tubelet_sync_template=tubelet_sync_template,
    )
    calibration_ablation_config = _build_calibration_ablation_config(
        base_ablation_config=base_ablation_config,
        runtime_profile=runtime_profile,
        generated_method_configs=generated_method_configs,
        method_config_root=method_config_root,
    )
    _write_json(temp_protocol_config_path, calibration_protocol_config)
    _write_json(temp_ablation_config_path, calibration_ablation_config)

    runner = RealVideoVaeLatentRunner(ROOT)
    runner.run(
        output_root=run_root_path,
        run_mode=run_mode,
        samples_per_role=samples_per_role,
        batch_size_frames=batch_size_frames,
        runtime_profile_override=runtime_profile,
        method_variants=None,
        protocol_config_path=temp_protocol_config_path,
        backend_config_path=backend_config_file,
        attack_matrix_path=attack_matrix_file,
        ablation_config_path=temp_ablation_config_path,
        dataset_manifest_path=dataset_manifest_file,
        runtime_config_path=runtime_config_file,
    )

    selected_candidate_payload = select_stage2_mechanism_candidate(
        run_root=run_root_path,
        grid_config_path=grid_config_file,
        mechanism_config_path=mechanism_config_file,
    )
    candidate_method_config = _build_tubelet_sync_candidate_method_config(
        tubelet_sync_template=tubelet_sync_template,
        candidate_payload=selected_candidate_payload,
    )
    _write_json(output_method_config_file, candidate_method_config)

    calibration_summary = {
        "run_root": str(run_root_path),
        "runtime_profile": runtime_profile,
        "allowed_splits": allowed_splits,
        "forbidden_splits": forbidden_splits,
        "grid_config_path": str(grid_config_file),
        "protocol_config_path": str(temp_protocol_config_path),
        "ablation_config_path": str(temp_ablation_config_path),
        "generated_method_variant_count": len(calibration_ablation_config["method_variants"]),
        "selected_candidate_output_path": str(selected_candidate_payload["output_path"]),
        "selected_report_path": str(selected_candidate_payload["report_path"]),
        "selected_grid_output_path": str(selected_candidate_payload["grid_output_path"]),
        "selected_tubelet_only_candidate": selected_candidate_payload[
            "selected_tubelet_only_candidate"
        ],
        "selected_tubelet_sync_candidate": selected_candidate_payload[
            "selected_tubelet_sync_candidate"
        ],
        "tubelet_sync_scan_seed": selected_candidate_payload["tubelet_sync_scan_seed"],
        "generated_tubelet_sync_candidate_config_path": str(output_method_config_file),
    }
    _write_json(calibration_summary_path, calibration_summary)
    return {
        **calibration_summary,
        "calibration_summary_path": str(calibration_summary_path),
    }


def _resolve_path(path_value: str | Path) -> Path:
    resolved_path = Path(path_value)
    if not resolved_path.is_absolute():
        resolved_path = ROOT / resolved_path
    if not resolved_path.exists():
        raise FileNotFoundError(resolved_path)
    return resolved_path


def _resolve_output_path(path_value: str | Path) -> Path:
    resolved_path = Path(path_value)
    if not resolved_path.is_absolute():
        resolved_path = ROOT / resolved_path
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_path


def _build_calibration_protocol_config(
    *,
    protocol_config: dict[str, Any],
    runtime_profile: str,
    allowed_splits: list[str],
) -> dict[str, Any]:
    calibration_protocol_config = copy.deepcopy(protocol_config)
    calibration_protocol_config["splits"] = list(allowed_splits)
    calibration_protocol_config.setdefault("splits_by_profile", {})
    calibration_protocol_config["splits_by_profile"][runtime_profile] = list(allowed_splits)
    return calibration_protocol_config


def _build_generated_method_configs(
    *,
    grid_config: dict[str, Any],
    frame_prc_template: dict[str, Any],
    tubelet_only_template: dict[str, Any],
    tubelet_sync_template: dict[str, Any],
) -> list[dict[str, Any]]:
    grid_payload = grid_config.get("grid", {})
    if not isinstance(grid_payload, dict):
        raise TypeError("grid must be a dictionary")

    tubelet_lengths = _read_grid_integer_list(grid_payload, "tubelet_length")
    spatial_patch_sizes = _read_grid_patch_size_list(grid_payload, "spatial_patch_size")
    projection_support_weights = _read_grid_numeric_list(
        grid_payload,
        "embedding_projection_support_weight",
    )
    lambda_sync_values = _read_grid_numeric_list(grid_payload, "lambda_sync")
    sync_search_radii = _read_grid_integer_list(grid_payload, "sync_search_radius")
    fusion_rules = _read_grid_string_list(grid_payload, "fusion_rule")

    generated_method_configs: list[dict[str, Any]] = [
        _build_frame_prc_baseline_config(frame_prc_template)
    ]
    for tubelet_length, spatial_patch_size, support_weight in itertools.product(
        tubelet_lengths,
        spatial_patch_sizes,
        projection_support_weights,
    ):
        generated_method_configs.append(
            _build_tubelet_only_calibration_config(
                tubelet_only_template=tubelet_only_template,
                tubelet_length=tubelet_length,
                spatial_patch_size=spatial_patch_size,
                support_weight=support_weight,
            )
        )
        for lambda_sync, sync_search_radius, fusion_rule in itertools.product(
            lambda_sync_values,
            sync_search_radii,
            fusion_rules,
        ):
            generated_method_configs.append(
                _build_tubelet_sync_calibration_config(
                    tubelet_sync_template=tubelet_sync_template,
                    tubelet_length=tubelet_length,
                    spatial_patch_size=spatial_patch_size,
                    support_weight=support_weight,
                    lambda_sync=lambda_sync,
                    sync_search_radius=sync_search_radius,
                    fusion_rule=fusion_rule,
                )
            )
    return generated_method_configs


def _build_calibration_ablation_config(
    *,
    base_ablation_config: dict[str, Any],
    runtime_profile: str,
    generated_method_configs: list[dict[str, Any]],
    method_config_root: Path,
) -> dict[str, Any]:
    calibration_ablation_config = copy.deepcopy(base_ablation_config)
    method_variants: list[str] = []
    method_config_paths: dict[str, str] = {}
    for method_config in generated_method_configs:
        method_variant = str(method_config["method_variant"])
        method_variants.append(method_variant)
        method_config_path = method_config_root / f"{method_variant}.json"
        _write_json(method_config_path, method_config)
        method_config_paths[method_variant] = str(method_config_path)
    calibration_ablation_config["method_variants"] = method_variants
    calibration_ablation_config["method_variants_by_profile"] = {
        **calibration_ablation_config.get("method_variants_by_profile", {}),
        runtime_profile: list(method_variants),
    }
    calibration_ablation_config["method_config_paths"] = method_config_paths
    calibration_ablation_config["tubelet_length_sweep_variant"] = None
    for field_name in (
        "tubelet_length_sweep_tiny",
        "tubelet_length_sweep_smoke",
        "tubelet_length_sweep_proof",
        "tubelet_length_sweep_formal",
        "tubelet_length_sweep_debug_real_video",
    ):
        calibration_ablation_config[field_name] = []
    return calibration_ablation_config


def _build_frame_prc_baseline_config(frame_prc_template: dict[str, Any]) -> dict[str, Any]:
    calibration_config = copy.deepcopy(frame_prc_template)
    calibration_config["target_construction_phase"] = "real_video_vae_latent_probe"
    calibration_config["method_status"] = "stage2_mechanism_calibration_baseline"
    return calibration_config


def _build_tubelet_only_calibration_config(
    *,
    tubelet_only_template: dict[str, Any],
    tubelet_length: int,
    spatial_patch_size: tuple[int, int],
    support_weight: float,
) -> dict[str, Any]:
    calibration_config = copy.deepcopy(tubelet_only_template)
    calibration_config["target_construction_phase"] = "real_video_vae_latent_probe"
    calibration_config["method_status"] = "stage2_mechanism_calibration_candidate"
    calibration_config["base_method_variant"] = "tubelet_only"
    calibration_config["method_variant"] = _build_tubelet_only_variant_name(
        tubelet_length=tubelet_length,
        spatial_patch_size=spatial_patch_size,
        support_weight=support_weight,
    )
    calibration_config["tubelet_length"] = int(tubelet_length)
    calibration_config["tubelet_partition"] = {
        "spatial_patch_size": [int(spatial_patch_size[0]), int(spatial_patch_size[1])],
    }
    calibration_config.setdefault("score_calibration", {})
    calibration_config["score_calibration"]["embedding_projection_support_weight"] = round(
        float(support_weight),
        6,
    )
    return calibration_config


def _build_tubelet_sync_calibration_config(
    *,
    tubelet_sync_template: dict[str, Any],
    tubelet_length: int,
    spatial_patch_size: tuple[int, int],
    support_weight: float,
    lambda_sync: float,
    sync_search_radius: int,
    fusion_rule: str,
) -> dict[str, Any]:
    calibration_config = copy.deepcopy(tubelet_sync_template)
    calibration_config["target_construction_phase"] = "real_video_vae_latent_probe"
    calibration_config["method_status"] = "stage2_mechanism_calibration_candidate"
    calibration_config["base_method_variant"] = "tubelet_sync"
    calibration_config["method_variant"] = _build_tubelet_sync_variant_name(
        tubelet_length=tubelet_length,
        spatial_patch_size=spatial_patch_size,
        support_weight=support_weight,
        lambda_sync=lambda_sync,
        sync_search_radius=sync_search_radius,
        fusion_rule=fusion_rule,
    )
    calibration_config["tubelet_length"] = int(tubelet_length)
    calibration_config["tubelet_partition"] = {
        "spatial_patch_size": [int(spatial_patch_size[0]), int(spatial_patch_size[1])],
    }
    calibration_config.setdefault("score_calibration", {})
    calibration_config["score_calibration"]["embedding_projection_support_weight"] = round(
        float(support_weight),
        6,
    )
    calibration_config.setdefault("sync_search", {})
    calibration_config["sync_search"]["offset_search_min"] = -int(sync_search_radius)
    calibration_config["sync_search"]["offset_search_max"] = int(sync_search_radius)
    calibration_config["lambda_sync"] = round(float(lambda_sync), 6)
    calibration_config["fusion_rule"] = str(fusion_rule)
    return calibration_config


def _build_tubelet_only_variant_name(
    *,
    tubelet_length: int,
    spatial_patch_size: tuple[int, int],
    support_weight: float,
) -> str:
    return (
        "tubelet_only_cal_"
        f"tl{int(tubelet_length):02d}_"
        f"sp{int(spatial_patch_size[0]):02d}x{int(spatial_patch_size[1]):02d}_"
        f"w{int(round(float(support_weight) * 100)):03d}"
    )


def _build_tubelet_sync_variant_name(
    *,
    tubelet_length: int,
    spatial_patch_size: tuple[int, int],
    support_weight: float,
    lambda_sync: float,
    sync_search_radius: int,
    fusion_rule: str,
) -> str:
    fusion_rule_token_map = {
        "sync_rescue_fusion": "sync_rescue",
        "calibrated_tubelet_sync": "cal_sync",
    }
    fusion_rule_token = fusion_rule_token_map.get(
        str(fusion_rule),
        str(fusion_rule).replace("_fusion", "")[:12],
    )
    return (
        "tubelet_sync_cal_"
        f"tl{int(tubelet_length):02d}_"
        f"sp{int(spatial_patch_size[0]):02d}x{int(spatial_patch_size[1]):02d}_"
        f"w{int(round(float(support_weight) * 100)):03d}_"
        f"sr{int(sync_search_radius):02d}_"
        f"ls{int(round(float(lambda_sync) * 1000)):03d}_"
        f"fr{fusion_rule_token}"
    )


def _build_tubelet_sync_candidate_method_config(
    *,
    tubelet_sync_template: dict[str, Any],
    candidate_payload: dict[str, Any],
) -> dict[str, Any]:
    selected_candidate = candidate_payload["selected_tubelet_sync_candidate"]
    calibration_config = copy.deepcopy(tubelet_sync_template)
    calibration_config["target_construction_phase"] = "real_video_vae_latent_probe"
    calibration_config["method_status"] = "stage2_mechanism_calibration_candidate"
    calibration_config["base_method_variant"] = str(selected_candidate["base_method_variant"])
    calibration_config["method_variant"] = str(selected_candidate["method_variant"])
    calibration_config["tubelet_length"] = int(selected_candidate["tubelet_length"])
    calibration_config["tubelet_partition"] = {
        "spatial_patch_size": list(
            selected_candidate["tubelet_partition"]["spatial_patch_size"]
        ),
    }
    calibration_config.setdefault("score_calibration", {})
    calibration_config["score_calibration"]["embedding_projection_support_weight"] = round(
        float(
            selected_candidate["score_calibration"]["embedding_projection_support_weight"]
        ),
        6,
    )
    calibration_config.setdefault("sync_search", {})
    calibration_config["sync_search"]["offset_search_min"] = int(
        selected_candidate["sync_search"]["offset_search_min"]
    )
    calibration_config["sync_search"]["offset_search_max"] = int(
        selected_candidate["sync_search"]["offset_search_max"]
    )
    calibration_config["lambda_sync"] = round(float(selected_candidate["lambda_sync"]), 6)
    calibration_config["fusion_rule"] = str(selected_candidate["fusion_rule"])
    return calibration_config


def _write_json(file_path: Path, payload: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_string_list(payload: dict[str, Any], field_name: str) -> list[str]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"{field_name} must be a non-empty list")
    resolved_values = [str(item) for item in field_value if isinstance(item, str) and item]
    if not resolved_values:
        raise ValueError(f"{field_name} must contain at least one non-empty string")
    return resolved_values


def _read_grid_string_list(payload: dict[str, Any], field_name: str) -> list[str]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [str(item) for item in field_value if isinstance(item, str) and item]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain non-empty strings")
    return resolved_values


def _read_grid_numeric_list(payload: dict[str, Any], field_name: str) -> list[float]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [round(float(item), 6) for item in field_value if isinstance(item, (int, float))]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain numeric values")
    return resolved_values


def _read_grid_integer_list(payload: dict[str, Any], field_name: str) -> list[int]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [int(item) for item in field_value if isinstance(item, int)]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain integer values")
    return resolved_values


def _read_grid_patch_size_list(
    payload: dict[str, Any],
    field_name: str,
) -> list[tuple[int, int]]:
    field_value = payload.get(field_name, [])
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values: list[tuple[int, int]] = []
    for patch_size in field_value:
        if (
            isinstance(patch_size, list)
            and len(patch_size) == 2
            and all(isinstance(size, int) and size > 0 for size in patch_size)
        ):
            resolved_values.append((int(patch_size[0]), int(patch_size[1])))
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain positive integer pairs")
    return resolved_values


def main(argv: list[str] | None = None) -> int:
    """Run the stage-two mechanism calibration CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Run the governed stage-two mechanism calibration sweep.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--run-mode", default="formal")
    parser.add_argument("--runtime-profile", default="formal")
    parser.add_argument("--grid-config", default=str(DEFAULT_GRID_CONFIG_PATH))
    parser.add_argument("--protocol-config", default=str(DEFAULT_PROTOCOL_CONFIG_PATH))
    parser.add_argument("--backend-config", default=str(DEFAULT_BACKEND_CONFIG_PATH))
    parser.add_argument("--attack-matrix", default=str(DEFAULT_ATTACK_MATRIX_PATH))
    parser.add_argument("--ablation-config", default=str(DEFAULT_ABLATION_CONFIG_PATH))
    parser.add_argument("--mechanism-config", default=str(DEFAULT_MECHANISM_CONFIG_PATH))
    parser.add_argument("--dataset-manifest", default=None)
    parser.add_argument("--runtime-config", default=None)
    parser.add_argument("--samples-per-role", type=int, default=None)
    parser.add_argument("--batch-size-frames", type=int, default=None)
    parser.add_argument(
        "--output-method-config",
        default=str(DEFAULT_OUTPUT_METHOD_CONFIG_PATH),
    )
    args = parser.parse_args(argv)
    result = run_stage2_mechanism_calibration(
        run_root=args.run_root,
        run_mode=args.run_mode,
        runtime_profile=args.runtime_profile,
        grid_config_path=args.grid_config,
        protocol_config_path=args.protocol_config,
        backend_config_path=args.backend_config,
        attack_matrix_path=args.attack_matrix,
        ablation_config_path=args.ablation_config,
        mechanism_config_path=args.mechanism_config,
        dataset_manifest_path=args.dataset_manifest,
        runtime_config_path=args.runtime_config,
        samples_per_role=args.samples_per_role,
        batch_size_frames=args.batch_size_frames,
        output_method_config_path=args.output_method_config,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
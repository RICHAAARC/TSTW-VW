"""
文件用途：运行阶段 2 机制校准参数扫描，并写出候选 method config。
File purpose: Run the stage-two mechanism calibration sweep and materialize a candidate method config.
Module type: General module
"""

from __future__ import annotations

import argparse
import copy
import hashlib
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
    temp_protocol_config_path = (
        calibration_workspace_root / "real_video_vae_mechanism_calibration_protocol.json"
    )
    temp_runtime_config_path = (
        calibration_workspace_root / "real_video_vae_mechanism_calibration_runtime_config.json"
    )
    calibration_summary_path = (
        run_root_path / "artifacts" / "stage2_mechanism_calibration_summary.json"
    )

    calibration_protocol_config = _build_calibration_protocol_config(
        protocol_config=protocol_config,
        runtime_profile=runtime_profile,
        allowed_splits=allowed_splits,
    )
    calibration_workspace_root.mkdir(parents=True, exist_ok=True)
    _write_json(temp_protocol_config_path, calibration_protocol_config)
    calibration_runtime_config = _build_calibration_runtime_config(runtime_config_file)
    _write_json(temp_runtime_config_path, calibration_runtime_config)
    search_stages = _read_search_stages(grid_config)
    if search_stages:
        calibration_summary = _run_staged_mechanism_calibration(
            run_root_path=run_root_path,
            runtime_profile=runtime_profile,
            run_mode=run_mode,
            grid_config=grid_config,
            grid_config_file=grid_config_file,
            base_ablation_config=base_ablation_config,
            frame_prc_template=frame_prc_template,
            tubelet_only_template=tubelet_only_template,
            tubelet_sync_template=tubelet_sync_template,
            mechanism_config_file=mechanism_config_file,
            backend_config_file=backend_config_file,
            attack_matrix_file=attack_matrix_file,
            dataset_manifest_file=dataset_manifest_file,
            runtime_config_file=temp_runtime_config_path,
            samples_per_role=samples_per_role,
            batch_size_frames=batch_size_frames,
            output_method_config_file=output_method_config_file,
            calibration_workspace_root=calibration_workspace_root,
            protocol_config_path=temp_protocol_config_path,
            search_stages=search_stages,
        )
    else:
        calibration_summary = _run_flat_mechanism_calibration(
            run_root_path=run_root_path,
            runtime_profile=runtime_profile,
            run_mode=run_mode,
            grid_config=grid_config,
            grid_config_file=grid_config_file,
            base_ablation_config=base_ablation_config,
            frame_prc_template=frame_prc_template,
            tubelet_only_template=tubelet_only_template,
            tubelet_sync_template=tubelet_sync_template,
            mechanism_config_file=mechanism_config_file,
            backend_config_file=backend_config_file,
            attack_matrix_file=attack_matrix_file,
            dataset_manifest_file=dataset_manifest_file,
            runtime_config_file=temp_runtime_config_path,
            samples_per_role=samples_per_role,
            batch_size_frames=batch_size_frames,
            output_method_config_file=output_method_config_file,
            calibration_workspace_root=calibration_workspace_root,
            protocol_config_path=temp_protocol_config_path,
        )
    _write_json(calibration_summary_path, calibration_summary)
    return {
        **calibration_summary,
        "runtime_config_path": str(temp_runtime_config_path),
        "calibration_summary_path": str(calibration_summary_path),
    }


def _run_flat_mechanism_calibration(
    *,
    run_root_path: Path,
    runtime_profile: str,
    run_mode: str,
    grid_config: dict[str, Any],
    grid_config_file: Path,
    base_ablation_config: dict[str, Any],
    frame_prc_template: dict[str, Any],
    tubelet_only_template: dict[str, Any],
    tubelet_sync_template: dict[str, Any],
    mechanism_config_file: Path,
    backend_config_file: Path,
    attack_matrix_file: Path,
    dataset_manifest_file: Path | None,
    runtime_config_file: Path | None,
    samples_per_role: int | None,
    batch_size_frames: int | None,
    output_method_config_file: Path,
    calibration_workspace_root: Path,
    protocol_config_path: Path,
) -> dict[str, Any]:
    method_config_root = calibration_workspace_root / "method_configs"
    method_config_root.mkdir(parents=True, exist_ok=True)
    temp_ablation_config_path = (
        calibration_workspace_root / "real_video_vae_mechanism_calibration_ablation.json"
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
    _write_json(temp_ablation_config_path, calibration_ablation_config)

    runner = RealVideoVaeLatentRunner(ROOT)
    runner.run(
        output_root=run_root_path,
        run_mode=run_mode,
        samples_per_role=samples_per_role,
        batch_size_frames=batch_size_frames,
        runtime_profile_override=runtime_profile,
        method_variants=None,
        protocol_config_path=protocol_config_path,
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
    generated_candidate_config_path: str | None = None
    if selected_candidate_payload.get("selected_tubelet_sync_candidate") is not None:
        candidate_method_config = _build_tubelet_sync_candidate_method_config(
            tubelet_sync_template=tubelet_sync_template,
            candidate_payload=selected_candidate_payload,
        )
        _write_json(output_method_config_file, candidate_method_config)
        generated_candidate_config_path = str(output_method_config_file)
    return {
        "run_root": str(run_root_path),
        "runtime_profile": runtime_profile,
        "campaign_mode": "flat_grid",
        "calibration_completion_status": selected_candidate_payload.get(
            "selection_completion_status",
            "complete",
        ),
        "calibration_blocking_reason": selected_candidate_payload.get(
            "selection_blocking_reason"
        ),
        "calibration_blocking_details": selected_candidate_payload.get(
            "selection_blocking_details"
        ),
        "allowed_splits": _read_string_list(grid_config, "allowed_splits"),
        "forbidden_splits": _read_string_list(grid_config, "forbidden_splits"),
        "grid_config_path": str(grid_config_file),
        "protocol_config_path": str(protocol_config_path),
        "runtime_config_path": str(runtime_config_file),
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
        "generated_tubelet_sync_candidate_config_path": generated_candidate_config_path,
    }


def _run_staged_mechanism_calibration(
    *,
    run_root_path: Path,
    runtime_profile: str,
    run_mode: str,
    grid_config: dict[str, Any],
    grid_config_file: Path,
    base_ablation_config: dict[str, Any],
    frame_prc_template: dict[str, Any],
    tubelet_only_template: dict[str, Any],
    tubelet_sync_template: dict[str, Any],
    mechanism_config_file: Path,
    backend_config_file: Path,
    attack_matrix_file: Path,
    dataset_manifest_file: Path | None,
    runtime_config_file: Path | None,
    samples_per_role: int | None,
    batch_size_frames: int | None,
    output_method_config_file: Path,
    calibration_workspace_root: Path,
    protocol_config_path: Path,
    search_stages: list[dict[str, Any]],
) -> dict[str, Any]:
    runner = RealVideoVaeLatentRunner(ROOT)
    stage_summaries: list[dict[str, Any]] = []
    total_generated_method_variant_count = 0
    selected_tubelet_only_candidate: dict[str, Any] | None = None
    selected_tubelet_sync_candidate: dict[str, Any] | None = None
    final_stage_selection_payload: dict[str, Any] | None = None
    search_terminated_early = False
    termination_reason = None
    termination_details = None
    terminated_before_stage_name = None
    search_stage_plan_path = (
        calibration_workspace_root / "stage2_mechanism_calibration_search_stage_plan.json"
    )
    _write_json(
        search_stage_plan_path,
        {
            "campaign_mode": "staged_search",
            "grid_config_path": str(grid_config_file),
            "search_stages": search_stages,
        },
    )

    for stage_index, stage_config in enumerate(search_stages, start=1):
        stage_name = str(stage_config["stage_name"])
        selection_scope = str(stage_config["selection_scope"])
        stage_workspace_root = calibration_workspace_root / stage_name
        stage_workspace_root.mkdir(parents=True, exist_ok=True)
        stage_method_config_root = stage_workspace_root / "method_configs"
        stage_method_config_root.mkdir(parents=True, exist_ok=True)
        stage_ablation_config_path = (
            stage_workspace_root / f"real_video_vae_mechanism_calibration_{stage_name}.json"
        )
        stage_grid_config_path = stage_workspace_root / f"{stage_name}_grid_config.json"
        stage_run_root = run_root_path / "stages" / stage_name
        stage_seed_candidate = _resolve_stage_seed_candidate(
            stage_config,
            selected_tubelet_only_candidate=selected_tubelet_only_candidate,
            selected_tubelet_sync_candidate=selected_tubelet_sync_candidate,
        )
        generated_method_configs = _build_stage_generated_method_configs(
            stage_config=stage_config,
            frame_prc_template=frame_prc_template,
            tubelet_only_template=tubelet_only_template,
            tubelet_sync_template=tubelet_sync_template,
            stage_seed_candidate=stage_seed_candidate,
        )
        stage_grid_config = _build_stage_grid_config(
            grid_config=grid_config,
            stage_config=stage_config,
        )
        calibration_ablation_config = _build_calibration_ablation_config(
            base_ablation_config=base_ablation_config,
            runtime_profile=runtime_profile,
            generated_method_configs=generated_method_configs,
            method_config_root=stage_method_config_root,
        )
        _write_json(stage_grid_config_path, stage_grid_config)
        _write_json(stage_ablation_config_path, calibration_ablation_config)

        runner.run(
            output_root=stage_run_root,
            run_mode=run_mode,
            samples_per_role=samples_per_role,
            batch_size_frames=batch_size_frames,
            runtime_profile_override=runtime_profile,
            method_variants=None,
            protocol_config_path=protocol_config_path,
            backend_config_path=backend_config_file,
            attack_matrix_path=attack_matrix_file,
            ablation_config_path=stage_ablation_config_path,
            dataset_manifest_path=dataset_manifest_file,
            runtime_config_path=runtime_config_file,
        )

        selector_kwargs: dict[str, Any] = {
            "run_root": stage_run_root,
            "grid_config_path": stage_grid_config_path,
            "mechanism_config_path": mechanism_config_file,
            "selection_scope": selection_scope,
            "top_candidate_limit": _resolve_top_candidate_limit(
                grid_config=grid_config,
                stage_config=stage_config,
            ),
        }
        if selection_scope == "tubelet_sync":
            if selected_tubelet_only_candidate is None:
                raise ValueError(
                    "selected_tubelet_only_candidate must be resolved before tubelet_sync stages"
                )
            selector_kwargs["selected_tubelet_only_candidate"] = selected_tubelet_only_candidate
        stage_selection_payload = select_stage2_mechanism_candidate(**selector_kwargs)
        total_generated_method_variant_count += len(generated_method_configs)
        if selection_scope == "tubelet_only":
            selected_tubelet_only_candidate = stage_selection_payload[
                "selected_tubelet_only_candidate"
            ]
        elif stage_selection_payload.get("selected_tubelet_sync_candidate") is not None:
            selected_tubelet_sync_candidate = stage_selection_payload[
                "selected_tubelet_sync_candidate"
            ]
        final_stage_selection_payload = stage_selection_payload
        stage_summaries.append(
            {
                "stage_index": stage_index,
                "stage_name": stage_name,
                "selection_scope": selection_scope,
                "candidate_source": stage_config.get("candidate_source"),
                "run_root": str(stage_run_root),
                "grid_config_path": str(stage_grid_config_path),
                "protocol_config_path": str(protocol_config_path),
                "ablation_config_path": str(stage_ablation_config_path),
                "generated_method_variant_count": len(generated_method_configs),
                "selected_candidate_output_path": str(stage_selection_payload["output_path"]),
                "selected_report_path": str(stage_selection_payload["report_path"]),
                "selected_grid_output_path": str(stage_selection_payload["grid_output_path"]),
                "selected_tubelet_only_candidate": stage_selection_payload.get(
                    "selected_tubelet_only_candidate"
                ),
                "selected_tubelet_sync_candidate": stage_selection_payload.get(
                    "selected_tubelet_sync_candidate"
                ),
                "selection_completion_status": stage_selection_payload.get(
                    "selection_completion_status"
                ),
                "selection_blocking_reason": stage_selection_payload.get(
                    "selection_blocking_reason"
                ),
                "selection_blocking_details": stage_selection_payload.get(
                    "selection_blocking_details"
                ),
                "top_tubelet_only_candidates": stage_selection_payload.get(
                    "top_tubelet_only_candidates",
                    [],
                ),
                "top_tubelet_sync_candidates": stage_selection_payload.get(
                    "top_tubelet_sync_candidates",
                    [],
                ),
                "parameter_interval_summary": stage_selection_payload.get(
                    "parameter_interval_summary",
                    {},
                ),
            }
        )
        if (
            selection_scope == "tubelet_sync"
            and stage_selection_payload.get("selected_tubelet_sync_candidate") is None
        ):
            next_required_sync_stage = _resolve_next_required_sync_stage_name(
                search_stages,
                stage_index,
            )
            if next_required_sync_stage is not None:
                search_terminated_early = True
                termination_reason = stage_selection_payload.get(
                    "selection_blocking_reason",
                    "selected_tubelet_sync_candidate_unavailable",
                )
                termination_details = stage_selection_payload.get(
                    "selection_blocking_details"
                )
                terminated_before_stage_name = next_required_sync_stage
                break

    if final_stage_selection_payload is None:
        raise ValueError("staged mechanism calibration must produce at least one stage summary")

    generated_candidate_config_path: str | None = None
    calibration_completion_status = final_stage_selection_payload.get(
        "selection_completion_status",
        "complete",
    )
    calibration_blocking_reason = final_stage_selection_payload.get(
        "selection_blocking_reason"
    )
    calibration_blocking_details = final_stage_selection_payload.get(
        "selection_blocking_details"
    )
    if selected_tubelet_sync_candidate is not None:
        candidate_method_config = _build_tubelet_sync_candidate_method_config(
            tubelet_sync_template=tubelet_sync_template,
            candidate_payload={
                "selected_tubelet_sync_candidate": selected_tubelet_sync_candidate,
            },
        )
        _write_json(output_method_config_file, candidate_method_config)
        generated_candidate_config_path = str(output_method_config_file)
    else:
        calibration_completion_status = "anchor_only_partial_selection"
        calibration_blocking_reason = (
            termination_reason
            or calibration_blocking_reason
            or "staged_search_missing_tubelet_sync_candidate"
        )
        calibration_blocking_details = termination_details or calibration_blocking_details

    return {
        "run_root": str(run_root_path),
        "runtime_profile": runtime_profile,
        "campaign_mode": "staged_search",
        "calibration_completion_status": calibration_completion_status,
        "calibration_blocking_reason": calibration_blocking_reason,
        "calibration_blocking_details": calibration_blocking_details,
        "search_terminated_early": search_terminated_early,
        "terminated_before_stage_name": terminated_before_stage_name,
        "search_stage_count": len(stage_summaries),
        "search_stage_plan_path": str(search_stage_plan_path),
        "search_stage_summaries": stage_summaries,
        "allowed_splits": _read_string_list(grid_config, "allowed_splits"),
        "forbidden_splits": _read_string_list(grid_config, "forbidden_splits"),
        "grid_config_path": str(grid_config_file),
        "protocol_config_path": str(protocol_config_path),
        "runtime_config_path": str(runtime_config_file),
        "ablation_config_path": str(stage_summaries[-1]["ablation_config_path"]),
        "generated_method_variant_count": total_generated_method_variant_count,
        "selected_candidate_output_path": str(final_stage_selection_payload["output_path"]),
        "selected_report_path": str(final_stage_selection_payload["report_path"]),
        "selected_grid_output_path": str(final_stage_selection_payload["grid_output_path"]),
        "selected_tubelet_only_candidate": selected_tubelet_only_candidate,
        "selected_tubelet_sync_candidate": selected_tubelet_sync_candidate,
        "tubelet_sync_scan_seed": final_stage_selection_payload.get("tubelet_sync_scan_seed"),
        "generated_tubelet_sync_candidate_config_path": generated_candidate_config_path,
    }


def _resolve_next_required_sync_stage_name(
    search_stages: list[dict[str, Any]],
    completed_stage_index: int,
) -> str | None:
    for stage_config in search_stages[completed_stage_index:]:
        if str(stage_config.get("selection_scope")) != "tubelet_sync":
            continue
        candidate_source = str(
            stage_config.get("candidate_source", "selected_tubelet_only_candidate")
        )
        if candidate_source == "selected_tubelet_sync_candidate":
            return str(stage_config["stage_name"])
    return None


def _read_search_stages(grid_config: dict[str, Any]) -> list[dict[str, Any]]:
    search_stages = grid_config.get("search_stages")
    if search_stages is None:
        return []
    if not isinstance(search_stages, list) or not search_stages:
        raise ValueError("search_stages must be a non-empty list when provided")
    normalized_stages: list[dict[str, Any]] = []
    seen_stage_names: set[str] = set()
    for stage_payload in search_stages:
        if not isinstance(stage_payload, dict):
            raise TypeError("each search stage must be a dictionary")
        stage_name = stage_payload.get("stage_name")
        if not isinstance(stage_name, str) or not stage_name:
            raise ValueError("search stage stage_name must be a non-empty string")
        if stage_name in seen_stage_names:
            raise ValueError(f"duplicate search stage stage_name: {stage_name}")
        seen_stage_names.add(stage_name)
        selection_scope = stage_payload.get("selection_scope")
        if selection_scope not in {"tubelet_only", "tubelet_sync"}:
            raise ValueError(
                "search stage selection_scope must be one of: tubelet_only, tubelet_sync"
            )
        stage_grid = stage_payload.get("grid")
        if not isinstance(stage_grid, dict) or not stage_grid:
            raise ValueError("search stage grid must be a non-empty dictionary")
        candidate_source = stage_payload.get(
            "candidate_source",
            stage_payload.get("seed_source"),
        )
        if candidate_source is not None and candidate_source not in {
            "selected_tubelet_only_candidate",
            "selected_tubelet_sync_candidate",
        }:
            raise ValueError(
                "search stage candidate_source must be one of: selected_tubelet_only_candidate, selected_tubelet_sync_candidate"
            )
        normalized_stage_payload = copy.deepcopy(stage_payload)
        if candidate_source is not None:
            normalized_stage_payload["candidate_source"] = candidate_source
        normalized_stage_payload.pop("seed_source", None)
        normalized_stages.append(normalized_stage_payload)
    return normalized_stages


def _build_stage_grid_config(
    *,
    grid_config: dict[str, Any],
    stage_config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "construction_phase": grid_config.get("construction_phase", "real_video_vae_latent_probe"),
        "calibration_purpose": stage_config.get(
            "calibration_purpose",
            grid_config.get("calibration_purpose", "stage2_mechanism_effect_calibration"),
        ),
        "allowed_splits": _read_string_list(grid_config, "allowed_splits"),
        "forbidden_splits": _read_string_list(grid_config, "forbidden_splits"),
        "selection_metrics": _read_string_list(grid_config, "selection_metrics"),
        "stage_name": str(stage_config["stage_name"]),
        "selection_scope": str(stage_config["selection_scope"]),
        "grid": copy.deepcopy(stage_config["grid"]),
    }


def _resolve_top_candidate_limit(
    *,
    grid_config: dict[str, Any],
    stage_config: dict[str, Any],
) -> int:
    stage_limit = stage_config.get("top_candidate_limit")
    if isinstance(stage_limit, int) and stage_limit > 0:
        return int(stage_limit)
    config_limit = grid_config.get("top_candidate_limit")
    if isinstance(config_limit, int) and config_limit > 0:
        return int(config_limit)
    return 5


def _resolve_stage_seed_candidate(
    stage_config: dict[str, Any],
    *,
    selected_tubelet_only_candidate: dict[str, Any] | None,
    selected_tubelet_sync_candidate: dict[str, Any] | None,
) -> dict[str, Any] | None:
    selection_scope = str(stage_config["selection_scope"])
    if selection_scope == "tubelet_only":
        return None
    candidate_source = str(
        stage_config.get("candidate_source", "selected_tubelet_only_candidate")
    )
    if candidate_source == "selected_tubelet_only_candidate":
        if selected_tubelet_only_candidate is None:
            raise ValueError("tubelet_sync search stage requires a selected tubelet-only candidate")
        return selected_tubelet_only_candidate
    if selected_tubelet_sync_candidate is None:
        raise ValueError("tubelet_sync refinement stage requires a selected tubelet-sync candidate")
    return selected_tubelet_sync_candidate


def _build_stage_generated_method_configs(
    *,
    stage_config: dict[str, Any],
    frame_prc_template: dict[str, Any],
    tubelet_only_template: dict[str, Any],
    tubelet_sync_template: dict[str, Any],
    stage_seed_candidate: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    stage_grid = stage_config["grid"]
    selection_scope = str(stage_config["selection_scope"])
    include_frame_prc_baseline = bool(
        stage_config.get("include_frame_prc_baseline", selection_scope == "tubelet_only")
    )
    generated_method_configs: list[dict[str, Any]] = []
    if include_frame_prc_baseline:
        generated_method_configs.append(_build_frame_prc_baseline_config(frame_prc_template))
    if selection_scope == "tubelet_only":
        tubelet_lengths = _read_grid_integer_list(stage_grid, "tubelet_length")
        spatial_patch_sizes = _read_grid_patch_size_list(stage_grid, "spatial_patch_size")
        projection_support_weights = _read_grid_numeric_list(
            stage_grid,
            "embedding_projection_support_weight",
        )
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
        return generated_method_configs

    if stage_seed_candidate is None:
        raise ValueError("tubelet_sync search stage requires a seed candidate")
    tubelet_length = int(stage_seed_candidate["tubelet_length"])
    spatial_patch_size = _resolve_seed_spatial_patch_size(stage_seed_candidate)
    support_weight = _resolve_seed_support_weight(stage_seed_candidate)
    seed_sync_defaults = _resolve_seed_sync_defaults(
        stage_seed_candidate=stage_seed_candidate,
        tubelet_sync_template=tubelet_sync_template,
    )
    lambda_sync_values = _read_optional_grid_numeric_list(
        stage_grid,
        "lambda_sync",
        [seed_sync_defaults["lambda_sync"]],
    )
    sync_search_radii = _read_optional_grid_integer_list(
        stage_grid,
        "sync_search_radius",
        [seed_sync_defaults["sync_search_radius"]],
    )
    fusion_rules = _read_optional_grid_string_list(
        stage_grid,
        "fusion_rule",
        [seed_sync_defaults["fusion_rule"]],
    )
    min_sync_margins = _read_optional_grid_numeric_list(
        stage_grid,
        "min_sync_positive_margin",
        [seed_sync_defaults["min_sync_positive_margin"]],
    )
    min_sync_coverage_ratios = _read_optional_grid_numeric_list(
        stage_grid,
        "min_sync_alignment_coverage_ratio",
        [seed_sync_defaults["min_sync_alignment_coverage_ratio"]],
    )
    min_sync_matched_counts = _read_optional_grid_integer_list(
        stage_grid,
        "min_sync_alignment_matched_count",
        [seed_sync_defaults["min_sync_alignment_matched_count"]],
    )
    for (
        lambda_sync,
        sync_search_radius,
        fusion_rule,
        min_sync_margin,
        min_sync_coverage_ratio,
        min_sync_matched_count,
    ) in itertools.product(
        lambda_sync_values,
        sync_search_radii,
        fusion_rules,
        min_sync_margins,
        min_sync_coverage_ratios,
        min_sync_matched_counts,
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
                min_sync_margin=min_sync_margin,
                min_sync_coverage_ratio=min_sync_coverage_ratio,
                min_sync_matched_count=min_sync_matched_count,
            )
        )
    return generated_method_configs


def _resolve_seed_spatial_patch_size(
    stage_seed_candidate: dict[str, Any],
) -> tuple[int, int]:
    tubelet_partition = stage_seed_candidate.get("tubelet_partition", {})
    if not isinstance(tubelet_partition, dict):
        raise TypeError("tubelet_partition must be a dictionary")
    spatial_patch_size = tubelet_partition.get("spatial_patch_size")
    if (
        not isinstance(spatial_patch_size, list)
        or len(spatial_patch_size) != 2
        or not all(isinstance(size, int) and size > 0 for size in spatial_patch_size)
    ):
        raise ValueError("tubelet_partition.spatial_patch_size must contain two positive integers")
    return (int(spatial_patch_size[0]), int(spatial_patch_size[1]))


def _resolve_seed_support_weight(stage_seed_candidate: dict[str, Any]) -> float:
    score_calibration = stage_seed_candidate.get("score_calibration", {})
    if not isinstance(score_calibration, dict):
        raise TypeError("score_calibration must be a dictionary")
    support_weight = score_calibration.get("embedding_projection_support_weight")
    if not isinstance(support_weight, (int, float)):
        raise ValueError(
            "score_calibration.embedding_projection_support_weight must be numeric"
        )
    return round(float(support_weight), 6)


def _resolve_seed_sync_defaults(
    *,
    stage_seed_candidate: dict[str, Any],
    tubelet_sync_template: dict[str, Any],
) -> dict[str, Any]:
    template_sync_search = tubelet_sync_template.get("sync_search", {})
    if not isinstance(template_sync_search, dict):
        template_sync_search = {}
    candidate_sync_search = stage_seed_candidate.get("sync_search", {})
    if not isinstance(candidate_sync_search, dict):
        candidate_sync_search = {}
    template_offset_min = template_sync_search.get("offset_search_min", -16)
    template_offset_max = template_sync_search.get("offset_search_max", 16)
    default_sync_search_radius = max(abs(int(template_offset_min)), abs(int(template_offset_max)))
    candidate_offset_min = candidate_sync_search.get("offset_search_min")
    candidate_offset_max = candidate_sync_search.get("offset_search_max")
    if isinstance(candidate_offset_min, int) and isinstance(candidate_offset_max, int):
        default_sync_search_radius = max(abs(candidate_offset_min), abs(candidate_offset_max))
    return {
        "fusion_rule": str(
            stage_seed_candidate.get(
                "fusion_rule",
                tubelet_sync_template.get("fusion_rule", "sync_rescue_fusion"),
            )
        ),
        "lambda_sync": round(
            float(stage_seed_candidate.get("lambda_sync", tubelet_sync_template.get("lambda_sync", 0.1))),
            6,
        ),
        "sync_search_radius": int(default_sync_search_radius),
        "min_sync_positive_margin": round(
            float(candidate_sync_search.get("min_sync_positive_margin", template_sync_search.get("min_sync_positive_margin", 0.0))),
            6,
        ),
        "min_sync_alignment_coverage_ratio": round(
            float(candidate_sync_search.get("min_sync_alignment_coverage_ratio", template_sync_search.get("min_sync_alignment_coverage_ratio", 0.5))),
            6,
        ),
        "min_sync_alignment_matched_count": int(
            candidate_sync_search.get("min_sync_alignment_matched_count", template_sync_search.get("min_sync_alignment_matched_count", 1))
        ),
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


def _build_calibration_runtime_config(runtime_config_path: Path | None) -> dict[str, Any]:
    runtime_config = {} if runtime_config_path is None else load_json_config(runtime_config_path)
    if not isinstance(runtime_config, dict):
        raise TypeError("runtime_config must be a dictionary")
    calibration_runtime_config = copy.deepcopy(runtime_config)

    quality_metrics_config = dict(calibration_runtime_config.get("quality_metrics") or {})
    quality_metrics_config["enable_lpips"] = False
    quality_metrics_config["enable_clip_similarity"] = False
    quality_metrics_config["enabled_attack_names"] = ["no_attack"]
    quality_metrics_config["enabled_sample_roles"] = ["watermarked_positive"]
    calibration_runtime_config["quality_metrics"] = quality_metrics_config

    temporal_metrics_config = dict(calibration_runtime_config.get("temporal_metrics") or {})
    temporal_metrics_config["enable_temporal_metrics"] = False
    temporal_metrics_config["enable_motion_consistency"] = False
    calibration_runtime_config["temporal_metrics"] = temporal_metrics_config
    return calibration_runtime_config


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
    min_sync_margins = _read_optional_grid_numeric_list(
        grid_payload,
        "min_sync_positive_margin",
        [0.0],
    )
    min_sync_coverage_ratios = _read_optional_grid_numeric_list(
        grid_payload,
        "min_sync_alignment_coverage_ratio",
        [0.5],
    )
    min_sync_matched_counts = _read_optional_grid_integer_list(
        grid_payload,
        "min_sync_alignment_matched_count",
        [1],
    )

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
        for (
            lambda_sync,
            sync_search_radius,
            fusion_rule,
            min_sync_margin,
            min_sync_coverage_ratio,
            min_sync_matched_count,
        ) in itertools.product(
            lambda_sync_values,
            sync_search_radii,
            fusion_rules,
            min_sync_margins,
            min_sync_coverage_ratios,
            min_sync_matched_counts,
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
                    min_sync_margin=min_sync_margin,
                    min_sync_coverage_ratio=min_sync_coverage_ratio,
                    min_sync_matched_count=min_sync_matched_count,
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
        method_config_path = method_config_root / _build_method_config_file_name(method_variant)
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


def _build_method_config_file_name(method_variant: str) -> str:
    normalized_variant = method_variant.strip()
    variant_digest = hashlib.sha1(normalized_variant.encode("utf-8")).hexdigest()[:12]
    variant_prefix = normalized_variant[:24].rstrip("_") or "method"
    return f"{variant_prefix}_{variant_digest}.json"


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
    min_sync_margin: float,
    min_sync_coverage_ratio: float,
    min_sync_matched_count: int,
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
        min_sync_margin=min_sync_margin,
        min_sync_coverage_ratio=min_sync_coverage_ratio,
        min_sync_matched_count=min_sync_matched_count,
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
    calibration_config["sync_search"]["min_sync_positive_margin"] = round(
        float(min_sync_margin),
        6,
    )
    calibration_config["sync_search"]["min_sync_alignment_coverage_ratio"] = round(
        float(min_sync_coverage_ratio),
        6,
    )
    calibration_config["sync_search"]["min_sync_alignment_matched_count"] = int(
        min_sync_matched_count
    )
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
    min_sync_margin: float,
    min_sync_coverage_ratio: float,
    min_sync_matched_count: int,
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
        f"mg{int(round(float(min_sync_margin) * 1000)):03d}_"
        f"cv{int(round(float(min_sync_coverage_ratio) * 1000)):03d}_"
        f"mc{int(min_sync_matched_count):02d}_"
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
    for field_name in (
        "min_sync_positive_margin",
        "min_sync_alignment_coverage_ratio",
        "min_sync_alignment_matched_count",
    ):
        if field_name in selected_candidate["sync_search"]:
            calibration_config["sync_search"][field_name] = selected_candidate[
                "sync_search"
            ][field_name]
    calibration_config["lambda_sync"] = round(float(selected_candidate["lambda_sync"]), 6)
    calibration_config["fusion_rule"] = str(selected_candidate["fusion_rule"])
    return calibration_config


def _write_json(file_path: Path, payload: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_optional_grid_numeric_list(
    payload: dict[str, Any],
    field_name: str,
    default_values: list[float],
) -> list[float]:
    field_value = payload.get(field_name, default_values)
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [
        round(float(item), 6)
        for item in field_value
        if isinstance(item, (int, float))
    ]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain numeric values")
    return resolved_values


def _read_optional_grid_integer_list(
    payload: dict[str, Any],
    field_name: str,
    default_values: list[int],
) -> list[int]:
    field_value = payload.get(field_name, default_values)
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [int(item) for item in field_value if isinstance(item, int)]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain integer values")
    return resolved_values


def _read_optional_grid_string_list(
    payload: dict[str, Any],
    field_name: str,
    default_values: list[str],
) -> list[str]:
    field_value = payload.get(field_name, default_values)
    if not isinstance(field_value, list) or not field_value:
        raise ValueError(f"grid field {field_name} must be a non-empty list")
    resolved_values = [str(item) for item in field_value if isinstance(item, str) and item]
    if not resolved_values:
        raise ValueError(f"grid field {field_name} must contain non-empty strings")
    return resolved_values


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
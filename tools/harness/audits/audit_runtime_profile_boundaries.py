"""
文件用途：审计 runtime_profile 执行层边界与 release 可移除性约束。
File purpose: Audit runtime-profile execution boundaries and release removability constraints.
Module type: General module
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_workflow.notebook_utils.runtime_profile_workflow import (
    ALLOWED_RUNTIME_PROFILE_KEYS,
    FORBIDDEN_RUNTIME_PROFILE_KEYS,
)
from tools.harness.lib.file_scanner import iter_text_files, read_text
from tools.harness.lib.json_report import build_report, exit_with_report


REQUIRED_PATHS = {
    "gpu_runtime_governance_doc": "docs/gpu_runtime_optimization_governance.md",
    "runtime_profiles_root": "configs/runtime_profiles",
    "runtime_profile_workflow": "paper_workflow/notebook_utils/runtime_profile_workflow.py",
    "run_timing_workflow": "paper_workflow/notebook_utils/run_timing_workflow.py",
    "run_notebook": "paper_workflow/run_real_video_vae_latent_probe.ipynb",
    "zip_packager": "scripts/package_results/package_real_video_vae_latent_outputs.py",
    "tar_packager": "scripts/package_results/package_real_video_vae_latent_tar_zst.py",
}

FORBIDDEN_MAIN_FRAGMENTS = {
    "from google.colab import": "main_imports_google_colab",
    "import google.colab": "main_imports_google_colab",
    "drive.mount": "main_mounts_drive",
    "/content/drive": "main_hardcodes_drive_path",
    "mydrive": "main_hardcodes_drive_path",
    "nvidia-smi": "main_calls_nvidia_smi",
    "capture_colab_environment": "main_depends_on_runtime_profile_capture",
    "profile_gpu_runtime": "main_depends_on_gpu_profiler",
    "summarize_gpu_profile": "main_depends_on_gpu_profile_summary",
    "profile_run_timing": "main_depends_on_run_timing_profiler",
    "summarize_run_timing": "main_depends_on_run_timing_summary",
    "recommend_runtime_parameters": "main_depends_on_runtime_recommendation",
    "profile_drive_io": "main_depends_on_drive_io_profiler",
    "runtime_profile_workflow": "main_depends_on_notebook_runtime_profile_wrapper",
    "run_timing_workflow": "main_depends_on_notebook_run_timing_wrapper",
}

FORBIDDEN_MAIN_PATH_TOKENS = (
    "profile_runtime",
    "gpu_runtime",
    "run_timing",
)

FORBIDDEN_NOTEBOOK_PROFILER_IMPORTS = {
    "from scripts.profile_runtime": "notebook_must_use_runtime_profile_wrapper",
    "import scripts.profile_runtime": "notebook_must_use_runtime_profile_wrapper",
    "from scripts.check_results.summarize_run_failures": "notebook_must_use_runtime_profile_wrapper",
    "from scripts.package_results.package_real_video_vae_latent_outputs": "notebook_must_use_packager_wrapper",
    "from scripts.package_results.package_real_video_vae_latent_tar_zst": "notebook_must_use_packager_wrapper",
}

REQUIRED_NOTEBOOK_IMPORTS = {
    "from paper_workflow.notebook_utils import runtime_profile_workflow": "notebook_missing_runtime_profile_wrapper_import",
    "from paper_workflow.notebook_utils import run_timing_workflow": "notebook_missing_run_timing_wrapper_import",
    "runtime_profile_workflow.load_runtime_profile_config(": "notebook_must_load_governed_runtime_profile_json",
}

PROFILE_OUTPUT_FORBIDDEN_FRAGMENTS = {
    '/ "records"': "runtime_profile_output_must_not_target_records",
    "/ 'records'": "runtime_profile_output_must_not_target_records",
    '/ "thresholds"': "runtime_profile_output_must_not_target_thresholds",
    "/ 'thresholds'": "runtime_profile_output_must_not_target_thresholds",
    '/ "tables"': "runtime_profile_output_must_not_target_tables",
    "/ 'tables'": "runtime_profile_output_must_not_target_tables",
}

RELEASE_BOUNDARY_REQUIRED_FRAGMENTS = (
    "paper_workflow/ 可以完全删除",
    "paper_workflow/ 不属于最终发布版默认内容",
)


def _extract_notebook_sources(notebook_text: str) -> str:
    try:
        payload = json.loads(notebook_text)
    except json.JSONDecodeError:
        return notebook_text
    sources: list[str] = []
    for cell in payload.get("cells", []):
        if not isinstance(cell, dict):
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            sources.append("".join(str(line) for line in source))
        elif isinstance(source, str):
            sources.append(source)
    return "\n".join(sources)


def _audit_required_paths(root_path: Path, violations: list[dict[str, Any]], checked_paths: list[str]) -> None:
    for requirement_name, relative_path in REQUIRED_PATHS.items():
        candidate = root_path / relative_path
        checked_paths.append(str(candidate))
        if candidate.exists():
            continue
        violations.append(
            {
                "path": str(candidate),
                "reason": "runtime_profile_required_path_missing",
                "requirement": requirement_name,
            }
        )


def _audit_main_boundaries(root_path: Path, violations: list[dict[str, Any]], checked_paths: list[str]) -> None:
    main_root = root_path / "main"
    if not main_root.exists():
        return
    for file_path in iter_text_files(main_root):
        checked_paths.append(str(file_path))
        lowered_name = file_path.name.lower()
        if any(token in lowered_name for token in FORBIDDEN_MAIN_PATH_TOKENS):
            violations.append(
                {
                    "path": str(file_path),
                    "reason": "main_hosts_runtime_profile_module",
                }
            )
        text = read_text(file_path).lower()
        for fragment, reason in FORBIDDEN_MAIN_FRAGMENTS.items():
            if fragment not in text:
                continue
            violations.append(
                {
                    "path": str(file_path),
                    "reason": reason,
                    "fragment": fragment,
                }
            )


def _audit_runtime_profile_configs(root_path: Path, violations: list[dict[str, Any]], checked_paths: list[str]) -> None:
    config_root = root_path / "configs" / "runtime_profiles"
    if not config_root.exists():
        return
    config_paths = sorted(config_root.glob("*.json"))
    if not config_paths:
        violations.append(
            {
                "path": str(config_root),
                "reason": "runtime_profile_config_root_empty",
            }
        )
        return
    for config_path in config_paths:
        checked_paths.append(str(config_path))
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            violations.append(
                {
                    "path": str(config_path),
                    "reason": "runtime_profile_config_not_valid_json",
                }
            )
            continue
        if not isinstance(payload, dict):
            violations.append(
                {
                    "path": str(config_path),
                    "reason": "runtime_profile_config_must_be_object",
                }
            )
            continue
        payload_keys = set(payload.keys())
        forbidden_keys = sorted(payload_keys & FORBIDDEN_RUNTIME_PROFILE_KEYS)
        if forbidden_keys:
            violations.append(
                {
                    "path": str(config_path),
                    "reason": "runtime_profile_config_contains_forbidden_semantic_keys",
                    "forbidden_keys": forbidden_keys,
                }
            )
        unknown_keys = sorted(payload_keys - ALLOWED_RUNTIME_PROFILE_KEYS)
        if unknown_keys:
            violations.append(
                {
                    "path": str(config_path),
                    "reason": "runtime_profile_config_contains_unknown_keys",
                    "unknown_keys": unknown_keys,
                }
            )
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                violations.append(
                    {
                        "path": str(config_path),
                        "reason": "runtime_profile_config_must_remain_flat",
                        "field": key,
                    }
                )
        runtime_profile_name = str(payload.get("runtime_profile", "")).strip()
        if runtime_profile_name != config_path.stem:
            violations.append(
                {
                    "path": str(config_path),
                    "reason": "runtime_profile_name_must_match_filename",
                    "runtime_profile": runtime_profile_name,
                }
            )


def _audit_notebook_boundaries(root_path: Path, violations: list[dict[str, Any]], checked_paths: list[str]) -> None:
    notebook_path = root_path / "paper_workflow" / "run_real_video_vae_latent_probe.ipynb"
    if not notebook_path.exists():
        return
    checked_paths.append(str(notebook_path))
    notebook_text = _extract_notebook_sources(read_text(notebook_path)).lower()
    for fragment, reason in REQUIRED_NOTEBOOK_IMPORTS.items():
        if fragment not in notebook_text:
            violations.append(
                {
                    "path": str(notebook_path),
                    "reason": reason,
                    "fragment": fragment,
                }
            )
    for fragment, reason in FORBIDDEN_NOTEBOOK_PROFILER_IMPORTS.items():
        if fragment not in notebook_text:
            continue
        violations.append(
            {
                "path": str(notebook_path),
                "reason": reason,
                "fragment": fragment,
            }
        )


def _audit_runtime_profile_outputs(root_path: Path, violations: list[dict[str, Any]], checked_paths: list[str]) -> None:
    candidate_paths = [
        root_path / "scripts" / "profile_runtime" / "capture_colab_environment.py",
        root_path / "scripts" / "profile_runtime" / "estimate_real_video_vae_latent_run_scale.py",
        root_path / "scripts" / "profile_runtime" / "profile_drive_io.py",
        root_path / "scripts" / "profile_runtime" / "profile_gpu_runtime.py",
        root_path / "scripts" / "profile_runtime" / "profile_run_timing.py",
        root_path / "scripts" / "profile_runtime" / "recommend_runtime_parameters.py",
        root_path / "scripts" / "profile_runtime" / "summarize_gpu_profile.py",
        root_path / "scripts" / "profile_runtime" / "summarize_run_timing.py",
        root_path / "paper_workflow" / "notebook_utils" / "runtime_profile_workflow.py",
        root_path / "paper_workflow" / "notebook_utils" / "run_timing_workflow.py",
    ]
    for candidate in candidate_paths:
        if not candidate.exists():
            continue
        checked_paths.append(str(candidate))
        text = read_text(candidate)
        for fragment, reason in PROFILE_OUTPUT_FORBIDDEN_FRAGMENTS.items():
            if fragment not in text:
                continue
            violations.append(
                {
                    "path": str(candidate),
                    "reason": reason,
                    "fragment": fragment,
                }
            )


def _audit_packager_contract(root_path: Path, violations: list[dict[str, Any]], checked_paths: list[str]) -> None:
    for relative_path in (
        "scripts/package_results/package_real_video_vae_latent_outputs.py",
        "scripts/package_results/package_real_video_vae_latent_tar_zst.py",
    ):
        candidate = root_path / relative_path
        if not candidate.exists():
            continue
        checked_paths.append(str(candidate))
        text = read_text(candidate)
        if "runtime_profile" not in text or "runtime_profile_included" not in text:
            violations.append(
                {
                    "path": str(candidate),
                    "reason": "packager_must_include_runtime_profile",
                }
            )


def _audit_release_boundary(root_path: Path, violations: list[dict[str, Any]], checked_paths: list[str]) -> None:
    boundary_paths = [
        root_path / "docs" / "file_organization.md",
        root_path / "docs" / "gpu_runtime_optimization_governance.md",
    ]
    boundary_text = ""
    for boundary_path in boundary_paths:
        checked_paths.append(str(boundary_path))
        if boundary_path.exists():
            boundary_text += "\n" + read_text(boundary_path)
    if not all(fragment in boundary_text for fragment in RELEASE_BOUNDARY_REQUIRED_FRAGMENTS):
        violations.append(
            {
                "path": str(root_path / "docs" / "gpu_runtime_optimization_governance.md"),
                "reason": "release_boundary_must_allow_paper_workflow_removal",
            }
        )


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the runtime-profile boundary audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized audit report.
    """
    root_path = Path(root)
    checked_paths: list[str] = []
    violations: list[dict[str, Any]] = []

    _audit_required_paths(root_path, violations, checked_paths)
    _audit_main_boundaries(root_path, violations, checked_paths)
    _audit_runtime_profile_configs(root_path, violations, checked_paths)
    _audit_notebook_boundaries(root_path, violations, checked_paths)
    _audit_runtime_profile_outputs(root_path, violations, checked_paths)
    _audit_packager_contract(root_path, violations, checked_paths)
    _audit_release_boundary(root_path, violations, checked_paths)

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_runtime_profile_boundaries",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the audit as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    exit_with_report(run_audit(root))


if __name__ == "__main__":
    main(sys.argv)

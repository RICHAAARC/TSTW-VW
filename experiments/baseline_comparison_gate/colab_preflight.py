"""阶段三 Colab 验证前的 baseline preflight 检查。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from experiments.baseline_comparison_gate.source_intake import (
    REQUIRED_BASELINE_NAMES,
    load_all_source_manifests,
    validate_source_manifest,
)


REQUIRED_STAGE_TWO_INPUT_FIELDS = {
    "workflow_key",
    "run_id",
    "required_manifest",
    "required_lpips",
    "required_clip_similarity",
}


def inspect_git_head(path: Path) -> str | None:
    """读取上游源码目录的 HEAD commit, 目录不可用时返回 None。"""
    if not path.exists():
        return None
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).strip()
    except Exception:
        return None


def run_colab_preflight(
    *,
    config_dir: str | Path,
    external_root: str | Path,
    stage_two_package_root: str | Path | None = None,
) -> dict[str, Any]:
    """检查进入 Colab 真实 baseline smoke 前的本地准备状态。"""
    config_dir_path = Path(config_dir)
    external_root_path = Path(external_root)
    manifests = load_all_source_manifests(config_dir_path)
    protocol_config = json.loads(
        (config_dir_path / "baseline_comparison_gate.json").read_text(encoding="utf-8")
    )

    baseline_entries = []
    blocking_reasons: list[str] = []
    for baseline_name in REQUIRED_BASELINE_NAMES:
        manifest = manifests[baseline_name]
        manifest_violations = validate_source_manifest(manifest)
        upstream_path = external_root_path / baseline_name / "upstream"
        observed_head = inspect_git_head(upstream_path)
        expected_head = manifest.get("upstream_commit")
        source_checkout_ready = observed_head == expected_head
        if manifest_violations:
            blocking_reasons.append(f"{baseline_name}:source_manifest_invalid")
        if not source_checkout_ready:
            blocking_reasons.append(f"{baseline_name}:upstream_checkout_not_ready")
        if manifest.get("model_availability_status") != "weights_digest_ready":
            blocking_reasons.append(f"{baseline_name}:model_weights_need_colab_digest")
        if manifest.get("adapter_status") != "formal_adapter_ready":
            blocking_reasons.append(f"{baseline_name}:adapter_needs_colab_smoke")
        baseline_entries.append(
            {
                "baseline_name": baseline_name,
                "source_manifest_valid": not manifest_violations,
                "upstream_path": str(upstream_path),
                "expected_commit": expected_head,
                "observed_commit": observed_head,
                "source_checkout_ready": source_checkout_ready,
                "model_availability_status": manifest.get("model_availability_status"),
                "adapter_status": manifest.get("adapter_status"),
            }
        )

    stage_two_input = protocol_config.get("input_stage_package", {})
    missing_stage_two_fields = sorted(REQUIRED_STAGE_TWO_INPUT_FIELDS - set(stage_two_input))
    if missing_stage_two_fields:
        blocking_reasons.append("stage_two_input_package_contract_incomplete")

    stage_two_package_status = "not_checked"
    if stage_two_package_root is not None:
        stage_two_path = Path(stage_two_package_root)
        stage_two_package_status = "available" if stage_two_path.exists() else "missing"
        if not stage_two_path.exists():
            blocking_reasons.append("stage_two_package_root_missing")

    return {
        "project_stage": "baseline_comparison_gate",
        "preflight_status": "ready_for_colab_smoke" if not blocking_reasons else "requires_colab_or_setup",
        "baseline_entries": baseline_entries,
        "stage_two_input_package": stage_two_input,
        "stage_two_package_status": stage_two_package_status,
        "blocking_reasons": blocking_reasons,
        "next_required_environment": "colab_gpu" if blocking_reasons else "colab_gpu_smoke_optional_next",
    }

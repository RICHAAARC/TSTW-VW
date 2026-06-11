"""阶段三 baseline source intake 配置校验。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_BASELINE_NAMES = (
    "external_videoseal",
    "external_rivagan",
    "external_hidden_framewise",
)

REQUIRED_SOURCE_FIELDS = {
    "project_stage",
    "baseline_name",
    "baseline_family",
    "upstream_repository_url",
    "upstream_commit",
    "license_name",
    "license_url",
    "source_intake_status",
    "model_availability_status",
    "model_weight_sources",
    "adapter_status",
    "score_mapping_rule",
    "known_limitations",
    "allowed_reproduction_repairs",
    "forbidden_reproduction_changes",
}


def load_source_manifest(path: str | Path) -> dict[str, Any]:
    """读取单个 baseline source manifest。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_source_manifest(data: dict[str, Any]) -> list[dict[str, str]]:
    """校验 baseline source manifest 是否满足阶段三最小审计要求。"""
    violations: list[dict[str, str]] = []

    missing_fields = REQUIRED_SOURCE_FIELDS - set(data)
    for field_name in sorted(missing_fields):
        violations.append({"field": field_name, "reason": "missing_required_field"})

    if data.get("project_stage") != "baseline_comparison_gate":
        violations.append(
            {"field": "project_stage", "reason": "must_equal_baseline_comparison_gate"}
        )

    if data.get("baseline_name") not in REQUIRED_BASELINE_NAMES:
        violations.append({"field": "baseline_name", "reason": "unsupported_baseline_name"})

    upstream_commit = data.get("upstream_commit")
    if not isinstance(upstream_commit, str) or len(upstream_commit) != 40:
        violations.append({"field": "upstream_commit", "reason": "must_be_full_git_sha"})

    if data.get("license_name") in {None, "", "unknown"}:
        violations.append({"field": "license_name", "reason": "license_must_be_recorded"})

    weight_sources = data.get("model_weight_sources")
    if not isinstance(weight_sources, list) or not weight_sources:
        violations.append(
            {"field": "model_weight_sources", "reason": "must_be_non_empty_list"}
        )
    else:
        for index, weight_source in enumerate(weight_sources):
            if not isinstance(weight_source, dict):
                violations.append(
                    {"field": f"model_weight_sources[{index}]", "reason": "must_be_object"}
                )
                continue
            if "weight_digest_status" not in weight_source:
                violations.append(
                    {
                        "field": f"model_weight_sources[{index}].weight_digest_status",
                        "reason": "missing_weight_digest_status",
                    }
                )

    if data.get("adapter_status") == "formal_adapter_ready":
        if data.get("score_mapping_rule") in {None, "pending_smoke_run"}:
            violations.append(
                {"field": "score_mapping_rule", "reason": "formal_adapter_requires_score_mapping"}
            )

    return violations


def load_all_source_manifests(config_dir: str | Path) -> dict[str, dict[str, Any]]:
    """读取阶段三固定的三个 baseline source manifest。"""
    root = Path(config_dir)
    manifests: dict[str, dict[str, Any]] = {}
    for baseline_name in REQUIRED_BASELINE_NAMES:
        path = root / f"{baseline_name}_source.json"
        data = load_source_manifest(path)
        manifests[baseline_name] = data
    return manifests


def build_source_intake_summary(manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """生成不含实验结果的 source intake 摘要。"""
    entries = []
    for baseline_name in REQUIRED_BASELINE_NAMES:
        manifest = manifests[baseline_name]
        violations = validate_source_manifest(manifest)
        entries.append(
            {
                "baseline_name": baseline_name,
                "baseline_family": manifest.get("baseline_family"),
                "upstream_repository_url": manifest.get("upstream_repository_url"),
                "upstream_commit": manifest.get("upstream_commit"),
                "license_name": manifest.get("license_name"),
                "source_intake_status": manifest.get("source_intake_status"),
                "model_availability_status": manifest.get("model_availability_status"),
                "adapter_status": manifest.get("adapter_status"),
                "violation_count": len(violations),
            }
        )
    return {
        "project_stage": "baseline_comparison_gate",
        "baseline_count": len(entries),
        "entries": entries,
    }

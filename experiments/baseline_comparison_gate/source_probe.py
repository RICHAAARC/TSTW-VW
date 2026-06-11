"""阶段三外部 baseline 上游源码能力探测。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.baseline_comparison_gate.source_intake import REQUIRED_BASELINE_NAMES

BASELINE_SOURCE_PROBES = {
    "external_videoseal": {
        "required_files": [
            "README.md",
            "LICENSE",
            "requirements.txt",
            "inference_streaming.py",
            "videoseal/__init__.py",
        ],
        "entrypoint_hints": [
            "videoseal.load",
            "model.embed",
            "model.detect",
            "torchvision.io.read_video",
            "torchvision.io.write_video",
        ],
        "model_source_hints": [
            "y_256b_img.pth",
            "dl.fbaipublicfiles.com/videoseal",
        ],
    },
    "external_rivagan": {
        "required_files": [
            "README.md",
            "LICENSE",
            "setup.py",
            "rivagan/__init__.py",
        ],
        "entrypoint_hints": [
            "RivaGAN.load",
            "model.encode",
            "model.decode",
        ],
        "model_source_hints": [
            "model.pt",
        ],
    },
    "external_hidden_framewise": {
        "required_files": [
            "README.md",
            "LICENSE",
            "main.py",
        ],
        "entrypoint_hints": [
            "HiDDeN",
            "EncoderDecoder",
            "--noise",
        ],
        "model_source_hints": [
            "checkpoint",
            "experiments",
        ],
    },
}


def probe_baseline_source_tree(external_root: str | Path) -> dict[str, Any]:
    """探测三个 baseline 的上游源码是否包含预期入口线索。"""
    external_root_path = Path(external_root)
    entries = []
    blocking_reasons: list[str] = []
    for baseline_name in REQUIRED_BASELINE_NAMES:
        upstream_root = external_root_path / baseline_name / "upstream"
        probe_spec = BASELINE_SOURCE_PROBES[baseline_name]
        entry = probe_single_source_tree(baseline_name, upstream_root, probe_spec)
        entries.append(entry)
        if not entry["source_tree_present"]:
            blocking_reasons.append(f"{baseline_name}:source_tree_missing")
        if entry["missing_required_files"]:
            blocking_reasons.append(f"{baseline_name}:required_files_missing")
        if not entry["entrypoint_hints_found"]:
            blocking_reasons.append(f"{baseline_name}:entrypoint_hints_missing")
    return {
        "project_stage": "baseline_comparison_gate",
        "probe_status": "pass" if not blocking_reasons else "blocked",
        "entries": entries,
        "blocking_reasons": blocking_reasons,
    }


def probe_single_source_tree(
    baseline_name: str,
    upstream_root: Path,
    probe_spec: dict[str, list[str]],
) -> dict[str, Any]:
    """探测单个 baseline 源码树。"""
    source_tree_present = upstream_root.exists()
    missing_required_files = []
    existing_required_files = []
    for relative_path in probe_spec["required_files"]:
        path = upstream_root / relative_path
        if path.exists():
            existing_required_files.append(relative_path)
        else:
            missing_required_files.append(relative_path)

    searchable_text = collect_searchable_text(upstream_root) if source_tree_present else ""
    entrypoint_hints_found = [
        hint for hint in probe_spec["entrypoint_hints"] if hint.lower() in searchable_text.lower()
    ]
    model_source_hints_found = [
        hint for hint in probe_spec["model_source_hints"] if hint.lower() in searchable_text.lower()
    ]
    return {
        "baseline_name": baseline_name,
        "source_tree_present": source_tree_present,
        "upstream_root": str(upstream_root),
        "existing_required_files": existing_required_files,
        "missing_required_files": missing_required_files,
        "entrypoint_hints_found": entrypoint_hints_found,
        "model_source_hints_found": model_source_hints_found,
        "adapter_next_step": infer_adapter_next_step(baseline_name, entrypoint_hints_found),
    }


def collect_searchable_text(upstream_root: Path) -> str:
    """收集 README 和少量入口源码文本, 用于轻量能力探测。"""
    chunks: list[str] = []
    candidate_patterns = ["README.md", "*.py", "docs/*.md"]
    for pattern in candidate_patterns:
        for path in sorted(upstream_root.glob(pattern))[:30]:
            if path.is_file() and path.stat().st_size < 500_000:
                try:
                    chunks.append(path.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
    return "\n".join(chunks)


def infer_adapter_next_step(baseline_name: str, entrypoint_hints_found: list[str]) -> str:
    """根据源码入口线索给出 adapter 的下一步实现建议。"""
    if baseline_name == "external_videoseal" and "videoseal.load" in entrypoint_hints_found:
        return "implement_dynamic_videoseal_load_adapter"
    if baseline_name == "external_rivagan" and "RivaGAN.load" in entrypoint_hints_found:
        return "implement_rivagan_model_load_adapter_after_weight_resolution"
    if baseline_name == "external_hidden_framewise" and entrypoint_hints_found:
        return "implement_framewise_hidden_adapter_after_checkpoint_resolution"
    return "manual_source_review_required"

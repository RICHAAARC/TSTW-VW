"""汇总阶段三外部 baseline 真实 smoke 结果包。

该模块只读取已经完成的真实 smoke 结果包, 并生成审计友好的摘要。
它不执行模型推理, 不重新计算正式阈值, 也不把单视频 smoke 结果升级为论文 claim 证据。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from experiments.baseline_comparison_gate.record_schema import validate_baseline_record
from experiments.baseline_comparison_gate.source_intake import REQUIRED_BASELINE_NAMES
from main.core.digest import compute_file_digest, compute_object_digest

WORKFLOW_KEY = "baseline_comparison_gate"
REAL_SMOKE_RECORD_FILENAMES = {
    "external_videoseal": "external_videoseal_real_smoke_records.jsonl",
    "external_rivagan": "external_rivagan_real_smoke_records.jsonl",
    "external_hidden_framewise": "external_hidden_framewise_real_smoke_records.jsonl",
}
REAL_SMOKE_RUN_KIND = {
    "external_videoseal": "external_videoseal_real_smoke",
    "external_rivagan": "external_rivagan_real_smoke",
    "external_hidden_framewise": "external_hidden_framewise_real_smoke",
}
SUMMARY_FIELDS = [
    "baseline_name",
    "run_id",
    "run_kind",
    "status",
    "schema_pass",
    "records_digest_match",
    "record_count_match",
    "clean_score",
    "clean_decision",
    "clean_failure_reason",
    "h264_score",
    "h264_decision",
    "h264_failure_reason",
    "model_digest",
    "adapter_version",
    "claim_support_allowed",
    "formal_fixed_fpr_complete",
    "gpu_profiling_status",
    "gpu_name",
    "mean_gpu_util_percent",
    "median_gpu_util_percent",
    "peak_memory_used_mb",
    "peak_memory_ratio",
    "low_utilization_ratio",
    "estimated_gpu_usage_status",
    "limitation_reason",
]


def load_json(path: str | Path) -> dict[str, Any]:
    """读取 UTF-8 JSON 文件, 用于复用 Google Drive 落盘结果包。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """读取 JSONL records, 空行会被忽略以兼容手动查看后留下的尾部换行。"""
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def find_record_path(run_root: Path, baseline_name: str) -> Path:
    """定位单个真实 smoke 包中的 records 文件。"""
    expected = run_root / "records" / REAL_SMOKE_RECORD_FILENAMES[baseline_name]
    if expected.exists():
        return expected
    candidates = sorted((run_root / "records").glob("*_real_smoke_records.jsonl"))
    if len(candidates) == 1:
        return candidates[0]
    raise FileNotFoundError(f"无法定位真实 smoke records 文件: {run_root}")


def summarize_real_smoke_run(run_root: str | Path) -> dict[str, Any]:
    """汇总一个 baseline 真实 smoke 结果包。

    返回值只表达可运行性与包完整性, 不表达正式 fixed-FPR 比较结论。
    """
    run_root_path = Path(run_root)
    manifest_path = run_root_path / "manifest.json"
    manifest = load_json(manifest_path)
    baseline_name = manifest.get("baseline_name")
    if baseline_name not in REQUIRED_BASELINE_NAMES:
        raise ValueError(f"不支持的 baseline_name: {baseline_name}")

    record_path = find_record_path(run_root_path, baseline_name)
    records = load_jsonl(record_path)
    schema_violations = [validate_baseline_record(record) for record in records]
    schema_pass = all(not violations for violations in schema_violations)
    manifest_records_digest = manifest.get("records_digest")
    records_digest_match = manifest_records_digest in {
        compute_file_digest(record_path),
        compute_object_digest(records),
    }
    record_count_match = len(records) == manifest.get("record_count")
    attack_index = {record.get("attack_name"): record for record in records}
    clean_record = attack_index.get("clean", {})
    h264_record = attack_index.get("h264_crf_28", {})

    decisions = [record.get("decision") for record in records]
    package_pass = schema_pass and records_digest_match and record_count_match
    smoke_decision_pass = all(decision == "positive" for decision in decisions)
    if not package_pass:
        status = "real_smoke_invalid"
        limitation_reason = "package_or_schema_check_failed"
    elif smoke_decision_pass:
        status = "real_smoke_passed"
        limitation_reason = "single_baseline_smoke_only_not_formal_fixed_fpr"
    else:
        status = "real_smoke_executed_negative"
        limitation_reason = "single_baseline_smoke_score_below_threshold"

    gpu_profile = manifest.get("gpu_profile") or {}

    return {
        "baseline_name": baseline_name,
        "run_id": manifest.get("run_id"),
        "run_kind": manifest.get("run_kind"),
        "run_root": run_root_path.as_posix(),
        "status": status,
        "schema_pass": schema_pass,
        "schema_violations": schema_violations,
        "records_digest_match": records_digest_match,
        "record_count_match": record_count_match,
        "record_count": len(records),
        "manifest_record_count": manifest.get("record_count"),
        "clean_score": clean_record.get("baseline_score"),
        "clean_decision": clean_record.get("decision"),
        "clean_failure_reason": clean_record.get("failure_reason"),
        "h264_score": h264_record.get("baseline_score"),
        "h264_decision": h264_record.get("decision"),
        "h264_failure_reason": h264_record.get("failure_reason"),
        "model_digest": manifest.get("model_digest"),
        "adapter_version": manifest.get("adapter_version"),
        "claim_support_allowed": bool(manifest.get("claim_support_allowed")),
        "formal_fixed_fpr_complete": bool(manifest.get("formal_fixed_fpr_complete")),
        "gpu_profiling_status": gpu_profile.get("profiling_status"),
        "gpu_name": gpu_profile.get("gpu_name"),
        "mean_gpu_util_percent": gpu_profile.get("mean_gpu_util_percent"),
        "median_gpu_util_percent": gpu_profile.get("median_gpu_util_percent"),
        "peak_memory_used_mb": gpu_profile.get("peak_memory_used_mb"),
        "peak_memory_ratio": gpu_profile.get("peak_memory_ratio"),
        "low_utilization_ratio": gpu_profile.get("low_utilization_ratio"),
        "estimated_gpu_usage_status": gpu_profile.get("estimated_gpu_usage_status"),
        "limitation_reason": limitation_reason,
    }


def discover_latest_real_smoke_runs(result_root: str | Path) -> list[Path]:
    """在 results/<WORKFLOW_KEY>/ 下为每个 baseline 选择最新的真实 smoke 结果包。"""
    root = Path(result_root)
    workflow_root = root / WORKFLOW_KEY if root.name != WORKFLOW_KEY else root
    selected: list[Path] = []
    for baseline_name in REQUIRED_BASELINE_NAMES:
        pattern = f"{baseline_name}_real_smoke_*"
        baseline_real_smoke_root = workflow_root / baseline_name / "real_smoke"
        matches = sorted(path for path in baseline_real_smoke_root.glob(pattern) if path.is_dir())
        if not matches:
            matches = sorted(path for path in workflow_root.glob(pattern) if path.is_dir())
        if not matches:
            raise FileNotFoundError(f"缺少 {baseline_name} 的真实 smoke 结果包: {workflow_root}")
        selected.append(matches[-1])
    return selected


def summarize_real_smoke_runs(run_roots: Iterable[str | Path]) -> dict[str, Any]:
    """汇总多个真实 smoke 结果包, 并生成阶段三进入正式比较前的检查结论。"""
    entries = [summarize_real_smoke_run(run_root) for run_root in run_roots]
    missing = sorted(set(REQUIRED_BASELINE_NAMES) - {entry["baseline_name"] for entry in entries})
    duplicate_count = len(entries) - len({entry["baseline_name"] for entry in entries})
    package_ready = all(
        entry["schema_pass"]
        and entry["records_digest_match"]
        and entry["record_count_match"]
        for entry in entries
    )
    all_smoke_positive = all(entry["status"] == "real_smoke_passed" for entry in entries)
    return {
        "workflow_key": WORKFLOW_KEY,
        "summary_kind": "baseline_real_smoke_summary",
        "baseline_count": len(entries),
        "missing_baselines": missing,
        "duplicate_baseline_count": duplicate_count,
        "package_ready_for_formal_planning": package_ready and not missing and duplicate_count == 0,
        "all_real_smoke_scores_positive": all_smoke_positive,
        "claim_support_allowed": False,
        "formal_fixed_fpr_complete": False,
        "blocking_reason": "real_smoke_summary_only_not_fixed_fpr_baseline_comparison",
        "entries": entries,
        "summary_digest": compute_object_digest(entries),
    }


def write_summary_outputs(summary: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    """写出 JSON、CSV 和 Markdown 摘要, 供 notebook 或人工审查复用。"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "baseline_real_smoke_summary.json"
    csv_path = output_path / "baseline_real_smoke_summary.csv"
    markdown_path = output_path / "baseline_real_smoke_summary.md"

    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for entry in summary["entries"]:
            writer.writerow({field: entry.get(field) for field in SUMMARY_FIELDS})
    markdown_path.write_text(build_summary_markdown(summary), encoding="utf-8")
    return {
        "json_path": json_path.as_posix(),
        "csv_path": csv_path.as_posix(),
        "markdown_path": markdown_path.as_posix(),
    }


def build_summary_markdown(summary: dict[str, Any]) -> str:
    """生成面向人工审查的真实 smoke 汇总报告。"""
    lines = [
        "# baseline real smoke summary",
        "",
        "该报告只汇总外部 baseline 的单视频真实 smoke 结果, 不能支撑正式论文 claim。",
        "正式比较仍需同一 split、同一 attack matrix、calibration split 固定 FPR 阈值和 test split 记录。",
        "",
        f"- package_ready_for_formal_planning: `{summary['package_ready_for_formal_planning']}`",
        f"- all_real_smoke_scores_positive: `{summary['all_real_smoke_scores_positive']}`",
        f"- claim_support_allowed: `{summary['claim_support_allowed']}`",
        f"- formal_fixed_fpr_complete: `{summary['formal_fixed_fpr_complete']}`",
        "",
        "| baseline_name | status | clean_score | h264_score | gpu_status | mean_gpu_util | peak_memory_mb | limitation_reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in summary["entries"]:
        lines.append(
            "| {baseline_name} | {status} | {clean_score} | {h264_score} | {estimated_gpu_usage_status} | {mean_gpu_util_percent} | {peak_memory_used_mb} | {limitation_reason} |".format(
                **entry
            )
        )
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "1. 将 package_ready_for_formal_planning 为 true 作为进入正式 baseline comparison runner 的前置条件。",
            "2. 对 smoke 阴性的 baseline 保留 limitation, 但不要把它描述为原生视频水印方法的成功结果。",
            "3. 后续必须生成 baseline_comparison_table、baseline_attack_breakdown、baseline_threshold_table 和 claim audit。",
        ]
    )
    return "\n".join(lines) + "\n"

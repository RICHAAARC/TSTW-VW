"""检查并准备阶段二 real-video VAE 正式结果包。

该模块服务于 `baseline_comparison_gate`: 它只验证阶段二结果包是否可作为正式 baseline
comparison 的输入, 并可把归档包解压到 Colab 会话本地目录。它不会重跑 VAE, 也不会生成新的
阶段二实验结果。
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import zipfile
from typing import Any

REQUIRED_PACKAGE_RELATIVE_PATHS = {
    "event_scores": "records/event_scores.jsonl",
    "thresholds": "thresholds/thresholds.json",
    "main_tpr_fpr_table": "tables/main_tpr_fpr_table.csv",
    "real_video_attack_breakdown": "tables/real_video_attack_breakdown.csv",
    "quality_table": "tables/quality_table.csv",
    "temporal_consistency_table": "tables/temporal_consistency_table.csv",
    "run_manifest": "artifacts/run_manifest.json",
    "runtime_config": "artifacts/runtime_config.json",
    "artifact_manifest": "artifacts/artifact_manifest.json",
    "runtime_manifest": "artifacts/runtime_manifest.json",
}


def load_json(path: str | Path) -> dict[str, Any]:
    """读取 UTF-8 JSON 文件。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def locate_stage_two_archive(package_root: str | Path) -> Path:
    """定位阶段二正式结果包中的可解压归档。

    优先使用兼容性更好的 zip 包。tar.zst 包仍保留为正式压缩包, 但在 Colab 冷启动中 zip
    可直接由 Python 标准库读取, 更适合作为阶段三输入检查路径。
    """
    root = Path(package_root)
    zip_path = root / "packages" / "real_video_vae_latent_probe_formal.zip"
    if zip_path.exists():
        return zip_path
    tar_zst_path = root / "packages" / "real_video_vae_latent_probe_formal.tar.zst"
    if tar_zst_path.exists():
        return tar_zst_path
    raise FileNotFoundError(f"未找到阶段二正式归档包: {root}")


def inspect_stage_two_package(package_root: str | Path) -> dict[str, Any]:
    """检查阶段二正式结果包是否满足阶段三 baseline comparison 的输入要求。"""
    root = Path(package_root)
    family_checks_path = root / "family_checks.json"
    family_manifest_path = root / "family_manifest.json"
    family_summary_path = root / "family_summary.json"
    archive_path = locate_stage_two_archive(root)
    archive_format = "zip" if archive_path.suffix == ".zip" else "tar.zst"

    family_checks = load_json(family_checks_path) if family_checks_path.exists() else {}
    family_manifest = load_json(family_manifest_path) if family_manifest_path.exists() else {}
    family_summary = load_json(family_summary_path) if family_summary_path.exists() else {}
    archive_listing = list_archive_members(archive_path)
    package_root_prefix = infer_archive_root_prefix(archive_listing)
    required_paths = {
        key: f"{package_root_prefix}/{relative_path}" in archive_listing
        for key, relative_path in REQUIRED_PACKAGE_RELATIVE_PATHS.items()
    }

    formal_checks = family_checks.get("formal_checks", {})
    mechanism_summary = family_checks.get("stage2_mechanism_summary", {})
    quality_metrics_enabled = mechanism_summary.get("quality_metrics_enabled", {})
    decision_pass = (
        family_checks.get("status") is True
        and formal_checks.get("status") is True
        and mechanism_summary.get("Stage2ImplementationDecision") == "PASS"
        and mechanism_summary.get("Stage2MechanismDecision") == "PASS"
    )
    metrics_ready = (
        formal_checks.get("lpips_evidence_available") is True
        and quality_metrics_enabled.get("lpips") is True
        and quality_metrics_enabled.get("clip_similarity") is True
    )
    required_paths_ready = all(required_paths.values())
    package_ready = decision_pass and metrics_ready and required_paths_ready

    return {
        "package_root": root.as_posix(),
        "archive_path": archive_path.as_posix(),
        "archive_format": archive_format,
        "archive_exists": archive_path.exists(),
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_root_prefix": package_root_prefix,
        "family_id": family_manifest.get("family_id") or family_summary.get("family_id"),
        "run_id": mechanism_summary.get("run_id"),
        "record_count": family_summary.get("formal_validation_summary", {}).get("record_count"),
        "threshold_count": family_summary.get("formal_validation_summary", {}).get("threshold_count"),
        "stage2_implementation_decision": mechanism_summary.get("Stage2ImplementationDecision"),
        "stage2_mechanism_decision": mechanism_summary.get("Stage2MechanismDecision"),
        "lpips_evidence_available": formal_checks.get("lpips_evidence_available"),
        "clip_similarity_enabled": quality_metrics_enabled.get("clip_similarity"),
        "quality_metrics_enabled": quality_metrics_enabled,
        "required_paths": required_paths,
        "decision_pass": decision_pass,
        "metrics_ready": metrics_ready,
        "required_paths_ready": required_paths_ready,
        "package_ready_for_baseline_comparison": package_ready,
        "rerun_real_video_vae_required": not package_ready,
        "blocking_reason": None if package_ready else "stage_two_package_not_ready_for_baseline_comparison",
    }


def list_archive_members(archive_path: str | Path) -> set[str]:
    """列出归档包成员路径。当前正式检查只要求 zip 可直接枚举。"""
    path = Path(archive_path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return set(archive.namelist())
    raise ValueError("当前阶段三输入检查要求使用 zip 兼容包, tar.zst 仅作为压缩归档保留")


def infer_archive_root_prefix(members: set[str]) -> str:
    """推断归档包内的单一根目录名。"""
    prefixes = {member.split("/", 1)[0] for member in members if "/" in member}
    if len(prefixes) != 1:
        raise ValueError(f"阶段二归档包应只有一个根目录, 实际为: {sorted(prefixes)}")
    return next(iter(prefixes))


def extract_stage_two_zip_package(
    *,
    package_root: str | Path,
    extract_root: str | Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """把阶段二 zip 兼容包解压到会话本地目录。

    该函数用于 Colab 冷启动复用阶段二结果。解压前会先完成输入包检查, 避免把无效结果包
    带入正式 baseline comparison runner。
    """
    inspection = inspect_stage_two_package(package_root)
    if not inspection["package_ready_for_baseline_comparison"]:
        raise ValueError(f"阶段二结果包不可用于 baseline comparison: {inspection}")
    archive_path = Path(inspection["archive_path"])
    if inspection["archive_format"] != "zip":
        raise ValueError("当前解压入口只支持 zip 兼容包")

    destination_root = Path(extract_root)
    package_dir = destination_root / inspection["archive_root_prefix"]
    if package_dir.exists():
        if not overwrite:
            return {**inspection, "extracted": False, "extracted_package_root": package_dir.as_posix()}
        shutil.rmtree(package_dir)
    destination_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination_root)
    return {**inspection, "extracted": True, "extracted_package_root": package_dir.as_posix()}

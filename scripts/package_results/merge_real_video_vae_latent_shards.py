"""合并阶段二 real-video VAE latent probe 的 shard 运行结果。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.real_video_vae_latent_probe.artifact_builder import (  # noqa: E402
    RealVideoVaeLatentArtifactBuilder,
)
from experiments.real_video_vae_latent_probe.mechanism_audit import (  # noqa: E402
    run_stage2_mechanism_audit,
)
from experiments.real_video_vae_latent_probe.output_layout import (  # noqa: E402
    build_real_video_vae_latent_output_paths,
)
from main.core.digest import compute_file_digest, compute_object_digest, compute_path_collection_digest  # noqa: E402
from main.core.records import RecordWriter  # noqa: E402
from main.core.registry import load_json_config  # noqa: E402
from main.protocol.calibrator import ThresholdCalibrator  # noqa: E402
from main.protocol.threshold_decision_materialization import materialize_threshold_decisions  # noqa: E402
from scripts.check_results.check_real_video_vae_latent_outputs import (  # noqa: E402
    check_real_video_vae_latent_outputs,
)
from scripts.package_results.package_real_video_vae_latent_outputs import (  # noqa: E402
    package_real_video_vae_latent_outputs,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="合并阶段二 shard run, 重新标定 threshold, 并生成正式聚合结果包。"
    )
    parser.add_argument("--shard-root", action="append", required=True, help="shard run 目录或 shard zip。")
    parser.add_argument("--merged-run-root", required=True, help="session-local 聚合 run root。")
    parser.add_argument("--family-root", required=True, help="聚合结果 family root。")
    parser.add_argument("--protocol-config", default="configs/protocol/real_video_vae_latent_probe.json")
    parser.add_argument("--mechanism-config", default="configs/protocol/stage2_mechanism_gate.json")
    parser.add_argument("--runtime-profile", default="formal")
    parser.add_argument("--short-commit", default=None)
    parser.add_argument("--exclude-large-intermediate-latents", action="store_true")
    return parser.parse_args()


def main() -> None:
    """执行 shard 聚合。"""
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="tstw_stage2_shard_merge_") as temp_dir:
        temp_root = Path(temp_dir)
        shard_roots = [
            _materialize_shard_root(Path(raw_root), temp_root / f"shard_{index:02d}")
            for index, raw_root in enumerate(args.shard_root)
        ]
        merged_run_root = Path(args.merged_run_root)
        if merged_run_root.exists():
            shutil.rmtree(merged_run_root)
        merged_run_root.mkdir(parents=True, exist_ok=True)
        summary = merge_stage_two_shards(
            shard_roots=shard_roots,
            merged_run_root=merged_run_root,
            family_root=Path(args.family_root),
            protocol_config_path=Path(args.protocol_config),
            mechanism_config_path=Path(args.mechanism_config),
            runtime_profile=args.runtime_profile,
            short_commit=args.short_commit,
            exclude_large_intermediate_latents=args.exclude_large_intermediate_latents,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))


def merge_stage_two_shards(
    *,
    shard_roots: list[Path],
    merged_run_root: Path,
    family_root: Path,
    protocol_config_path: Path,
    mechanism_config_path: Path,
    runtime_profile: str,
    short_commit: str | None,
    exclude_large_intermediate_latents: bool,
) -> dict[str, Any]:
    """合并 shard records 并生成可供下一阶段使用的正式结果包。"""
    if not shard_roots:
        raise ValueError("至少需要一个 shard root")
    protocol_config = load_json_config(protocol_config_path)
    shard_infos = [_load_shard_info(shard_root) for shard_root in shard_roots]
    _validate_shard_coverage(shard_infos)
    records = _load_and_rewrite_records(shard_infos, merged_run_root.name)
    thresholds = _recalibrate_thresholds(
        records=records,
        protocol_config=protocol_config,
        runtime_profile=runtime_profile,
        run_id=merged_run_root.name,
    )
    materialized_records = _materialize_records_with_thresholds(records, thresholds)
    record_writer = RecordWriter(merged_run_root)
    record_writer.write_event_score_records(materialized_records)
    record_writer.write_threshold_records(thresholds)
    artifact_builder = RealVideoVaeLatentArtifactBuilder()
    artifact_builder.build_artifacts(materialized_records, thresholds, merged_run_root)
    _write_merged_manifests(
        merged_run_root=merged_run_root,
        shard_infos=shard_infos,
        records=materialized_records,
        thresholds=thresholds,
        protocol_config_path=protocol_config_path,
        short_commit=short_commit,
    )
    mechanism_summary = run_stage2_mechanism_audit(
        run_root=merged_run_root,
        mechanism_config_path=mechanism_config_path,
    )
    formal_summary = check_real_video_vae_latent_outputs(
        run_root=merged_run_root,
        construction_phase="real_video_vae_latent_probe",
        run_mode="formal",
        require_formal_pass_criteria=True,
    )
    package_payload = package_real_video_vae_latent_outputs(
        run_root=merged_run_root,
        family_root=family_root,
        exclude_large_intermediate_latents=exclude_large_intermediate_latents,
    )
    _write_family_stage_two_baseline_handoff(
        family_root=family_root,
        formal_summary=formal_summary,
        mechanism_summary=mechanism_summary,
        package_payload=package_payload,
    )
    aggregation_summary = {
        "status": bool(formal_summary.get("status")) and mechanism_summary.get("Stage2MechanismDecision") == "PASS",
        "merged_run_root": merged_run_root.as_posix(),
        "family_root": family_root.as_posix(),
        "record_count": len(materialized_records),
        "threshold_count": len(thresholds),
        "shard_count": shard_infos[0]["shard_count"],
        "shard_indexes": sorted(info["shard_index"] for info in shard_infos),
        "formal_summary": formal_summary,
        "mechanism_summary": mechanism_summary,
        "package_payload": _json_safe(package_payload),
    }
    (family_root / "shard_aggregation_summary.json").write_text(
        json.dumps(aggregation_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return aggregation_summary



def _write_family_stage_two_baseline_handoff(
    *,
    family_root: Path,
    formal_summary: dict[str, Any],
    mechanism_summary: dict[str, Any],
    package_payload: dict[str, Any],
) -> None:
    """补齐阶段三输入检查所需的 family 级 formal 与 mechanism 字段。

    package_real_video_vae_latent_outputs 会生成通用 family 元数据, 但它内部的轻量
    package check 不会携带聚合后的 strict formal summary。阶段三只应消费聚合后的
    formal gate 结果, 因此这里把该结果显式写回 family_checks 与 family_summary。
    """
    family_root.mkdir(parents=True, exist_ok=True)
    family_checks_path = family_root / "family_checks.json"
    family_summary_path = family_root / "family_summary.json"
    family_manifest_path = family_root / "family_manifest.json"
    family_checks = json.loads(family_checks_path.read_text(encoding="utf-8")) if family_checks_path.exists() else {}
    family_summary = json.loads(family_summary_path.read_text(encoding="utf-8")) if family_summary_path.exists() else {}
    family_manifest = json.loads(family_manifest_path.read_text(encoding="utf-8")) if family_manifest_path.exists() else {}
    family_checks.update(
        {
            "status": bool(formal_summary.get("status"))
            and mechanism_summary.get("Stage2ImplementationDecision") == "PASS"
            and mechanism_summary.get("Stage2MechanismDecision") == "PASS",
            "formal_checks": formal_summary.get("formal_checks") or {},
            "formal_summary": formal_summary,
            "stage2_mechanism_summary": mechanism_summary,
        }
    )
    family_summary.update(
        {
            "formal_validation_summary": formal_summary,
            "stage2_mechanism_summary": mechanism_summary,
            "package_payload": _json_safe(package_payload),
        }
    )
    family_manifest.update(
        {
            "formal_validation_summary": formal_summary,
            "stage2_mechanism_summary": mechanism_summary,
        }
    )
    family_checks_path.write_text(json.dumps(family_checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    family_summary_path.write_text(json.dumps(family_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    family_manifest_path.write_text(json.dumps(family_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def _materialize_shard_root(source: Path, destination: Path) -> Path:
    if source.is_dir():
        return _find_run_root(source)
    if source.suffix.lower() != ".zip":
        raise ValueError(f"不支持的 shard 输入: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        archive.extractall(destination)
    return _find_run_root(destination)


def _find_run_root(root: Path) -> Path:
    candidates = [root] + [path for path in root.rglob("*") if path.is_dir()]
    for candidate in candidates:
        if (candidate / "records" / "event_scores.jsonl").exists() and (
            candidate / "artifacts" / "runtime_config.json"
        ).exists():
            return candidate
    raise FileNotFoundError(f"未找到 shard run root: {root}")


def _load_shard_info(shard_root: Path) -> dict[str, Any]:
    runtime_config = json.loads(
        (shard_root / "artifacts" / "runtime_config.json").read_text(encoding="utf-8")
    )
    run_manifest = json.loads(
        (shard_root / "artifacts" / "run_manifest.json").read_text(encoding="utf-8")
    )
    event_scores_path = shard_root / "records" / "event_scores.jsonl"
    return {
        "shard_root": shard_root,
        "runtime_config": runtime_config,
        "run_manifest": run_manifest,
        "event_scores_path": event_scores_path,
        "shard_count": int(runtime_config.get("shard_count", 1)),
        "shard_index": int(runtime_config.get("shard_index", 0)),
        "git_commit": runtime_config.get("git_commit"),
        "dataset_manifest_path": runtime_config.get("dataset_manifest_path"),
    }


def _validate_shard_coverage(shard_infos: list[dict[str, Any]]) -> None:
    shard_counts = {info["shard_count"] for info in shard_infos}
    if len(shard_counts) != 1:
        raise ValueError(f"shard_count 不一致: {sorted(shard_counts)}")
    shard_count = next(iter(shard_counts))
    shard_indexes = sorted(info["shard_index"] for info in shard_infos)
    expected_indexes = list(range(shard_count))
    if shard_indexes != expected_indexes:
        raise ValueError(f"shard_index 覆盖不完整: actual={shard_indexes}, expected={expected_indexes}")
    commits = {str(info.get("git_commit") or "")[:7] for info in shard_infos}
    if len(commits) != 1:
        raise ValueError(f"shard short commit 不一致: {sorted(commits)}")


def _load_and_rewrite_records(shard_infos: list[dict[str, Any]], merged_run_id: str) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for info in shard_infos:
        with Path(info["event_scores_path"]).open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                record["run_id"] = merged_run_id
                event_id = str(record["event_id"])
                if event_id in records_by_id:
                    raise ValueError(f"重复 event_id: {event_id}")
                records_by_id[event_id] = record
    return [records_by_id[key] for key in sorted(records_by_id)]


def _recalibrate_thresholds(
    *,
    records: list[dict[str, Any]],
    protocol_config: dict[str, Any],
    runtime_profile: str,
    run_id: str,
) -> list[dict[str, Any]]:
    calibrator = ThresholdCalibrator()
    thresholds: list[dict[str, Any]] = []
    for method_variant in sorted({str(record["method_variant"]) for record in records}):
        method_config = load_json_config(ROOT / "configs" / "method" / f"{method_variant}.json")
        method_records = [record for record in records if record["method_variant"] == method_variant]
        threshold_record = calibrator.calibrate(
            run_id,
            method_config,
            protocol_config,
            method_records,
            runtime_profile_override=runtime_profile,
        )
        threshold_record = dict(threshold_record)
        threshold_record["threshold_id"] = (
            f"{threshold_record['threshold_id']}:{protocol_config['construction_phase']}"
        )
        threshold_record["construction_phase"] = protocol_config["construction_phase"]
        thresholds.append(threshold_record)
    return thresholds


def _materialize_records_with_thresholds(
    records: list[dict[str, Any]],
    thresholds: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    threshold_by_method = {str(item["method_variant"]): item for item in thresholds}
    materialized: list[dict[str, Any]] = []
    for method_variant in sorted(threshold_by_method):
        method_records = [record for record in records if record["method_variant"] == method_variant]
        calibration_records = [record for record in method_records if record["split"] == "calibration"]
        non_calibration_records = [record for record in method_records if record["split"] != "calibration"]
        materialized.extend(
            materialize_threshold_decisions(
                calibration_records,
                threshold_by_method[method_variant],
                attach_threshold_id=False,
            )
        )
        materialized.extend(
            materialize_threshold_decisions(
                non_calibration_records,
                threshold_by_method[method_variant],
                attach_threshold_id=True,
            )
        )
    return sorted(materialized, key=lambda record: str(record.get("event_id", "")))


def _write_merged_manifests(
    *,
    merged_run_root: Path,
    shard_infos: list[dict[str, Any]],
    records: list[dict[str, Any]],
    thresholds: list[dict[str, Any]],
    protocol_config_path: Path,
    short_commit: str | None,
) -> None:
    output_paths = build_real_video_vae_latent_output_paths(merged_run_root)
    for manifest_path in [
        output_paths.runtime_config_path,
        output_paths.runtime_manifest_path,
        output_paths.artifact_manifest_path,
        output_paths.run_manifest_path,
    ]:
        # 聚合流程会先由 RecordWriter 和 ArtifactBuilder 写入 records、thresholds、tables、figures、reports。
        # artifacts 目录并不一定已经存在, 因此这里在写入 manifest 前统一创建父目录。
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_config = dict(shard_infos[0]["runtime_config"])
    runtime_config.update(
        {
            "shard_aggregation": True,
            "source_shard_count": shard_infos[0]["shard_count"],
            "source_shard_indexes": sorted(info["shard_index"] for info in shard_infos),
            "short_commit": short_commit or str(runtime_config.get("git_commit", ""))[:7],
        }
    )
    output_paths.runtime_config_path.write_text(
        json.dumps(runtime_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    runtime_manifest = dict(
        json.loads((shard_infos[0]["shard_root"] / "artifacts" / "runtime_manifest.json").read_text(encoding="utf-8"))
    )
    runtime_manifest.update(
        {
            "run_id": merged_run_root.name,
            "shard_aggregation": True,
            "source_shard_count": shard_infos[0]["shard_count"],
            "source_shard_indexes": sorted(info["shard_index"] for info in shard_infos),
        }
    )
    output_paths.runtime_manifest_path.write_text(
        json.dumps(runtime_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    artifact_manifest = _build_minimal_artifact_manifest(records)
    output_paths.artifact_manifest_path.write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    run_manifest = {
        "run_id": merged_run_root.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "construction_phase": "real_video_vae_latent_probe",
        "protocol_name": "fixed_low_fpr_calibrated_detection",
        "protocol_config_digest": compute_file_digest(protocol_config_path),
        "runtime_config_digest": compute_file_digest(output_paths.runtime_config_path),
        "records_digest": compute_object_digest(records),
        "thresholds_digest": compute_object_digest(thresholds),
        "tables_digest": compute_path_collection_digest(output_paths.table_paths()),
        "figures_digest": compute_path_collection_digest(output_paths.figure_paths()),
        "placeholder_fields": [],
        "random_fields": ["latent_generation_seed_random"],
    }
    output_paths.run_manifest_path.write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_minimal_artifact_manifest(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        trace = record.get("mechanism_trace", {})
        if not isinstance(trace, dict):
            continue
        for kind, rel_key, digest_key in (
            ("decoded_video", "decoded_video_relpath", "decoded_video_digest"),
            ("attacked_video", "attacked_video_relpath", "attacked_video_digest"),
            ("reencoded_latent", "reencoded_latent_relpath", "reencoded_latent_digest"),
        ):
            relpath = trace.get(rel_key)
            digest = trace.get(digest_key)
            if isinstance(relpath, str) and isinstance(digest, str):
                entries[(kind, relpath)] = {
                    "artifact_kind": kind,
                    "artifact_relpath": relpath,
                    "artifact_digest": digest,
                }
    return [entries[key] for key in sorted(entries)]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


if __name__ == "__main__":
    main()

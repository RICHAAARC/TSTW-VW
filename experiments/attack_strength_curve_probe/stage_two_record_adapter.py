"""从阶段二真实视频 VAE records 生成攻击强度曲线基础 records。

该模块的作用是把已经完成的 `real_video_vae_latent_probe` records 转换为
`attack_strength_curve_probe` 可以消费的基础数据。它不会重新运行 VAE, 也不会新增攻击强度。

这一实现属于项目特定的过渡实现: 它用于先产出攻击强度曲线所需的基础 records,
便于验证后续聚合、绘图和 paper artifact 链路。若要支撑完整投稿 claim, 后续仍应
由真实多强度攻击 runner 生成多强度 sweep records。
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from main.core.digest import compute_file_digest, compute_object_digest

from experiments.attack_strength_curve_probe.attack_strength_builder import (
    ATTACKS,
    INTERNAL_METHODS,
    WORKFLOW_KEY,
    resolve_short_commit,
    utc_timestamp,
    write_jsonl,
)

STAGE_TWO_ZIP_MEMBER_PREFIX = "real_video_vae_latent_probe_shard_aggregated"
DEFAULT_SOURCE_MODE = "from_stage_two_existing_records"


def latest_child_dir(root: str | Path) -> Path | None:
    """返回目录下最近修改的子目录。"""
    root_path = Path(root)
    if not root_path.exists():
        return None
    children = [path for path in root_path.iterdir() if path.is_dir()]
    if not children:
        return None
    return max(children, key=lambda path: path.stat().st_mtime)


def discover_latest_stage_two_root(result_root: str | Path) -> Path:
    """从 TSTW results 根目录发现最新阶段二聚合结果。"""
    stage_two_root = latest_child_dir(Path(result_root) / "real_video_vae_latent_probe" / "shard_aggregated")
    if stage_two_root is None:
        raise FileNotFoundError("未找到 real_video_vae_latent_probe/shard_aggregated 下的阶段二聚合结果。")
    return stage_two_root


def resolve_stage_two_event_scores_path(stage_two_root: str | Path) -> tuple[Path, str | None]:
    """定位阶段二 event_scores 来源。

    返回值中的第二个元素表示 zip 内部 member 名称。若为 `None`, 表示第一个元素本身就是
    可直接读取的 JSONL 文件。
    """
    root = Path(stage_two_root)
    direct_path = root / "records" / "event_scores.jsonl"
    if direct_path.exists():
        return direct_path, None
    packages_dir = root / "packages"
    candidates = sorted(packages_dir.glob("*.zip")) if packages_dir.exists() else []
    if not candidates:
        raise FileNotFoundError(f"阶段二聚合目录缺少 records/event_scores.jsonl 或 packages/*.zip: {root}")
    archive_path = candidates[0]
    member_name = f"{STAGE_TWO_ZIP_MEMBER_PREFIX}/records/event_scores.jsonl"
    with zipfile.ZipFile(archive_path) as archive:
        if member_name not in archive.namelist():
            raise FileNotFoundError(f"阶段二 zip 缺少 {member_name}: {archive_path}")
    return archive_path, member_name


def read_stage_two_event_scores(stage_two_root: str | Path) -> list[dict[str, Any]]:
    """读取阶段二 event_scores records。"""
    source_path, member_name = resolve_stage_two_event_scores_path(stage_two_root)
    if member_name is None:
        text = source_path.read_text(encoding="utf-8")
    else:
        with zipfile.ZipFile(source_path) as archive:
            text = archive.read(member_name).decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def score_of_stage_two_record(record: dict[str, Any]) -> float | None:
    """从阶段二 record 中解析最终检测分数。"""
    evidence_scores = record.get("evidence_scores") or {}
    if evidence_scores.get("S_final") is not None:
        return float(evidence_scores["S_final"])
    if record.get("score") is not None:
        return float(record["score"])
    if record.get("S_final") is not None:
        return float(record["S_final"])
    return None


def derive_attack_strength(record: dict[str, Any]) -> tuple[str, float]:
    """从阶段二 attack_params 中推导曲线横轴强度。

    通用写法是优先读取显式 attack_params。项目特定写法是对缺失强度的历史 records
    使用每类攻击的协议默认值, 并在输出 record 中用 `source_mode` 标记来源。
    """
    params = record.get("attack_params") or {}
    attack_name = str(record.get("attack_name"))
    if "crf" in params:
        value = float(params["crf"])
        return f"crf_{int(value)}", value
    if "keep_ratio" in params:
        value = float(params["keep_ratio"])
        return f"keep_{value:.2f}", value
    if "crop_ratio" in params:
        value = float(params["crop_ratio"])
        return f"keep_{value:.2f}", value
    if "drop_rate" in params:
        value = float(params["drop_rate"])
        return f"drop_{value:.2f}", value
    if "frame_drop_rate" in params:
        value = float(params["frame_drop_rate"])
        return f"drop_{value:.2f}", value
    defaults = {
        "h264_compression": ("crf_23", 23.0),
        "h265_compression": ("crf_23", 23.0),
        "temporal_crop": ("keep_0.75", 0.75),
        "frame_dropping": ("drop_0.20", 0.20),
    }
    return defaults.get(attack_name, ("default", 0.0))


def convert_stage_two_records_to_attack_strength_records(
    records: list[dict[str, Any]],
    *,
    method_names: tuple[str, ...] = INTERNAL_METHODS,
    attack_names: tuple[str, ...] = ATTACKS,
    max_records_per_group: int | None = None,
    source_mode: str = DEFAULT_SOURCE_MODE,
) -> list[dict[str, Any]]:
    """转换阶段二 records 为攻击强度曲线基础 records。"""
    selected: list[dict[str, Any]] = []
    group_counts: dict[tuple[str, str, str, str], int] = {}
    method_set = set(method_names)
    attack_set = set(attack_names)
    for record in records:
        method_name = str(record.get("method_variant") or record.get("method_name") or "")
        attack_name = str(record.get("attack_name") or "")
        split = str(record.get("split") or "")
        sample_role = str(record.get("sample_role") or "")
        if method_name not in method_set or attack_name not in attack_set:
            continue
        score = score_of_stage_two_record(record)
        if score is None:
            continue
        strength_name, strength_value = derive_attack_strength(record)
        group_key = (method_name, attack_name, split, sample_role)
        if max_records_per_group is not None and group_counts.get(group_key, 0) >= max_records_per_group:
            continue
        group_counts[group_key] = group_counts.get(group_key, 0) + 1
        selected.append(
            {
                "method_name": method_name,
                "attack_name": attack_name,
                "attack_strength_name": strength_name,
                "attack_strength_value": strength_value,
                "split": split,
                "sample_role": sample_role,
                "score": float(score),
                "source_mode": source_mode,
                "stage_two_run_id": record.get("run_id"),
                "stage_two_event_id": record.get("event_id"),
                "stage_two_sample_id": record.get("sample_id"),
                "source_artifact": "real_video_vae_latent_probe/records/event_scores.jsonl",
            }
        )
    return selected


def write_attack_strength_shard_from_stage_two(
    *,
    output_root: str | Path,
    stage_two_root: str | Path,
    run_id: str | None = None,
    method_names: tuple[str, ...] = INTERNAL_METHODS,
    attack_names: tuple[str, ...] = ATTACKS,
    max_records_per_group: int | None = None,
) -> dict[str, Any]:
    """从阶段二 records 生成一个 attack_strength_curve_probe shard run。"""
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)
    actual_run_id = run_id or f"{WORKFLOW_KEY}_base_records_{utc_timestamp()}_{resolve_short_commit()[:7]}"
    source_records = read_stage_two_event_scores(stage_two_root)
    attack_strength_records = convert_stage_two_records_to_attack_strength_records(
        source_records,
        method_names=method_names,
        attack_names=attack_names,
        max_records_per_group=max_records_per_group,
    )
    if not attack_strength_records:
        raise ValueError("阶段二 records 未能转换出任何 attack_strength_event_scores。")
    record_path = output_root_path / "records" / "attack_strength_event_scores.jsonl"
    write_jsonl(record_path, attack_strength_records)
    manifest = {
        "workflow_key": WORKFLOW_KEY,
        "run_id": actual_run_id,
        "source_mode": DEFAULT_SOURCE_MODE,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "stage_two_root": Path(stage_two_root).as_posix(),
        "record_count": len(attack_strength_records),
        "method_names": sorted({row["method_name"] for row in attack_strength_records}),
        "attack_names": sorted({row["attack_name"] for row in attack_strength_records}),
        "strength_points": sorted(
            {
                f"{row['attack_name']}:{row['attack_strength_name']}"
                for row in attack_strength_records
            }
        ),
        "claim_support_allowed": False,
        "claim_support_blocking_reason": "base_records_only_not_full_multi_strength_sweep",
        "source_digest": compute_object_digest(
            {
                "stage_two_root": Path(stage_two_root).as_posix(),
                "method_names": method_names,
                "attack_names": attack_names,
                "max_records_per_group": max_records_per_group,
            }
        ),
        "artifact_digests": {
            "attack_strength_event_scores": compute_file_digest(record_path),
        },
    }
    manifest_path = output_root_path / "artifacts" / "attack_strength_base_records_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix(), "output_root": output_root_path.as_posix()}


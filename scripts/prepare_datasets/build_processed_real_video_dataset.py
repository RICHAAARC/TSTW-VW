"""
File purpose: Build a governed processed real-video dataset from a raw archive or raw manifest.
Module type: General module
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np

from main.core.digest import compute_file_digest, compute_object_digest
from main.video.frame_preprocess import standardize_video_frames
from main.video.video_io import read_video_frames, write_video_mp4


SUPPORTED_VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")
SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


@dataclass(frozen=True)
class RawSource:
    """Describe a raw source item used to build a processed dataset."""

    source_path: Path
    source_kind: str
    source_key: str


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object")
    return payload


def _sanitize_slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "sample"


def _resolve_candidate_path(candidate_value: str, base_path: Path) -> Path:
    candidate_path = Path(candidate_value)
    if candidate_path.is_absolute():
        return candidate_path
    return (base_path / candidate_path).resolve()


def _resolve_raw_archive_path(
    *,
    raw_dataset_download_manifest_path: str | Path | None,
    raw_dataset_key: str,
    raw_archive_path: str | Path | None,
) -> tuple[Path, str]:
    if raw_archive_path is not None:
        resolved_path = Path(raw_archive_path).resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(resolved_path)
        resolved_key = raw_dataset_key or resolved_path.stem
        return resolved_path, resolved_key

    if raw_dataset_download_manifest_path is None:
        raise ValueError(
            "either raw_archive_path or raw_dataset_download_manifest_path must be provided"
        )

    manifest_path = Path(raw_dataset_download_manifest_path).resolve()
    manifest_payload = _read_json(manifest_path)
    manifest_base = manifest_path.parent
    candidates: list[tuple[str, Path]] = []
    for collection_key in ("datasets", "downloads", "artifacts", "entries"):
        collection = manifest_payload.get(collection_key)
        if not isinstance(collection, list):
            continue
        for entry in collection:
            if not isinstance(entry, dict):
                continue
            candidate_key = str(
                entry.get("dataset_key")
                or entry.get("raw_dataset_key")
                or entry.get("key")
                or entry.get("id")
                or ""
            ).strip()
            candidate_value = (
                entry.get("archive_path")
                or entry.get("local_archive_path")
                or entry.get("zip_path")
                or entry.get("path")
            )
            if not isinstance(candidate_value, str) or not candidate_value.strip():
                continue
            candidates.append(
                (
                    candidate_key,
                    _resolve_candidate_path(candidate_value.strip(), manifest_base),
                )
            )
    if not candidates:
        direct_candidate = (
            manifest_payload.get("archive_path")
            or manifest_payload.get("local_archive_path")
            or manifest_payload.get("zip_path")
            or manifest_payload.get("path")
        )
        if isinstance(direct_candidate, str) and direct_candidate.strip():
            candidates.append(
                (
                    str(manifest_payload.get("dataset_key") or raw_dataset_key or "raw_dataset").strip(),
                    _resolve_candidate_path(direct_candidate.strip(), manifest_base),
                )
            )
    if raw_dataset_key:
        candidates = [candidate for candidate in candidates if candidate[0] == raw_dataset_key]
    if len(candidates) != 1:
        raise ValueError("raw dataset manifest must resolve exactly one governed archive path")
    resolved_path, resolved_key = candidates[0][1], candidates[0][0] or raw_dataset_key
    if not resolved_path.exists():
        raise FileNotFoundError(resolved_path)
    return resolved_path, resolved_key


def _materialize_raw_source_root(source_path: Path, workspace_root: Path) -> Path:
    if source_path.is_dir():
        return source_path
    if source_path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
        return source_path
    if source_path.suffix.lower() != ".zip":
        raise ValueError("raw source must be a directory, a supported video file, or a .zip archive")

    extraction_root = workspace_root / source_path.stem
    extraction_root.mkdir(parents=True, exist_ok=True)
    marker_path = extraction_root / ".extract_complete"
    if not marker_path.exists():
        with zipfile.ZipFile(source_path) as archive:
            archive.extractall(extraction_root)
        marker_path.write_text("ok\n", encoding="utf-8")
    return extraction_root


def _collect_raw_sources(source_root: Path) -> list[RawSource]:
    if source_root.is_file():
        return [
            RawSource(
                source_path=source_root,
                source_kind="video_file",
                source_key=source_root.name,
            )
        ]

    raw_sources: list[RawSource] = []
    for video_path in sorted(path for path in source_root.rglob("*") if path.is_file()):
        if video_path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            continue
        raw_sources.append(
            RawSource(
                source_path=video_path,
                source_kind="video_file",
                source_key=video_path.relative_to(source_root).as_posix(),
            )
        )

    for directory_path in sorted(path for path in source_root.rglob("*") if path.is_dir()):
        image_paths = sorted(
            image_path
            for image_path in directory_path.iterdir()
            if image_path.is_file() and image_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        )
        if not image_paths:
            continue
        raw_sources.append(
            RawSource(
                source_path=directory_path,
                source_kind="frame_directory",
                source_key=directory_path.relative_to(source_root).as_posix(),
            )
        )
    if not raw_sources:
        raise ValueError("no governed raw video sources were found")
    return raw_sources


def _normalize_image_frame(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 2:
        frame = np.stack([frame, frame, frame], axis=-1)
    if frame.ndim != 3:
        raise ValueError("frame_directory entries must decode to 2D or 3D arrays")
    if frame.shape[2] == 4:
        frame = frame[:, :, :3]
    if frame.shape[2] != 3:
        raise ValueError("frame_directory entries must resolve to RGB-compatible arrays")
    return np.clip(frame.astype(np.float32) / 255.0, 0.0, 1.0)


def _load_source_frames(raw_source: RawSource, *, fallback_fps: int) -> tuple[np.ndarray, int]:
    if raw_source.source_kind == "video_file":
        video_frames = read_video_frames(raw_source.source_path)
        return video_frames.frames, video_frames.fps

    image_paths = sorted(
        image_path
        for image_path in raw_source.source_path.iterdir()
        if image_path.is_file() and image_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    )
    if not image_paths:
        raise ValueError("frame directory must contain image frames")
    frames = np.stack(
        [_normalize_image_frame(np.asarray(imageio.imread(image_path))) for image_path in image_paths],
        axis=0,
    )
    return frames.astype(np.float32), int(fallback_fps)


def _infer_split(source_key: str, index: int) -> str:
    normalized_key = source_key.lower()
    if any(token in normalized_key for token in ("calibration", "train", "training")):
        return "calibration"
    if any(token in normalized_key for token in ("test", "val", "validation", "eval")):
        return "test"
    return "calibration" if index % 2 == 0 else "test"


def _default_registry_path(processed_dataset_root: Path) -> Path:
    datasets_root = processed_dataset_root.parent.parent
    return datasets_root / "registry" / "dataset_registry.json"


def _update_processed_dataset_registry(
    registry_path: Path,
    *,
    processed_dataset_key: str,
    processed_dataset_root: Path,
    dataset_manifest_path: Path,
    summary_path: Path,
    checks_path: Path,
    summary_payload: dict[str, Any],
) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    if registry_path.exists():
        registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        registry_payload = {"datasets": []}

    if isinstance(registry_payload, list):
        existing_entries = registry_payload
        registry_payload = {"datasets": existing_entries}
    datasets = registry_payload.get("datasets")
    if not isinstance(datasets, list):
        raise ValueError("dataset registry must define a datasets list")

    updated_entry = {
        "processed_dataset_key": processed_dataset_key,
        "processed_dataset_root": str(processed_dataset_root),
        "dataset_manifest_path": str(dataset_manifest_path),
        "summary_path": str(summary_path),
        "checks_path": str(checks_path),
        "sample_count": int(summary_payload.get("sample_count", 0)),
        "split_counts": summary_payload.get("split_counts", {}),
        "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    remaining_entries = [
        entry
        for entry in datasets
        if isinstance(entry, dict)
        and entry.get("processed_dataset_key") != processed_dataset_key
    ]
    remaining_entries.append(updated_entry)
    registry_payload["datasets"] = sorted(
        remaining_entries,
        key=lambda entry: str(entry.get("processed_dataset_key", "")),
    )
    registry_path.write_text(
        json.dumps(registry_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_processed_real_video_dataset(
    *,
    raw_dataset_download_manifest_path: str | Path | None = None,
    raw_dataset_key: str = "",
    raw_archive_path: str | Path | None = None,
    processed_dataset_root: str | Path,
    processed_dataset_key: str,
    target_frame_count: int = 32,
    target_fps: int = 8,
    target_height: int = 256,
    target_width: int = 256,
    frame_sampling_policy: str = "deterministic_uniform",
    codec: str = "libx264",
    crf: int = 18,
    local_workspace_root: str | Path | None = None,
    registry_path: str | Path | None = None,
    clean_workspace: bool = False,
) -> dict[str, Any]:
    """Build a governed processed dataset and write manifest, summary, and checks.

    Args:
        raw_dataset_download_manifest_path: Optional raw-download manifest path.
        raw_dataset_key: Governed raw dataset key.
        raw_archive_path: Optional raw archive path override.
        processed_dataset_root: Output processed dataset root.
        processed_dataset_key: Output dataset key.
        target_frame_count: Output frame count.
        target_fps: Output fps.
        target_height: Output frame height.
        target_width: Output frame width.
        frame_sampling_policy: Governed frame sampling policy.
        codec: Output mp4 codec.
        crf: Output mp4 CRF.
        local_workspace_root: Optional extraction workspace root.
        registry_path: Optional dataset registry path override.
        clean_workspace: Whether to remove any existing extraction workspace first.

    Returns:
        A processed-dataset handoff payload.
    """
    if frame_sampling_policy != "deterministic_uniform":
        raise ValueError("frame_sampling_policy must be deterministic_uniform")
    if not processed_dataset_key.strip():
        raise ValueError("processed_dataset_key must be non-empty")

    processed_root = Path(processed_dataset_root).resolve()
    processed_root.mkdir(parents=True, exist_ok=True)
    source_archive_path, resolved_raw_dataset_key = _resolve_raw_archive_path(
        raw_dataset_download_manifest_path=raw_dataset_download_manifest_path,
        raw_dataset_key=raw_dataset_key,
        raw_archive_path=raw_archive_path,
    )

    workspace_root = Path(local_workspace_root).resolve() if local_workspace_root else processed_root / "_workspace"
    if clean_workspace and workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)

    source_root = _materialize_raw_source_root(source_archive_path, workspace_root)
    raw_sources = _collect_raw_sources(source_root)
    output_video_root = processed_root / "source"
    output_video_root.mkdir(parents=True, exist_ok=True)
    checks_root = processed_root / "checks"
    checks_root.mkdir(parents=True, exist_ok=True)

    processing_plan: list[tuple[RawSource, str]] = []
    if len(raw_sources) == 1:
        processing_plan.extend([(raw_sources[0], "calibration"), (raw_sources[0], "test")])
    else:
        for index, raw_source in enumerate(raw_sources):
            processing_plan.append((raw_source, _infer_split(raw_source.source_key, index)))

    samples: list[dict[str, Any]] = []
    materialized_paths: list[Path] = []
    for index, (raw_source, split_name) in enumerate(processing_plan):
        source_frames, source_fps = _load_source_frames(raw_source, fallback_fps=target_fps)
        standardized_frames = standardize_video_frames(
            source_frames,
            target_frame_count=target_frame_count,
            target_fps=target_fps,
            target_resolution=(target_height, target_width),
            frame_sampling_policy=frame_sampling_policy,
        )
        source_digest = compute_object_digest(
            {
                "source_key": raw_source.source_key,
                "split_name": split_name,
                "index": index,
            }
        )[:12]
        source_stem = _sanitize_slug(Path(raw_source.source_key).stem)
        video_source_id = f"{source_stem}_{split_name}_{source_digest}"
        output_path = output_video_root / f"{video_source_id}.mp4"
        artifact_metadata = write_video_mp4(
            standardized_frames,
            output_path=output_path,
            fps=target_fps,
            codec=codec,
            crf=crf,
        )
        relpath = output_path.relative_to(processed_root).as_posix()
        samples.append(
            {
                "video_source_id": video_source_id,
                "split": split_name,
                "relpath": relpath,
                "source_kind": raw_source.source_kind,
                "source_key": raw_source.source_key,
                "source_digest": compute_file_digest(output_path),
                "source_fps": int(source_fps),
                "frame_count": int(target_frame_count),
                "fps": int(target_fps),
                "height": int(target_height),
                "width": int(target_width),
                "container": artifact_metadata["container"],
            }
        )
        materialized_paths.append(output_path)

    dataset_manifest_path = processed_root / "dataset_manifest.json"
    summary_path = processed_root / "processed_dataset_summary.json"
    checks_path = checks_root / "processed_dataset_checks.json"
    split_counts: dict[str, int] = {}
    for sample in samples:
        split_name = str(sample["split"])
        split_counts[split_name] = split_counts.get(split_name, 0) + 1
    dataset_manifest = {
        "dataset_name": "processed_real_video_dataset",
        "dataset_key": processed_dataset_key,
        "dataset_version": "freeze001",
        "raw_dataset_key": resolved_raw_dataset_key,
        "raw_source_path": str(source_archive_path),
        "processed_dataset_root": str(processed_root),
        "frame_sampling_policy": frame_sampling_policy,
        "target_frame_count": int(target_frame_count),
        "target_fps": int(target_fps),
        "target_resolution": [int(target_height), int(target_width)],
        "codec": codec,
        "samples": samples,
    }
    summary_payload = {
        "processed_dataset_key": processed_dataset_key,
        "processed_dataset_root": str(processed_root),
        "dataset_manifest_path": str(dataset_manifest_path),
        "sample_count": len(samples),
        "split_counts": split_counts,
        "output_digest": compute_object_digest([str(path) for path in materialized_paths]),
    }
    dataset_manifest_path.write_text(
        json.dumps(dataset_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checks_payload = {
        "status": bool(samples)
        and {"calibration", "test"}.issubset(set(split_counts))
        and all(path.exists() for path in materialized_paths),
        "processed_dataset_key": processed_dataset_key,
        "required_paths": {
            "dataset_manifest": dataset_manifest_path.exists(),
            "processed_dataset_summary": summary_path.exists(),
            "processed_dataset_checks": True,
            "materialized_videos": all(path.exists() for path in materialized_paths),
        },
        "sample_count": len(samples),
        "split_counts": split_counts,
    }
    checks_path.write_text(
        json.dumps(checks_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    resolved_registry_path = Path(registry_path).resolve() if registry_path else _default_registry_path(processed_root)
    _update_processed_dataset_registry(
        resolved_registry_path,
        processed_dataset_key=processed_dataset_key,
        processed_dataset_root=processed_root,
        dataset_manifest_path=dataset_manifest_path,
        summary_path=summary_path,
        checks_path=checks_path,
        summary_payload=summary_payload,
    )

    handoff_payload = {
        "PROCESSED_DATASET_KEY": processed_dataset_key,
        "PROCESSED_DATASET_ROOT": str(processed_root),
        "PROCESSED_DATASET_MANIFEST": str(dataset_manifest_path),
        "processed_dataset_summary.json": str(summary_path),
        "processed_dataset_checks.json": str(checks_path),
        "dataset_registry.json": str(resolved_registry_path),
    }
    return handoff_payload


def main(argv: list[str] | None = None) -> int:
    """Run the governed processed-dataset builder CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Build a governed processed real-video dataset.",
    )
    parser.add_argument("--raw-dataset-download-manifest-path", default="")
    parser.add_argument("--raw-dataset-key", default="")
    parser.add_argument("--raw-archive-path", default="")
    parser.add_argument("--processed-dataset-root", required=True)
    parser.add_argument("--processed-dataset-key", required=True)
    parser.add_argument("--target-frame-count", type=int, default=32)
    parser.add_argument("--target-fps", type=int, default=8)
    parser.add_argument("--target-height", type=int, default=256)
    parser.add_argument("--target-width", type=int, default=256)
    parser.add_argument("--frame-sampling-policy", default="deterministic_uniform")
    parser.add_argument("--codec", default="libx264")
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--local-workspace-root", default="")
    parser.add_argument("--registry-path", default="")
    parser.add_argument("--clean-workspace", action="store_true")
    args = parser.parse_args(argv)

    handoff_payload = build_processed_real_video_dataset(
        raw_dataset_download_manifest_path=args.raw_dataset_download_manifest_path or None,
        raw_dataset_key=args.raw_dataset_key,
        raw_archive_path=args.raw_archive_path or None,
        processed_dataset_root=args.processed_dataset_root,
        processed_dataset_key=args.processed_dataset_key,
        target_frame_count=args.target_frame_count,
        target_fps=args.target_fps,
        target_height=args.target_height,
        target_width=args.target_width,
        frame_sampling_policy=args.frame_sampling_policy,
        codec=args.codec,
        crf=args.crf,
        local_workspace_root=args.local_workspace_root or None,
        registry_path=args.registry_path or None,
        clean_workspace=args.clean_workspace,
    )
    print(json.dumps(handoff_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

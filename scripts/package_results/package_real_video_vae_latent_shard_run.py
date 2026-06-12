"""Package a real-video VAE latent shard run without requiring formal full-run gates."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any


REQUIRED_RELATIVE_PATHS = (
    "records/event_scores.jsonl",
    "thresholds/thresholds.json",
    "artifacts/runtime_config.json",
    "artifacts/run_manifest.json",
    "artifacts/runtime_manifest.json",
    "artifacts/artifact_manifest.json",
)


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def _write_zip(*, run_root: Path, zip_path: Path, exclude_large_intermediate_latents: bool) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    excluded_prefixes = []
    if exclude_large_intermediate_latents:
        excluded_prefixes.extend([
            Path("artifacts/latents"),
            Path("artifacts/videos"),
        ])
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in run_root.rglob("*") if path.is_file()):
            relative_path = file_path.relative_to(run_root)
            if any(relative_path == prefix or prefix in relative_path.parents for prefix in excluded_prefixes):
                continue
            archive.write(file_path, arcname=f"{run_root.name}/{relative_path.as_posix()}")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def package_shard_run(
    *,
    run_root: Path,
    family_root: Path,
    shard_count: int | None,
    shard_index: int | None,
    short_commit: str | None,
    exclude_large_intermediate_latents: bool,
) -> dict[str, Any]:
    """Package a single shard run into a local family result tree.

    该函数只检查 shard 运行是否产生了可聚合的基本文件, 不把单个 shard 误判为
    完整 formal PASS。后续 fixed-FPR 判定必须在 shard_aggregated 流程中完成。
    """
    missing = [relative for relative in REQUIRED_RELATIVE_PATHS if not (run_root / relative).exists()]
    if missing:
        raise FileNotFoundError("real-video VAE shard run is incomplete: " + ", ".join(missing))
    family_root.mkdir(parents=True, exist_ok=True)
    package_dir = family_root / "packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    zip_path = package_dir / f"{family_root.name}.zip"
    _write_zip(
        run_root=run_root,
        zip_path=zip_path,
        exclude_large_intermediate_latents=exclude_large_intermediate_latents,
    )
    compat_root = family_root / "compat_run_root"
    _copy_tree(run_root, compat_root)
    runtime_config = _load_json(run_root / "artifacts" / "runtime_config.json")
    run_manifest = _load_json(run_root / "artifacts" / "run_manifest.json")
    runtime_manifest = _load_json(run_root / "artifacts" / "runtime_manifest.json")
    resolved_shard_count = shard_count if shard_count is not None else runtime_config.get("shard_count")
    resolved_shard_index = shard_index if shard_index is not None else runtime_config.get("shard_index")
    resolved_short_commit = short_commit or str(runtime_config.get("git_commit") or runtime_manifest.get("git_commit") or "unknown")[:7]
    summary = {
        "status": "shard_run_completed",
        "workflow_key": "real_video_vae_latent_probe",
        "result_kind": "shard_run",
        "family_id": family_root.name,
        "run_root": str(run_root),
        "package_path": str(zip_path),
        "archive_path": str(zip_path),
        "compat_run_root": str(compat_root),
        "shard_count": resolved_shard_count,
        "shard_index": resolved_shard_index,
        "short_commit": resolved_short_commit,
        "run_id": run_manifest.get("run_id", run_root.name),
        "formal_pass_required": False,
        "aggregation_required_for_next_stage": True,
        "required_paths": {relative: (run_root / relative).exists() for relative in REQUIRED_RELATIVE_PATHS},
    }
    (family_root / "family_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (family_root / "family_checks.json").write_text(json.dumps({"status": True, **summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (family_root / "family_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--family-root", type=Path, required=True)
    parser.add_argument("--shard-count", type=int, default=None)
    parser.add_argument("--shard-index", type=int, default=None)
    parser.add_argument("--short-commit", type=str, default=None)
    parser.add_argument("--exclude-large-intermediate-latents", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = package_shard_run(
        run_root=args.run_root,
        family_root=args.family_root,
        shard_count=args.shard_count,
        shard_index=args.shard_index,
        short_commit=args.short_commit,
        exclude_large_intermediate_latents=args.exclude_large_intermediate_latents,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""
文件用途：打包阶段 2 scaffold 运行目录到目标输出目录。
File purpose: Package a stage-two scaffold run directory into a target output directory.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import zipfile

from main.colab.notebook_result_checker import check_real_video_vae_latent_outputs
from main.protocol.real_video_vae_latent_paths import build_real_video_vae_latent_output_paths


def pack_real_video_vae_latent_run(
    run_root: str | Path,
    drive_output_dir: str | Path,
    include_records: bool = True,
    include_thresholds: bool = True,
    include_tables: bool = True,
    include_figures: bool = True,
    include_reports: bool = True,
    include_failure_gallery: bool = True,
    include_manifest: bool = True,
    exclude_large_intermediate_latents: bool = False,
) -> dict[str, Path]:
    """功能：将阶段 2 运行目录打包为 zip 与摘要文件。

    Package a stage-two run directory into a zip archive and sidecar summaries.

    Args:
        run_root: Run root path.
        drive_output_dir: Target output directory.
        include_records: Whether to include the records directory.
        include_thresholds: Whether to include the thresholds directory.
        include_tables: Whether to include the tables directory.
        include_figures: Whether to include the figures directory.
        include_reports: Whether to include the reports directory.
        include_failure_gallery: Whether to include the failure-case gallery.
        include_manifest: Whether to include manifest files under artifacts.
        exclude_large_intermediate_latents: Whether to exclude artifact video/latent trees.

    Returns:
        A dictionary containing the produced archive and JSON paths.
    """
    run_root_path = Path(run_root)
    if not run_root_path.exists():
        raise FileNotFoundError(run_root_path)
    output_dir = Path(drive_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = build_real_video_vae_latent_output_paths(run_root_path)
    checks_payload = check_real_video_vae_latent_outputs(run_root_path)
    run_manifest = json.loads(output_paths.run_manifest_path.read_text(encoding="utf-8"))
    runtime_manifest = json.loads(output_paths.colab_runtime_manifest_path.read_text(encoding="utf-8"))
    run_id = str(run_manifest["run_id"])
    zip_path = output_dir / f"{run_id}.zip"
    summary_path = output_dir / f"{run_id}_summary.json"
    checks_path = output_dir / f"{run_id}_checks.json"

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        if include_records:
            _write_tree_to_archive(archive, run_root_path, run_root_path / "records")
        if include_thresholds:
            _write_tree_to_archive(archive, run_root_path, run_root_path / "thresholds")
        if include_tables:
            _write_tree_to_archive(archive, run_root_path, run_root_path / "tables")
        if include_figures:
            _write_tree_to_archive(archive, run_root_path, run_root_path / "figures")
        if include_reports:
            _write_tree_to_archive(archive, run_root_path, run_root_path / "reports")
        if include_failure_gallery:
            _write_tree_to_archive(archive, run_root_path, run_root_path / "failure_case_gallery")
        if include_manifest:
            for manifest_path in (
                output_paths.run_manifest_path,
                output_paths.artifact_manifest_path,
                output_paths.colab_runtime_manifest_path,
                output_paths.colab_real_video_vae_latent_runtime_config_path,
            ):
                if manifest_path.exists():
                    archive.write(manifest_path, arcname=_build_archive_name(run_root_path, manifest_path))
        if not exclude_large_intermediate_latents:
            for artifact_tree in (
                run_root_path / "artifacts" / "latents",
                run_root_path / "artifacts" / "videos",
            ):
                _write_tree_to_archive(archive, run_root_path, artifact_tree)

    summary_payload = {
        "run_id": run_id,
        "git_commit": runtime_manifest.get("git_commit", "unknown"),
        "construction_phase": run_manifest.get("construction_phase"),
        "RealVideoVaeLatentDecision": checks_payload["RealVideoVaeLatentDecision"],
        "BlockingReasons": checks_payload["BlockingReasons"],
    }
    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checks_path.write_text(
        json.dumps(checks_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "zip_path": zip_path,
        "summary_path": summary_path,
        "checks_path": checks_path,
    }


def _write_tree_to_archive(archive: zipfile.ZipFile, run_root: Path, tree_path: Path) -> None:
    if not tree_path.exists():
        return
    for file_path in sorted(path for path in tree_path.rglob("*") if path.is_file()):
        archive.write(file_path, arcname=_build_archive_name(run_root, file_path))


def _build_archive_name(run_root: Path, file_path: Path) -> str:
    return f"{run_root.name}/{file_path.relative_to(run_root).as_posix()}"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Package the governed placeholder stage-two outputs.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--drive-output-dir", required=True)
    parser.add_argument("--include-records", action="store_true")
    parser.add_argument("--include-thresholds", action="store_true")
    parser.add_argument("--include-tables", action="store_true")
    parser.add_argument("--include-figures", action="store_true")
    parser.add_argument("--include-reports", action="store_true")
    parser.add_argument("--include-failure-gallery", action="store_true")
    parser.add_argument("--include-manifest", action="store_true")
    parser.add_argument("--exclude-large-intermediate-latents", action="store_true")
    args = parser.parse_args(argv)
    include_any = any(
        (
            args.include_records,
            args.include_thresholds,
            args.include_tables,
            args.include_figures,
            args.include_reports,
            args.include_failure_gallery,
            args.include_manifest,
        )
    )
    pack_real_video_vae_latent_run(
        run_root=args.run_root,
        drive_output_dir=args.drive_output_dir,
        include_records=True if not include_any else args.include_records,
        include_thresholds=True if not include_any else args.include_thresholds,
        include_tables=True if not include_any else args.include_tables,
        include_figures=True if not include_any else args.include_figures,
        include_reports=True if not include_any else args.include_reports,
        include_failure_gallery=True if not include_any else args.include_failure_gallery,
        include_manifest=True if not include_any else args.include_manifest,
        exclude_large_intermediate_latents=args.exclude_large_intermediate_latents,
    )


if __name__ == "__main__":
    main()
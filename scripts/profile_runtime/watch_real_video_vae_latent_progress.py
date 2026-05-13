"""
文件用途：扫描 run_root 并输出 real-video VAE latent probe 的进度快照。
File purpose: Scan a run_root and emit a progress snapshot for the real-video VAE latent probe.
Module type: General module
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from scripts.profile_runtime import iso_timestamp_utc, write_json_file


def _count_files(root: Path, pattern: str) -> int:
    """功能：统计匹配给定 glob 的文件数量。

    Count files matching the provided glob pattern.

    Args:
        root: Root directory.
        pattern: Glob pattern.

    Returns:
        The number of matched files.
    """
    if not root.exists():
        return 0
    return sum(1 for path in root.glob(pattern) if path.is_file())


def _age_seconds(path: Path) -> float | None:
    """功能：返回文件最近修改年龄。

    Return the age of the last file update in seconds.

    Args:
        path: File path.

    Returns:
        The age in seconds, or None when the file does not exist.
    """
    if not path.exists():
        return None
    return max(time.time() - path.stat().st_mtime, 0.0)


def watch_real_video_vae_latent_progress(
    *,
    run_root: str | Path,
    output_json: str | Path,
    stall_threshold_seconds: float = 900.0,
) -> dict[str, Any]:
    """功能：生成 real-video VAE latent run 的当前进度快照。

    Generate a current progress snapshot for the real-video VAE latent run.

    Args:
        run_root: Run-root path.
        output_json: Output JSON path.
        stall_threshold_seconds: Stall-detection threshold in seconds.

    Returns:
        The progress snapshot payload.
    """
    run_root_path = Path(run_root)
    if not run_root_path.exists():
        payload = {
            "status": False,
            "run_root": str(run_root_path),
            "timestamp_utc": iso_timestamp_utc(),
            "error_message": "run_root does not exist",
        }
        write_json_file(output_json, payload)
        return payload

    records_path = run_root_path / "records" / "event_scores.jsonl"
    records_written = 0
    if records_path.exists():
        with records_path.open("r", encoding="utf-8") as handle:
            records_written = sum(1 for _ in handle)

    thresholds_ready = (run_root_path / "thresholds" / "thresholds.json").exists()
    tables_ready = any(path.is_file() for path in (run_root_path / "tables").glob("*.csv")) if (run_root_path / "tables").exists() else False
    report_ready = (run_root_path / "reports" / "vae_latent_probe_report.md").exists()

    source_video_count = _count_files(run_root_path / "artifacts" / "videos" / "source", "**/*.mp4")
    decoded_video_count = _count_files(run_root_path / "artifacts" / "videos" / "decoded", "**/*.mp4")
    attacked_video_count = _count_files(run_root_path / "artifacts" / "videos" / "attacked", "**/*.mp4")
    encoded_latent_count = _count_files(run_root_path / "artifacts" / "latents" / "encoded", "**/*.npy")
    watermarked_latent_count = _count_files(run_root_path / "artifacts" / "latents" / "watermarked", "**/*.npy")
    reencoded_latent_count = _count_files(run_root_path / "artifacts" / "latents" / "reencoded", "**/*.npy")

    gpu_trace_path = run_root_path / "runtime_profile" / "gpu_runtime_trace.csv"
    last_record_update_age_seconds = _age_seconds(records_path)
    last_gpu_trace_update_age_seconds = _age_seconds(gpu_trace_path)

    possible_stall = bool(
        last_record_update_age_seconds is not None
        and last_gpu_trace_update_age_seconds is not None
        and last_record_update_age_seconds > stall_threshold_seconds
        and last_gpu_trace_update_age_seconds > stall_threshold_seconds
    )
    stall_reason = "record_and_gpu_trace_stalled" if possible_stall else None

    payload = {
        "status": True,
        "run_root": str(run_root_path),
        "timestamp_utc": iso_timestamp_utc(),
        "records_written": records_written,
        "thresholds_ready": thresholds_ready,
        "tables_ready": tables_ready,
        "report_ready": report_ready,
        "source_video_count": source_video_count,
        "decoded_video_count": decoded_video_count,
        "attacked_video_count": attacked_video_count,
        "encoded_latent_count": encoded_latent_count,
        "watermarked_latent_count": watermarked_latent_count,
        "reencoded_latent_count": reencoded_latent_count,
        "last_record_update_age_seconds": last_record_update_age_seconds,
        "last_gpu_trace_update_age_seconds": last_gpu_trace_update_age_seconds,
        "possible_stall": possible_stall,
        "stall_reason": stall_reason,
    }
    write_json_file(output_json, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    """功能：执行 progress watcher CLI。

    Execute the progress watcher CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Watch real-video VAE latent run progress.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--stall-threshold-seconds", type=float, default=900.0)
    args = parser.parse_args(argv)
    payload = watch_real_video_vae_latent_progress(
        run_root=args.run_root,
        output_json=args.output_json,
        stall_threshold_seconds=args.stall_threshold_seconds,
    )
    return 0 if payload.get("status", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())

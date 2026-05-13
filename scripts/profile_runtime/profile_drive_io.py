"""
文件用途：测量 Drive 与 session local 之间的读写速度。
File purpose: Measure Drive and session-local read/write throughput.
Module type: General module
"""

from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path
from typing import Any

from scripts.profile_runtime import iso_timestamp_utc, write_json_file


def _write_sample_file(path: Path, sample_size_mb: int) -> None:
    """功能：写出固定大小的采样文件。

    Write a fixed-size sample file.

    Args:
        path: Output file path.
        sample_size_mb: Sample size in megabytes.

    Returns:
        None.
    """
    chunk = b"0" * (1024 * 1024)
    with path.open("wb") as handle:
        for _ in range(sample_size_mb):
            handle.write(chunk)


def _measure_copy(source: Path, target: Path) -> float:
    """功能：测量文件复制速度。

    Measure the file-copy throughput.

    Args:
        source: Source file path.
        target: Target file path.

    Returns:
        Throughput in MB/s.
    """
    start_time = time.perf_counter()
    shutil.copyfile(source, target)
    elapsed_seconds = max(time.perf_counter() - start_time, 1e-9)
    size_mb = float(source.stat().st_size) / (1024 * 1024)
    return round(size_mb / elapsed_seconds, 6)


def profile_drive_io(
    *,
    drive_root: str | Path,
    local_root: str | Path,
    output_json: str | Path,
    sample_size_mb: int = 64,
) -> dict[str, Any]:
    """功能：测量 Drive 与本地磁盘之间的 IO 速度。

    Measure the IO throughput between Drive and the local session disk.

    Args:
        drive_root: Drive root path.
        local_root: Local session root path.
        output_json: Output JSON path.
        sample_size_mb: Probe sample size in MB.

    Returns:
        The Drive-IO profile payload.
    """
    warnings: list[str] = []
    normalized_sample_size_mb = int(sample_size_mb)
    if normalized_sample_size_mb > 64:
        normalized_sample_size_mb = 64
        warnings.append("sample_size_capped_at_64_mb")
    if normalized_sample_size_mb <= 0:
        normalized_sample_size_mb = 1
        warnings.append("sample_size_adjusted_to_1_mb")

    drive_root_path = Path(drive_root)
    local_root_path = Path(local_root)
    local_root_path.mkdir(parents=True, exist_ok=True)
    runtime_tmp_dir = local_root_path / ".runtime_profile_tmp"
    runtime_tmp_dir.mkdir(parents=True, exist_ok=True)

    local_sample_path = runtime_tmp_dir / "drive_io_local_probe.bin"
    local_copy_back_path = runtime_tmp_dir / "drive_io_local_roundtrip.bin"
    drive_sample_path = drive_root_path / ".runtime_profile_drive_probe.bin"

    local_write_start = time.perf_counter()
    _write_sample_file(local_sample_path, normalized_sample_size_mb)
    local_write_elapsed = max(time.perf_counter() - local_write_start, 1e-9)
    local_write_mb_s = round(normalized_sample_size_mb / local_write_elapsed, 6)

    drive_to_local_mb_s: float | None = None
    local_to_drive_mb_s: float | None = None
    if not drive_root_path.exists():
        warnings.append("drive_root_missing")
        drive_io_status = "drive_root_unavailable"
    else:
        try:
            local_to_drive_mb_s = _measure_copy(local_sample_path, drive_sample_path)
            drive_to_local_mb_s = _measure_copy(drive_sample_path, local_copy_back_path)
        except Exception:
            warnings.append("drive_io_copy_failed")
        if local_to_drive_mb_s is None or drive_to_local_mb_s is None:
            drive_io_status = "unavailable"
        elif min(local_to_drive_mb_s, drive_to_local_mb_s) < 20.0:
            drive_io_status = "slow"
        elif min(local_to_drive_mb_s, drive_to_local_mb_s) < 80.0:
            drive_io_status = "moderate"
        else:
            drive_io_status = "fast"

    for candidate_path in (local_sample_path, local_copy_back_path, drive_sample_path):
        if candidate_path.exists():
            candidate_path.unlink()
    if runtime_tmp_dir.exists() and not any(runtime_tmp_dir.iterdir()):
        runtime_tmp_dir.rmdir()

    payload = {
        "status": True,
        "timestamp_utc": iso_timestamp_utc(),
        "drive_root": str(drive_root_path),
        "local_root": str(local_root_path),
        "sample_size_mb": normalized_sample_size_mb,
        "drive_to_local_mb_s": drive_to_local_mb_s,
        "local_to_drive_mb_s": local_to_drive_mb_s,
        "local_write_mb_s": local_write_mb_s,
        "drive_io_status": drive_io_status,
        "warnings": warnings,
    }
    write_json_file(output_json, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    """功能：执行 Drive IO profile CLI。

    Execute the Drive IO profile CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Profile Drive and local-session IO throughput.",
    )
    parser.add_argument("--drive-root", required=True)
    parser.add_argument("--local-root", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--sample-size-mb", type=int, default=64)
    args = parser.parse_args(argv)
    profile_drive_io(
        drive_root=args.drive_root,
        local_root=args.local_root,
        output_json=args.output_json,
        sample_size_mb=args.sample_size_mb,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

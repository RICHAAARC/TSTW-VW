"""
文件用途：周期性采样 GPU、CPU 与 RAM 使用情况并写入 runtime_profile trace。
File purpose: Periodically sample GPU, CPU, and RAM utilization into a runtime_profile trace.
Module type: General module
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from scripts.profile_runtime import ensure_runtime_profile_dir, iso_timestamp_utc


TRACE_HEADER = [
    "timestamp_utc",
    "elapsed_seconds",
    "event_tag",
    "gpu_index",
    "gpu_name",
    "gpu_util_percent",
    "memory_used_mb",
    "memory_total_mb",
    "memory_util_percent",
    "power_draw_w",
    "temperature_c",
    "cpu_percent",
    "ram_used_gb",
    "ram_total_gb",
]


def _read_event_tag(current_event_tag_file: Path) -> str:
    """功能：读取当前 event tag。

    Read the current runtime event tag.

    Args:
        current_event_tag_file: Event tag sidecar path.

    Returns:
        The normalized event tag string.
    """
    if not current_event_tag_file.exists():
        return "unlabeled"
    event_tag = current_event_tag_file.read_text(encoding="utf-8").strip()
    return event_tag or "unlabeled"


def _probe_cpu_and_ram() -> tuple[float | None, float | None, float | None]:
    """功能：采样 CPU 与 RAM 信息。

    Sample CPU and RAM information.

    Args:
        None.

    Returns:
        A tuple of (cpu_percent, ram_used_gb, ram_total_gb).
    """
    try:
        psutil = __import__("psutil")
    except Exception:
        return None, None, None
    try:
        cpu_percent = float(psutil.cpu_percent(interval=None))
        virtual_memory = psutil.virtual_memory()
    except Exception:
        return None, None, None
    ram_total_gb = round(float(virtual_memory.total) / (1024**3), 3)
    ram_used_gb = round(float(virtual_memory.used) / (1024**3), 3)
    return cpu_percent, ram_used_gb, ram_total_gb


def _sample_gpu_rows(
    *,
    event_tag: str,
    elapsed_seconds: float,
    cpu_percent: float | None,
    ram_used_gb: float | None,
    ram_total_gb: float | None,
) -> list[dict[str, Any]]:
    """功能：执行单次 nvidia-smi 采样。

    Execute a single nvidia-smi sampling operation.

    Args:
        event_tag: Current event tag.
        elapsed_seconds: Elapsed seconds since the profiler start.
        cpu_percent: Current CPU utilization.
        ram_used_gb: Current RAM usage in GB.
        ram_total_gb: Total RAM in GB.

    Returns:
        A list of normalized CSV rows.

    Raises:
        RuntimeError: Raised when nvidia-smi cannot be executed or parsed.
    """
    nvidia_smi_path = shutil.which("nvidia-smi")
    if nvidia_smi_path is None:
        raise RuntimeError("nvidia-smi is unavailable")
    query_command = [
        nvidia_smi_path,
        "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(
            query_command,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as error:
        raise RuntimeError("nvidia-smi sampling failed") from error

    rows: list[dict[str, Any]] = []
    for line in output.splitlines():
        normalized_line = line.strip()
        if not normalized_line:
            continue
        parts = [part.strip() for part in normalized_line.split(",")]
        if len(parts) != 7:
            raise RuntimeError(f"unexpected nvidia-smi row: {normalized_line}")
        memory_used_mb = float(parts[3])
        memory_total_mb = float(parts[4])
        memory_util_percent = round((memory_used_mb / memory_total_mb) * 100, 3) if memory_total_mb > 0 else None
        rows.append(
            {
                "timestamp_utc": iso_timestamp_utc(),
                "elapsed_seconds": round(elapsed_seconds, 3),
                "event_tag": event_tag,
                "gpu_index": parts[0],
                "gpu_name": parts[1],
                "gpu_util_percent": float(parts[2]),
                "memory_used_mb": memory_used_mb,
                "memory_total_mb": memory_total_mb,
                "memory_util_percent": memory_util_percent,
                "power_draw_w": float(parts[5]) if parts[5] else None,
                "temperature_c": float(parts[6]) if parts[6] else None,
                "cpu_percent": cpu_percent,
                "ram_used_gb": ram_used_gb,
                "ram_total_gb": ram_total_gb,
            }
        )
    return rows


def _write_unavailable_row(writer: csv.DictWriter[str], *, event_tag: str) -> None:
    """功能：写入 GPU unavailable 行。

    Write a single unavailable row when nvidia-smi is absent.

    Args:
        writer: CSV writer.
        event_tag: Current event tag.

    Returns:
        None.
    """
    writer.writerow(
        {
            "timestamp_utc": iso_timestamp_utc(),
            "elapsed_seconds": 0.0,
            "event_tag": event_tag,
            "gpu_index": "",
            "gpu_name": "unavailable",
            "gpu_util_percent": "",
            "memory_used_mb": "",
            "memory_total_mb": "",
            "memory_util_percent": "",
            "power_draw_w": "",
            "temperature_c": "",
            "cpu_percent": "",
            "ram_used_gb": "",
            "ram_total_gb": "",
        }
    )


def profile_gpu_runtime(
    *,
    run_root: str | Path,
    interval_seconds: float,
    output_csv: str | Path,
    stop_file: str | Path,
    current_event_tag_file: str | Path | None = None,
) -> dict[str, Any]:
    """功能：持续采样 GPU runtime trace。

    Continuously sample a GPU runtime trace until a stop file is created.

    Args:
        run_root: Run-root path.
        interval_seconds: Sampling interval in seconds.
        output_csv: Output CSV path.
        stop_file: Stop-file path.
        current_event_tag_file: Optional sidecar event tag file.

    Returns:
        A normalized profiling payload.
    """
    run_root_path = Path(run_root)
    runtime_profile_dir = ensure_runtime_profile_dir(run_root_path)
    output_csv_path = Path(output_csv)
    stop_file_path = Path(stop_file)
    current_event_tag_path = Path(current_event_tag_file) if current_event_tag_file is not None else runtime_profile_dir / "current_runtime_event_tag.txt"

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.perf_counter()
    row_count = 0
    with output_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACE_HEADER)
        writer.writeheader()
        handle.flush()

        if shutil.which("nvidia-smi") is None:
            _write_unavailable_row(writer, event_tag=_read_event_tag(current_event_tag_path))
            handle.flush()
            return {
                "status": True,
                "trace_available": True,
                "output_csv": str(output_csv_path),
                "sample_count": 1,
                "nvidia_smi_available": False,
            }

        try:
            while True:
                if stop_file_path.exists():
                    break
                elapsed_seconds = time.perf_counter() - start_time
                event_tag = _read_event_tag(current_event_tag_path)
                cpu_percent, ram_used_gb, ram_total_gb = _probe_cpu_and_ram()
                try:
                    rows = _sample_gpu_rows(
                        event_tag=event_tag,
                        elapsed_seconds=elapsed_seconds,
                        cpu_percent=cpu_percent,
                        ram_used_gb=ram_used_gb,
                        ram_total_gb=ram_total_gb,
                    )
                except RuntimeError as error:
                    writer.writerow(
                        {
                            "timestamp_utc": iso_timestamp_utc(),
                            "elapsed_seconds": round(elapsed_seconds, 3),
                            "event_tag": event_tag,
                            "gpu_index": "",
                            "gpu_name": f"sample_failure:{error}",
                            "gpu_util_percent": "",
                            "memory_used_mb": "",
                            "memory_total_mb": "",
                            "memory_util_percent": "",
                            "power_draw_w": "",
                            "temperature_c": "",
                            "cpu_percent": cpu_percent if cpu_percent is not None else "",
                            "ram_used_gb": ram_used_gb if ram_used_gb is not None else "",
                            "ram_total_gb": ram_total_gb if ram_total_gb is not None else "",
                        }
                    )
                    row_count += 1
                    handle.flush()
                    time.sleep(max(float(interval_seconds), 0.01))
                    continue
                for row in rows:
                    writer.writerow(row)
                    row_count += 1
                handle.flush()
                time.sleep(max(float(interval_seconds), 0.01))
        except KeyboardInterrupt:
            # 允许 notebook 或手动中断时安全退出并保留已有 trace。
            handle.flush()

    return {
        "status": True,
        "trace_available": output_csv_path.exists(),
        "output_csv": str(output_csv_path),
        "sample_count": row_count,
        "nvidia_smi_available": True,
    }


def main(argv: list[str] | None = None) -> int:
    """功能：执行 GPU runtime profiler CLI。

    Execute the GPU runtime profiler CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Profile GPU runtime utilization into a CSV trace.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--current-event-tag-file", default=None)
    args = parser.parse_args(argv)
    profile_gpu_runtime(
        run_root=args.run_root,
        interval_seconds=args.interval_seconds,
        output_csv=args.output_csv,
        stop_file=args.stop_file,
        current_event_tag_file=args.current_event_tag_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

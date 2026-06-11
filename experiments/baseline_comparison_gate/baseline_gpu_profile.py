"""外部 baseline smoke 的 GPU profiling 辅助工具。

该模块只负责启动 `nvidia-smi` 采样、停止采样、汇总 trace, 并把结果写入当前 baseline
结果包。它不参与 detection 分数计算, 也不把 profiling 结果作为论文 claim 证据。
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from main.core.digest import compute_file_digest, compute_object_digest
from scripts.profile_runtime.summarize_gpu_profile import summarize_gpu_runtime_profile

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class BaselineGpuProfileSession:
    """保存一次 baseline GPU profiling 会话的路径和运行状态。"""

    run_root: Path
    baseline_name: str
    interval_seconds: float = 0.5
    enabled: bool = True
    process: subprocess.Popen[str] | None = None
    summary: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.profile_dir = self.run_root / "runtime_profile" / "baseline_gpu_profiles" / self.baseline_name
        self.trace_csv = self.profile_dir / "gpu_runtime_trace.csv"
        self.summary_json = self.profile_dir / "gpu_runtime_summary.json"
        self.report_md = self.profile_dir / "gpu_runtime_report.md"
        self.session_json = self.profile_dir / "gpu_runtime_profiler_session.json"
        self.stop_file = self.profile_dir / "gpu_profile_stop.flag"
        self.event_tag_file = self.profile_dir / "current_runtime_event_tag.txt"

    def __enter__(self) -> "BaselineGpuProfileSession":
        """启动 profiling 子进程。"""
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.event_tag_file.write_text(self.baseline_name + "\n", encoding="utf-8")
        if self.stop_file.exists():
            self.stop_file.unlink()
        if not self.enabled:
            self.session_json.write_text(
                json.dumps(
                    {
                        "status": True,
                        "process_started": False,
                        "profiling_enabled": False,
                        "skip_reason": "baseline_gpu_profile_disabled",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            return self

        command = [
            sys.executable,
            "-m",
            "scripts.profile_runtime.profile_gpu_runtime",
            "--run-root",
            str(self.run_root),
            "--interval-seconds",
            str(self.interval_seconds),
            "--output-csv",
            str(self.trace_csv),
            "--stop-file",
            str(self.stop_file),
            "--current-event-tag-file",
            str(self.event_tag_file),
        ]
        try:
            self.process = subprocess.Popen(command, cwd=ROOT, text=True)
            session_payload = {
                "status": True,
                "process_started": True,
                "profiling_enabled": True,
                "pid": self.process.pid,
                "command": command,
            }
        except Exception as exc:
            session_payload = {
                "status": False,
                "process_started": False,
                "profiling_enabled": True,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
        self.session_json.write_text(
            json.dumps(session_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """停止 profiling 子进程并汇总 trace。"""
        if self.enabled and self.process is not None:
            self.stop_file.write_text("stop\n", encoding="utf-8")
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
        ensure_gpu_profile_trace_exists(
            trace_csv=self.trace_csv,
            baseline_name=self.baseline_name,
        )
        self.summary = summarize_gpu_runtime_profile(
            run_root=self.run_root,
            trace_csv=self.trace_csv,
            output_json=self.summary_json,
            output_md=self.report_md,
        )
        manifest = {
            "baseline_name": self.baseline_name,
            "profiling_enabled": self.enabled,
            "trace_csv": self.trace_csv.as_posix(),
            "summary_json": self.summary_json.as_posix(),
            "report_md": self.report_md.as_posix(),
            "session_json": self.session_json.as_posix(),
            "summary_digest": compute_object_digest(self.summary),
            "trace_digest": compute_file_digest(self.trace_csv) if self.trace_csv.exists() else None,
        }
        manifest_path = self.profile_dir / "gpu_runtime_profile_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")



def ensure_gpu_profile_trace_exists(*, trace_csv: str | Path, baseline_name: str) -> None:
    """确保即使 profiler 子进程启动失败也会留下可汇总 trace。

    该兜底路径把 profiling 状态标记为 unavailable, 目的是保留完整结果包和失败原因,
    而不是让 smoke 本身因为工程采样失败而丢失已经完成的模型可运行性证据。
    """
    path = Path(trace_csv)
    if path.exists() and path.stat().st_size > 0:
        return
    from scripts.profile_runtime.profile_gpu_runtime import TRACE_HEADER
    from scripts.profile_runtime import iso_timestamp_utc

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACE_HEADER)
        writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": iso_timestamp_utc(),
                "elapsed_seconds": 0.0,
                "event_tag": baseline_name,
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

def attach_gpu_profile_to_manifest(manifest_path: str | Path, profile_session: BaselineGpuProfileSession) -> dict[str, Any]:
    """把 GPU profiling 摘要路径和关键指标追加到 baseline manifest。"""
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    summary = profile_session.summary or {}
    profile_payload = {
        "baseline_name": profile_session.baseline_name,
        "profiling_enabled": profile_session.enabled,
        "profile_dir": profile_session.profile_dir.as_posix(),
        "trace_csv": profile_session.trace_csv.as_posix(),
        "summary_json": profile_session.summary_json.as_posix(),
        "report_md": profile_session.report_md.as_posix(),
        "profiling_status": summary.get("profiling_status"),
        "gpu_name": summary.get("gpu_name"),
        "sample_count": summary.get("sample_count"),
        "usable_sample_count": summary.get("usable_sample_count"),
        "peak_memory_used_mb": summary.get("peak_memory_used_mb"),
        "peak_memory_ratio": summary.get("peak_memory_ratio"),
        "mean_gpu_util_percent": summary.get("mean_gpu_util_percent"),
        "median_gpu_util_percent": summary.get("median_gpu_util_percent"),
        "low_utilization_ratio": summary.get("low_utilization_ratio"),
        "estimated_gpu_usage_status": summary.get("estimated_gpu_usage_status"),
        "recommended_batch_size_direction": summary.get("recommended_batch_size_direction"),
    }
    manifest["gpu_profile"] = profile_payload
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return profile_payload


def required_gpu_profile_paths(baseline_name: str) -> list[str]:
    """返回 materialize 时应检查的 GPU profiling 文件相对路径。"""
    base = f"runtime_profile/baseline_gpu_profiles/{baseline_name}"
    return [
        f"{base}/gpu_runtime_trace.csv",
        f"{base}/gpu_runtime_summary.json",
        f"{base}/gpu_runtime_report.md",
        f"{base}/gpu_runtime_profile_manifest.json",
    ]

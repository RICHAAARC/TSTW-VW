"""
文件用途：记录 notebook 或脚本阶段耗时事件到 runtime_profile。
File purpose: Record notebook or script timing events into runtime_profile outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.profile_runtime import ensure_runtime_profile_dir, iso_timestamp_utc


@dataclass
class _TimingEventContext(AbstractContextManager[None]):
    """功能：封装单个 timing event 的 context manager。

    Wrap one timing event as a context manager.

    Args:
        recorder: Timing recorder instance.
        event_name: Event name.
        metadata: Event metadata payload.

    Returns:
        None.
    """

    recorder: "RunTimingRecorder"
    event_name: str
    metadata: dict[str, Any]

    def __enter__(self) -> None:
        self._start_counter = time.perf_counter()
        self._start_utc = datetime.now(timezone.utc)
        return None

    def __exit__(self, exc_type, exc, exc_tb) -> bool:
        end_counter = time.perf_counter()
        end_utc = datetime.now(timezone.utc)
        status = "failed" if exc is not None else "ok"
        self.recorder._append_event_record(
            event_name=self.event_name,
            start_counter=self._start_counter,
            end_counter=end_counter,
            start_utc=self._start_utc,
            end_utc=end_utc,
            status=status,
            error_type=exc_type.__name__ if exc_type is not None else None,
            error_message=str(exc) if exc is not None else None,
            metadata=self.metadata,
        )
        return False


class RunTimingRecorder:
    """功能：记录 run_root 下的阶段级 timing 事件。

    Record stage-level timing events under the run_root runtime_profile directory.

    Args:
        run_root: Run-root path.
        run_id: Optional run identifier.

    Returns:
        None.
    """

    def __init__(self, run_root: str | Path, run_id: str | None = None):
        self.run_root = Path(run_root)
        self.run_id = run_id or self.run_root.name
        self.runtime_profile_dir = ensure_runtime_profile_dir(self.run_root)
        self.events_path = self.runtime_profile_dir / "run_timing_events.jsonl"

    def event(self, event_name: str, **metadata: Any) -> _TimingEventContext:
        """功能：返回可用于 with 语法的 timing event context。

        Return a timing event context manager for use with the `with` statement.

        Args:
            event_name: Event name.
            **metadata: Event metadata.

        Returns:
            A context manager that records the event lifecycle.
        """
        return _TimingEventContext(self, event_name=event_name, metadata=metadata)

    def write_event(
        self,
        event_name: str,
        start_time: float,
        end_time: float,
        status: str,
        **metadata: Any,
    ) -> None:
        """功能：直接写入一条 timing event 记录。

        Write one timing event record directly.

        Args:
            event_name: Event name.
            start_time: Event start timestamp in relative seconds.
            end_time: Event end timestamp in relative seconds.
            status: Event status.
            **metadata: Event metadata.

        Returns:
            None.
        """
        elapsed_seconds = max(float(end_time) - float(start_time), 0.0)
        end_utc = datetime.now(timezone.utc)
        start_utc = end_utc - timedelta(seconds=elapsed_seconds)
        self._append_event_record(
            event_name=event_name,
            start_counter=float(start_time),
            end_counter=float(end_time),
            start_utc=start_utc,
            end_utc=end_utc,
            status=status,
            error_type=metadata.pop("error_type", None),
            error_message=metadata.pop("error_message", None),
            metadata=metadata,
        )

    def _append_event_record(
        self,
        *,
        event_name: str,
        start_counter: float,
        end_counter: float,
        start_utc: datetime,
        end_utc: datetime,
        status: str,
        error_type: str | None,
        error_message: str | None,
        metadata: dict[str, Any],
    ) -> None:
        """功能：写入内部 timing event 记录。

        Write the normalized internal timing event record.

        Args:
            event_name: Event name.
            start_counter: Start monotonic counter.
            end_counter: End monotonic counter.
            start_utc: Start UTC time.
            end_utc: End UTC time.
            status: Event status.
            error_type: Optional error type.
            error_message: Optional error message.
            metadata: Event metadata.

        Returns:
            None.
        """
        event_group = str(metadata.get("event_group", "real_video_vae_latent_probe"))
        record = {
            "run_id": self.run_id,
            "event_name": event_name,
            "event_group": event_group,
            "start_time_utc": start_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "end_time_utc": end_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "elapsed_seconds": round(max(end_counter - start_counter, 0.0), 6),
            "status": status,
            "metadata": metadata,
            "error_type": error_type,
            "error_message": error_message,
            "written_at_utc": iso_timestamp_utc(),
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    """功能：执行手动 timing event 写入 CLI。

    Execute the manual timing event recording CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Write a manual runtime timing event into runtime_profile.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--elapsed-seconds", required=True, type=float)
    parser.add_argument("--status", required=True)
    args = parser.parse_args(argv)

    recorder = RunTimingRecorder(run_root=args.run_root, run_id=args.run_id)
    recorder.write_event(
        event_name=args.event_name,
        start_time=0.0,
        end_time=float(args.elapsed_seconds),
        status=args.status,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

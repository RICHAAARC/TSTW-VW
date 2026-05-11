"""
文件用途：定义通用 run output layout 基类。
File purpose: Define the generic run output layout base used by protocol and experiment runners.
Module type: General module
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BaseRunOutputPaths:
    """Base output layout for governed protocol runs.

    Args:
        root_path: Run root path.
        event_scores_path: Event score JSONL path.
        thresholds_path: Threshold JSON path.
        run_manifest_path: Run manifest JSON path.
        artifact_manifest_path: Artifact manifest JSON path.
        runtime_manifest_path: Runtime manifest JSON path.
        runtime_config_path: Runtime-config JSON path.

    Returns:
        None.
    """

    root_path: Path
    event_scores_path: Path
    thresholds_path: Path
    run_manifest_path: Path
    artifact_manifest_path: Path
    runtime_manifest_path: Path
    runtime_config_path: Path


def build_base_run_output_paths(output_root: str | Path) -> BaseRunOutputPaths:
    """Build the generic governed output layout for a run root.

    Args:
        output_root: Run root path.

    Returns:
        A `BaseRunOutputPaths` instance.
    """
    output_root_path = Path(output_root)
    return BaseRunOutputPaths(
        root_path=output_root_path,
        event_scores_path=output_root_path / "records" / "event_scores.jsonl",
        thresholds_path=output_root_path / "thresholds" / "thresholds.json",
        run_manifest_path=output_root_path / "artifacts" / "run_manifest.json",
        artifact_manifest_path=output_root_path / "artifacts" / "artifact_manifest.json",
        runtime_manifest_path=output_root_path / "artifacts" / "runtime_manifest.json",
        runtime_config_path=output_root_path / "artifacts" / "runtime_config.json",
    )
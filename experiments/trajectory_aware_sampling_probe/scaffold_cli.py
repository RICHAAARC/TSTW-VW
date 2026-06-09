"""
文件用途: 提供 trajectory-aware sampling probe 的命令行 scaffold 入口。
Module type: CLI module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.trajectory_aware_sampling_probe.runner import (
    TrajectoryAwareSamplingProbeRunner,
)


def main(argv: list[str] | None = None) -> int:
    """功能: 从命令行执行 trajectory-aware sampling scaffold 闭环。"""
    parser = argparse.ArgumentParser(
        description=(
            "Build trajectory-aware sampling readiness, selection plan, manifest, "
            "and report from a trajectory statistic probe output root."
        ),
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--upstream-trajectory-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--sampling-config-path",
        default="configs/protocol/trajectory_aware_sampling_probe.json",
    )
    args = parser.parse_args(argv)

    result = TrajectoryAwareSamplingProbeRunner(
        Path(args.repository_root).resolve()
    ).run(
        upstream_trajectory_root=Path(args.upstream_trajectory_root),
        output_root=Path(args.output_root),
        sampling_config_path=Path(args.sampling_config_path),
    )
    print(json.dumps(result.policy_manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
文件用途：提供 trajectory statistic probe 的命令行 replay 入口。
File purpose: Provide the command-line replay entrypoint for the trajectory statistic probe.
Module type: CLI module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.trajectory_statistic_probe.formal_replay_runner import (
    FormalReplayRequest,
    run_trajectory_statistic_formal_replay,
)


def main(argv: list[str] | None = None) -> int:
    """功能：从命令行运行阶段 3 replay 闭环。

    Args:
        argv: 可选命令行参数列表。

    Returns:
        进程退出码。
    """
    parser = argparse.ArgumentParser(
        description="Run trajectory statistic probe replay from a frozen baseline root.",
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--frozen-baseline-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--samples-per-role", type=int, default=2)
    parser.add_argument("--runtime-profile", default="smoke")
    args = parser.parse_args(argv)

    result = run_trajectory_statistic_formal_replay(
        FormalReplayRequest(
            repository_root=Path(args.repository_root).resolve(),
            output_root=Path(args.output_root),
            frozen_baseline_root=Path(args.frozen_baseline_root),
            samples_per_role=args.samples_per_role,
            runtime_profile=args.runtime_profile,
        )
    )
    print(json.dumps(result.mechanism_decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

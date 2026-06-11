"""阶段三 baseline smoke runner 的命令行入口。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.smoke_runner import (
    materialize_completed_smoke_run,
    run_baseline_smoke,
)


def resolve_short_commit() -> str:
    """读取当前仓库短 commit, 失败时返回 unknown。"""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).strip()
    except Exception:
        return "unknown"


def main(argv: list[str] | None = None) -> None:
    """执行本地 baseline adapter skeleton smoke。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=ROOT / "configs" / "baselines",
    )
    parser.add_argument("--short-commit", default=None)
    parser.add_argument("--timestamp-utc", default=None)
    parser.add_argument(
        "--result-root",
        type=Path,
        default=None,
        help="可选结果根目录。若提供, smoke 成功后复制到 <result-root>/baseline_comparison_gate/<run_id>/。",
    )
    parser.add_argument(
        "--overwrite-result",
        action="store_true",
        help="允许覆盖已经存在的结果目录。默认禁止覆盖, 以避免误删历史结果。",
    )
    args = parser.parse_args(argv)

    summary = run_baseline_smoke(
        run_root=args.run_root,
        config_dir=args.config_dir,
        short_commit=args.short_commit or resolve_short_commit(),
        timestamp_utc=args.timestamp_utc,
    )
    if args.result_root is not None:
        destination = materialize_completed_smoke_run(
            run_root=args.run_root,
            result_root=args.result_root,
            run_id=summary["run_id"],
            overwrite=args.overwrite_result,
        )
        summary["materialized_result_path"] = str(destination)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""聚合 baseline comparison score records 并生成 fixed-FPR 表格骨架。"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.formal_scoring_aggregation import run_baseline_score_aggregation
from experiments.baseline_comparison_gate.smoke_runner import build_smoke_run_id


def resolve_short_commit() -> str:
    """读取当前短 commit。"""
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True, encoding="utf-8", errors="replace").strip()
    except Exception:
        return "unknown"


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--record-path", type=Path, action="append", required=True)
    parser.add_argument("--target-fpr", type=float, default=0.001)
    parser.add_argument("--baseline-name", type=str, required=True)
    parser.add_argument("--result-root", type=Path, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--short-commit", type=str, default=None)
    parser.add_argument("--timestamp-utc", type=str, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    """执行聚合并可选复制到 Drive。"""
    args = parse_args()
    summary = run_baseline_score_aggregation(run_root=args.run_root, record_paths=args.record_path, target_fpr=args.target_fpr)
    materialized_path = None
    if args.result_root is not None:
        short_commit = args.short_commit or resolve_short_commit()
        run_id = args.run_id or build_smoke_run_id(short_commit=short_commit, timestamp_utc=args.timestamp_utc).replace("baseline_comparison_smoke", f"baseline_score_records_aggregation_{args.baseline_name}")
        destination = args.result_root / "baseline_comparison_gate" / args.baseline_name / "shard_aggregated" / run_id
        if destination.exists():
            if not args.overwrite:
                raise FileExistsError(destination)
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(args.run_root, destination)
        materialized_path = destination.as_posix()
    print(json.dumps({"summary": summary, "materialized_path": materialized_path}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

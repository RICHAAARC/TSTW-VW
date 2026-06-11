"""命令行汇总阶段三外部 baseline 真实 smoke 结果包。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.real_smoke_summary import (
    discover_latest_real_smoke_runs,
    summarize_real_smoke_runs,
    write_summary_outputs,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="汇总 external_videoseal、external_rivagan 和 external_hidden_framewise 的真实 smoke 结果包。"
    )
    parser.add_argument(
        "--result-root",
        type=Path,
        default=None,
        help="results 根目录或 results/baseline_comparison_gate 目录, 用于自动选择每个 baseline 的最新结果包。",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        action="append",
        default=None,
        help="单个真实 smoke 结果包目录。可重复传入三次。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="摘要输出目录。该目录只保存 summary, 不保存正式实验 records。",
    )
    return parser.parse_args()


def main() -> None:
    """执行真实 smoke 汇总。"""
    args = parse_args()
    if args.run_root:
        run_roots = args.run_root
    elif args.result_root:
        run_roots = discover_latest_real_smoke_runs(args.result_root)
    else:
        raise SystemExit("必须提供 --run-root 或 --result-root")

    summary = summarize_real_smoke_runs(run_roots)
    outputs = write_summary_outputs(summary, args.output_dir)
    print(json.dumps({"summary": summary, "outputs": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

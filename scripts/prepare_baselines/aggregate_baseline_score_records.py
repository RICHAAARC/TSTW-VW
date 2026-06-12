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


def validate_record_paths_belong_to_baseline(record_paths: list[Path], baseline_name: str) -> None:
    """校验聚合输入确实属于当前 baseline。

    该函数属于项目特定防混淆约束: 阶段三每个 baseline 的 shard run 和聚合结果都独立存放,
    因此聚合脚本需要拒绝把其他 baseline 的 score records 混入当前 baseline 表格。
    """
    mismatches: list[dict[str, str]] = []
    for record_path in record_paths:
        with record_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                actual = str(record.get("baseline_name"))
                if actual != baseline_name:
                    mismatches.append(
                        {
                            "record_path": record_path.as_posix(),
                            "line_number": str(line_number),
                            "expected": baseline_name,
                            "actual": actual,
                        }
                    )
                break
    if mismatches:
        raise ValueError(f"record paths do not belong to baseline {baseline_name}: {mismatches}")


def main() -> None:
    """执行聚合并可选复制到 Drive。"""
    args = parse_args()
    validate_record_paths_belong_to_baseline(args.record_path, args.baseline_name)
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

"""聚合 `additional_dataset_validation_probe` shard records。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.additional_dataset_validation_probe.additional_dataset_builder import (  # noqa: E402
    DEFAULT_DATASET_NAME,
    WORKFLOW_KEY,
    build_additional_dataset_artifacts,
    discover_record_paths,
    resolve_short_commit,
    utc_timestamp,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="聚合 additional_dataset_validation_probe 结果。")
    parser.add_argument("--result-root", type=Path, required=True, help="TSTW results 根目录。")
    parser.add_argument("--dataset-name", type=str, default=DEFAULT_DATASET_NAME, help="附加数据集名称, 默认 ucf101。")
    parser.add_argument("--record-path", type=Path, action="append", default=None, help="可重复传入的 shard JSONL 记录路径。")
    parser.add_argument("--output-root", type=Path, default=None, help="可选输出目录。")
    parser.add_argument("--target-fpr", type=float, default=0.01, help="固定目标 FPR。")
    parser.add_argument("--run-id", type=str, default=None, help="可选 run_id。")
    parser.add_argument("--short-commit", type=str, default=None, help="用于默认 run_id 的短 commit。")
    parser.add_argument("--overwrite", action="store_true", help="输出目录存在时允许覆盖。")
    return parser.parse_args()


def main() -> None:
    """命令行入口。"""
    args = parse_args()
    short_commit = args.short_commit or resolve_short_commit()
    run_id = args.run_id or f"{WORKFLOW_KEY}_{args.dataset_name}_{utc_timestamp()}_{short_commit[:7]}"
    output_root = args.output_root or args.result_root / WORKFLOW_KEY / args.dataset_name / "shard_aggregated" / run_id
    if output_root.exists():
        if not args.overwrite:
            raise FileExistsError(f"输出目录已存在, 如需覆盖请传入 --overwrite: {output_root}")
        shutil.rmtree(output_root)
    record_paths = args.record_path or discover_record_paths(args.result_root, args.dataset_name)
    summary = build_additional_dataset_artifacts(
        output_root=output_root,
        record_paths=record_paths,
        dataset_name=args.dataset_name,
        run_id=run_id,
        target_fpr=args.target_fpr,
    )
    print(json.dumps({"summary": summary, "output_root": output_root.as_posix()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


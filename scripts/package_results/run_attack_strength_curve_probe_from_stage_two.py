"""从阶段二真实视频 VAE 结果生成攻击强度曲线基础 records。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.attack_strength_curve_probe.attack_strength_builder import (  # noqa: E402
    ATTACKS,
    INTERNAL_METHODS,
    WORKFLOW_KEY,
    resolve_short_commit,
)
from experiments.attack_strength_curve_probe.stage_two_record_adapter import (  # noqa: E402
    discover_latest_stage_two_root,
    utc_timestamp,
    write_attack_strength_shard_from_stage_two,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="从阶段二 records 生成攻击强度曲线基础 records。")
    parser.add_argument("--result-root", type=Path, required=True, help="TSTW results 根目录。")
    parser.add_argument("--stage-two-root", type=Path, default=None, help="阶段二 shard_aggregated 结果目录。")
    parser.add_argument("--output-root", type=Path, default=None, help="可选 shard run 输出目录。")
    parser.add_argument("--method-name", action="append", default=None, help="需要纳入的内部方法名。")
    parser.add_argument("--attack-name", action="append", default=None, help="需要纳入的攻击名。")
    parser.add_argument("--max-records-per-group", type=int, default=None, help="每个 method/attack/split/role 最多抽取的记录数。")
    parser.add_argument("--run-id", type=str, default=None, help="可选 run_id。")
    parser.add_argument("--short-commit", type=str, default=None, help="用于默认 run_id 的短 commit。")
    parser.add_argument("--overwrite", action="store_true", help="输出目录存在时允许覆盖。")
    return parser.parse_args()


def main() -> None:
    """命令行入口。"""
    args = parse_args()
    short_commit = args.short_commit or resolve_short_commit()
    run_id = args.run_id or f"{WORKFLOW_KEY}_base_records_{utc_timestamp()}_{short_commit[:7]}"
    stage_two_root = args.stage_two_root or discover_latest_stage_two_root(args.result_root)
    output_root = args.output_root or args.result_root / WORKFLOW_KEY / "shard_runs" / run_id
    if output_root.exists():
        if not args.overwrite:
            raise FileExistsError(f"输出目录已存在, 如需覆盖请传入 --overwrite: {output_root}")
        shutil.rmtree(output_root)
    summary = write_attack_strength_shard_from_stage_two(
        output_root=output_root,
        stage_two_root=stage_two_root,
        run_id=run_id,
        method_names=tuple(args.method_name or INTERNAL_METHODS),
        attack_names=tuple(args.attack_name or ATTACKS),
        max_records_per_group=args.max_records_per_group,
    )
    print(json.dumps({"summary": summary, "output_root": output_root.as_posix()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


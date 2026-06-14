"""构建 `temporal_quality_metric_probe` 的本地或 Colab 结果包。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.temporal_quality_metric_probe.temporal_quality_builder import (  # noqa: E402
    DEFAULT_ATTACKS,
    INTERNAL_METHODS,
    WORKFLOW_KEY,
    TemporalQualityInputs,
    discover_latest_inputs,
    resolve_short_commit,
    run_temporal_quality_probe,
    utc_timestamp,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="构建 temporal_quality_metric_probe 结果。")
    parser.add_argument("--result-root", type=Path, required=True, help="TSTW results 根目录。")
    parser.add_argument("--output-root", type=Path, default=None, help="可选输出目录。")
    parser.add_argument("--stage-two-aggregation-root", type=Path, default=None, help="阶段二聚合结果目录。")
    parser.add_argument("--shard-root", type=Path, action="append", default=None, help="可重复传入的阶段二 shard run 目录。")
    parser.add_argument("--method-name", action="append", default=None, help="需要纳入的内部方法名。")
    parser.add_argument("--attack-name", action="append", default=None, help="需要纳入的攻击名。")
    parser.add_argument("--max-events-per-method-attack", type=int, default=5, help="每个 method / attack 最多抽取的事件数。")
    parser.add_argument("--lpips-model-root", type=Path, default=None, help="可选 LPIPS 模型缓存目录。")
    parser.add_argument("--lpips-backbone", type=str, default="alex", help="LPIPS backbone。")
    parser.add_argument("--lpips-device", type=str, default="cuda", help="LPIPS 运行设备。")
    parser.add_argument("--lpips-batch-size", type=int, default=8, help="LPIPS batch size。")
    parser.add_argument("--run-id", type=str, default=None, help="可选 run_id。")
    parser.add_argument("--short-commit", type=str, default=None, help="用于默认 run_id 的短 commit。")
    parser.add_argument("--overwrite", action="store_true", help="输出目录存在时允许覆盖。")
    return parser.parse_args()


def inputs_from_args(args: argparse.Namespace) -> TemporalQualityInputs:
    """根据命令行参数或自动发现规则构造输入。"""
    if args.stage_two_aggregation_root is None and not args.shard_root:
        return discover_latest_inputs(args.result_root)
    if args.stage_two_aggregation_root is None or not args.shard_root:
        raise ValueError("--stage-two-aggregation-root 和 --shard-root 必须同时显式传入, 或者都不传入以启用自动发现。")
    return TemporalQualityInputs(
        stage_two_aggregation_root=args.stage_two_aggregation_root,
        shard_roots=tuple(args.shard_root),
    )


def main() -> None:
    """命令行入口。"""
    args = parse_args()
    short_commit = args.short_commit or resolve_short_commit()
    run_id = args.run_id or f"{WORKFLOW_KEY}_{utc_timestamp()}_{short_commit[:7]}"
    output_root = args.output_root or args.result_root / WORKFLOW_KEY / "shard_aggregated" / run_id
    if output_root.exists():
        if not args.overwrite:
            raise FileExistsError(f"输出目录已存在, 如需覆盖请传入 --overwrite: {output_root}")
        shutil.rmtree(output_root)
    summary = run_temporal_quality_probe(
        output_root=output_root,
        inputs=inputs_from_args(args),
        run_id=run_id,
        method_names=tuple(args.method_name or INTERNAL_METHODS),
        attack_names=tuple(args.attack_name or DEFAULT_ATTACKS),
        max_events_per_method_attack=args.max_events_per_method_attack,
        lpips_model_root=args.lpips_model_root,
        lpips_backbone=args.lpips_backbone,
        lpips_device=args.lpips_device,
        lpips_batch_size=args.lpips_batch_size,
    )
    print(json.dumps({"summary": summary, "output_root": output_root.as_posix()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


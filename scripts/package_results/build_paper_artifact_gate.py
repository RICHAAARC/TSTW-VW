"""构建阶段四 paper_artifact_gate 论文表格、图表数据和 claim audit。"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.paper_artifact_gate.artifact_builder import (  # noqa: E402
    EXTERNAL_BASELINES,
    PaperArtifactInputs,
    build_paper_artifacts,
    discover_latest_inputs,
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


def utc_timestamp() -> str:
    """生成用于结果目录命名的 UTC 时间戳。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="构建 paper_artifact_gate 论文产物。")
    parser.add_argument("--result-root", type=Path, required=True, help="TSTW results 根目录。")
    parser.add_argument("--output-root", type=Path, default=None, help="可选输出目录。未填写时写入 result-root/paper_artifact_gate。")
    parser.add_argument("--stage-two-root", type=Path, default=None, help="可选阶段二聚合结果目录。")
    parser.add_argument("--baseline-root", type=Path, action="append", default=None, help="可重复传入的 baseline 聚合目录。")
    parser.add_argument("--baseline-name", action="append", default=None, help="需要纳入的 baseline 名称。默认使用三个正式 baseline。")
    parser.add_argument("--run-id", type=str, default=None, help="可选 run_id。")
    parser.add_argument("--short-commit", type=str, default=None, help="用于默认 run_id 的短 commit。")
    parser.add_argument("--overwrite", action="store_true", help="输出目录已存在时允许覆盖。")
    parser.add_argument("--skip-figures", action="store_true", help="只生成表格和 claim audit, 跳过 PNG/PDF 图表导出。")
    return parser.parse_args()


def inputs_from_args(args: argparse.Namespace) -> PaperArtifactInputs:
    """根据参数或自动发现规则解析阶段四输入。"""
    baseline_names = tuple(args.baseline_name or EXTERNAL_BASELINES)
    if args.stage_two_root is None and not args.baseline_root:
        return discover_latest_inputs(args.result_root, baseline_names)
    if args.stage_two_root is None:
        raise ValueError("显式传入 baseline-root 时也必须传入 --stage-two-root。")
    baseline_roots: dict[str, Path] = {}
    if args.baseline_root:
        for root in args.baseline_root:
            matched = [name for name in baseline_names if name in root.as_posix()]
            if len(matched) != 1:
                raise ValueError(f"无法从路径唯一识别 baseline 名称: {root}")
            baseline_roots[matched[0]] = root
    missing = [name for name in baseline_names if name not in baseline_roots]
    if missing:
        discovered = discover_latest_inputs(args.result_root, missing)
        baseline_roots.update(discovered.baseline_aggregation_roots)
    return PaperArtifactInputs(stage_two_root=args.stage_two_root, baseline_aggregation_roots=baseline_roots)


def main() -> None:
    """命令行入口。"""
    args = parse_args()
    short_commit = args.short_commit or resolve_short_commit()
    run_id = args.run_id or f"paper_artifact_gate_{utc_timestamp()}_{short_commit[:7]}"
    output_root = args.output_root or args.result_root / "paper_artifact_gate" / run_id
    if output_root.exists():
        if not args.overwrite:
            raise FileExistsError(f"输出目录已存在, 如需覆盖请传入 --overwrite: {output_root}")
        shutil.rmtree(output_root)
    inputs = inputs_from_args(args)
    summary = build_paper_artifacts(output_root=output_root, inputs=inputs, run_id=run_id, build_figures=not args.skip_figures)
    print(json.dumps({"summary": summary, "output_root": output_root.as_posix()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

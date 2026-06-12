"""运行 baseline comparison 正式 scoring plan 或小规模 execution runner。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.formal_scoring_runner import (
    materialize_formal_scoring_execution_run,
    materialize_formal_scoring_plan_run,
    run_formal_scoring_execution,
    run_formal_scoring_plan,
)
from experiments.baseline_comparison_gate.baseline_gpu_profile import (
    BaselineGpuProfileSession,
    attach_gpu_profile_to_manifest,
    required_gpu_profile_paths,
)
from experiments.baseline_comparison_gate.smoke_runner import build_smoke_run_id


FORMAL_SCORING_PLAN_PREFIX = "baseline_comparison_formal_scoring_plan"
FORMAL_SCORING_EXECUTION_PREFIX = "baseline_comparison_formal_scoring_execution"
FORMAL_SCORING_MULTI_BASELINE_LABEL = "multi_baseline"


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


def build_baseline_run_id_label(baseline_names: list[str] | None) -> str:
    """生成可写入 run_id 的 baseline 标签。

    该函数用于让 Drive 顶层结果目录直接暴露 baseline 身份, 避免正式全量实验中只能打开
    manifest 才能区分结果包。单 baseline 运行使用该 baseline 名称; 多 baseline 运行使用
    `multi_baseline`; 未显式传入 baseline 过滤器时也视为多 baseline 运行。
    """
    normalized = sorted({name.strip() for name in baseline_names or [] if name and name.strip()})
    if len(normalized) == 1:
        return normalized[0]
    return FORMAL_SCORING_MULTI_BASELINE_LABEL


def build_formal_scoring_run_id(
    *,
    execute: bool,
    short_commit: str,
    timestamp_utc: str | None,
    baseline_names: list[str] | None,
    shard_count: int = 1,
    shard_index: int = 0,
) -> str:
    """生成 formal scoring 的 Drive run_id。

    plan 目录保持原有命名, 因为它描述的是 work-item 计划; execution 目录额外加入 baseline 标签,
    使三种外部 baseline 分开正式运行时能够从目录名直接区分。
    """
    if execute:
        baseline_label = build_baseline_run_id_label(baseline_names)
        return f"{FORMAL_SCORING_EXECUTION_PREFIX}_{baseline_label}_sc{shard_count:02d}_si{shard_index:02d}_{short_commit[:7]}"
    return build_smoke_run_id(
        short_commit=short_commit,
        timestamp_utc=timestamp_utc,
    ).replace("baseline_comparison_smoke", FORMAL_SCORING_PLAN_PREFIX)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    不带 --execute 时只生成 work-item plan。
    带 --execute 时执行小规模或分片 formal scoring, 但仍不生成 fixed-FPR 表格。
    """
    parser = argparse.ArgumentParser(
        description="运行 baseline comparison 正式 scoring plan 或小规模 execution runner。"
    )
    parser.add_argument("--run-root", type=Path, required=True, help="会话本地运行目录。")
    parser.add_argument("--stage-two-package-root", type=Path, required=True, help="已解压的阶段二结果包根目录。")
    parser.add_argument("--formal-input-contract", type=Path, required=True, help="formal input contract JSON 路径。")
    parser.add_argument("--baseline-name", action="append", default=None, help="可重复传入的 baseline 过滤器。")
    parser.add_argument("--shard-count", type=int, default=1, help="外层 work-item shard 总数。")
    parser.add_argument("--shard-index", type=int, default=0, help="当前 shard 索引。")
    parser.add_argument("--result-root", type=Path, default=None, help="可选的 Google Drive results 根目录。")
    parser.add_argument("--run-id", type=str, default=None, help="可选的 Drive run_id。")
    parser.add_argument("--short-commit", type=str, default=None, help="生成 run_id 时使用的短 commit。")
    parser.add_argument("--timestamp-utc", type=str, default=None, help="生成 run_id 时使用的 UTC 时间戳。")
    parser.add_argument("--overwrite", action="store_true", help="Drive 目标目录已存在时允许覆盖。")
    parser.add_argument("--config-dir", type=Path, default=ROOT / "configs" / "baselines", help="baseline source manifest 配置目录。")
    parser.add_argument("--external-root", type=Path, default=ROOT / "external_baselines", help="外部 baseline 源码根目录。")
    parser.add_argument("--execute", action="store_true", help="执行小规模 formal scoring, 而不是只生成 work-item plan。")
    parser.add_argument("--max-work-items", type=int, default=None, help="小规模验证最多执行的 work item 数量。")
    parser.add_argument("--worker-count", type=int, default=1, help="当前 shard 内的并发 worker 数。")
    parser.add_argument("--batch-size", type=int, default=1, help="每个 worker 一次领取的 work item 数。")
    parser.add_argument("--include-large-cache", action="store_true", help="复制 execution 结果包时包含大型模型权重缓存。默认不包含。")
    parser.add_argument("--profile-gpu", action=argparse.BooleanOptionalAction, default=True, help="execution 阶段是否采样 GPU runtime trace。默认开启。")
    parser.add_argument("--gpu-profile-interval-seconds", type=float, default=0.5, help="execution 阶段 GPU profiling 采样间隔秒数。")
    return parser.parse_args()


def main() -> None:
    """执行 scoring plan 或 scoring execution。"""
    args = parse_args()
    short_commit = args.short_commit or resolve_short_commit()
    run_id = args.run_id or build_formal_scoring_run_id(
        execute=args.execute,
        short_commit=short_commit,
        timestamp_utc=args.timestamp_utc,
        baseline_names=args.baseline_name,
        shard_count=args.shard_count,
        shard_index=args.shard_index,
    )

    if args.execute:
        with BaselineGpuProfileSession(
            run_root=args.run_root,
            baseline_name="formal_scoring_execution",
            interval_seconds=args.gpu_profile_interval_seconds,
            enabled=args.profile_gpu,
        ) as gpu_profile_session:
            summary = run_formal_scoring_execution(
                run_root=args.run_root,
                stage_two_package_root=args.stage_two_package_root,
                formal_input_contract_path=args.formal_input_contract,
                config_dir=args.config_dir,
                external_root=args.external_root,
                run_id=run_id,
                baseline_names=args.baseline_name,
                shard_count=args.shard_count,
                shard_index=args.shard_index,
                max_work_items=args.max_work_items,
                worker_count=args.worker_count,
                batch_size=args.batch_size,
            )
        gpu_profile_payload = attach_gpu_profile_to_manifest(
            summary["manifest_path"],
            gpu_profile_session,
        )
        summary["gpu_profile"] = gpu_profile_payload
        summary["gpu_profile_summary_path"] = str(gpu_profile_session.summary_json)
    else:
        summary = run_formal_scoring_plan(
            run_root=args.run_root,
            stage_two_package_root=args.stage_two_package_root,
            formal_input_contract_path=args.formal_input_contract,
            baseline_names=args.baseline_name,
            shard_count=args.shard_count,
            shard_index=args.shard_index,
        )

    materialized_path = None
    if args.result_root is not None:
        materializer = (
            materialize_formal_scoring_execution_run
            if args.execute
            else materialize_formal_scoring_plan_run
        )
        if args.execute:
            baseline_label = build_baseline_run_id_label(args.baseline_name)
            materialized_path = materializer(
                run_root=args.run_root,
                result_root=args.result_root / "baseline_comparison_gate" / baseline_label / "shard_runs",
                workflow_key="",
                run_id=run_id,
                overwrite=args.overwrite,
                include_large_cache=args.include_large_cache,
                required_relative_paths=(
                    required_gpu_profile_paths("formal_scoring_execution")
                    if args.profile_gpu
                    else None
                ),
            ).as_posix()
        else:
            materialized_path = materializer(
                run_root=args.run_root,
                result_root=args.result_root,
                run_id=run_id,
                overwrite=args.overwrite,
            ).as_posix()

    print(json.dumps({"summary": summary, "materialized_path": materialized_path}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

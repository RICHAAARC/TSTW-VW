"""准备正式 baseline comparison runner 的输入契约。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.formal_input_contract import (
    build_formal_input_contract,
    materialize_formal_input_contract_run,
    write_formal_input_contract,
)
from experiments.baseline_comparison_gate.source_intake import REQUIRED_BASELINE_NAMES
from experiments.baseline_comparison_gate.smoke_runner import build_smoke_run_id


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="冻结 baseline comparison 正式 runner 的输入契约。")
    parser.add_argument("--stage-two-package-root", type=Path, required=True, help="已解压的阶段二包根目录。")
    parser.add_argument(
        "--baseline-config",
        type=Path,
        default=ROOT / "configs" / "baselines" / "baseline_comparison_gate.json",
        help="阶段三 baseline comparison 配置文件。",
    )
    parser.add_argument("--real-smoke-summary", type=Path, default=None, help="真实 smoke 汇总 JSON。")
    parser.add_argument("--run-root", type=Path, required=True, help="阶段三正式 comparison 会话本地运行目录。")
    parser.add_argument("--result-root", type=Path, default=None, help="可选的 Google Drive results 根目录。")
    parser.add_argument("--run-id", type=str, default=None, help="可选的 Drive run_id。未提供时使用时间戳和短 commit 生成。")
    parser.add_argument("--short-commit", type=str, default="unknown", help="生成 run_id 时使用的短 commit。")
    parser.add_argument("--timestamp-utc", type=str, default=None, help="生成 run_id 时使用的 UTC 时间戳。")
    parser.add_argument("--baseline-name", action="append", default=None, help="可重复传入的 baseline 过滤器。未提供时为三个 baseline 分别落盘。")
    parser.add_argument("--overwrite", action="store_true", help="Drive 目标目录已存在时允许覆盖。")
    return parser.parse_args()


def normalize_baseline_names(baseline_names: list[str] | None) -> list[str]:
    """规范化 formal input contract 的 baseline 落盘目标。"""
    if baseline_names is None:
        return list(REQUIRED_BASELINE_NAMES)
    normalized = [name for name in baseline_names if name]
    unsupported = sorted(set(normalized) - set(REQUIRED_BASELINE_NAMES))
    if unsupported:
        raise ValueError(f"unsupported baseline names: {unsupported}")
    if not normalized:
        raise ValueError("baseline filter must contain at least one baseline")
    return sorted(set(normalized))


def main() -> None:
    """生成输入契约并在不满足条件时失败。"""
    args = parse_args()
    contract = build_formal_input_contract(
        stage_two_package_root=args.stage_two_package_root,
        baseline_config_path=args.baseline_config,
        real_smoke_summary_path=args.real_smoke_summary,
    )
    outputs = write_formal_input_contract(contract, args.run_root)
    materialized_path = None
    if args.result_root is not None:
        baseline_names = normalize_baseline_names(args.baseline_name)
        base_run_id = args.run_id or build_smoke_run_id(
            short_commit=args.short_commit,
            timestamp_utc=args.timestamp_utc,
        ).replace("baseline_comparison_smoke", "baseline_comparison_formal_inputs")
        materialized_paths = []
        for baseline_name in baseline_names:
            run_id = base_run_id.replace(
                "baseline_comparison_formal_inputs",
                f"baseline_comparison_formal_inputs_{baseline_name}",
                1,
            )
            destination = materialize_formal_input_contract_run(
                run_root=args.run_root,
                result_root=args.result_root / "baseline_comparison_gate" / baseline_name,
                workflow_key="",
                run_id=run_id,
                overwrite=args.overwrite,
            )
            materialized_paths.append(destination.as_posix())
        materialized_path = materialized_paths[0] if len(materialized_paths) == 1 else materialized_paths
    print(json.dumps({"contract": contract, "outputs": outputs, "materialized_path": materialized_path}, ensure_ascii=False, indent=2))
    if not contract["ready_for_formal_baseline_runner"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

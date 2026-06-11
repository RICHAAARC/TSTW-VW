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
    write_formal_input_contract,
)


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
    return parser.parse_args()


def main() -> None:
    """生成输入契约并在不满足条件时失败。"""
    args = parse_args()
    contract = build_formal_input_contract(
        stage_two_package_root=args.stage_two_package_root,
        baseline_config_path=args.baseline_config,
        real_smoke_summary_path=args.real_smoke_summary,
    )
    outputs = write_formal_input_contract(contract, args.run_root)
    print(json.dumps({"contract": contract, "outputs": outputs}, ensure_ascii=False, indent=2))
    if not contract["ready_for_formal_baseline_runner"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

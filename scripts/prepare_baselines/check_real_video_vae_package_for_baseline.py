"""检查并可选解压阶段二 real-video VAE 正式结果包。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.stage_two_package import (
    extract_stage_two_zip_package,
    inspect_stage_two_package,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="检查阶段二 real-video VAE 正式结果包是否可作为 baseline comparison 输入。"
    )
    parser.add_argument("--package-root", type=Path, required=True, help="阶段二 Drive family 结果目录。")
    parser.add_argument("--extract-root", type=Path, default=None, help="可选的会话本地解压根目录。")
    parser.add_argument("--extract", action="store_true", help="检查通过后解压 zip 兼容包。")
    parser.add_argument("--overwrite", action="store_true", help="解压目标已存在时先删除再解压。")
    parser.add_argument("--summary-path", type=Path, default=None, help="可选的检查摘要 JSON 输出路径。")
    return parser.parse_args()


def main() -> None:
    """执行阶段二输入包检查。"""
    args = parse_args()
    if args.extract:
        if args.extract_root is None:
            raise SystemExit("使用 --extract 时必须提供 --extract-root")
        summary = extract_stage_two_zip_package(
            package_root=args.package_root,
            extract_root=args.extract_root,
            overwrite=args.overwrite,
        )
    else:
        summary = inspect_stage_two_package(args.package_root)

    if args.summary_path is not None:
        args.summary_path.parent.mkdir(parents=True, exist_ok=True)
        args.summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["package_ready_for_baseline_comparison"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

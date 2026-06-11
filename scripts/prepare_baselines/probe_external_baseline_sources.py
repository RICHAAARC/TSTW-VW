"""运行阶段三外部 baseline 源码能力探测。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.source_probe import probe_baseline_source_tree


def main(argv: list[str] | None = None) -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--external-root",
        type=Path,
        default=ROOT / "external_baselines",
    )
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args(argv)
    payload = probe_baseline_source_tree(args.external_root)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()

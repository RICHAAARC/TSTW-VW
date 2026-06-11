"""运行阶段三 Colab baseline 验证前 preflight。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.colab_preflight import run_colab_preflight


def main(argv: list[str] | None = None) -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=ROOT / "configs" / "baselines",
    )
    parser.add_argument(
        "--external-root",
        type=Path,
        default=ROOT / "external_baselines",
    )
    parser.add_argument("--stage-two-package-root", type=Path, default=None)
    args = parser.parse_args(argv)
    payload = run_colab_preflight(
        config_dir=args.config_dir,
        external_root=args.external_root,
        stage_two_package_root=args.stage_two_package_root,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

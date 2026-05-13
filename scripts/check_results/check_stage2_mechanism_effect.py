"""
文件用途：提供阶段 2 mechanism audit 的命令行入口。
File purpose: Provide the CLI entrypoint for the stage-two mechanism audit.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.real_video_vae_latent_probe.mechanism_audit import (
    run_stage2_mechanism_audit,
)


def main(argv: list[str] | None = None) -> int:
    """Run the stage-two mechanism audit CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Run the governed stage-two mechanism audit.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument(
        "--mechanism-config",
        default="configs/protocol/stage2_mechanism_gate.json",
    )
    parser.add_argument("--target-fpr", type=float, default=None)
    parser.add_argument("--output-path", default=None)
    args = parser.parse_args(argv)
    result = run_stage2_mechanism_audit(
        run_root=args.run_root,
        mechanism_config_path=args.mechanism_config,
        target_fpr=args.target_fpr,
    )
    if args.output_path:
        output_path = Path(args.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
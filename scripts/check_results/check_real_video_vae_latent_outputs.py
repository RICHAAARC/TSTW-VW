"""
File purpose: Provide the governed named CLI entrypoint for real-video VAE latent output checks.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.check_results.real_video_vae_latent_output_checker import (
    check_real_video_vae_latent_outputs,
)


def main(argv: list[str] | None = None) -> int:
    """Run the governed named checker CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Check governed real-video VAE latent outputs.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument(
        "--construction-phase",
        default="real_video_vae_latent_probe",
    )
    parser.add_argument("--run-mode", default="formal")
    parser.add_argument(
        "--require-formal-pass-criteria",
        action="store_true",
    )
    parser.add_argument("--output-json", default="")
    args = parser.parse_args(argv)

    payload = check_real_video_vae_latent_outputs(
        run_root=args.run_root,
        construction_phase=args.construction_phase,
        run_mode=args.run_mode,
        require_formal_pass_criteria=args.require_formal_pass_criteria,
    )
    output_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output_json:
        Path(args.output_json).write_text(output_text, encoding="utf-8")
    print(output_text, end="")
    return 0 if bool(payload.get("status", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())

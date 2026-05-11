"""
File purpose: Provide the governed named tar.zst package entrypoint for real-video VAE latent outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.check_results.real_video_vae_latent_output_checker import (
    check_real_video_vae_latent_outputs,
)
from scripts.package_results.tar_zst_packager import pack_run_to_tar_zst


def package_real_video_vae_latent_tar_zst(
    run_root: str | Path,
    family_root: str | Path,
    *,
    require_formal_pass_criteria: bool = True,
    exclude_large_intermediate_latents: bool = False,
) -> dict[str, Any]:
    """Package a governed run into a family tar.zst archive.

    Args:
        run_root: Run-root path.
        family_root: Family-result root path.
        require_formal_pass_criteria: Whether the checker must enforce formal PASS.
        exclude_large_intermediate_latents: Whether to exclude heavy artifact trees.

    Returns:
        A package summary payload.
    """
    family_root_path = Path(family_root)
    packages_root = family_root_path / "packages"
    packages_root.mkdir(parents=True, exist_ok=True)

    checks_payload = check_real_video_vae_latent_outputs(
        run_root=run_root,
        run_mode="formal",
        require_formal_pass_criteria=require_formal_pass_criteria,
    )
    tar_payload = pack_run_to_tar_zst(
        run_root=run_root,
        drive_result_dir=packages_root,
        checks_payload=checks_payload,
        exclude_large_intermediate_latents=exclude_large_intermediate_latents,
    )
    family_summary = {
        "family_id": family_root_path.name,
        "drive_archive_path": str(tar_payload["archive_path"]),
        "archive_format": "tar.zst",
        "formal_validation_summary": checks_payload,
    }
    family_checks = {
        "status": bool(checks_payload.get("status", False)),
        "archive_exists": tar_payload["archive_path"].exists(),
        "formal_checks": checks_payload.get("formal_checks"),
    }

    (family_root_path / "family_summary.json").write_text(
        json.dumps(family_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (family_root_path / "family_checks.json").write_text(
        json.dumps(family_checks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "archive_path": tar_payload["archive_path"],
        "summary_path": tar_payload["summary_path"],
        "checks_path": tar_payload["checks_path"],
        "family_summary_path": family_root_path / "family_summary.json",
        "family_checks_path": family_root_path / "family_checks.json",
    }


def main(argv: list[str] | None = None) -> int:
    """Run the governed named tar.zst package CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Package governed real-video VAE latent outputs to tar.zst.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--family-root", required=True)
    parser.add_argument(
        "--require-formal-pass-criteria",
        action="store_true",
    )
    parser.add_argument(
        "--exclude-large-intermediate-latents",
        action="store_true",
    )
    args = parser.parse_args(argv)
    package_real_video_vae_latent_tar_zst(
        run_root=args.run_root,
        family_root=args.family_root,
        require_formal_pass_criteria=args.require_formal_pass_criteria,
        exclude_large_intermediate_latents=args.exclude_large_intermediate_latents,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

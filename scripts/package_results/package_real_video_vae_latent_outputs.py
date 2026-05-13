"""
File purpose: Provide the governed named package entrypoint for real-video VAE latent outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import zipfile

from scripts.package_results.drive_packager import pack_real_video_vae_latent_run


def package_real_video_vae_latent_outputs(
    run_root: str | Path,
    family_root: str | Path,
    *,
    exclude_large_intermediate_latents: bool = False,
) -> dict[str, Any]:
    """Package a governed run into the family result tree.

    Args:
        run_root: Run-root path.
        family_root: Family-result root path.
        exclude_large_intermediate_latents: Whether to exclude heavy artifact trees.

    Returns:
        A package summary payload.
    """
    run_root_path = Path(run_root)
    family_root_path = Path(family_root)
    packages_root = family_root_path / "packages"
    packages_root.mkdir(parents=True, exist_ok=True)

    package_payload = pack_real_video_vae_latent_run(
        run_root=run_root_path,
        drive_output_dir=packages_root,
        exclude_large_intermediate_latents=exclude_large_intermediate_latents,
    )
    _append_runtime_profile_to_zip(
        zip_path=package_payload["zip_path"],
        run_root=run_root_path,
    )

    summary_payload = json.loads(package_payload["summary_path"].read_text(encoding="utf-8"))
    checks_payload = json.loads(package_payload["checks_path"].read_text(encoding="utf-8"))
    family_manifest = {
        "family_id": family_root_path.name,
        "run_id": summary_payload.get("run_id"),
        "construction_phase": summary_payload.get("construction_phase"),
        "package_format": "zip",
        "package_path": str(package_payload["zip_path"]),
        "summary_path": str(package_payload["summary_path"]),
        "checks_path": str(package_payload["checks_path"]),
        "runtime_profile_included": True,
    }
    family_summary = {
        "family_id": family_root_path.name,
        "drive_result_summary": summary_payload,
        "package_path": str(package_payload["zip_path"]),
        "runtime_profile_dir": str(run_root_path / "runtime_profile"),
    }
    family_checks = {
        "status": bool(checks_payload.get("status", False)),
        "run_checks": checks_payload,
        "package_exists": package_payload["zip_path"].exists(),
        "runtime_profile_included": True,
    }

    (family_root_path / "family_manifest.json").write_text(
        json.dumps(family_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (family_root_path / "family_summary.json").write_text(
        json.dumps(family_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (family_root_path / "family_checks.json").write_text(
        json.dumps(family_checks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "zip_path": package_payload["zip_path"],
        "summary_path": package_payload["summary_path"],
        "checks_path": package_payload["checks_path"],
        "family_manifest_path": family_root_path / "family_manifest.json",
        "family_summary_path": family_root_path / "family_summary.json",
        "family_checks_path": family_root_path / "family_checks.json",
    }


def _append_runtime_profile_to_zip(
    *,
    zip_path: Path,
    run_root: Path,
) -> None:
    """Append runtime_profile artifacts into the family zip package.

    Args:
        zip_path: Target zip archive path.
        run_root: Run-root path.

    Returns:
        None.
    """
    runtime_profile_dir = run_root / "runtime_profile"
    if not runtime_profile_dir.exists():
        return
    with zipfile.ZipFile(zip_path, mode="a", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in runtime_profile_dir.rglob("*") if path.is_file()):
            archive.write(
                file_path,
                arcname=f"{run_root.name}/{file_path.relative_to(run_root).as_posix()}",
            )


def main(argv: list[str] | None = None) -> int:
    """Run the governed named package CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Package governed real-video VAE latent outputs.",
    )
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--family-root", required=True)
    parser.add_argument(
        "--exclude-large-intermediate-latents",
        action="store_true",
    )
    args = parser.parse_args(argv)
    package_real_video_vae_latent_outputs(
        run_root=args.run_root,
        family_root=args.family_root,
        exclude_large_intermediate_latents=args.exclude_large_intermediate_latents,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

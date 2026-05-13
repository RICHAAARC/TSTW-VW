"""
File purpose: Provide the governed named tar.zst package entrypoint for real-video VAE latent outputs.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any

from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)
from scripts.check_results.real_video_vae_latent_output_checker import (
    check_real_video_vae_latent_outputs,
)
from scripts.package_results.tar_zst_packager import (
    _build_tar_inputs,
    _pack_with_external_tar_zstd,
    _pack_with_python_zstandard,
    _supports_tar_zstd,
)


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
    run_root_path = Path(run_root)
    family_root_path = Path(family_root)
    packages_root = family_root_path / "packages"
    packages_root.mkdir(parents=True, exist_ok=True)

    checks_payload = check_real_video_vae_latent_outputs(
        run_root=run_root_path,
        run_mode="formal",
        require_formal_pass_criteria=require_formal_pass_criteria,
    )
    tar_payload = _package_run_with_runtime_profile(
        run_root=run_root_path,
        drive_result_dir=packages_root,
        checks_payload=checks_payload,
        exclude_large_intermediate_latents=exclude_large_intermediate_latents,
    )
    family_summary = {
        "family_id": family_root_path.name,
        "drive_archive_path": str(tar_payload["archive_path"]),
        "archive_format": "tar.zst",
        "formal_validation_summary": checks_payload,
        "runtime_profile_dir": str(run_root_path / "runtime_profile"),
    }
    family_checks = {
        "status": bool(checks_payload.get("status", False)),
        "archive_exists": tar_payload["archive_path"].exists(),
        "formal_checks": checks_payload.get("formal_checks"),
        "runtime_profile_included": True,
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


def _package_run_with_runtime_profile(
    *,
    run_root: Path,
    drive_result_dir: Path,
    checks_payload: dict[str, Any],
    exclude_large_intermediate_latents: bool,
) -> dict[str, Path]:
    """Package the run into tar.zst with runtime_profile included.

    Args:
        run_root: Run-root path.
        drive_result_dir: Family package directory.
        checks_payload: Checker payload.
        exclude_large_intermediate_latents: Whether to exclude heavy artifacts.

    Returns:
        The produced tar.zst archive payload.

    Raises:
        RuntimeError: Raised when both external and Python fallback packers are unavailable.
    """
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    run_manifest = json.loads(output_paths.run_manifest_path.read_text(encoding="utf-8"))
    run_id = str(run_manifest.get("run_id", run_root.name))
    archive_path = drive_result_dir / f"{run_id}.tar.zst"
    summary_path = drive_result_dir / f"{run_id}_summary.json"
    checks_path = drive_result_dir / f"{run_id}_checks.json"

    include_relpaths = [
        "records",
        "thresholds",
        "tables",
        "figures",
        "reports",
        "failure_case_gallery",
        "artifacts",
        "logs",
        "runtime_profile",
    ]
    if exclude_large_intermediate_latents:
        include_relpaths.remove("artifacts")
        include_relpaths.extend(
            [
                "artifacts/run_manifest.json",
                "artifacts/artifact_manifest.json",
                "artifacts/runtime_manifest.json",
                "artifacts/runtime_config.json",
            ]
        )

    tar_inputs = _build_tar_inputs(run_root, include_relpaths)
    tar_failure_message: str | None = None
    if _supports_tar_zstd():
        try:
            _pack_with_external_tar_zstd(
                archive_path=archive_path,
                run_root_path=run_root,
                tar_inputs=tar_inputs,
            )
        except subprocess.CalledProcessError as error:
            if archive_path.exists():
                archive_path.unlink()
            stderr_text = (error.stderr or "").strip()
            stdout_text = (error.stdout or "").strip()
            tar_failure_message = (
                "external tar --zstd packaging failed"
                f" (returncode={error.returncode})"
            )
            if stderr_text:
                tar_failure_message += f"; stderr={stderr_text}"
            elif stdout_text:
                tar_failure_message += f"; stdout={stdout_text}"
    else:
        tar_failure_message = "tar --zstd is unavailable"

    if not archive_path.exists():
        try:
            _pack_with_python_zstandard(
                archive_path=archive_path,
                run_root_path=run_root,
                tar_inputs=tar_inputs,
            )
        except RuntimeError as error:
            if tar_failure_message is None:
                tar_failure_message = "tar.zst packaging failed before archive creation"
            raise RuntimeError(
                f"{tar_failure_message}; python fallback requires the zstandard package"
            ) from error

    decision = str(checks_payload.get("RealVideoVaeLatentDecision", "INCONCLUSIVE")) or "INCONCLUSIVE"
    summary_payload = {
        "run_id": run_id,
        "construction_phase": run_manifest.get("construction_phase"),
        "decision": decision,
        "status": bool(checks_payload.get("status", False)),
        "archive_format": "tar.zst",
        "archive_path": str(archive_path),
        "summary_path": str(summary_path),
        "checks_path": str(checks_path),
        "runtime_profile_included": True,
    }
    summary_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checks_path.write_text(
        json.dumps(checks_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "archive_path": archive_path,
        "summary_path": summary_path,
        "checks_path": checks_path,
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

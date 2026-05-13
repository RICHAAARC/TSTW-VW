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

from experiments.real_video_vae_latent_probe.output_layout import (
    build_real_video_vae_latent_output_paths,
)
from scripts.package_results.drive_packager import pack_real_video_vae_latent_run


def build_family_package_manifest(
    *,
    family_id: str,
    run_id: str | None,
    construction_phase: str | None,
    package_format: str,
    package_path: str | Path,
    archive_format: str,
    archive_path: str | Path,
    summary_path: str | Path,
    checks_path: str | Path,
    runtime_profile_included: bool,
    compat_package_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build the canonical family package manifest payload.

    Args:
        family_id: Family identifier.
        run_id: Run identifier.
        construction_phase: Construction phase.
        package_format: Canonical package format.
        package_path: Canonical package path.
        archive_format: Canonical archive format.
        archive_path: Canonical archive path.
        summary_path: Summary path.
        checks_path: Checks path.
        runtime_profile_included: Whether runtime_profile is included.
        compat_package_path: Optional compatibility package path.

    Returns:
        A canonical family package manifest payload.
    """
    manifest_payload: dict[str, Any] = {
        "family_id": family_id,
        "run_id": run_id,
        "construction_phase": construction_phase,
        "package_format": package_format,
        "archive_format": archive_format,
        "package_path": str(package_path),
        "archive_path": str(archive_path),
        "summary_path": str(summary_path),
        "checks_path": str(checks_path),
        "runtime_profile_included": bool(runtime_profile_included),
    }
    if compat_package_path is not None:
        manifest_payload["compat_package_path"] = str(compat_package_path)
    return manifest_payload


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
    family_manifest = build_family_package_manifest(
        family_id=family_root_path.name,
        run_id=summary_payload.get("run_id"),
        construction_phase=summary_payload.get("construction_phase"),
        package_format="zip",
        package_path=package_payload["zip_path"],
        archive_format="zip",
        archive_path=package_payload["zip_path"],
        summary_path=package_payload["summary_path"],
        checks_path=package_payload["checks_path"],
        runtime_profile_included=True,
    )
    stage2_summary = _build_stage2_family_summary(run_root_path, checks_payload)
    family_summary = {
        "family_id": family_root_path.name,
        "drive_result_summary": summary_payload,
        "package_format": "zip",
        "archive_format": "zip",
        "package_path": str(package_payload["zip_path"]),
        "archive_path": str(package_payload["zip_path"]),
        "runtime_profile_dir": str(run_root_path / "runtime_profile"),
        **stage2_summary,
    }
    family_checks = {
        "status": bool(checks_payload.get("status", False)),
        "run_checks": checks_payload,
        "package_exists": package_payload["zip_path"].exists(),
        "runtime_profile_included": True,
    }
    family_manifest.update(stage2_summary)
    if stage2_summary.get("Stage2MechanismDecision") not in {None, "NOT_RUN"}:
        family_checks["stage2_mechanism_summary"] = _read_optional_stage2_mechanism_summary(
            run_root_path
        )

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


def _read_optional_stage2_mechanism_summary(run_root: Path) -> dict[str, Any] | None:
    output_paths = build_real_video_vae_latent_output_paths(run_root)
    if not output_paths.stage2_mechanism_decision_path.exists():
        return None
    return json.loads(output_paths.stage2_mechanism_decision_path.read_text(encoding="utf-8"))


def _build_stage2_family_summary(
    run_root: Path,
    checks_payload: dict[str, Any],
) -> dict[str, Any]:
    mechanism_summary = _read_optional_stage2_mechanism_summary(run_root)
    summary_payload = {
        "Stage2ImplementationDecision": checks_payload.get(
            "Stage2ImplementationDecision",
            checks_payload.get("RealVideoVaeLatentDecision", "INCONCLUSIVE"),
        ),
        "NextAllowedStageByImplementation": checks_payload.get(
            "NextAllowedStageByImplementation",
            checks_payload.get("NextAllowedStage", "remain_in_real_video_vae_latent_probe"),
        ),
    }
    if mechanism_summary is None:
        summary_payload.update(
            {
                "Stage2MechanismDecision": "NOT_RUN",
                "Stage2MechanismBlockingReasons": ["stage2_mechanism_audit_missing"],
                "NextAllowedStageByMechanism": "remain_in_real_video_vae_latent_probe",
                "RecommendedNextAction": "run_stage2_mechanism_audit",
            }
        )
        return summary_payload
    for field_name in (
        "Stage2ImplementationDecision",
        "Stage2MechanismDecision",
        "Stage2MechanismBlockingReasons",
        "Stage2MechanismWarnings",
        "NextAllowedStageByImplementation",
        "NextAllowedStageByMechanism",
        "RecommendedNextAction",
        "quality_metrics_enabled",
        "temporal_metrics_enabled",
    ):
        if field_name in mechanism_summary:
            summary_payload[field_name] = mechanism_summary[field_name]
    return summary_payload


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

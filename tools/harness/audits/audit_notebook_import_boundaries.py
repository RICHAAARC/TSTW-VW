"""
文件用途：审计 notebook import 边界，不得回退到 main.colab 或旧 stage-specific main 路径。
File purpose: Audit notebook import boundaries so notebooks do not fall back to main.colab or legacy stage-specific main modules.
Module type: General module
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.file_scanner import iter_text_files, read_text
from tools.harness.lib.json_report import build_report, exit_with_report


FORBIDDEN_IMPORT_FRAGMENTS = {
    "main.colab": "notebook_must_not_import_main_colab",
    "main.protocol.real_video_vae_latent_runner": "notebook_must_use_experiments_runner",
    "main.analysis.real_video_vae_latent_artifacts": "notebook_must_use_experiments_artifact_builder",
    "colab_runtime_manifest.json": "notebook_must_use_runtime_manifest_name",
    "colab_real_video_vae_latent_runtime_config.json": "notebook_must_use_runtime_config_name",
    "colab_runtime_manifest_overrides": "notebook_must_use_runtime_manifest_overrides_name",
}


def _extract_sources(notebook_text: str) -> list[str]:
    try:
        payload = json.loads(notebook_text)
    except json.JSONDecodeError:
        return [notebook_text]
    sources: list[str] = []
    for cell in payload.get("cells", []):
        if not isinstance(cell, dict):
            continue
        source = cell.get("source", [])
        if isinstance(source, list):
            sources.append("".join(str(line) for line in source))
        elif isinstance(source, str):
            sources.append(source)
    return sources


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the notebook import-boundary audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized audit report.
    """
    root_path = Path(root)
    checked_paths: list[str] = []
    violations: list[dict[str, Any]] = []

    for file_path in iter_text_files(root_path / "paper_workflow"):
        if file_path.suffix.lower() != ".ipynb":
            continue
        checked_paths.append(str(file_path))
        notebook_sources = _extract_sources(read_text(file_path))
        notebook_text = "\n".join(notebook_sources).lower()
        for fragment, reason in FORBIDDEN_IMPORT_FRAGMENTS.items():
            if fragment not in notebook_text:
                continue
            violations.append(
                {
                    "path": str(file_path),
                    "reason": reason,
                    "fragment": fragment,
                }
            )

    decision = "fail" if violations else "pass"
    return build_report(
        audit_name="audit_notebook_import_boundaries",
        decision=decision,
        violations=violations,
        checked_paths=checked_paths,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the audit as a CLI.

    Args:
        argv: Optional CLI argument list.

    Returns:
        None.
    """
    arguments = argv or sys.argv
    root = Path(arguments[1]) if len(arguments) > 1 else ROOT
    exit_with_report(run_audit(root))


if __name__ == "__main__":
    main(sys.argv)
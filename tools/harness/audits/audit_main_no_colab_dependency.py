"""
文件用途：审计 main 目录不得依赖 Colab、Drive 或 paper_workflow。
File purpose: Audit that main does not depend on Colab, Drive paths, or paper_workflow wrappers.
Module type: General module
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.harness.lib.file_scanner import iter_text_files, read_text
from tools.harness.lib.json_report import build_report, exit_with_report


FORBIDDEN_FRAGMENTS = {
    "from google.colab import": "main_imports_google_colab",
    "import google.colab": "main_imports_google_colab",
    "/content/drive": "main_hardcodes_drive_path",
    "mydrive": "main_hardcodes_drive_path",
    "main.colab": "main_depends_on_main_colab",
    "paper_workflow": "main_depends_on_paper_workflow",
    "colab_runtime_manifest": "main_uses_legacy_colab_runtime_field",
    "colab_real_video_vae_latent_runtime_config": "main_uses_legacy_colab_runtime_field",
}


def run_audit(root: str | Path) -> dict[str, Any]:
    """Run the main no-Colab-dependency audit.

    Args:
        root: Repository root path.

    Returns:
        A normalized audit report.
    """
    root_path = Path(root)
    main_root = root_path / "main"
    checked_paths: list[str] = []
    violations: list[dict[str, Any]] = []

    if main_root.exists():
        for file_path in iter_text_files(main_root):
            checked_paths.append(str(file_path))
            text = read_text(file_path).lower()
            for fragment, reason in FORBIDDEN_FRAGMENTS.items():
                if fragment not in text:
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
        audit_name="audit_main_no_colab_dependency",
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
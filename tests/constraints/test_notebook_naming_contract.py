"""
文件用途：验证 notebook 命名与 helper 归属审计行为。
File purpose: Validate the notebook naming and helper-placement audit behavior.
Module type: General module
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

from pathlib import Path

from tools.harness.audits.audit_notebook_naming_contract import run_audit


def _write_text(path: Path, text: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _create_governed_notebook_layout(root: Path) -> None:
    _write_text(root / "paper_workflow" / "build_processed_real_video_dataset.ipynb", "{}\n")
    _write_text(root / "paper_workflow" / "run_real_video_vae_latent_probe.ipynb", "{}\n")
    _write_text(root / "paper_workflow" / "colab_utils" / "runtime_check.py", "pass\n")
    _write_text(root / "paper_workflow" / "colab_utils" / "tar_zst_packager.py", "pass\n")
    _write_text(root / "paper_workflow" / "colab_utils" / "__init__.py", "\"\"\"pkg\"\"\"\n")
    _write_text(root / "paper_workflow" / "notebook_utils" / "__init__.py", "\"\"\"pkg\"\"\"\n")
    _write_text(root / "paper_workflow" / "notebook_utils" / "real_video_vae_latent_helper.py", "pass\n")


def test_notebook_naming_audit_accepts_governed_layout(tmp_path: Path) -> None:
    """Validate the audit accepts the governed notebook naming layout.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    _create_governed_notebook_layout(tmp_path)

    report = run_audit(tmp_path)

    assert report["decision"] == "pass"
    assert report["violations"] == []


def test_notebook_naming_audit_rejects_legacy_stage_notebook(tmp_path: Path) -> None:
    """Validate the audit rejects the legacy Stage2 notebook entrypoint.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    _create_governed_notebook_layout(tmp_path)
    _write_text(tmp_path / "paper_workflow" / "Stage2_Real_Video_VAE_Latent_Probe.ipynb")

    report = run_audit(tmp_path)

    assert report["decision"] == "fail"
    assert any(
        violation["reason"] == "forbidden_legacy_notebook_naming_path_present"
        for violation in report["violations"]
    )


def test_notebook_naming_audit_rejects_stage_token_helper_in_notebook_utils(tmp_path: Path) -> None:
    """Validate the audit rejects weak-stage helper names under notebook_utils.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    _create_governed_notebook_layout(tmp_path)
    _write_text(
        tmp_path / "paper_workflow" / "notebook_utils" / "stage2_real_video_vae_latent_probe_result_checker.py",
        "pass\n",
    )

    report = run_audit(tmp_path)

    assert report["decision"] == "fail"
    assert any(
        violation["reason"] == "notebook_utils_file_name_uses_forbidden_stage_token"
        for violation in report["violations"]
    )


def test_notebook_naming_audit_rejects_unexpected_root_notebook(tmp_path: Path) -> None:
    """Validate the audit rejects extra root notebooks beyond the governed pair.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    _create_governed_notebook_layout(tmp_path)
    _write_text(tmp_path / "paper_workflow" / "extra_workflow.ipynb", "{}\n")

    report = run_audit(tmp_path)

    assert report["decision"] == "fail"
    assert any(
        violation["reason"] == "unexpected_governed_root_notebook"
        for violation in report["violations"]
    )


def test_notebook_naming_audit_ignores_python_cache_directories(tmp_path: Path) -> None:
    """Validate the audit ignores Python cache directories under governed helper roots.

    Args:
        tmp_path: Temporary repository root.

    Returns:
        None.
    """
    _create_governed_notebook_layout(tmp_path)
    (tmp_path / "paper_workflow" / "colab_utils" / "__pycache__").mkdir(parents=True)
    (tmp_path / "paper_workflow" / "notebook_utils" / "__pycache__").mkdir(parents=True)

    report = run_audit(tmp_path)

    assert report["decision"] == "pass"
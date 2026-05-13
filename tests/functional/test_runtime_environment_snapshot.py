"""
文件用途：验证 runtime environment snapshot 脚本在无 GPU 环境下的输出合同。
File purpose: Validate runtime environment snapshot contracts under a no-GPU environment.
Module type: Functional test module
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

import scripts.profile_runtime.capture_colab_environment as snapshot_module


pytestmark = pytest.mark.quick


class _FakeCuda:
    def is_available(self) -> bool:
        return False

    def device_count(self) -> int:
        return 0


def test_capture_colab_environment_without_gpu(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate environment snapshot generation succeeds without a GPU.

    Args:
        tmp_path: Temporary run root.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        None.
    """
    run_root = tmp_path / "run_root"
    output_json = run_root / "runtime_profile" / "colab_environment_snapshot.json"

    def fake_import_module(module_name: str) -> types.SimpleNamespace:
        if module_name == "torch":
            return types.SimpleNamespace(__version__="2.3.1", cuda=_FakeCuda())
        if module_name in {"diffusers", "lpips", "cv2", "skimage", "imageio", "numpy", "pandas"}:
            return types.SimpleNamespace(__version__="1.0.0")
        if module_name == "psutil":
            return types.SimpleNamespace(
                virtual_memory=lambda: types.SimpleNamespace(
                    total=16 * 1024 * 1024 * 1024,
                    available=10 * 1024 * 1024 * 1024,
                )
            )
        raise ModuleNotFoundError(module_name)

    def fake_version(package_name: str) -> str:
        return f"{package_name}-version"

    def fake_which(command_name: str) -> str | None:
        if command_name in {"ffmpeg", "tar", "git"}:
            return f"/usr/bin/{command_name}"
        return None

    def fake_check_output(command: list[str], **_: object) -> str:
        if command[:2] == ["/usr/bin/ffmpeg", "-version"]:
            return "ffmpeg version 6.1\n"
        if command[:2] == ["/usr/bin/tar", "--help"]:
            return "tar help text with --zstd support\n"
        if command[0] == "/usr/bin/git" and command[-2:] == ["rev-parse", "HEAD"]:
            return "abc123def456\n"
        if command[0] == "/usr/bin/git" and command[-2:] == ["status", "--short"]:
            return " M notebook.ipynb\n"
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(snapshot_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(snapshot_module.importlib_metadata, "version", fake_version)
    monkeypatch.setattr(snapshot_module.shutil, "which", fake_which)
    monkeypatch.setattr(snapshot_module.subprocess, "check_output", fake_check_output)

    payload = snapshot_module.capture_colab_environment(
        run_root=run_root,
        run_id="runtime_profile_smoke",
        run_mode="smoke",
        runtime_profile="debug_real_video",
        output_json=output_json,
    )

    persisted_payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] is True
    assert payload["cuda_available"] is False
    assert payload["ffmpeg_available"] is True
    assert payload["dependency_imports"]["diffusers"] is True
    assert payload["dependency_imports"]["lpips"] is True
    assert payload["dependency_imports"]["cv2"] is True
    assert payload["disk_free_gb"] > 0.0
    assert payload["output_json"] == str(output_json)
    assert persisted_payload == payload

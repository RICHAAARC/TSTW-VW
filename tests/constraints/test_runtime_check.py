"""
文件用途：验证 Colab runtime 预检的版本、导入与 formal 阻断行为。
File purpose: Validate Colab runtime preflight version checks, imports, and formal blocking behavior.
Module type: General module
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

import paper_workflow.colab_utils.runtime_check as runtime_check


class _FakeCuda:
    def __init__(self, *, available: bool = True, gpu_name: str = "Fake GPU", total_memory: int = 8 * 1024 * 1024 * 1024) -> None:
        self._available = available
        self._gpu_name = gpu_name
        self._total_memory = total_memory

    def is_available(self) -> bool:
        return self._available

    def get_device_name(self, index: int) -> str:
        assert index == 0
        return self._gpu_name

    def get_device_properties(self, index: int) -> types.SimpleNamespace:
        assert index == 0
        return types.SimpleNamespace(total_memory=self._total_memory)


class _FakeTorchModule(types.SimpleNamespace):
    pass


def _build_fake_import(name: str, *, missing_lpips: bool = False) -> types.SimpleNamespace:
    if name == "torch":
        return _FakeTorchModule(__version__="2.3.1", cuda=_FakeCuda())
    if name == "diffusers":
        return types.SimpleNamespace(__version__="0.31.0")
    if name == "lpips":
        if missing_lpips:
            raise ModuleNotFoundError("No module named 'lpips'")
        return types.SimpleNamespace(__version__="0.1.4")
    if name == "cv2":
        return types.SimpleNamespace(__version__="4.10.0")
    if name == "skimage":
        return types.SimpleNamespace(__version__="0.24.0")
    raise ModuleNotFoundError(name)


def _patch_runtime_environment(monkeypatch: pytest.MonkeyPatch, *, missing_lpips: bool = False) -> None:
    def fake_which(command_name: str) -> str | None:
        if command_name in {"ffmpeg", "tar", "nvidia-smi"}:
            return f"/usr/bin/{command_name}"
        return None

    def fake_check_output(command: list[str], text: bool = True) -> str:
        if command[:2] == ["/usr/bin/ffmpeg", "-version"]:
            return "ffmpeg version 6.1\n"
        if command[0] == "/usr/bin/tar" and command[1] == "--help":
            return "tar help text --zstd supported\n"
        if command[:2] == ["nvidia-smi", "--query-gpu=name"]:
            return "Fake GPU\n"
        raise AssertionError(f"unexpected command: {command!r}")

    def fake_import(module_name: str):
        return _build_fake_import(module_name, missing_lpips=missing_lpips)

    monkeypatch.setattr(runtime_check.shutil, "which", fake_which)
    monkeypatch.setattr(runtime_check.subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(runtime_check.importlib, "import_module", fake_import)


def test_runtime_preflight_report_contains_dependency_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate that the runtime preflight report records P10 dependency metadata.

    Args:
        tmp_path: Temporary directory root.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        None.
    """
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    (dataset_dir / "sample.mp4").write_bytes(b"fake-mp4")

    vae_dir = tmp_path / "models" / "vae"
    lpips_dir = tmp_path / "models" / "lpips"
    vae_dir.mkdir(parents=True, exist_ok=True)
    lpips_dir.mkdir(parents=True, exist_ok=True)
    (vae_dir / "weights.bin").write_bytes(b"weights")
    (lpips_dir / "weights.bin").write_bytes(b"weights")

    _patch_runtime_environment(monkeypatch)

    report = runtime_check.run_runtime_preflight_check(
        run_mode="formal",
        local_dataset_dir=dataset_dir,
        local_model_dirs=[vae_dir, lpips_dir],
    )

    assert report["python_version"]
    assert report["torch_imported"] is True
    assert report["torch_version"] == "2.3.1"
    assert report["cuda_available"] is True
    assert report["gpu_name"] == "Fake GPU"
    assert report["gpu_memory_mb"] == 8192
    assert report["ffmpeg_available"] is True
    assert report["ffmpeg_version"] == "ffmpeg version 6.1"
    assert report["tar_zstd_available"] is True
    assert report["dependency_imports"]["diffusers"] is True
    assert report["dependency_imports"]["lpips"] is True
    assert report["dependency_imports"]["cv2"] is True
    assert report["dependency_imports"]["skimage"] is True
    assert report["dependency_versions"]["diffusers"] == "0.31.0"
    assert report["dependency_versions"]["lpips"] == "0.1.4"
    assert report["dataset_mp4_count"] == 1
    assert len(report["model_dirs"]) == 2
    assert all(entry["ready"] for entry in report["model_dirs"])


def test_runtime_preflight_formal_rejects_missing_lpips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate that formal preflight fails when LPIPS cannot be imported.

    Args:
        tmp_path: Temporary directory root.
        monkeypatch: Pytest monkeypatch helper.

    Returns:
        None.
    """
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    (dataset_dir / "sample.mp4").write_bytes(b"fake-mp4")

    vae_dir = tmp_path / "models" / "vae"
    lpips_dir = tmp_path / "models" / "lpips"
    vae_dir.mkdir(parents=True, exist_ok=True)
    lpips_dir.mkdir(parents=True, exist_ok=True)
    (vae_dir / "weights.bin").write_bytes(b"weights")
    (lpips_dir / "weights.bin").write_bytes(b"weights")

    _patch_runtime_environment(monkeypatch, missing_lpips=True)

    with pytest.raises(RuntimeError, match="required python dependencies are unavailable: lpips"):
        runtime_check.run_runtime_preflight_check(
            run_mode="formal",
            local_dataset_dir=dataset_dir,
            local_model_dirs=[vae_dir, lpips_dir],
        )

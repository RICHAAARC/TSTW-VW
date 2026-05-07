"""
文件用途：验证 stage-one runtime 不依赖真实视频生成模型栈。
File purpose: Validate that the stage-one runtime has no real video model dependency.
Module type: General module
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = ROOT / "main"
FORBIDDEN_IMPORT_ROOTS = {
    "diffusers",
    "transformers",
}
FORBIDDEN_RUNTIME_SYMBOLS = {
    "AutoencoderKL",
    "DiT",
    "FlowMatching",
    "VAE",
    "from_pretrained",
}


def _iter_main_python_files() -> list[Path]:
    return sorted(MAIN_ROOT.rglob("*.py"))


def _parse_python_file(file_path: Path) -> ast.AST:
    return ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))


def test_stage1_has_no_real_dit_flow_vae_runtime_dependency() -> None:
    """Validate that `main/` does not import or call real model backends.

    Args:
        None.

    Returns:
        None.
    """
    violations: list[tuple[str, str]] = []
    for file_path in _iter_main_python_files():
        tree = _parse_python_file(file_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_root = alias.name.split(".")[0]
                    if import_root in FORBIDDEN_IMPORT_ROOTS:
                        violations.append((str(file_path), alias.name))
            if isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                import_root = module_name.split(".")[0]
                if import_root in FORBIDDEN_IMPORT_ROOTS:
                    violations.append((str(file_path), module_name))
                for alias in node.names:
                    if alias.name in FORBIDDEN_RUNTIME_SYMBOLS:
                        violations.append((str(file_path), alias.name))
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_RUNTIME_SYMBOLS:
                violations.append((str(file_path), node.id))
            if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_RUNTIME_SYMBOLS:
                violations.append((str(file_path), node.attr))

    assert violations == []

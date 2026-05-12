"""
文件用途：根据 pytest 收集结果重建测试清单文档。
File purpose: Rebuild the test inventory document from pytest collection output.
Module type: General module
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MARKER_PATTERN = re.compile(r"pytest\.mark\.([a-z_]+)")
PYTEST_NODE_PATTERN = re.compile(r"^(?P<path>tests/.+?\.py)::")


def _run_collect(marker_expression: str | None = None) -> list[str]:
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    if marker_expression is not None:
        command.extend(["-m", marker_expression])
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if "::" in line and line.strip().startswith("tests/")
    ]


def _counts_by_file(nodes: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for node in nodes:
        match = PYTEST_NODE_PATTERN.match(node)
        if match:
            counts[match.group("path")] += 1
    return counts


def _test_files() -> list[Path]:
    return sorted((ROOT / "tests").glob("**/test_*.py"))


def _layer_for(path: Path) -> str:
    parts = path.relative_to(ROOT).parts
    return parts[1] if len(parts) > 2 else "root"


def _summary_from_docstring(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return ""
    docstring = ast.get_docstring(tree) or ""
    for line in docstring.splitlines():
        line = line.strip()
        if line.startswith("File purpose:"):
            return line.removeprefix("File purpose:").strip()
        if line.startswith("文件用途："):
            return line.removeprefix("文件用途：").strip()
    return docstring.splitlines()[0].strip() if docstring.splitlines() else ""


def _markers_for(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return sorted(set(MARKER_PATTERN.findall(text)) & {
        "unit",
        "constraint",
        "quick",
        "integration",
        "smoke",
        "slow",
        "formal",
    })


def _resource_flags(path: Path, markers: list[str]) -> tuple[str, str, str]:
    text = path.read_text(encoding="utf-8").lower()
    uses_io = any(token in text for token in ("tmp_path", "tmp_path_factory", "write_text", "write_video_mp4", "run_root"))
    external = any(token in text for token in ("subprocess", "ffmpeg", "tar --zstd", "shutil.which"))
    model_or_data = any(token in text for token in ("vae", "model", "dataset", "mp4"))
    if "integration" in markers or "smoke" in markers or "formal" in markers:
        uses_io = True if uses_io or "integration" in markers else uses_io
    return (
        "yes" if uses_io else "no",
        "yes" if external else "no",
        "yes" if model_or_data else "no",
    )


def _markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    separator = ["---" for _ in header]
    rendered = ["| " + " | ".join(header) + " |", "| " + " | ".join(separator) + " |"]
    for row in rows[1:]:
        rendered.append("| " + " | ".join(cell.replace("\n", " ") for cell in row) + " |")
    return "\n".join(rendered)


def build_document() -> str:
    all_nodes = _run_collect("not __never__")
    default_nodes = _run_collect()
    all_counts = _counts_by_file(all_nodes)
    default_counts = _counts_by_file(default_nodes)
    total_count = len(all_nodes)
    default_count = len(default_nodes)
    excluded_count = total_count - default_count

    files = _test_files()
    layer_counts: dict[str, int] = defaultdict(int)
    layer_nodes: dict[str, int] = defaultdict(int)
    for path in files:
        relative_path = path.relative_to(ROOT).as_posix()
        layer = _layer_for(path)
        layer_counts[layer] += 1
        layer_nodes[layer] += all_counts.get(relative_path, 0)

    layer_rows = [["Layer", "Files", "Nodes", "Default role"]]
    for layer in ("constraints", "functional", "integration"):
        role = {
            "constraints": "default governance checks",
            "functional": "default quick behavior checks",
            "integration": "excluded runner/smoke/formal checks",
        }[layer]
        layer_rows.append([layer, str(layer_counts[layer]), str(layer_nodes[layer]), role])

    detail_rows = [[
        "Test file",
        "Nodes",
        "Layer",
        "Markers",
        "Default nodes",
        "I/O",
        "External",
        "Model/data",
        "Summary",
    ]]
    for path in files:
        relative_path = path.relative_to(ROOT).as_posix()
        markers = _markers_for(path)
        uses_io, external, model_or_data = _resource_flags(path, markers)
        detail_rows.append([
            f"`{relative_path}`",
            str(all_counts.get(relative_path, 0)),
            _layer_for(path),
            ", ".join(f"`{marker}`" for marker in markers) or "-",
            str(default_counts.get(relative_path, 0)),
            uses_io,
            external,
            model_or_data,
            _summary_from_docstring(path),
        ])

    return "\n".join(
        [
            "# 测试列表",
            "",
            "本文档由 `python tools/harness/update_test_list.py` 根据当前 pytest 收集结果重建。",
            "",
            "## 1. 当前测试执行口径",
            "",
            "- 测试根目录：`tests/`",
            "- 测试构建约束：`docs/test_case_constraints.md`",
            "- 当前 pytest 默认参数来自 `pyproject.toml`：`(constraint or unit or quick) and not integration and not smoke and not slow and not formal`",
            f"- 当前全量测试节点：{total_count} 个",
            f"- 当前默认会执行的测试节点：{default_count} 个",
            f"- 当前默认排除的测试节点：{excluded_count} 个",
            "",
            "## 2. 分层统计",
            "",
            _markdown_table(layer_rows),
            "",
            "## 3. 推荐执行命令",
            "",
            "```bash",
            "python -m pytest -q",
            "python -m pytest -q tests/constraints",
            "python -m pytest -q tests/functional -m \"unit or quick\"",
            "python -m pytest -q tests/integration -m \"smoke\" --collect-only",
            "python -m pytest -q -m \"formal\" --collect-only",
            "python tools/harness/run_all_audits.py",
            "```",
            "",
            "## 4. 测试文件清单",
            "",
            _markdown_table(detail_rows),
            "",
        ]
    )


def main() -> None:
    target = ROOT / "docs" / "test_list.md"
    target.write_text(build_document(), encoding="utf-8")


if __name__ == "__main__":
    main()
